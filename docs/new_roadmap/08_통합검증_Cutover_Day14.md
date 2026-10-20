# 8단계 — 통합 검증·Cutover (Day 14)

## 목표

전체 수직 경로와 복구 가능성을 검증하고 전환 결과를 증거로 남긴다.

## 작업

- C++ Simulator→Rust Gateway→Kotlin Core→React UI E2E
- 정상·손실·역순·단절·ACK 손실·재접속 전체 회귀
- FastAPI/Kotlin Replay 비교와 승인된 차이 기록
- mTLS·RBAC·Replay·Prompt Injection·Artifact 변조 시험
- 부하 중 Command p95와 긴급 경보 전달 시간 측정
- DB Backup/Restore, Gateway·Redis·AI 중단 시험
- Canary Routing과 Go `opsctl` Rollback 리허설
- REQ–TEST–Artifact–Deployment 추적표와 Portfolio Report

## 완료 게이트

Kotlin 핵심 경로가 System of Record 후보 기준을 충족하고, 장애 시 기존 경로 또는 이전 Artifact로 복구할 수 있다. FastAPI 제거는 별도 관찰 기간과 두 차례 이상의 Cutover 리허설 후 결정한다.
