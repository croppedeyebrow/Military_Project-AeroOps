# ApprovalQueue

승인 대기 중인 명령(`PENDING_APPROVAL`) 목록과 승인/취소 UI (5단계).
`GET /commands?status=PENDING_APPROVAL`을 3초 간격 폴링한다(WS로는 Command 채널을 직접
받지 않음 — `docs/dev_history/05_단계_임무경보관리.md` 참고).

요청자 본인이 승인자로 승인을 시도하면 백엔드가 403으로 거부하며, 그 사유를 그대로
보여준다("요청자와 승인자를 분리한다").
