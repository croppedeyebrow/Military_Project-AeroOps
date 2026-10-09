# CommandTimeline

선택한 명령의 상태 전이 이력(`command_events`)을 보여준다 (5단계).
`ApprovalQueue`에서 명령을 고르면 `GET /commands/{id}`를 3초 간격 폴링해 이벤트 목록을
시간순으로 보여준다.
