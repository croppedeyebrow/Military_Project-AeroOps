# AlertPanel

배터리·통신·구역 이탈 경보 목록과 확인/해제 UI (5단계 완료).

`useOperationsStore.alertsById`(WS 스냅샷 + 실시간 "alert" 메시지로 채워짐)를 그대로
읽는다. 확인(`useAcknowledgeAlert`)·해제(`useResolveAlert`)는 REST mutation이며, 성공
결과는 다음 WS 갱신이 최종 반영한다.
