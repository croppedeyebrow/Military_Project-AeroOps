"""프로세스 전역 "지금 운용 세션이 뭔지"를 들고 있는 작은 모듈.

목적: 7단계부터 `event_log`(재생용 이벤트)에 쓰는 모든 행에는 `operation_session_id`가
같이 들어가야 한다(`docs/planning/03_데이터베이스_아키텍처.md` "이벤트·배포 추적성").
문제는 이 값을 만드는 곳(`main.py`의 lifespan, 앱 시작 시 1회)과 이 값을 쓰는 곳
(telemetry consumer, command/alert/sync repository — 전부 다른 모듈)이 따로라는 것이다.

왜 이런 방식인가(근거): FastAPI의 `Request.app.state`는 HTTP 요청 핸들러에서는 편하지만,
telemetry consumer(`app/modules/telemetry/consumer.py`)는 백그라운드 asyncio task라
`Request`가 없다. 그래서 `app.main`을 직접 import해서 `app.state`를 읽는 방법도 있지만,
`main.py`가 거의 모든 모듈을 import하는 진입점이라 거꾸로 모듈들이 `main`을 import하면
순환 import가 생긴다. 대신 `get_settings()`(lru_cache)처럼 의존성 없는 독립 모듈에
"지금 값"을 두고 getter/setter로만 접근하게 하면, 어느 모듈이든 이 모듈만 import하면
되고 순환 참조가 생기지 않는다.

주의: 이 값은 "변경 가능한 전역 상태"라 테스트 간 격리에 주의해야 한다 — 하지만
운용 세션은 앱이 떠 있는 동안 하나뿐이어야 하는 개념이라(세션 = 프로세스 수명과 1:1),
오히려 전역 상태로 표현하는 것이 모델과 맞는다(여러 세션을 동시에 추적할 필요가 생기면
그때 요청 스코프 방식으로 바꾼다).
"""
_current_operation_session_id: str | None = None
# 세션과 세트로 같이 고정되는 값이라(OperationSession.deployment_id) 함께 보관한다 —
# event_log에 쓸 때마다 DB로 세션을 다시 조회해 deployment_id를 알아내지 않아도 된다.
_current_deployment_id: str | None = None


def set_current_operation_session(session_id: str | None, deployment_id: str | None) -> None:
    """lifespan이 세션을 시작한 직후 딱 한 번 호출한다. 둘을 항상 같이 설정해서
    "세션은 있는데 배포는 모른다" 같은 어중간한 상태가 생기지 않게 한다."""
    global _current_operation_session_id, _current_deployment_id
    _current_operation_session_id = session_id
    _current_deployment_id = deployment_id


def get_current_operation_session_id() -> str | None:
    """아직 세션이 시작되지 않았거나(DB 미연결 등으로) 시작에 실패했으면 `None` — 호출하는
    쪽(`event_log` 기록 함수)은 `None`이면 "역추적용 세션 연결 없이 기록"으로 처리한다
    (서비스 핵심 기능이 아니라 부가 정보이므로, 없다고 기록 자체를 막지 않는다)."""
    return _current_operation_session_id


def get_current_deployment_id() -> str | None:
    return _current_deployment_id
