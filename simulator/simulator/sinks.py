"""전송 계층: 생성된 TelemetryFrame을 내보내는 목적지(Sink) 추상화.

3단계에서 backend에 `POST /telemetry`가 생기기 전에도 시뮬레이터를 독립적으로
검증할 수 있도록 sink를 분리한다(`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day0304.md`).
"""
from __future__ import annotations

import sys
from typing import Protocol

import httpx

from simulator.contracts.telemetry import TelemetryFrame


class Sink(Protocol):
    def send(self, frame: TelemetryFrame) -> None: ...

    def close(self) -> None: ...


class ListSink:
    """테스트/디버깅용: 전송 대신 메모리 리스트에 쌓는다."""

    def __init__(self) -> None:
        self.frames: list[TelemetryFrame] = []

    def send(self, frame: TelemetryFrame) -> None:
        self.frames.append(frame)

    def close(self) -> None:
        pass


class StdoutSink:
    """표준 출력으로 한 줄에 하나씩 JSON을 출력한다."""

    def send(self, frame: TelemetryFrame) -> None:
        sys.stdout.write(frame.model_dump_json() + "\n")

    def close(self) -> None:
        pass


class HttpSink:
    """backend 수집 엔드포인트(`POST /telemetry`)로 전송한다.

    3단계 이전에는 엔드포인트가 없으므로 전송 실패는 예외를 던지지 않고
    표준 에러에 경고만 남긴다 — 시뮬레이터 자체 검증(2단계)이 backend 가용성에
    의존하지 않게 하기 위함이다.
    """

    def __init__(self, ingest_url: str, timeout_s: float = 5.0) -> None:
        self._client = httpx.Client(timeout=timeout_s)
        self._url = ingest_url

    def send(self, frame: TelemetryFrame) -> None:
        try:
            response = self._client.post(self._url, json=frame.model_dump(mode="json"))
            if response.status_code >= 400:
                sys.stderr.write(
                    f"[simulator] {self._url} 응답 {response.status_code}: {response.text}\n"
                )
        except httpx.HTTPError as exc:
            sys.stderr.write(f"[simulator] {self._url} 전송 실패: {exc}\n")

    def close(self) -> None:
        self._client.close()
