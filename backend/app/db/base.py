"""SQLAlchemy 베이스 및 세션.

`docs/planning/03_데이터베이스_아키텍처.md`의 핵심 테이블(assets, missions,
mission_routes, geofences, telemetry_frames, asset_latest_state, alerts,
users, roles, audit_logs)은 3단계 이후 `app/modules/*/models.py`에 정의하고
alembic migration으로 반영한다.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
