package com.aeroops.c2.shared

/**
 * 기체가 전원 투입·프로세스 시작마다 새로 만드는 부팅 식별자(ADR 0005).
 *
 * 목적: `sequence_no`는 같은 부팅 안에서만 단조 증가하고 재부팅하면 0부터 다시 시작한다. 그래서
 * 중복 판정 키는 `(assetId, bootId, sequenceNo)`다. 부팅 간 순서를 의미하지 않으므로 정렬 키로 쓰지
 * 않는다(부팅 간 순서는 event_time/received_at으로 판단).
 *
 * 형식 근거: 1~64자, `[A-Za-z0-9_-]`. 실제 기체는 UUIDv4를 권장한다(하이픈 포함 36자).
 * 생성 시점에 검증해서 "잘못된 부팅 ID"가 도메인 안으로 들어오지 못하게 한다.
 */
@JvmInline
value class BootId(val value: String) {
    init {
        require(PATTERN.matches(value)) {
            "boot_id는 1~64자의 영문·숫자·'_'·'-'여야 한다: '$value'"
        }
    }

    override fun toString(): String = value

    companion object {
        private val PATTERN = Regex("^[A-Za-z0-9_-]{1,64}$")

        /**
         * `boot_id`가 없는 v1 프레임을 받아들이는 전환기 값. legacy FastAPI의 기존 동작
         * `(asset_id, sequence_no)`와 같은 의미가 되도록 모든 v1 프레임을 이 부팅으로 본다.
         * 모든 생산자가 v2로 옮겨가면 Contract 단계에서 제거한다.
         */
        val LEGACY: BootId = BootId("legacy")
    }
}
