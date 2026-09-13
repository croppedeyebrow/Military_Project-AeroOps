# AssetList

자산(드론) 목록, 검색, 상태 필터. 4단계에서 구현.

목록은 `useOperationsStore`의 `assetsById`(WebSocket으로 갱신)를 그대로 읽는다. 신선도
표시는 2초마다 리렌더해서 "마지막 수신 후 경과 시간"이 계속 최신으로 보이게 한다(새
텔레메트리가 없어도 `live → stale → disconnected` 표시가 시간이 지나면 저절로 바뀐다).
