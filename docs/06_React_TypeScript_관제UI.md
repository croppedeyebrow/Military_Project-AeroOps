# React·TypeScript 관제 UI

## 적용 위치

Fleet Map, 선택 기체 3D View, 경보·Incident, 명령 승인, 효과 검증과 Replay Timeline을 제공한다.

## 공부할 개념

- Server State와 UI State 분리
- React Query, Zustand와 immutable update
- WebSocket reconnect, snapshot, last event ID
- discriminated union과 Exhaustive Check
- MapLibre Source/Layer, 공간 좌표계
- Three.js Quaternion·Euler·좌표축
- Error Boundary와 저하 상태 UX
- 접근성, 확인 Dialog, 이중 승인 UX

## 적용 원칙

- 오래된 Event가 화면 상태를 후퇴시키지 않는다.
- 기체 상태와 데이터 품질을 별도로 표시한다.
- ACK와 목표 상태 달성을 같은 완료 표시로 합치지 않는다.
- AI의 확인된 사실과 가설을 시각적으로 구분한다.

## 실습

역순·단절·재접속 Event를 주입하고 지도·3D·차트가 같은 Timestamp 기준으로 복구되는지 시험한다.
