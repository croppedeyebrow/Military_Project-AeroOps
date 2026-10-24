# Device Identity 모듈

책임: 기체 인증서(mTLS client certificate) 식별·상태·폐기 확인.

`docs/planning/04_인프라_네트워크_클라우드.md`: 기체마다 별도 client certificate를 발급하고
인증서 fingerprint를 장비 ID(`device_id`)와 1:1 매핑한다. 만료·미등록·폐기·타 기체 인증서를
거부한다.

## 로드맵

8단계(`docs/roadmap/08_단계_보안검증_배포_Day19-20.md`)에서 구현한다:

- 인증서 fingerprint ↔ `device_id` 매핑 조회
- 유효/만료/폐기 상태 확인
- reverse-proxy/gateway의 mTLS 종단 처리와 연동

## 예정 구성

- `router.py` — 인증서 상태 조회(운영자용)
- `models.py` — `DeviceCertificate`
- `verifier.py` — fingerprint 검증 로직(만료·폐기·미등록 판정)
