"""backend/app/schemas/telemetry.py의 TelemetryFrame 계약을 공유 참조한다.

MVP에서는 스키마를 두 곳에 복제하지 않고, 시뮬레이터가 backend 스키마를
직접 임포트하거나(모노레포 경로 참조) JSON Schema를 별도 파일로 내보내
양쪽에서 검증하는 방식 중 2단계에서 확정한다.
"""
