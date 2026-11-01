package com.aeroops.c2.operationalpicture.domain

import java.time.Duration
import java.time.Instant

/**
 * "언제 관측된 무엇"을 품질과 함께 담는다.
 *
 * 왜 값마다 시각을 따로 두나(근거): `docs/new_roadmap/03`의 "위치·자세·배터리·통신별 관측·수신 시각 분리".
 * 한 프레임에 모든 값이 들어오더라도, 실제 기체는 항목마다 갱신 주기가 다르다(위치 1Hz, 배터리는 수 초에
 * 한 번). 하나의 시각으로 뭉뚱그리면 "10초 전 배터리"가 "지금 배터리"로 보인다. legacy는 프레임 단위
 * 시각 하나만 가졌고, 그래서 항목별 신선도를 구분할 수 없었다.
 *
 * `T`가 null이면 보고가 없었다는 뜻이고 품질은 [Quality.UNKNOWN]이다 — "0"이나 이전 값으로 채우지 않는다.
 *
 * 연관 코드: 품질 정의는 [Quality], 신선도 임계는 [FreshnessPolicy], 사용처는 [AssetSnapshot].
 */
data class ObservedValue<T : Any>(
    val value: T?,
    /** 기체가 이 값을 관측한 시각(기체 시계 기준, Wire의 event_time). */
    val observedAt: Instant?,
    val quality: Quality,
    /** [Quality.PARTIAL]일 때 실제로 보고된 구성요소 이름들. 다른 품질에서는 비어 있다. */
    val reportedFields: Set<String> = emptySet(),
) {
    init {
        // 값이 없는데 품질이 "안다"고 주장하면 소비자가 속는다. 모델 수준에서 막는다.
        // PARTIAL이 값 없이 올 수 있는 이유: 복합 값(자세 = roll·pitch·yaw)의 일부만 보고되면 완전한 값
        // 객체를 만들 수 없다. 빠진 성분을 0으로 채우면 "모르는 것을 아는 것처럼" 만드는 셈이라, 값은
        // 비워 두고 "일부만 왔다"는 사실만 남긴다.
        require(value != null || quality in VALUELESS_QUALITIES) {
            "값이 없으면 품질은 UNKNOWN·INVALID·PARTIAL 중 하나여야 한다: quality=$quality"
        }
    }

    /** 운용 판단에 쓸 수 있는 값만 꺼낸다. STALE·INVALID·UNKNOWN이면 null이다. */
    fun trustedValue(): T? = if (quality.isTrustworthy) value else null

    companion object {
        /** 보고가 없었다. */
        fun <T : Any> unknown(): ObservedValue<T> = ObservedValue(null, null, Quality.UNKNOWN)

        /** 보고는 왔지만 계약·물리 범위를 벗어났다. 원본 값은 진단을 위해 버리지 않는다. */
        fun <T : Any> invalid(raw: T?, observedAt: Instant?): ObservedValue<T> =
            ObservedValue(raw, observedAt, Quality.INVALID)

        /**
         * 정상 보고를 담되, [now] 기준으로 너무 오래됐으면 [Quality.STALE]로 낮춘다.
         *
         * 왜 생성 시점에 판정하나: 저장할 때의 품질과 조회할 때의 품질은 다르다(시간이 흐르므로).
         * 이 함수는 "그 시점의 판정"을 만들고, 조회 시점 재판정은 [AssetSnapshot.refreshedAt]이 한다.
         */
        fun <T : Any> observed(
            value: T,
            observedAt: Instant,
            now: Instant,
            policy: FreshnessPolicy = FreshnessPolicy.DEFAULT,
        ): ObservedValue<T> {
            val quality = if (policy.isStale(observedAt, now)) Quality.STALE else Quality.KNOWN
            return ObservedValue(value, observedAt, quality)
        }

        /**
         * 복합 값의 구성요소 일부만 보고됐다(예: 자세 중 roll만 왔다).
         *
         * [reportedFields]는 무엇이 왔는지 남겨 진단에 쓴다 — "센서 중 하나만 죽었다"를 알아보려면
         * "일부만 왔다"는 사실만으로는 부족하다.
         */
        fun <T : Any> partial(observedAt: Instant?, reportedFields: Set<String> = emptySet()): ObservedValue<T> =
            ObservedValue(null, observedAt, Quality.PARTIAL, reportedFields)

        private val VALUELESS_QUALITIES = setOf(Quality.UNKNOWN, Quality.INVALID, Quality.PARTIAL)
    }
}

/**
 * "언제부터 오래된 값으로 볼 것인가"의 기준.
 *
 * 왜 설정으로 빼나: 항목마다, 운용 상황마다 기준이 다르다. 상수를 코드 여기저기 박아두면 한 곳만 바꾸고
 * 다른 곳을 잊는다. 기본값은 프론트가 쓰던 기준(`frontend/src/types/telemetry.ts`의 STALE 15초,
 * 통신 단절 60초)과 맞춰, 전환 중 서버·화면 판정이 어긋나지 않게 했다.
 *
 * 연관 코드: [ObservedValue.observed], [AssetSnapshot], 프론트 대응은 `classifyFreshness`.
 */
data class FreshnessPolicy(val staleAfter: Duration) {
    fun isStale(observedAt: Instant, now: Instant): Boolean =
        Duration.between(observedAt, now) > staleAfter

    companion object {
        /** 프론트의 STALE 기준(15초)과 같은 값. */
        val DEFAULT = FreshnessPolicy(Duration.ofSeconds(15))
    }
}
