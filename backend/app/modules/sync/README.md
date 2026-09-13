# Synchronization 모듈

책임: 통신 단절 후 재연결 handshake와 서버·기체 상태 대조 (`/devices/{id}/sync`).

`docs/planning/02_백엔드_아키텍처.md` "재동기화": 재연결 시 기체 인증 → 마지막 telemetry
sequence → 기체 상태 snapshot → 미종결 command 목록 → 서버 상태 비교 → 충돌 정책 적용
순으로 수행한다. 기체 인증(mTLS)은 8단계 전까지 없으므로 이 단계에서는 생략한다.

## 구현 (4단계)

- `router.py` — `POST /devices/{asset_id}/sync`: 기체가 마지막 송신 `sequence_no`,
  `state_version`, 마지막 처리 `command_id`를 보고하면, 서버가 저장 상태와 대조해
  응답한다.
- `repository.py` — 손실 구간(sequence gap) 계산, "기체가 서버보다 뒤처짐"(재부팅 등)
  이상 징후 판정, 미종결 명령(`commands.status`가 터미널이 아닌 것) 조회, snapshot 재발급
  여부 결정. 모든 판단을 `sync_sessions`에 append-only로 기록한다.
- `models.py` — `SyncSession`.

## 알려진 제한

- 명령 상태 머신(5단계)이 아직 없어 모든 명령이 `DRAFT`다 — "미종결 명령 목록"은
  현재 사실상 "이 기체 대상 명령 전체"와 같다. 상태 머신이 생기면 자동으로 의미가
  좁혀진다(코드 변경 불필요).
- `reported_last_processed_command_id`는 기록만 하고 자동으로 명령 상태를 전이시키지는
  않는다 — 실행 결과 확인·상태 전이는 5단계 몫이다.
