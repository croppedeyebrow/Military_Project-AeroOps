package com.aeroops.c2.operationalpicture.domain

import com.aeroops.c2.shared.AssetId
import com.aeroops.c2.shared.BootId

/**
 * 관측 1건의 멱등 키 — "같은 관측인가?"를 판정하는 정체성.
 *
 * 왜 만드나(근거): legacy는 `(asset_id, sequence_no)`로 중복을 판정해서, 기체를 재부팅하면
 * `sequence_no`가 0부터 다시 시작해 새 프레임이 전부 "중복"으로 버려졌다(ADR 0005 §배경).
 * 키에 `bootId`를 넣으면 "부팅 A의 0번"과 "부팅 B의 0번"이 서로 다른 관측으로 구분된다.
 *
 * 목적: 중복 판정 규칙을 한 타입에 모아, 저장·재동기화·재생이 같은 정체성 정의를 쓰게 한다.
 * `data class`라서 세 값이 모두 같을 때만 equals가 true다(= 중복).
 *
 * 연관 코드:
 * - 설계 근거: docs/decisions/0005-telemetry-boot-id.md (+ 시험 REQ-TEL-05, docs/planning/13 §5).
 * - 구성 요소: shared-kernel의 `AssetId`, `BootId`.
 * - 현행 대응: legacy-backend `telemetry/repository.py`의 `insert_raw_frame`(ON CONFLICT 키) —
 *   Kotlin에서는 이 타입이 같은 역할을 하고, DB 유일 제약은 Flyway에서 이 세 컬럼으로 만든다(2-3, ADR 0005
 *   "적용 시점 제약"에 따라 제약 교체는 3단계 승격 때).
 * - 도메인 레이어 규칙상 Spring·JPA를 알면 안 된다(bootstrap `LayeringRulesTest`).
 *
 * `sequenceNo`가 Long인 이유: legacy 계약은 0 이상의 정수이고 DB는 32비트 정수였다. Kotlin에서는
 * 오버플로 걱정 없이 Long으로 받고, 저장 시 범위는 Flyway 컬럼 타입이 정한다.
 */
data class ObservationKey(
    val assetId: AssetId,
    val bootId: BootId,
    val sequenceNo: Long,
) {
    init {
        // legacy 계약(TelemetryFrame.sequence_no: ge=0)과 같은 기준 — Golden Replay에서 같은 입력을
        // 같은 기준으로 받아야 하기 때문이다.
        require(sequenceNo >= 0) { "sequence_no는 0 이상이어야 한다: $sequenceNo" }
    }
}
