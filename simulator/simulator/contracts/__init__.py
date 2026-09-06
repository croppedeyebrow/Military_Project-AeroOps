"""TelemetryFrame 계약(시뮬레이터 측 구현).

backend와 독립적으로 구현하는 이유는
`docs/decisions/0002-telemetry-contract-duplication.md` 참고.
"""
from simulator.contracts.telemetry import FlightMode, TelemetryFrame

__all__ = ["FlightMode", "TelemetryFrame"]
