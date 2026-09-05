"""AeroOps 시뮬레이터 진입점 (스텁).

2단계(`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day0304.md`)에서
원형·직선·경유지 비행 시나리오와 10대 x 1Hz 정상 데이터 생성, 중복·지연·
역순·GPS 점프·단절 오류 주입을 구현한다. seed와 scenario_id로 재현성을
확보한다.
"""
import typer

app = typer.Typer(help="AeroOps 드론 텔레메트리 시뮬레이터")


@app.command()
def run(
    seed: int = 42,
    num_drones: int = 10,
    frequency_hz: float = 1.0,
    scenario: str = "circle",
) -> None:
    """시뮬레이터를 실행한다 (현재는 스텁 — 2단계에서 구현).

    Args:
        seed: 재현성을 위한 난수 시드.
        num_drones: 시뮬레이션할 드론 수.
        frequency_hz: 텔레메트리 발행 주파수.
        scenario: 비행 시나리오 (circle | straight | waypoint).
    """
    typer.echo(
        f"[stub] seed={seed} num_drones={num_drones} "
        f"frequency_hz={frequency_hz} scenario={scenario}"
    )
    typer.echo("TODO: 2단계에서 TelemetryFrame 생성 및 POST /telemetry 전송 구현")


if __name__ == "__main__":
    app()
