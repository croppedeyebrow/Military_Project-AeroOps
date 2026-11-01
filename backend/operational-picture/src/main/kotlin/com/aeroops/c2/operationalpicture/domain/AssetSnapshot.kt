package com.aeroops.c2.operationalpicture.domain

import com.aeroops.c2.shared.AssetId
import java.time.Instant

/**
 * 기체 하나의 **최신 상황** — 관측들을 쌓아 만든, 다시 계산 가능한 Projection.
 *
 * 왜 원본과 따로 두나(근거): `docs/planning/13` §1 — 원본 관측은 불변으로 보존하고, "지금 어떤 상태인가"는
 * 그것들로부터 만든 별도의 뷰다. 관제 화면이 매번 수만 건을 훑지 않아도 되고, 규칙이 바뀌면 원본에서 다시
 * 만들 수 있다.
 *
 * 연관 코드: 갱신 규칙은 [apply], 품질 재판정은 [refreshedAt], 저장은 3-3의 adapter.outbound,
 * legacy 대응은 `legacy-backend/app/modules/telemetry/models.py`의 `AssetLatestState`.
 */
data class AssetSnapshot(
    val assetId: AssetId,
    /** 이 상태를 만든 마지막 관측의 키. 어느 부팅·몇 번째 관측까지 반영됐는지 알 수 있다. */
    val lastKey: ObservationKey,
    /** 이 상태의 기준 시각(= 마지막으로 반영된 관측의 event_time). 후퇴 방지 판정에 쓴다. */
    val eventTime: Instant,
    val receivedAt: Instant,
    val position: ObservedValue<Position>,
    val attitude: ObservedValue<Attitude>,
    val battery: ObservedValue<BatteryLevel>,
    val link: ObservedValue<LinkQuality>,
    val flightMode: ObservedValue<String>,
    val missionId: String? = null,
) {
    /**
     * 새 관측을 반영한다. **더 최신일 때만** 갱신하고, 아니면 [ApplyResult.Ignored]를 돌려준다.
     *
     * 왜 이 규칙인가(가장 중요한 불변조건): "오래된 Telemetry가 최신 상태를 후퇴시키지 않는다"
     * (docs/planning/13 §4의 불변조건 1, 3단계 완료 게이트). 네트워크는 순서를 보장하지 않아서, 늦게
     * 도착한 과거 관측이 최신 상태를 덮어쓰면 화면의 기체가 뒤로 점프한다.
     *
     * 판정 기준을 `event_time`으로 삼는 이유: 도착 순서(received_at)는 네트워크 사정에 좌우되지만
     * 관측 시각은 사실의 순서다. legacy도 같은 기준을 쓴다
     * (`upsert_latest_state_if_newer`의 `WHERE event_time < excluded.event_time`).
     *
     * **같은 event_time이면 갱신하지 않는다** — legacy의 `<` 비교와 같게 맞춘 것이다(Golden Replay 일치).
     *
     * 전체를 교체하고 항목별로 병합하지 않는 이유: legacy가 모든 컬럼을 통째로 덮어쓰기 때문이다. 항목별
     * 병합("배터리는 옛 값을 유지")이 운용상 더 정확할 수 있지만, 그러면 legacy와 결과가 달라져 전환
     * 비교가 깨진다. 전환을 마친 뒤 별도 결정으로 다룬다(남은 이슈에 기록).
     */
    fun apply(observation: Observation): ApplyResult {
        if (observation.key.assetId != assetId) {
            return ApplyResult.Ignored(IgnoreReason.DIFFERENT_ASSET)
        }
        if (!observation.eventTime.isAfter(eventTime)) {
            return ApplyResult.Ignored(IgnoreReason.NOT_NEWER)
        }
        return ApplyResult.Applied(from(observation))
    }

    /**
     * 조회 시점 기준으로 품질을 다시 판정한다.
     *
     * 왜 필요한가: 저장된 품질은 "저장하던 순간"의 판정이다. 그 뒤 통신이 끊겨 10분이 지나도 저장값은
     * KNOWN인 채다. 조회할 때 현재 시각으로 다시 보지 않으면, 끊긴 기체의 옛 위치가 현재 위치처럼 보인다
     * ([Quality] 설명의 위험 그대로).
     */
    fun refreshedAt(now: Instant, policy: FreshnessPolicy = FreshnessPolicy.DEFAULT): AssetSnapshot = copy(
        position = position.restale(now, policy),
        attitude = attitude.restale(now, policy),
        battery = battery.restale(now, policy),
        link = link.restale(now, policy),
        flightMode = flightMode.restale(now, policy),
    )

    private fun <T : Any> ObservedValue<T>.restale(now: Instant, policy: FreshnessPolicy): ObservedValue<T> {
        // UNKNOWN·INVALID·PARTIAL은 시간이 흐른다고 의미가 바뀌지 않는다. KNOWN만 STALE로 내려갈 수 있다.
        if (quality != Quality.KNOWN || observedAt == null) return this
        return if (policy.isStale(observedAt, now)) copy(quality = Quality.STALE) else this
    }

    companion object {
        /** 관측 하나로 최신 상태를 만든다(첫 관측이거나 전체 교체 시). */
        fun from(observation: Observation): AssetSnapshot = AssetSnapshot(
            assetId = observation.key.assetId,
            lastKey = observation.key,
            eventTime = observation.eventTime,
            receivedAt = observation.receivedAt,
            position = observation.position,
            attitude = observation.attitude,
            battery = observation.battery,
            link = observation.link,
            flightMode = observation.flightMode,
            missionId = observation.missionId,
        )
    }
}

/** [AssetSnapshot.apply]의 결과. 무시된 경우 그 이유를 함께 돌려줘 호출부가 기록·집계할 수 있게 한다. */
sealed interface ApplyResult {
    data class Applied(val snapshot: AssetSnapshot) : ApplyResult
    data class Ignored(val reason: IgnoreReason) : ApplyResult
}

enum class IgnoreReason {
    /** 관측의 event_time이 현재 상태보다 과거이거나 같다(늦게 도착한 과거 관측). */
    NOT_NEWER,

    /** 다른 기체의 관측이다(호출 실수 방지용 — 정상 흐름에서는 일어나지 않는다). */
    DIFFERENT_ASSET,
}
