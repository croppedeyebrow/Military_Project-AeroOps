package com.aeroops.c2.operationalpicture.adapter.outbound

import com.aeroops.c2.operationalpicture.application.ObservationIngestResult
import com.aeroops.c2.operationalpicture.application.ObservationStore
import com.aeroops.c2.operationalpicture.domain.Attitude
import com.aeroops.c2.operationalpicture.domain.BatteryLevel
import com.aeroops.c2.operationalpicture.domain.LinkQuality
import com.aeroops.c2.operationalpicture.domain.Observation
import com.aeroops.c2.operationalpicture.domain.ObservationKey
import com.aeroops.c2.operationalpicture.domain.ObservedValue
import com.aeroops.c2.operationalpicture.domain.Position
import com.aeroops.c2.operationalpicture.domain.Quality
import com.aeroops.c2.operationalpicture.domain.AssetSnapshot
import com.aeroops.c2.shared.AssetId
import com.aeroops.c2.shared.BootId
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.jdbc.core.RowMapper
import org.springframework.stereotype.Repository
import org.springframework.transaction.annotation.Transactional
import java.sql.ResultSet
import java.sql.Timestamp
import java.time.Instant

/**
 * Shadow 테이블에 관측과 최신 상황을 저장·조회한다.
 *
 * 왜 JPA가 아니라 JDBC인가(근거): 이 컨텍스트가 다루는 것은 Aggregate가 아니라 **Projection**이다.
 * - 핵심 연산이 "있으면 무시"(멱등 삽입)와 "더 최신일 때만 갱신"(조건부 upsert)인데, 둘 다 SQL의
 *   `ON CONFLICT`로 한 번에 끝난다. JPA로 하면 조회 후 분기가 필요해 경쟁 상태가 생긴다.
 * - legacy도 같은 `ON CONFLICT` 방식이라, 같은 수단을 쓰면 "같은 결과인가"를 비교하기 쉽다.
 * - Mission·Command처럼 불변조건을 가진 Aggregate는 계획대로 JPA를 쓴다(docs/planning/02).
 *
 * 연관 코드: 포트는 [ObservationStore], 스키마는 `V3__operational_picture_shadow.sql`,
 * legacy 대응은 `telemetry/repository.py`의 `insert_raw_frame`·`upsert_latest_state_if_newer`.
 */
@Repository
class JdbcObservationStore(private val jdbc: JdbcTemplate) : ObservationStore {

    /**
     * 원본 저장과 최신 상태 갱신을 **한 트랜잭션**으로 처리한다.
     *
     * 왜 한 트랜잭션인가: 둘이 갈라지면 "원본은 있는데 최신 상태에 반영 안 된" 또는 그 반대 상태가 생긴다.
     * legacy는 이 둘을 한 커밋으로 묶되 그 **이후** 단계(event_log·경보)는 분리돼 있어 구멍이 있었다
     * (docs/planning/13 §6). Kotlin에서는 그 이후 단계를 Outbox로 같은 커밋에 넣는다(4단계).
     */
    @Transactional
    override fun record(observation: Observation): ObservationIngestResult {
        val isNew = insertObservation(observation) > 0
        // 중복이면 최신 상태를 건드리지 않는다 — legacy의 `latest_updated = ... if is_new else False`와 같다.
        val latestUpdated = if (isNew) upsertSnapshotIfNewer(observation) > 0 else false
        return ObservationIngestResult(isNew = isNew, latestUpdated = latestUpdated)
    }

    /** 멱등 삽입. 같은 `(asset_id, boot_id, sequence_no)`가 이미 있으면 0행이 영향받는다. */
    private fun insertObservation(observation: Observation): Int = jdbc.update(
        """
        insert into shadow.observation (
          asset_id, boot_id, sequence_no, event_time, received_at,
          latitude, longitude, altitude_m, position_observed_at, position_quality,
          roll_deg, pitch_deg, yaw_deg, attitude_observed_at, attitude_quality, attitude_reported,
          battery_pct, battery_observed_at, battery_quality,
          rssi_dbm, link_observed_at, link_quality,
          flight_mode, flight_mode_observed_at, flight_mode_quality,
          mission_id
        ) values (?, ?, ?, ?, ?,  ?, ?, ?, ?, ?,  ?, ?, ?, ?, ?, ?,  ?, ?, ?,  ?, ?, ?,  ?, ?, ?,  ?)
        on conflict (asset_id, boot_id, sequence_no) do nothing
        """.trimIndent(),
        *observationParameters(observation),
    )

    /**
     * 최신 상태를 **더 최신일 때만** 갱신한다.
     *
     * `where asset_snapshot.event_time < excluded.event_time`이 후퇴 방지의 핵심이다. 같은 시각이면
     * 갱신하지 않는 것도 legacy와 같다(부등호가 `<`이지 `<=`가 아니다) — 도메인의 [AssetSnapshot.apply]와
     * 같은 규칙을 SQL로 표현한 것이다.
     */
    private fun upsertSnapshotIfNewer(observation: Observation): Int = jdbc.update(
        """
        insert into shadow.asset_snapshot (
          asset_id, last_boot_id, last_sequence_no, event_time, received_at,
          latitude, longitude, altitude_m, position_observed_at, position_quality,
          roll_deg, pitch_deg, yaw_deg, attitude_observed_at, attitude_quality, attitude_reported,
          battery_pct, battery_observed_at, battery_quality,
          rssi_dbm, link_observed_at, link_quality,
          flight_mode, flight_mode_observed_at, flight_mode_quality,
          mission_id
        ) values (?, ?, ?, ?, ?,  ?, ?, ?, ?, ?,  ?, ?, ?, ?, ?, ?,  ?, ?, ?,  ?, ?, ?,  ?, ?, ?,  ?)
        on conflict (asset_id) do update set
          last_boot_id = excluded.last_boot_id,
          last_sequence_no = excluded.last_sequence_no,
          event_time = excluded.event_time,
          received_at = excluded.received_at,
          latitude = excluded.latitude, longitude = excluded.longitude, altitude_m = excluded.altitude_m,
          position_observed_at = excluded.position_observed_at, position_quality = excluded.position_quality,
          roll_deg = excluded.roll_deg, pitch_deg = excluded.pitch_deg, yaw_deg = excluded.yaw_deg,
          attitude_observed_at = excluded.attitude_observed_at, attitude_quality = excluded.attitude_quality,
          attitude_reported = excluded.attitude_reported,
          battery_pct = excluded.battery_pct, battery_observed_at = excluded.battery_observed_at,
          battery_quality = excluded.battery_quality,
          rssi_dbm = excluded.rssi_dbm, link_observed_at = excluded.link_observed_at,
          link_quality = excluded.link_quality,
          flight_mode = excluded.flight_mode, flight_mode_observed_at = excluded.flight_mode_observed_at,
          flight_mode_quality = excluded.flight_mode_quality,
          mission_id = excluded.mission_id
        where shadow.asset_snapshot.event_time < excluded.event_time
        """.trimIndent(),
        *observationParameters(observation),
    )

    /** 두 upsert가 같은 컬럼 순서를 쓰므로 파라미터 구성을 공유한다(순서가 어긋나면 조용히 잘못 저장된다). */
    private fun observationParameters(observation: Observation): Array<Any?> = arrayOf(
        observation.key.assetId.value,
        observation.key.bootId.value,
        observation.key.sequenceNo,
        Timestamp.from(observation.eventTime),
        Timestamp.from(observation.receivedAt),

        observation.position.value?.latitude,
        observation.position.value?.longitude,
        observation.position.value?.altitudeM,
        observation.position.observedAt?.let(Timestamp::from),
        observation.position.quality.name,

        observation.attitude.value?.rollDeg,
        observation.attitude.value?.pitchDeg,
        observation.attitude.value?.yawDeg,
        observation.attitude.observedAt?.let(Timestamp::from),
        observation.attitude.quality.name,
        observation.attitude.reportedFields.takeIf { it.isNotEmpty() }?.sorted()?.joinToString(","),

        observation.battery.value?.percent,
        observation.battery.observedAt?.let(Timestamp::from),
        observation.battery.quality.name,

        observation.link.value?.rssiDbm,
        observation.link.observedAt?.let(Timestamp::from),
        observation.link.quality.name,

        observation.flightMode.value,
        observation.flightMode.observedAt?.let(Timestamp::from),
        observation.flightMode.quality.name,

        observation.missionId,
    )

    override fun findSnapshot(assetId: AssetId): AssetSnapshot? = jdbc.query(
        "select * from shadow.asset_snapshot where asset_id = ?",
        snapshotMapper,
        assetId.value,
    ).firstOrNull()

    override fun findAllSnapshots(): List<AssetSnapshot> = jdbc.query(
        "select * from shadow.asset_snapshot order by asset_id",
        snapshotMapper,
    )

    private val snapshotMapper = RowMapper { rs, _ ->
        AssetSnapshot(
            assetId = AssetId(rs.getString("asset_id")),
            lastKey = ObservationKey(
                assetId = AssetId(rs.getString("asset_id")),
                bootId = BootId(rs.getString("last_boot_id")),
                sequenceNo = rs.getLong("last_sequence_no"),
            ),
            eventTime = rs.instant("event_time")!!,
            receivedAt = rs.instant("received_at")!!,
            position = rs.observedValue("position_observed_at", "position_quality") {
                val lat = rs.doubleOrNull("latitude")
                val lon = rs.doubleOrNull("longitude")
                val alt = rs.doubleOrNull("altitude_m")
                if (lat != null && lon != null && alt != null) Position(lat, lon, alt) else null
            },
            attitude = rs.observedValue(
                "attitude_observed_at",
                "attitude_quality",
                reported = rs.getString("attitude_reported")?.split(",")?.toSet() ?: emptySet(),
            ) {
                val roll = rs.doubleOrNull("roll_deg")
                val pitch = rs.doubleOrNull("pitch_deg")
                val yaw = rs.doubleOrNull("yaw_deg")
                if (roll != null && pitch != null && yaw != null) Attitude(roll, pitch, yaw) else null
            },
            battery = rs.observedValue("battery_observed_at", "battery_quality") {
                rs.doubleOrNull("battery_pct")?.let(::BatteryLevel)
            },
            link = rs.observedValue("link_observed_at", "link_quality") {
                rs.doubleOrNull("rssi_dbm")?.let(::LinkQuality)
            },
            flightMode = rs.observedValue("flight_mode_observed_at", "flight_mode_quality") {
                rs.getString("flight_mode")
            },
            missionId = rs.getString("mission_id"),
        )
    }
}

/** `getDouble`은 NULL을 0.0으로 돌려준다 — "모름"이 "0"이 되지 않도록 명시적으로 확인한다. */
private fun ResultSet.doubleOrNull(column: String): Double? =
    getDouble(column).takeUnless { wasNull() }

private fun ResultSet.instant(column: String): Instant? = getTimestamp(column)?.toInstant()

/** 값·관측시각·품질 세 컬럼을 하나의 [ObservedValue]로 되살린다. */
private fun <T : Any> ResultSet.observedValue(
    observedAtColumn: String,
    qualityColumn: String,
    reported: Set<String> = emptySet(),
    buildValue: () -> T?,
): ObservedValue<T> = ObservedValue(
    value = buildValue(),
    observedAt = instant(observedAtColumn),
    quality = Quality.valueOf(getString(qualityColumn)),
    reportedFields = reported,
)
