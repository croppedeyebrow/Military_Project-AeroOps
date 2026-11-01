package com.aeroops.c2.operationalpicture.adapter.inbound

import com.aeroops.c2.operationalpicture.domain.Attitude
import com.aeroops.c2.operationalpicture.domain.BatteryLevel
import com.aeroops.c2.operationalpicture.domain.LinkQuality
import com.aeroops.c2.operationalpicture.domain.Observation
import com.aeroops.c2.operationalpicture.domain.ObservationKey
import com.aeroops.c2.operationalpicture.domain.ObservedValue
import com.aeroops.c2.operationalpicture.domain.Position
import com.aeroops.c2.shared.AssetId
import com.aeroops.c2.shared.BootId
import com.fasterxml.jackson.annotation.JsonProperty
import java.time.Instant

/**
 * 장비가 보내는 **Wire 포맷** 그대로의 모양 — legacy `TelemetryFrame`(JSON)과 1:1이다.
 *
 * 왜 도메인 타입과 따로 두나(Anti-Corruption Layer, docs/planning/10 §4): 이 모양은 우리가 정한 것이
 * 아니라 **외부와의 약속**이다(tests/contracts/baseline/openapi.json에 고정돼 있다). 프로토콜이 바뀌면
 * (v2에서 boot_id 필수, 나중에 Protobuf) 이 클래스만 바뀌고 도메인 규칙은 그대로여야 한다.
 *
 * 필드가 대부분 nullable인 이유: 계약상 선택 필드다. 필수는 asset_id·event_time·sequence_no·위경도·고도·
 * battery_pct뿐이고, 자세·속도·RSSI·비행모드는 올 수도 안 올 수도 있다. "안 왔다"를 0으로 채우지 않고
 * 그대로 null로 받아, 변환 단계에서 [com.aeroops.c2.operationalpicture.domain.Quality]로 표현한다.
 *
 * 연관 코드: 변환은 [toObservation], 도메인 타입은 `domain` 패키지, Wire 계약 원본은
 * `legacy-backend/app/schemas/telemetry.py`와 `docs/api/telemetry_frame_dictionary.md`.
 */
data class TelemetryWireFrame(
    @param:JsonProperty("schema_version") val schemaVersion: Int = 1,
    @param:JsonProperty("asset_id") val assetId: String,
    @param:JsonProperty("event_time") val eventTime: Instant,
    @param:JsonProperty("sequence_no") val sequenceNo: Long,
    @param:JsonProperty("latitude") val latitude: Double,
    @param:JsonProperty("longitude") val longitude: Double,
    @param:JsonProperty("altitude_m") val altitudeM: Double,
    @param:JsonProperty("battery_pct") val batteryPct: Double,
    /** v2부터 필수(ADR 0005). v1 프레임에는 없으며 [BootId.LEGACY]로 정규화한다. */
    @param:JsonProperty("boot_id") val bootId: String? = null,
    @param:JsonProperty("received_at") val receivedAt: Instant? = null,
    @param:JsonProperty("roll_deg") val rollDeg: Double? = null,
    @param:JsonProperty("pitch_deg") val pitchDeg: Double? = null,
    @param:JsonProperty("yaw_deg") val yawDeg: Double? = null,
    @param:JsonProperty("speed_mps") val speedMps: Double? = null,
    @param:JsonProperty("heading_deg") val headingDeg: Double? = null,
    @param:JsonProperty("rssi_dbm") val rssiDbm: Double? = null,
    @param:JsonProperty("flight_mode") val flightMode: String? = null,
    @param:JsonProperty("mission_id") val missionId: String? = null,
)

/**
 * Wire 프레임을 도메인 관측으로 바꾼다.
 *
 * 변환 규칙과 근거:
 * - **boot_id 없음 → [BootId.LEGACY]**: v1 프레임을 모두 같은 "부팅"으로 보면 멱등 키가
 *   `(asset_id, LEGACY, sequence_no)`가 되어 legacy의 `(asset_id, sequence_no)`와 같은 판정이 된다
 *   (ADR 0005의 하위 호환 전략). 이것이 Golden Replay 일치의 전제다.
 * - **범위를 벗어난 값 → [Quality.INVALID]**: 예외를 던져 프레임 전체를 버리지 않는다. 배터리 센서 하나가
 *   고장 나도 위치는 여전히 쓸모 있기 때문이다. 거부가 아니라 "믿을 수 없음"으로 기록한다.
 *   (수신 단계에서 계약 검증을 통과한 프레임만 오지만, Shadow는 방어적으로 다룬다.)
 * - **자세는 셋 중 일부만 오면 [Quality.PARTIAL]**: 빠진 각도를 0으로 채우면 기체가 수평인 것처럼 보인다.
 *
 * @param now 신선도 판정 기준 시각. 호출부가 주입해 시험이 시계를 고정할 수 있게 한다.
 */
fun TelemetryWireFrame.toObservation(now: Instant): Observation {
    val receivedAtOrNow = receivedAt ?: now
    return Observation(
        key = ObservationKey(
            assetId = AssetId(assetId),
            bootId = bootId?.let(::BootId) ?: BootId.LEGACY,
            sequenceNo = sequenceNo,
        ),
        eventTime = eventTime,
        receivedAt = receivedAtOrNow,
        position = observedOrInvalid(eventTime, now) { Position(latitude, longitude, altitudeM) },
        attitude = toAttitude(now),
        battery = observedOrInvalid(eventTime, now) { BatteryLevel(batteryPct) },
        link = rssiDbm?.let { rssi -> observedOrInvalid(eventTime, now) { LinkQuality(rssi) } }
            ?: ObservedValue.unknown(),
        flightMode = flightMode?.let { ObservedValue.observed(it, eventTime, now) }
            ?: ObservedValue.unknown(),
        missionId = missionId,
    )
}

/**
 * 자세 세 각도를 묶는다. 전부 있으면 값으로, 일부만 있으면 PARTIAL(무엇이 왔는지 기록), 전혀 없으면 UNKNOWN.
 *
 * 왜 일부를 버리지 않고 기록하나: "roll만 계속 온다"는 센서 이상 신호다. 그냥 UNKNOWN으로 뭉개면 그 단서가
 * 사라진다([ObservedValue.reportedFields]).
 */
private fun TelemetryWireFrame.toAttitude(now: Instant): ObservedValue<Attitude> {
    val reported = buildSet {
        if (rollDeg != null) add("roll")
        if (pitchDeg != null) add("pitch")
        if (yawDeg != null) add("yaw")
    }
    return when (reported.size) {
        0 -> ObservedValue.unknown()
        3 -> observedOrInvalid(eventTime, now) { Attitude(rollDeg!!, pitchDeg!!, yawDeg!!) }
        else -> ObservedValue.partial(eventTime, reported)
    }
}

/**
 * 값 객체를 만들되, 도메인 범위 검증에 걸리면 [Quality.INVALID]로 감싼다.
 *
 * 왜 예외를 삼키나: 도메인 생성자의 `require`는 "이 값은 도메인에 들어올 수 없다"는 뜻이지 "프레임을
 * 버려라"는 뜻이 아니다. 경계(ACL)에서 잡아 품질로 바꾸는 것이 이 계층의 역할이다.
 * 원본 값을 보존할 수 없는 이유: 값 객체 생성 자체가 실패했으므로 담을 타입이 없다. 대신 품질이 INVALID로
 * 남아 "보고는 왔지만 믿을 수 없다"는 사실은 전달된다.
 */
private inline fun <T : Any> observedOrInvalid(
    observedAt: Instant,
    now: Instant,
    build: () -> T,
): ObservedValue<T> = try {
    ObservedValue.observed(build(), observedAt, now)
} catch (_: IllegalArgumentException) {
    ObservedValue.invalid(null, observedAt)
}
