"""Golden Replay 실행기 — 같은 입력을 HTTP API에 넣고 최종 상태를 기준선과 비교한다.

목적(ADR 0004, `docs/new_roadmap/01_기준선과_전환계약_Day01.md`): 현행 FastAPI의 최종
Asset/Alert/Command/Audit 결과를 "정답"(golden)으로 고정하고, Kotlin C2 Core가 같은 입력에서
같은 결과를 내는지 비교한다. 구현 언어와 무관하도록 HTTP(`--base-url`)로만 호출한다.

입력은 시뮬레이터(`simulator/`)의 고정 seed·고정 시작 시각으로 결정적으로 생성한다. 실행마다
asset_id·command_id에 임의 태그를 붙여 이전 실행의 DB 잔여물과 섞이지 않게 하고, 결과를
정규화할 때 태그를 제거한다. 시각처럼 실행마다 달라지는 값은 결과에 넣지 않는다.

사용(시뮬레이터 venv 필요: numpy, httpx):
  python tests/contracts/replay/run_golden_replay.py --base-url http://localhost:8000          # 비교
  python tests/contracts/replay/run_golden_replay.py --base-url http://localhost:8000 --update # 기준선 갱신
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import zip_longest
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = REPO_ROOT / "tests" / "contracts" / "golden" / "fastapi_replay.json"
sys.path.insert(0, str(REPO_ROOT / "simulator"))

from simulator.faults import apply_faults, apply_packet_loss, apply_reorder_window  # noqa: E402
from simulator.generator import build_fleet, generate_frames  # noqa: E402

SEED = 42
NUM_DRONES = 3
DURATION_S = 60.0
FREQUENCY_HZ = 1.0
BASE_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
SETTLE_TIMEOUT_S = 90.0
COMMAND_TIMEOUT_WAIT_S = 45.0

# (이름, 장애 유형, 패킷 손실률, 재정렬 구간, 장애 파라미터). 시나리오마다 하루씩 다른
# event_time 구간을 써서 event-log 조회 범위가 서로 겹치지 않게 한다.
TELEMETRY_SCENARIOS: list[tuple[str, list[str], float, int, dict]] = [
    ("normal", [], 0.0, 0, {}),
    ("duplicate", ["duplicate"], 0.0, 0, {}),
    ("delay", ["delay"], 0.0, 0, {}),
    ("out_of_order", ["out_of_order"], 0.0, 0, {}),
    ("missing", ["missing"], 0.0, 0, {}),
    ("disconnect", ["disconnect"], 0.0, 0, {}),
    ("battery_drop", ["battery_drop"], 0.0, 0, {}),
    ("gps_jump", ["gps_jump"], 0.0, 0, {}),
    ("loss20", [], 0.2, 0, {}),
    ("reorder5", [], 0.0, 5, {}),
    # 기본 battery_drop(25%p)은 경보 임계값에 닿지 않아 경보 판정이 기준선에 안 잡힌다 —
    # 급락 폭을 키워 BATTERY_LOW 경보가 실제로 발생하는 경로를 고정한다.
    ("battery_low", ["battery_drop"], 0.0, 0, {"battery_drop": {"drop_pct": 85.0}}),
]


def _utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


class Runner:
    def __init__(self, base_url: str) -> None:
        self.http = httpx.Client(base_url=base_url, timeout=30.0)
        self.tag = f"gr{uuid.uuid4().hex[:8]}-"

    # ---- 입력 생성 ----
    def build_frames(
        self, index: int, faults: list[str], loss: float, window: int, fault_kwargs: dict
    ):
        fleet = build_fleet(seed=SEED, num_drones=NUM_DRONES, scenario_name="circle")
        start = BASE_START + timedelta(days=index)
        streams = []
        for drone in fleet:
            frames = generate_frames(
                drone, start_time=start, frequency_hz=FREQUENCY_HZ, duration_s=DURATION_S
            )
            if faults:
                frames = apply_faults(frames, faults, drone.rng, fault_kwargs=fault_kwargs)
            if loss > 0.0:
                frames = apply_packet_loss(frames, drone.rng, loss_rate=loss)
            if window > 1:
                frames = apply_reorder_window(frames, drone.rng, window_size=window)
            streams.append(frames)
        interleaved = []
        for round_frames in zip_longest(*streams, fillvalue=None):
            interleaved.extend(f for f in round_frames if f is not None)
        return start, interleaved

    # ---- 텔레메트리 시나리오 ----
    def run_telemetry(
        self, index: int, name: str, faults: list[str], loss: float, window: int, fault_kwargs: dict
    ):
        start, frames = self.build_frames(index, faults, loss, window, fault_kwargs)
        payloads = []
        for frame in frames:
            body = frame.model_dump(mode="json")
            body["asset_id"] = f"{self.tag}{name}-{body['asset_id']}"
            payloads.append(body)
        fingerprint = hashlib.sha256(
            json.dumps(
                [{**p, "asset_id": p["asset_id"].replace(self.tag, "")} for p in payloads],
                sort_keys=True,
            ).encode()
        ).hexdigest()

        statuses: Counter[int] = Counter()
        accepted = 0
        for body in payloads:
            response = self.http.post("/telemetry", json=body)
            statuses[response.status_code] += 1
            if response.status_code == 202:
                accepted += 1

        until = start + timedelta(hours=2)
        self._wait_event_log_count(name, start, until, accepted)

        assets = sorted({p["asset_id"] for p in payloads})
        event_log = self._telemetry_event_log(name, start, until)
        result_assets = {}
        for asset_id in assets:
            result_assets[asset_id.replace(self.tag, "")] = self._asset_result(
                asset_id, [e for e in event_log if e["payload"]["asset_id"] == asset_id]
            )
        return fingerprint, {
            "frames_posted": len(payloads),
            "post_status_counts": {str(k): v for k, v in sorted(statuses.items())},
            "assets": result_assets,
        }

    def _telemetry_event_log(self, name: str, start: datetime, until: datetime) -> list[dict]:
        response = self.http.get(
            "/event-log",
            params={
                "source_channel": "telemetry",
                "since": _utc(start - timedelta(seconds=1)),
                "until": _utc(until),
                "limit": 2000,
            },
        )
        response.raise_for_status()
        prefix = f"{self.tag}{name}-"
        return [
            e
            for e in response.json()
            if e["payload"] and str(e["payload"].get("asset_id", "")).startswith(prefix)
        ]

    def _wait_event_log_count(self, name: str, start: datetime, until: datetime, expected: int):
        deadline = time.monotonic() + SETTLE_TIMEOUT_S
        count = -1
        while time.monotonic() < deadline:
            count = len(self._telemetry_event_log(name, start, until))
            if count >= expected:
                return
            time.sleep(0.5)
        raise RuntimeError(f"[{name}] 처리 완료 대기 시간 초과: event_log {count}/{expected}")

    def _asset_result(self, asset_id: str, events: list[dict]) -> dict:
        latest_response = self.http.get(f"/assets/{asset_id}/latest")
        latest = None
        if latest_response.status_code == 200:
            body = latest_response.json()
            latest = {
                "sequence_no": body["sequence_no"],
                "event_time": body["event_time"],
                "latitude": _round(body["latitude"]),
                "longitude": _round(body["longitude"]),
                "altitude_m": _round(body["altitude_m"]),
                "battery_pct": _round(body["battery_pct"]),
                "flight_mode": body.get("flight_mode"),
            }
        history = self.http.get(f"/assets/{asset_id}/telemetry", params={"limit": 1000}).json()
        alerts = self.http.get("/alerts", params={"asset_id": asset_id}).json()
        return {
            "latest": latest,
            "stored_frames": history["count"],
            "stored_sequence_nos": sorted(i["sequence_no"] for i in history["items"]),
            "event_log": {
                "total": len(events),
                "duplicates": sum(1 for e in events if not e["payload"]["is_new"]),
                "not_advancing_latest": sum(
                    1 for e in events if e["payload"]["is_new"] and not e["payload"]["latest_updated"]
                ),
            },
            "alerts": sorted(
                [a["alert_type"], a["severity"], a["status"], a["evidence"].get("sequence_no")]
                for a in alerts
            ),
        }

    # ---- 명령 시나리오 ----
    def _command_body(self, name: str, asset_id: str, expires_in_s: float = 3600.0) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "command_id": f"{self.tag}{name}",
            "idempotency_key": f"{self.tag}{name}",
            "target_asset_id": asset_id,
            "command_type": "LOITER",
            "payload": {},
            "requested_by": "operator-1",
            "issued_at": _utc(now),
            "expires_at": _utc(now + timedelta(seconds=expires_in_s)),
        }

    def run_commands(self, asset_id: str) -> dict:
        steps_by_command: dict[str, list[list]] = {}

        def call(name: str, label: str, method: str, path: str, body: dict | None = None):
            response = self.http.request(method, path, json=body)
            steps_by_command.setdefault(name, []).append([label, response.status_code])
            return response

        def cid(name: str) -> str:
            return f"{self.tag}{name}"

        def approve(name: str, who: str = "approver-1", label: str = "approve"):
            return call(name, label, "POST", f"/commands/{cid(name)}/approve", {"approved_by": who})

        def create(
            name: str,
            expires_in_s: float = 3600.0,
            label: str = "create",
            overrides: dict | None = None,
        ):
            body = {**self._command_body(name, asset_id, expires_in_s), **(overrides or {})}
            return call(name, label, "POST", "/commands", body)

        def step(name: str, action: str):
            return call(name, action, "POST", f"/commands/{cid(name)}/{action}")

        # 1) 정상 수명주기
        create("success")
        approve("success")
        step("success", "ack")
        step("success", "execute")
        call("success", "result", "POST", f"/commands/{cid('success')}/result", {"outcome": "SUCCEEDED"})
        # 2) 요청자 본인 승인 거부 후 정상 승인
        create("self_approve")
        approve("self_approve", who="operator-1", label="approve_self")
        approve("self_approve")
        # 3) 같은 idempotency_key 재요청은 명령을 하나만 만든다
        create("idempotent")
        create("idempotent", label="create_again")
        # 4) 취소 후 승인 불가
        create("cancel")
        call("cancel", "cancel", "POST", f"/commands/{cid('cancel')}/cancel", {"cancelled_by": "operator-1"})
        approve("cancel", label="approve_after_cancel")
        # 5) 승인 전 ACK는 불법 전이
        create("illegal")
        step("illegal", "ack")
        # 6) 실행 실패 보고
        create("failed")
        approve("failed")
        step("failed", "ack")
        step("failed", "execute")
        call("failed", "result", "POST", f"/commands/{cid('failed')}/result", {"outcome": "FAILED"})
        # 8) 같은 키·command_id에 다른 command_type으로 재요청하면 409(조용히 기존 명령을 돌려주지 않는다)
        create("conflict_type")
        create("conflict_type", label="create_other_type", overrides={"command_type": "RTL"})
        # 9) 다른 idempotency_key로 이미 있는 command_id를 쓰면 409(500이 아니다)
        create("conflict_id")
        create(
            "conflict_id",
            label="create_other_key",
            overrides={"idempotency_key": f"{self.tag}conflict_id_other_key"},
        )
        # 7) ACK 손실: 승인·전달 후 ACK가 오지 않으면 만료 시 TIMED_OUT
        create("ack_lost", expires_in_s=4.0)
        approve("ack_lost")
        self._wait_status("ack_lost", {"TIMED_OUT"})

        result = {}
        for name, steps in steps_by_command.items():
            detail = self.http.get(f"/commands/{cid(name)}")
            audit = self.http.get(
                "/audit-logs", params={"target_type": "command", "target_id": cid(name)}
            ).json()
            body = detail.json() if detail.status_code == 200 else {}
            result[name] = {
                "steps": steps,
                "final_status": body.get("status"),
                "events": [[e["event_type"], e["actor"]] for e in body.get("events", [])],
                "audit": sorted([a["action"], a["actor"], a["result"]] for a in audit),
            }
        return result

    def _wait_status(self, name: str, targets: set[str]) -> None:
        deadline = time.monotonic() + COMMAND_TIMEOUT_WAIT_S
        status = None
        while time.monotonic() < deadline:
            status = self.http.get(f"/commands/{self.tag}{name}").json().get("status")
            if status in targets:
                return
            time.sleep(1.0)
        raise RuntimeError(f"[{name}] 상태 {targets} 대기 시간 초과(현재 {status})")

    # ---- 전체 ----
    def run_all(self) -> dict:
        fingerprints, scenarios = {}, {}
        first_asset = None
        for index, (name, faults, loss, window, kwargs) in enumerate(TELEMETRY_SCENARIOS):
            fingerprint, result = self.run_telemetry(index, name, faults, loss, window, kwargs)
            fingerprints[name] = fingerprint
            scenarios[name] = result
            if first_asset is None:
                first_asset = f"{self.tag}{name}-drone-01"
            print(f"[replay] telemetry/{name}: posted={result['frames_posted']}", flush=True)
        commands = self.run_commands(first_asset)
        print(f"[replay] commands: {len(commands)} flows", flush=True)

        document = {
            "meta": {
                "seed": SEED,
                "num_drones": NUM_DRONES,
                "duration_s": DURATION_S,
                "frequency_hz": FREQUENCY_HZ,
                "scenario": "circle",
            },
            "input_fingerprints": fingerprints,
            "telemetry": scenarios,
            "commands": commands,
        }
        # 태그는 임의값이라 결과에 남으면 실행마다 달라진다 — 모두 제거한다.
        return json.loads(json.dumps(document).replace(self.tag, ""))


def render(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--update", action="store_true", help="기준선 파일을 현재 결과로 덮어쓴다")
    parser.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    args = parser.parse_args()

    actual = render(Runner(args.base_url).run_all())
    if args.update:
        args.golden.parent.mkdir(parents=True, exist_ok=True)
        args.golden.write_text(actual, encoding="utf-8", newline="\n")
        print(f"기준선 갱신: {args.golden}")
        return 0

    expected = args.golden.read_text(encoding="utf-8")
    if actual == expected:
        print("Golden Replay 일치")
        return 0
    diff = difflib.unified_diff(
        expected.splitlines(), actual.splitlines(), "golden", "actual", lineterm="", n=2
    )
    print("\n".join(list(diff)[:200]))
    print("Golden Replay 불일치", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
