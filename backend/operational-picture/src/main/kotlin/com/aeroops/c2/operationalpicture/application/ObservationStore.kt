package com.aeroops.c2.operationalpicture.application

import com.aeroops.c2.operationalpicture.domain.AssetSnapshot
import com.aeroops.c2.operationalpicture.domain.Observation
import com.aeroops.c2.shared.AssetId

/**
 * 관측 저장소의 **포트**(application이 정의하고 adapter가 구현한다).
 *
 * 왜 인터페이스를 여기 두나(의존 역전): 유스케이스가 `JdbcObservationStore` 같은 구현을 직접 쥐면 저장소를
 * 바꿀 때 업무 흐름이 함께 흔들리고, 시험에서 가짜 저장소로 바꿔 끼울 수도 없다. ArchUnit 규칙
 * (`LayeringRules.applicationDoesNotDependOnAdapters`)이 이 방향을 강제한다.
 *
 * 연관 코드: 구현은 `adapter.outbound.JdbcObservationStore`, 사용처는 [RecordObservation],
 * 저장 대상 스키마는 Flyway `V3__operational_picture_shadow.sql`.
 */
interface ObservationStore {
    /**
     * 관측 하나를 저장하고 최신 상태에 반영한다. **이미 본 관측이면 아무것도 바꾸지 않는다.**
     *
     * 이 메서드가 돌려주는 두 가지 판정은 legacy의 `process_frame`이 돌려주던 것과 같은 의미다
     * (`legacy-backend/app/modules/telemetry/repository.py`). Golden Replay가 이 수치를 비교하므로
     * 의미가 어긋나면 전환 판정이 틀어진다.
     */
    fun record(observation: Observation): ObservationIngestResult

    /** 기체의 최신 상황. 없으면 null(아직 한 번도 보고받지 못한 기체). */
    fun findSnapshot(assetId: AssetId): AssetSnapshot?

    /** 전체 기체의 최신 상황(관제 화면의 초기 목록). */
    fun findAllSnapshots(): List<AssetSnapshot>
}

/**
 * 관측 한 건을 처리한 결과.
 *
 * 두 값이 따로인 이유(legacy와 같은 구분): 저장은 됐지만 최신 상태는 안 바뀔 수 있다. 늦게 도착한 과거
 * 관측이 그렇다 — 원본은 보존해야 하고(이력·재생), 최신 상태는 후퇴하면 안 된다
 * (docs/planning/13 불변조건 1). Golden Replay의 event-log 집계가 이 둘을 센다.
 */
data class ObservationIngestResult(
    /** 원본이 새로 저장됐는가. false면 이미 본 관측(중복)이다. */
    val isNew: Boolean,
    /** 최신 상태가 갱신됐는가. 중복이거나 과거 관측이면 false다. */
    val latestUpdated: Boolean,
)
