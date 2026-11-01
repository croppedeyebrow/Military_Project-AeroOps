package com.aeroops.c2.operationalpicture.domain

import java.time.Instant

/**
 * 기체가 보고한 사실 한 건 — 외부 Wire 포맷이 아니라 **도메인이 이해하는 형태**.
 *
 * 왜 Wire 모델과 분리하나(근거): `docs/planning/10` §4의 Anti-Corruption Layer. 장비 프로토콜은 바뀐다
 * (JSON → Protobuf, v1 → v2, boot_id 추가 …). Wire 타입을 그대로 도메인에 들이면 프로토콜이 바뀔 때마다
 * 업무 규칙이 흔들린다. 변환은 adapter가 하고([com.aeroops.c2.operationalpicture.adapter] 패키지),
 * 도메인은 이 타입만 안다.
 *
 * 설계상 중요한 점: 위치·자세·배터리·통신을 **각각 [ObservedValue]로** 담는다. 한 프레임에 함께 왔더라도
 * 항목별로 품질·시각이 다를 수 있기 때문이다(ObservedValue 설명 참고).
 *
 * 연관 코드: 멱등 키는 [ObservationKey](ADR 0005), 최신 상태 반영 규칙은 [AssetSnapshot.apply],
 * Wire 변환은 3-2의 ACL, 저장은 3-3의 adapter.outbound.
 */
data class Observation(
    val key: ObservationKey,
    /** 기체가 이 관측을 만든 시각. 프레임 단위 기준 시각이며, 항목별 시각은 각 [ObservedValue]에 있다. */
    val eventTime: Instant,
    /** 서버가 받은 시각. 기체 시계와 서버 시계가 다를 수 있어 둘 다 보존한다(docs/planning/05). */
    val receivedAt: Instant,
    val position: ObservedValue<Position>,
    val attitude: ObservedValue<Attitude>,
    val battery: ObservedValue<BatteryLevel>,
    val link: ObservedValue<LinkQuality>,
    val flightMode: ObservedValue<String>,
    val missionId: String? = null,
)

/**
 * WGS84 위치. 고도는 지면 기준 m(docs/api/telemetry_frame_dictionary.md).
 *
 * 범위 검증을 생성 시점에 두는 이유: 잘못된 좌표가 도메인 안으로 들어오면 거리·지오펜스 계산이 조용히
 * 틀린다. legacy도 같은 범위를 계약에서 강제한다(`TelemetryFrame`의 ge/le) — 같은 입력을 같은 기준으로
 * 받아야 Golden Replay 비교가 성립한다.
 */
data class Position(val latitude: Double, val longitude: Double, val altitudeM: Double) {
    init {
        require(latitude in -90.0..90.0) { "위도 범위를 벗어났다: $latitude" }
        require(longitude in -180.0..180.0) { "경도 범위를 벗어났다: $longitude" }
        require(altitudeM in -500.0..10_000.0) { "고도 범위를 벗어났다: $altitudeM" }
    }
}

/**
 * 기체 자세. 축 정의와 부호 규칙은 ADR 0003(`docs/decisions/0003-vehicle-3d-axis-convention.md`)을 따른다
 * — 3D 뷰어와 서버가 같은 규칙을 쓰지 않으면 화면의 기체가 엉뚱한 방향을 본다.
 */
data class Attitude(val rollDeg: Double, val pitchDeg: Double, val yawDeg: Double) {
    init {
        require(rollDeg in -180.0..180.0) { "roll 범위를 벗어났다: $rollDeg" }
        require(pitchDeg in -90.0..90.0) { "pitch 범위를 벗어났다: $pitchDeg" }
        require(yawDeg in -180.0..180.0) { "yaw 범위를 벗어났다: $yawDeg" }
    }
}

/** 배터리 잔량(%). 경보 규칙(배터리 부족)의 입력이다. */
data class BatteryLevel(val percent: Double) {
    init {
        require(percent in 0.0..100.0) { "배터리 범위를 벗어났다: $percent" }
    }
}

/** 통신 품질. RSSI는 음수 dBm이며 0에 가까울수록 좋다. */
data class LinkQuality(val rssiDbm: Double) {
    init {
        require(rssiDbm in -130.0..0.0) { "RSSI 범위를 벗어났다: $rssiDbm" }
    }
}
