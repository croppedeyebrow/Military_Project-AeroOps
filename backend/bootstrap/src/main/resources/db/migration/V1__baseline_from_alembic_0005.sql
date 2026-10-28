-- =====================================================================================
-- V1: Baseline — legacy FastAPI(Alembic 0001~0005)가 만들던 최종 스키마와 동일한 스키마.
--
-- 왜 이 파일이 있나(근거):
--   ADR 0004(2026-10-24)에서 스키마 DDL의 소유를 Alembic에서 Kotlin(Flyway)으로 옮기기로 했다.
--   Alembic은 head 0005에서 동결한다. 이 파일은 그 시점의 스키마를 그대로 재현해서, 앞으로의 모든
--   변경(V2 이후)이 하나의 도구(Flyway)로 이어지게 하는 출발점이다.
--
-- 목적(두 경로):
--   · 빈 DB       : Flyway가 이 파일을 실행해 전체 스키마를 만든다.
--   · 기존 DB     : 이미 Alembic 0005까지 적용된 DB는 flyway baselineOnMigrate=true,
--                   baselineVersion=1 설정으로 "V1은 이미 적용됨"으로 기록만 하고 건너뛴다.
--                   (그래서 기존 데이터는 건드리지 않는다.)
--
-- 만든 방법(손으로 옮기지 않았다): Alembic head까지 적용한 PostGIS DB에서
--   pg_dump --schema-only --no-owner --no-privileges --no-comments -n public -T public.alembic_version
--   로 추출하고 다음만 정리했다 — ① 세션 설정(SET, set_config('search_path'))은 Flyway 연결을
--   오염시키므로 제거 ② PostGIS 이미지가 자체로 만든 확장(fuzzystrmatch, tiger, topology)과
--   CREATE SCHEMA public 제거 ③ alembic_version 테이블 제외(Alembic 전용 메타데이터).
--
-- 연관 코드:
--   · 원본 정의: legacy-backend/alembic/versions/0001 ~ 0005 (SQLAlchemy 모델은 legacy-backend/app/modules/*/models.py)
--   · 동등성 증명: bootstrap/src/test/.../MigrationGateTest (빈 DB 경로와 기존 DB 경로의 스키마를 비교)
--   · 규칙: 이 파일은 절대 수정하지 않는다(Flyway가 체크섬을 검증한다). 변경은 V2 이후 새 파일로 하고,
--           legacy가 쓰는 테이블은 legacy가 깨지지 않는 Expand 전용 변경만 한다(ADR 0004 "영향").
-- =====================================================================================

-- 우리 스키마가 필요로 하는 확장은 PostGIS 하나뿐이다(Alembic 0001도 이것만 만들었다).
CREATE EXTENSION IF NOT EXISTS postgis;

--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4
-- Dumped by pg_dump version 16.4

--
-- Name: alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alerts (
    id bigint NOT NULL,
    asset_id character varying NOT NULL,
    alert_type character varying NOT NULL,
    severity character varying NOT NULL,
    rule_version character varying NOT NULL,
    evidence jsonb NOT NULL,
    status character varying DEFAULT 'OPEN'::character varying NOT NULL,
    triggered_at timestamp with time zone NOT NULL,
    acknowledged_at timestamp with time zone,
    acknowledged_by character varying,
    resolved_at timestamp with time zone,
    resolved_by character varying,
    created_at timestamp with time zone DEFAULT now()
);

--
-- Name: alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.alerts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.alerts_id_seq OWNED BY public.alerts.id;

--
-- Name: asset_latest_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asset_latest_state (
    asset_id character varying NOT NULL,
    mission_id character varying,
    event_time timestamp with time zone NOT NULL,
    received_at timestamp with time zone NOT NULL,
    sequence_no integer NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    altitude_m double precision NOT NULL,
    "position" public.geometry(PointZ,4326),
    speed_mps double precision,
    heading_deg double precision,
    roll_deg double precision,
    pitch_deg double precision,
    yaw_deg double precision,
    battery_pct double precision NOT NULL,
    rssi_dbm double precision,
    flight_mode character varying,
    updated_at timestamp with time zone DEFAULT now()
);

--
-- Name: assets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assets (
    id character varying NOT NULL,
    asset_type character varying DEFAULT 'drone'::character varying NOT NULL,
    model_name character varying,
    status character varying DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id bigint NOT NULL,
    actor character varying NOT NULL,
    action character varying NOT NULL,
    target_type character varying NOT NULL,
    target_id character varying NOT NULL,
    result character varying DEFAULT 'SUCCESS'::character varying NOT NULL,
    detail jsonb,
    occurred_at timestamp with time zone DEFAULT now()
);

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;

--
-- Name: command_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.command_events (
    id integer NOT NULL,
    command_id character varying NOT NULL,
    event_no integer NOT NULL,
    event_type character varying NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    actor character varying,
    detail jsonb
);

--
-- Name: command_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.command_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: command_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.command_events_id_seq OWNED BY public.command_events.id;

--
-- Name: commands; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.commands (
    id character varying NOT NULL,
    idempotency_key character varying NOT NULL,
    target_asset_id character varying NOT NULL,
    command_type character varying NOT NULL,
    payload_hash character varying NOT NULL,
    requested_by character varying NOT NULL,
    approved_by character varying,
    issued_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    expected_asset_state_version integer,
    deployment_id character varying,
    status character varying DEFAULT 'DRAFT'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

--
-- Name: deployments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deployments (
    id character varying NOT NULL,
    git_sha character varying NOT NULL,
    image_tag character varying NOT NULL,
    schema_version character varying,
    rule_version character varying,
    config_version character varying,
    created_at timestamp with time zone DEFAULT now()
);

--
-- Name: event_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_log (
    id bigint NOT NULL,
    operation_session_id character varying,
    event_time timestamp with time zone NOT NULL,
    stream_sequence bigint NOT NULL,
    source_channel character varying NOT NULL,
    event_type character varying NOT NULL,
    correlation_id character varying,
    deployment_id character varying,
    payload jsonb,
    created_at timestamp with time zone DEFAULT now()
);

--
-- Name: event_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: event_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_log_id_seq OWNED BY public.event_log.id;

--
-- Name: geofences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geofences (
    id character varying NOT NULL,
    name character varying NOT NULL,
    zone_type character varying NOT NULL,
    polygon jsonb NOT NULL,
    geom public.geometry(Polygon,4326),
    created_at timestamp with time zone DEFAULT now()
);

--
-- Name: mission_routes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.mission_routes (
    id bigint NOT NULL,
    mission_id character varying NOT NULL,
    waypoints jsonb NOT NULL,
    route public.geometry(LineStringZ,4326),
    recorded_at timestamp with time zone DEFAULT now()
);

--
-- Name: mission_routes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.mission_routes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: mission_routes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.mission_routes_id_seq OWNED BY public.mission_routes.id;

--
-- Name: missions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.missions (
    id character varying NOT NULL,
    name character varying NOT NULL,
    status character varying DEFAULT 'PLANNED'::character varying NOT NULL,
    start_time timestamp with time zone,
    end_time timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

--
-- Name: operation_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.operation_sessions (
    id character varying NOT NULL,
    deployment_id character varying NOT NULL,
    started_at timestamp with time zone DEFAULT now(),
    ended_at timestamp with time zone,
    started_by character varying,
    created_at timestamp with time zone DEFAULT now()
);

--
-- Name: sync_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_sessions (
    id bigint NOT NULL,
    asset_id character varying NOT NULL,
    requested_at timestamp with time zone NOT NULL,
    reported_last_sequence_no integer NOT NULL,
    server_last_sequence_no integer,
    sequence_gap_count integer NOT NULL,
    reported_last_processed_command_id character varying,
    pending_command_ids jsonb,
    snapshot_reissued boolean NOT NULL,
    detail jsonb,
    created_at timestamp with time zone DEFAULT now()
);

--
-- Name: sync_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sync_sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: sync_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sync_sessions_id_seq OWNED BY public.sync_sessions.id;

--
-- Name: telemetry_frames; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.telemetry_frames (
    id bigint NOT NULL,
    asset_id character varying NOT NULL,
    mission_id character varying,
    schema_version integer DEFAULT 1 NOT NULL,
    event_time timestamp with time zone NOT NULL,
    received_at timestamp with time zone NOT NULL,
    sequence_no integer NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    altitude_m double precision NOT NULL,
    "position" public.geometry(PointZ,4326),
    speed_mps double precision,
    heading_deg double precision,
    roll_deg double precision,
    pitch_deg double precision,
    yaw_deg double precision,
    battery_pct double precision NOT NULL,
    rssi_dbm double precision,
    flight_mode character varying,
    created_at timestamp with time zone DEFAULT now()
);

--
-- Name: telemetry_frames_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.telemetry_frames_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: telemetry_frames_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.telemetry_frames_id_seq OWNED BY public.telemetry_frames.id;

--
-- Name: alerts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts ALTER COLUMN id SET DEFAULT nextval('public.alerts_id_seq'::regclass);

--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);

--
-- Name: command_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.command_events ALTER COLUMN id SET DEFAULT nextval('public.command_events_id_seq'::regclass);

--
-- Name: event_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_log ALTER COLUMN id SET DEFAULT nextval('public.event_log_id_seq'::regclass);

--
-- Name: mission_routes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mission_routes ALTER COLUMN id SET DEFAULT nextval('public.mission_routes_id_seq'::regclass);

--
-- Name: sync_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_sessions ALTER COLUMN id SET DEFAULT nextval('public.sync_sessions_id_seq'::regclass);

--
-- Name: telemetry_frames id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_frames ALTER COLUMN id SET DEFAULT nextval('public.telemetry_frames_id_seq'::regclass);

--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);

--
-- Name: asset_latest_state asset_latest_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_latest_state
    ADD CONSTRAINT asset_latest_state_pkey PRIMARY KEY (asset_id);

--
-- Name: assets assets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_pkey PRIMARY KEY (id);

--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);

--
-- Name: command_events command_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.command_events
    ADD CONSTRAINT command_events_pkey PRIMARY KEY (id);

--
-- Name: commands commands_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.commands
    ADD CONSTRAINT commands_idempotency_key_key UNIQUE (idempotency_key);

--
-- Name: commands commands_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.commands
    ADD CONSTRAINT commands_pkey PRIMARY KEY (id);

--
-- Name: deployments deployments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT deployments_pkey PRIMARY KEY (id);

--
-- Name: event_log event_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_log
    ADD CONSTRAINT event_log_pkey PRIMARY KEY (id);

--
-- Name: geofences geofences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geofences
    ADD CONSTRAINT geofences_pkey PRIMARY KEY (id);

--
-- Name: mission_routes mission_routes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mission_routes
    ADD CONSTRAINT mission_routes_pkey PRIMARY KEY (id);

--
-- Name: missions missions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.missions
    ADD CONSTRAINT missions_pkey PRIMARY KEY (id);

--
-- Name: operation_sessions operation_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operation_sessions
    ADD CONSTRAINT operation_sessions_pkey PRIMARY KEY (id);

--
-- Name: sync_sessions sync_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_sessions
    ADD CONSTRAINT sync_sessions_pkey PRIMARY KEY (id);

--
-- Name: telemetry_frames telemetry_frames_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_frames
    ADD CONSTRAINT telemetry_frames_pkey PRIMARY KEY (id);

--
-- Name: command_events uq_command_events_command_event_no; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.command_events
    ADD CONSTRAINT uq_command_events_command_event_no UNIQUE (command_id, event_no);

--
-- Name: telemetry_frames uq_telemetry_asset_sequence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_frames
    ADD CONSTRAINT uq_telemetry_asset_sequence UNIQUE (asset_id, sequence_no);

--
-- Name: idx_asset_latest_state_position; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_asset_latest_state_position ON public.asset_latest_state USING gist ("position");

--
-- Name: idx_geofences_geom; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_geofences_geom ON public.geofences USING gist (geom);

--
-- Name: idx_mission_routes_route; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mission_routes_route ON public.mission_routes USING gist (route);

--
-- Name: idx_telemetry_frames_position; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_telemetry_frames_position ON public.telemetry_frames USING gist ("position");

--
-- Name: ix_alerts_asset_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alerts_asset_status ON public.alerts USING btree (asset_id, status);

--
-- Name: ix_alerts_open; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_alerts_open ON public.alerts USING btree (asset_id) WHERE ((status)::text = 'OPEN'::text);

--
-- Name: ix_audit_logs_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_target ON public.audit_logs USING btree (target_type, target_id, occurred_at);

--
-- Name: ix_command_events_command_occurred; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_command_events_command_occurred ON public.command_events USING btree (command_id, occurred_at, event_no);

--
-- Name: ix_commands_target_status_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_commands_target_status_expires ON public.commands USING btree (target_asset_id, status, expires_at);

--
-- Name: ix_event_log_session_time_seq; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_event_log_session_time_seq ON public.event_log USING btree (operation_session_id, event_time, stream_sequence);

--
-- Name: ix_operation_sessions_deployment_ended; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operation_sessions_deployment_ended ON public.operation_sessions USING btree (deployment_id, ended_at);

--
-- Name: ix_sync_sessions_asset_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sync_sessions_asset_created ON public.sync_sessions USING btree (asset_id, created_at);

--
-- Name: ix_telemetry_asset_event_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_telemetry_asset_event_time ON public.telemetry_frames USING btree (asset_id, event_time DESC);

--
-- Name: ix_telemetry_position; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_telemetry_position ON public.telemetry_frames USING gist ("position");

--
-- Name: alerts alerts_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);

--
-- Name: asset_latest_state asset_latest_state_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_latest_state
    ADD CONSTRAINT asset_latest_state_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);

--
-- Name: command_events command_events_command_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.command_events
    ADD CONSTRAINT command_events_command_id_fkey FOREIGN KEY (command_id) REFERENCES public.commands(id);

--
-- Name: commands commands_target_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.commands
    ADD CONSTRAINT commands_target_asset_id_fkey FOREIGN KEY (target_asset_id) REFERENCES public.assets(id);

--
-- Name: mission_routes mission_routes_mission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.mission_routes
    ADD CONSTRAINT mission_routes_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES public.missions(id);

--
-- Name: sync_sessions sync_sessions_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_sessions
    ADD CONSTRAINT sync_sessions_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);

--
-- Name: telemetry_frames telemetry_frames_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_frames
    ADD CONSTRAINT telemetry_frames_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id);

--
-- PostgreSQL database dump complete
--
