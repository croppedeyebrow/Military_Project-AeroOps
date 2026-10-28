-- =====================================================================================
-- V2: 이벤트 발행 기록(Transactional Outbox) 테이블.
--
-- 왜 필요한가(근거): docs/planning/02_백엔드_아키텍처.md "명령 불변조건" — "상태 전이와 Outbox Event는
--   동일 DB 트랜잭션으로 기록한다". 상태는 DB에 저장됐는데 이벤트 발행이 실패하면(또는 그 반대),
--   두 시스템의 사실이 어긋난다. legacy에서 실제로 겪은 문제이기도 하다: 원본 저장은 커밋됐는데
--   그 뒤 단계(event_log·경보)가 실패하면 "저장은 됐지만 재생 기록에는 없는 프레임"이 생겼다
--   (docs/planning/13 §6 "한 프레임 처리의 커밋 범위").
--
-- 목적: 업무 트랜잭션과 **같은 커밋**으로 "발행할 이벤트"를 이 테이블에 남긴다. 실제 전달은 그 뒤에
--   비동기로 일어나고, 성공하면 completion_date가 채워진다. 실패하면 미완료로 남아 재시도할 수 있다.
--
-- 이 스키마의 출처: 직접 설계한 것이 아니라 Spring Modulith 2.1.2가 제공하는 표준 스키마
--   (jar 안 org/springframework/modulith/events/jdbc/schemas/v2/schema-postgresql.sql)를 그대로 옮겼다.
--   Modulith가 이 컬럼 구조를 전제로 조회·완료 처리를 하므로 임의로 바꾸면 안 된다.
--   스키마 자동 생성(spring.modulith.events.jdbc.schema-initialization)은 끄고 Flyway가 소유한다 —
--   DDL 주체를 하나로 유지하기 위함(ADR 0004).
--
-- legacy 영향 없음: 새 테이블만 추가하므로 legacy FastAPI는 이 변경을 모른다(ADR 0004의 "Expand 전용" 규칙).
--
-- 연관 코드:
--   · 사용 예시와 동작 확인: bootstrap/src/test/.../EventPublicationOutboxTest
--   · 설정: bootstrap/src/main/resources/application.yml 의 spring.modulith.events
--   · 이후 단계: 4단계(Command)에서 명령 상태 전이가 이 메커니즘으로 이벤트를 남긴다.
-- =====================================================================================

CREATE TABLE IF NOT EXISTS event_publication
(
  id                     UUID NOT NULL,
  listener_id            TEXT NOT NULL,
  event_type             TEXT NOT NULL,
  serialized_event       TEXT NOT NULL,
  publication_date       TIMESTAMP WITH TIME ZONE NOT NULL,
  completion_date        TIMESTAMP WITH TIME ZONE,
  status                 TEXT,
  completion_attempts    INT,
  last_resubmission_date TIMESTAMP WITH TIME ZONE,
  PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS event_publication_serialized_event_hash_idx ON event_publication USING hash(serialized_event);
CREATE INDEX IF NOT EXISTS event_publication_by_completion_date_idx ON event_publication (completion_date);

-- 완료된 발행 기록을 옮겨 보관하는 테이블. 본 테이블이 무한히 커지지 않게 하면서도 "무슨 일이 있었는지"는
-- 남긴다(운용 추적성 — docs/planning/13의 불변조건 7 "운용 세션에서 역추적").
CREATE TABLE IF NOT EXISTS event_publication_archive
(
  id                     UUID NOT NULL,
  listener_id            TEXT NOT NULL,
  event_type             TEXT NOT NULL,
  serialized_event       TEXT NOT NULL,
  publication_date       TIMESTAMP WITH TIME ZONE NOT NULL,
  completion_date        TIMESTAMP WITH TIME ZONE,
  status                 TEXT,
  completion_attempts    INT,
  last_resubmission_date TIMESTAMP WITH TIME ZONE,
  PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS event_publication_archive_serialized_event_hash_idx ON event_publication_archive USING hash(serialized_event);
CREATE INDEX IF NOT EXISTS event_publication_archive_by_completion_date_idx ON event_publication_archive (completion_date);
