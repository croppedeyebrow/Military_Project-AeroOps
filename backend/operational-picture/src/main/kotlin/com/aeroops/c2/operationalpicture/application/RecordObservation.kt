package com.aeroops.c2.operationalpicture.application

import com.aeroops.c2.operationalpicture.domain.Observation
import org.springframework.stereotype.Service

/**
 * 관측 한 건을 받아들이는 유스케이스.
 *
 * 왜 저장소를 그냥 부르지 않고 한 겹을 두나: 지금은 저장만 하지만, 이 지점이 **"관측을 받아들일 때 해야
 * 하는 일"이 모이는 자리**다. 앞으로 ① 관측 이벤트 발행(Outbox, 4단계에서 Incident·Readiness가 구독),
 * ② 수신량·품질 메트릭, ③ 재동기화 판단이 여기 붙는다. 입구가 여러 개(Redis 소비, 나중에 Rust Gateway
 * 직접 수신)가 되어도 규칙은 한 곳에 있어야 갈라지지 않는다.
 *
 * 연관 코드: 저장 포트는 [ObservationStore], 호출부는 `adapter.inbound.TelemetryStreamConsumer`,
 * 도메인 규칙은 `domain.AssetSnapshot.apply`.
 */
@Service
class RecordObservation(private val store: ObservationStore) {

    /**
     * 관측을 저장하고 최신 상태에 반영한다.
     *
     * 반환값의 두 판정([ObservationIngestResult])은 호출부가 "중복이었는지", "최신 상태가 바뀌었는지"를
     * 기록·집계하는 데 쓴다. Golden Replay가 이 수치를 legacy와 비교한다.
     */
    fun handle(observation: Observation): ObservationIngestResult = store.record(observation)
}
