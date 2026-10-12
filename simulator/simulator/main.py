"""AeroOps 시뮬레이터 진입점.

2단계(`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day03-04.md`)의 원형·직선·경유지
시나리오, 10대 × 1Hz 정상 데이터 생성, 장애 주입, seed 재현성을 구현한다.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from itertools import zip_longest

import typer

from simulator.device_loop import (
    DeviceCommandClient,
    DroneRuntimeState,
    advance_pose,
    build_frame,
    flight_mode_for,
    poll_and_apply_commands,
    report_completed_commands,
)
from simulator.faults import FAULT_TYPES, apply_faults, apply_packet_loss, apply_reorder_window
from simulator.generator import (
    BATTERY_DRAIN_PCT_PER_HOUR,
    RSSI_BASE_DBM,
    RSSI_JITTER_STD_DBM,
    build_fleet,
    generate_frames,
    scenario_run_id,
)
from simulator.sinks import HttpSink, Sink, StdoutSink

app = typer.Typer(help="AeroOps 드론 텔레메트리 시뮬레이터")


@app.callback()
def _callback() -> None:
    """`run` 서브커맨드를 강제하기 위한 콜백(명령이 하나뿐이어도 typer가 그룹으로 유지하게 한다)."""


def _parse_faults(faults: str) -> list[str]:
    fault_types = [f.strip() for f in faults.split(",") if f.strip()]
    unknown = [f for f in fault_types if f not in FAULT_TYPES]
    if unknown:
        raise typer.BadParameter(
            f"알 수 없는 장애 유형: {', '.join(unknown)} (지원: {', '.join(FAULT_TYPES)})"
        )
    return fault_types


def _build_sink(sink: str, ingest_url: str) -> Sink:
    if sink == "http":
        return HttpSink(ingest_url)
    if sink == "stdout":
        return StdoutSink()
    raise typer.BadParameter(f"알 수 없는 sink: {sink} (http|stdout 중 선택)")


def _derive_api_base_url(ingest_url: str) -> str:
    """`http://host:port/telemetry` -> `http://host:port`. 명령 API(`/commands`,
    `/commands/{id}/ack` 등)는 수집 API(`/telemetry`)와 같은 서버·포트를 쓰므로,
    `--ingest-url` 하나로 둘 다 유도한다 — 옵션을 따로 받지 않아도 되게 한다."""
    return ingest_url.rsplit("/telemetry", 1)[0] if ingest_url.endswith("/telemetry") else ingest_url


def _run_reactive(
    fleet: list,
    *,
    frequency_hz: float,
    duration_sec: float,
    start_time: datetime,
    sink_impl: Sink,
    ingest_url: str,
) -> int:
    """실시간 반응형 루프 — 한 틱씩 자세를 계산해 보내면서, 매 틱 명령도 확인해 반영한다
    (`device_loop.py`). 사전계산(`generate_frames`) 경로와 달리 "다음 틱에 무슨 일이
    생길지"가 이전 틱 결과(명령 수신 여부)에 달려 있어 미리 계산해둘 수 없다.
    """
    dt = 1.0 / frequency_hz
    num_ticks = int(duration_sec * frequency_hz)
    client = DeviceCommandClient(_derive_api_base_url(ingest_url))
    states = {
        drone.asset_id: DroneRuntimeState(
            config=drone,
            lat=drone.scenario.pose_at(0.0).latitude,
            lon=drone.scenario.pose_at(0.0).longitude,
            alt=drone.scenario.pose_at(0.0).altitude_m,
        )
        for drone in fleet
    }

    sent = 0
    try:
        for seq in range(num_ticks):
            t = seq * dt
            now = start_time + timedelta(seconds=t)

            poll_and_apply_commands(client, states)

            for drone in fleet:
                state = states[drone.asset_id]
                pose = advance_pose(state, t, dt)
                battery_pct = max(
                    0.0,
                    drone.start_battery_pct - BATTERY_DRAIN_PCT_PER_HOUR * (t / 3600.0),
                )
                rssi = float(RSSI_BASE_DBM + drone.rng.normal(0, RSSI_JITTER_STD_DBM))
                rssi = min(0.0, max(-130.0, rssi))
                frame = build_frame(
                    drone,
                    pose,
                    seq=seq,
                    event_time=now,
                    battery_pct=battery_pct,
                    rssi_dbm=rssi,
                    flight_mode=flight_mode_for(state),
                )
                sink_impl.send(frame)
                sent += 1

            report_completed_commands(client, states)
            time.sleep(dt)
    finally:
        client.close()
    return sent


@app.command()
def run(
    seed: int = typer.Option(42, envvar="SIMULATOR_SEED", help="재현성을 위한 난수 시드"),
    num_drones: int = typer.Option(10, envvar="NUM_DRONES", help="시뮬레이션할 드론 수"),
    frequency_hz: float = typer.Option(1.0, envvar="FREQUENCY_HZ", help="텔레메트리 발행 주파수"),
    scenario: str = typer.Option("circle", help="비행 시나리오 (circle|straight|waypoint)"),
    duration_sec: float = typer.Option(60.0, help="생성할 시뮬레이션 구간 길이(초)"),
    faults: str = typer.Option(
        "", help=f"쉼표로 구분된 장애 유형(비우면 정상 데이터만). 지원: {', '.join(FAULT_TYPES)}"
    ),
    delay_min_shift: int = typer.Option(5, help="delay 장애: 최소 지연 칸수"),
    delay_max_shift: int | None = typer.Option(None, help="delay 장애: 최대 지연 칸수(비우면 무제한)"),
    disconnect_min_duration: int = typer.Option(5, help="disconnect 장애: 최소 단절 구간 길이(틱)"),
    disconnect_max_duration: int = typer.Option(15, help="disconnect 장애: 최대 단절 구간 길이(틱)"),
    gps_jump_min_m: float = typer.Option(5000.0, help="gps_jump 장애: 최소 점프 거리(m)"),
    battery_drop_pct: float = typer.Option(25.0, help="battery_drop 장애: 급락 폭(%p)"),
    loss_rate: float = typer.Option(
        0.0, min=0.0, max=1.0, help="프레임별 독립 손실 확률(0~1). --faults와 별개로 적용된다"
    ),
    reorder_window: int = typer.Option(
        0, min=0, help="이 크기의 구간 단위로 순서를 섞는다(0 또는 1이면 미적용)"
    ),
    sink: str = typer.Option("http", envvar="SIMULATOR_SINK", help="전송 목적지 (http|stdout)"),
    ingest_url: str = typer.Option(
        "http://localhost:8000/telemetry", envvar="INGEST_URL", help="수집 API 엔드포인트"
    ),
    real_time: bool = typer.Option(
        True, help="frequency_hz 속도로 실시간 페이싱할지 여부(false면 즉시 모두 전송)"
    ),
) -> None:
    """시뮬레이터를 실행해 편대 텔레메트리를 생성·전송한다."""
    fault_types = _parse_faults(faults)
    fault_kwargs = {
        "delay": {"min_shift": delay_min_shift, "max_shift": delay_max_shift},
        "disconnect": {"min_gap": disconnect_min_duration, "max_gap": disconnect_max_duration},
        "gps_jump": {"min_jump_m": gps_jump_min_m},
        "battery_drop": {"drop_pct": battery_drop_pct},
    }
    run_id = scenario_run_id(scenario, seed)

    # 실시간 + 장애 주입 없음일 때만 명령 반응형 루프를 쓴다. 장애 주입(disconnect/
    # gps_jump 등)과 재정렬은 "미리 계산해둔 전체 시퀀스를 변형"하는 방식이라, "한 틱씩
    # 그때그때 계산하며 명령을 끼워 넣는" 반응형 루프와 같이 쓸 수 없다(2026-10-12,
    # 사용자가 RTL을 보냈는데 드론이 반응하지 않는다고 보고해서 반응형 루프를 새로
    # 추가했다 — 기존 사전계산 경로는 장애 주입 테스트를 위해 그대로 남겨둔다).
    use_reactive = real_time and not fault_types and loss_rate == 0.0 and reorder_window <= 1
    typer.echo(
        f"[simulator] run_id={run_id} num_drones={num_drones} frequency_hz={frequency_hz} "
        f"duration_sec={duration_sec} faults={fault_types or '(none)'} loss_rate={loss_rate} "
        f"reorder_window={reorder_window} sink={sink} mode={'reactive' if use_reactive else 'precomputed'}"
    )

    fleet = build_fleet(seed=seed, num_drones=num_drones, scenario_name=scenario)
    start_time = datetime.now(timezone.utc)
    sink_impl = _build_sink(sink, ingest_url)

    if use_reactive:
        try:
            sent = _run_reactive(
                fleet,
                frequency_hz=frequency_hz,
                duration_sec=duration_sec,
                start_time=start_time,
                sink_impl=sink_impl,
                ingest_url=ingest_url,
            )
        finally:
            sink_impl.close()
        typer.echo(f"[simulator] 완료: {sent}건 전송")
        return

    per_drone_streams: list[list] = []
    for drone in fleet:
        frames = generate_frames(
            drone, start_time=start_time, frequency_hz=frequency_hz, duration_s=duration_sec
        )
        if fault_types:
            frames = apply_faults(frames, fault_types, drone.rng, fault_kwargs=fault_kwargs)
        if loss_rate > 0.0:
            frames = apply_packet_loss(frames, drone.rng, loss_rate=loss_rate)
        if reorder_window > 1:
            frames = apply_reorder_window(frames, drone.rng, window_size=reorder_window)
        per_drone_streams.append(frames)

    sent = 0
    try:
        interval_s = 1.0 / frequency_hz
        for round_frames in zip_longest(*per_drone_streams, fillvalue=None):
            for frame in round_frames:
                if frame is None:
                    continue
                sink_impl.send(frame)
                sent += 1
            if real_time:
                time.sleep(interval_s)
    finally:
        sink_impl.close()

    typer.echo(f"[simulator] 완료: {sent}건 전송")


if __name__ == "__main__":
    app()
