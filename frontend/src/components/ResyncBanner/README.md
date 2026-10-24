# ResyncBanner

`docs/planning/01_프론트엔드_아키텍처.md`에 정의된 신규 컴포넌트. WebSocket이 끊겼다가
다시 붙었을 때("재연결됨 — 최신 상태로 복구했습니다") 잠깐 보여주는 배너, 재연결
시도 중일 때는 별도 안내를 보여준다.

`legacy-backend/app/modules/sync`(기체 ↔ 서버 재동기화 handshake)와는 다른 개념이다 — 여기는
순수하게 "브라우저 ↔ 서버 WebSocket 연결" 상태만 다룬다. 기체 쪽 재동기화 결과를 보여줄
화면은 아직 없다(운영자가 기체를 직접 조작하는 화면이 없어서 — 필요해지면 이후 단계에서
`sync_sessions` 조회 화면으로 추가한다).
