"""AeroOps 시뮬레이터 진입점.

2단계(`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day0304.md`)의 원형·직선·경유지
시나리오, 10대 × 1Hz 정상 데이터 생성, 장애 주입, seed 재현성을 구현한다.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from itertools import zip_longest

import typer

from simulator.faults import FAULT_TYPES, apply_faults
from simulator.generator import build_fleet, generate_frames, scenario_run_id
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
    run_id = scenario_run_id(scenario, seed)
    typer.echo(
        f"[simulator] run_id={run_id} num_drones={num_drones} frequency_hz={frequency_hz} "
        f"duration_sec={duration_sec} faults={fault_types or '(none)'} sink={sink}"
    )

    fleet = build_fleet(seed=seed, num_drones=num_drones, scenario_name=scenario)
    start_time = datetime.now(timezone.utc)

    per_drone_streams: list[list] = []
    for drone in fleet:
        frames = generate_frames(
            drone, start_time=start_time, frequency_hz=frequency_hz, duration_s=duration_sec
        )
        if fault_types:
            frames = apply_faults(frames, fault_types, drone.rng)
        per_drone_streams.append(frames)

    sink_impl = _build_sink(sink, ingest_url)
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
