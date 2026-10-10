"""DB 접근 계층: 저장·최신 상태 갱신·조회.

동기 SQLAlchemy Session을 사용한다. 비동기 컨텍스트(`consumer.py`)에서는
`asyncio.to_thread`로 감싸 이벤트 루프를 막지 않는다.

신뢰성 규칙(`docs/planning/02_백엔드_아키텍처.md`):
- `asset_id + sequence_no`로 중복을 판정한다(DB 유일 제약, `models.py` 참고).
- 역순 데이터는 원본을 보존하되 `asset_latest_state` 갱신 여부는 별도로 판정한다.
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.modules.telemetry.downsampling import downsample_fixed_stride
from app.modules.telemetry.models import Asset, AssetLatestState, TelemetryFrameRecord
from app.schemas.telemetry import TelemetryFrame

# 다운샘플링 모드(max_points 지정 시)에서 한 번에 메모리로 끌어올 수 있는 원본 행 수
# 상한. 목적: 아주 긴 시간 구간을 요청해도(예: 하루 전체) 쿼리가 무한정 커지지 않게
# 막는다 — MVP 성공 기준이 "10대×1Hz를 20분"이라 20분×10대=12,000행 정도를 기준점으로
# 삼고 여유를 둬 50,000으로 잡았다. 이 한도에 걸리면 다운샘플링은 "최근 50,000행
# 안에서"만 수행된다(전체 구간이 아니라 뒷부분이 잘릴 수 있다는 뜻 — 더 긴 구간을
# 다루려면 SQL 레벨 집계로 가야 하는데, 지금 요구사항엔 없어 YAGNI로 미룬다).
MAX_DOWNSAMPLE_SOURCE_ROWS = 50_000


def _position_expr(latitude: float, longitude: float, altitude_m: float):
    return ST_SetSRID(ST_MakePoint(longitude, latitude, altitude_m), 4326)


def _frame_values(frame: TelemetryFrame) -> dict:
    return dict(
        asset_id=frame.asset_id,
        mission_id=frame.mission_id,
        event_time=frame.event_time,
        received_at=frame.received_at,
        sequence_no=frame.sequence_no,
        latitude=frame.latitude,
        longitude=frame.longitude,
        altitude_m=frame.altitude_m,
        position=_position_expr(frame.latitude, frame.longitude, frame.altitude_m),
        speed_mps=frame.speed_mps,
        heading_deg=frame.heading_deg,
        roll_deg=frame.roll_deg,
        pitch_deg=frame.pitch_deg,
        yaw_deg=frame.yaw_deg,
        battery_pct=frame.battery_pct,
        rssi_dbm=frame.rssi_dbm,
        flight_mode=frame.flight_mode.value if frame.flight_mode else None,
    )


def ensure_asset_exists(db: Session, asset_id: str) -> None:
    """처음 보는 asset_id는 최소 정보로 자동 등록한다(3단계 MVP — 자산 관리 화면은 이후 단계)."""
    stmt = pg_insert(Asset).values(id=asset_id).on_conflict_do_nothing(index_elements=["id"])
    db.execute(stmt)


def insert_raw_frame(db: Session, frame: TelemetryFrame) -> bool:
    """원본 프레임을 저장한다. 이미 존재하는 (asset_id, sequence_no)면 무시하고 False를 반환한다."""
    stmt = (
        pg_insert(TelemetryFrameRecord)
        .values(**_frame_values(frame))
        .on_conflict_do_nothing(index_elements=["asset_id", "sequence_no"])
        .returning(TelemetryFrameRecord.id)
    )
    result = db.execute(stmt)
    return result.first() is not None


def upsert_latest_state_if_newer(db: Session, frame: TelemetryFrame) -> bool:
    """asset_latest_state의 event_time이 이 프레임보다 오래된 경우에만 갱신한다."""
    values = _frame_values(frame)
    stmt = pg_insert(AssetLatestState).values(**values)
    update_cols = {k: getattr(stmt.excluded, k) for k in values if k != "asset_id"}
    stmt = stmt.on_conflict_do_update(
        index_elements=["asset_id"],
        set_=update_cols,
        where=(AssetLatestState.event_time < stmt.excluded.event_time),
    ).returning(AssetLatestState.asset_id)
    result = db.execute(stmt)
    return result.first() is not None


def process_frame(db: Session, frame: TelemetryFrame) -> tuple[bool, bool]:
    """한 프레임을 처리한다. `(원본_신규저장여부, 최신상태_갱신여부)`를 반환한다."""
    ensure_asset_exists(db, frame.asset_id)
    is_new = insert_raw_frame(db, frame)
    latest_updated = upsert_latest_state_if_newer(db, frame) if is_new else False
    db.commit()
    return is_new, latest_updated


def get_latest_state(db: Session, asset_id: str) -> AssetLatestState | None:
    return db.get(AssetLatestState, asset_id)


def get_all_latest_states(db: Session) -> list[AssetLatestState]:
    """전체 기체의 최신 상태. `/ws/operations` 연결 시 초기 스냅샷으로 쓴다(4단계)."""
    stmt = select(AssetLatestState).order_by(AssetLatestState.asset_id)
    return list(db.execute(stmt).scalars().all())


def get_max_sequence_no(db: Session, asset_id: str) -> int | None:
    """이 기체에 대해 서버가 실제로 저장하고 있는 가장 큰 sequence_no.

    재동기화(`sync` 모듈)에서 기체가 보고한 마지막 송신 sequence와 비교해 손실 구간
    (sequence gap)을 계산하는 데 쓴다.
    """
    stmt = select(func.max(TelemetryFrameRecord.sequence_no)).where(
        TelemetryFrameRecord.asset_id == asset_id
    )
    return db.execute(stmt).scalar_one_or_none()


def get_telemetry_history(
    db: Session,
    asset_id: str,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
    max_points: int | None = None,
) -> list[TelemetryFrameRecord]:
    """기간·기체 조건 이력 조회.

    `max_points`가 없으면(기존 동작, 3단계부터 있던 것) `event_time` 오름차순으로
    `limit`/`offset` 페이지네이션한다 — 원본을 그대로 쪽지어 보는 용도(이력 상세 조회 등).

    `max_points`가 있으면(7단계 추가) 의미가 달라진다: "이 구간 안의 모든 점을 보고
    싶지만, 그릴 때는 최대 N개면 충분하다"는 차트용 요청이라 `limit`/`offset`은
    무시하고 구간 내 전체(단, `MAX_DOWNSAMPLE_SOURCE_ROWS`까지)를 가져온 뒤
    `downsample_fixed_stride`로 줄인다. 두 모드를 하나의 함수에 같이 둔 이유는
    호출부(router)가 "같은 endpoint, 파라미터 하나로 모드 전환"이라는 단순한 API
    모양을 유지하게 하기 위함이다 — 두 endpoint로 쪼개면 프론트가 언제 어느 걸
    불러야 하는지 또 하나의 분기를 떠안는다.
    """
    stmt = select(TelemetryFrameRecord).where(TelemetryFrameRecord.asset_id == asset_id)
    if start is not None:
        stmt = stmt.where(TelemetryFrameRecord.event_time >= start)
    if end is not None:
        stmt = stmt.where(TelemetryFrameRecord.event_time <= end)
    stmt = stmt.order_by(TelemetryFrameRecord.event_time.asc())

    if max_points is not None:
        stmt = stmt.limit(MAX_DOWNSAMPLE_SOURCE_ROWS)
        records = list(db.execute(stmt).scalars().all())
        return downsample_fixed_stride(records, max_points)

    stmt = stmt.limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())
