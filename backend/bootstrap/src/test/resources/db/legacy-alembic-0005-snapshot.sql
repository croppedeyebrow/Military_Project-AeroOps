-- =====================================================================================
-- 시험 전용 스냅샷: "Alembic 0005까지 적용된 기존 DB + 실제 앱이 만든 데이터"
--
-- 왜 필요한가: Unit 2-3의 완료 게이트는 "빈 DB와 기존 DB 모두에서 Flyway 마이그레이션이 성공"이다.
--   기존 DB 경로를 시험하려면 Alembic으로 만든 실제 DB 상태가 필요한데, Gradle 시험에서는 Alembic(Python)을
--   돌릴 수 없으므로 그 결과를 이 파일로 고정해 둔다.
-- 만든 방법: Alembic head(0005)까지 적용한 PostGIS DB에 legacy FastAPI 앱을 실제로 띄워 텔레메트리 3건과
--   명령 1건(생성·승인)을 보내고, `pg_dump --inserts --no-owner --no-privileges --no-comments -n public`로
--   추출했다(SET·extension 줄은 제거). 즉 기체·텔레메트리·최신상태·명령·이벤트·event_log·감사·배포/세션
--   기록·지오메트리 컬럼이 실제 경로로 생성된 값이다.
-- 사용처: MigrationGateTest — 이 파일을 빈 DB에 복원한 뒤 Flyway(baselineOnMigrate)를 돌려 ① V1이 다시
--   실행되지 않고 ② 데이터가 보존되고 ③ 스키마가 빈 DB 경로와 같은지 확인한다.
-- 연관: backend/bootstrap/src/main/resources/db/migration/V1__baseline_from_alembic_0005.sql
-- =====================================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4
-- Dumped by pg_dump version 16.4

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);

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
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.alembic_version VALUES ('0005');

--
-- Data for Name: alerts; Type: TABLE DATA; Schema: public; Owner: -
--

--
-- Data for Name: asset_latest_state; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.asset_latest_state VALUES ('snapshot-drone-01', NULL, '2026-10-25 08:56:00+00', '2026-10-25 08:56:08.381686+00', 2, 37.3947, 127.1112, 52, '01010000A0E61000002CD49AE61DC75F4098DD938785B242400000000000004A40', NULL, NULL, NULL, NULL, NULL, 88, -70, 'AUTO', '2026-10-25 08:56:07.551983+00');

--
-- Data for Name: assets; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.assets VALUES ('snapshot-drone-01', 'drone', NULL, 'active', '2026-10-25 08:56:07.551983+00');

--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.audit_logs VALUES (1, 'operator-1', 'command.create', 'command', 'snap-cmd-1', 'SUCCESS', '{"command_type": "LOITER", "target_asset_id": "snapshot-drone-01"}', '2026-10-25 08:56:09.130974+00');
INSERT INTO public.audit_logs VALUES (2, 'approver-1', 'command.approve', 'command', 'snap-cmd-1', 'SUCCESS', '{"resulting_status": "DISPATCHED"}', '2026-10-25 08:56:09.575749+00');

--
-- Data for Name: command_events; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.command_events VALUES (1, 'snap-cmd-1', 1, 'CREATED', '2026-10-25 08:56:09.089075+00', 'operator-1', '{"payload": {}, "issued_at": "2026-10-25T08:56:08Z", "command_id": "snap-cmd-1", "expires_at": "2026-10-25T09:56:08Z", "approved_by": null, "command_type": "LOITER", "requested_by": "operator-1", "deployment_id": null, "schema_version": 1, "idempotency_key": "snap-key-1", "target_asset_id": "snapshot-drone-01", "expected_asset_state_version": null}');
INSERT INTO public.command_events VALUES (2, 'snap-cmd-1', 2, 'APPROVED', '2026-10-25 08:56:09.484235+00', 'approver-1', 'null');
INSERT INTO public.command_events VALUES (3, 'snap-cmd-1', 3, 'DISPATCHED', '2026-10-25 08:56:09.543834+00', 'system', 'null');

--
-- Data for Name: commands; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.commands VALUES ('snap-cmd-1', 'snap-key-1', 'snapshot-drone-01', 'LOITER', '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a', 'operator-1', 'approver-1', '2026-10-25 08:56:08+00', '2026-10-25 09:56:08+00', NULL, NULL, 'DISPATCHED', '2026-10-25 08:56:09.070691+00', '2026-10-25 08:56:09.537928+00');

--
-- Data for Name: deployments; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.deployments VALUES ('deploy-57e5fbdf', 'local-dev', 'local-dev', '0005', 'v1', NULL, '2026-10-25 08:56:06.284862+00');

--
-- Data for Name: event_log; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.event_log VALUES (1, 'opsession-ca42c686', '2026-10-25 08:55:57+00', 0, 'telemetry', 'telemetry.received', NULL, 'deploy-57e5fbdf', '{"is_new": true, "asset_id": "snapshot-drone-01", "sequence_no": 0, "latest_updated": true}', '2026-10-25 08:56:07.622254+00');
INSERT INTO public.event_log VALUES (2, 'opsession-ca42c686', '2026-10-25 08:55:58+00', 1, 'telemetry', 'telemetry.received', NULL, 'deploy-57e5fbdf', '{"is_new": true, "asset_id": "snapshot-drone-01", "sequence_no": 1, "latest_updated": true}', '2026-10-25 08:56:08.065276+00');
INSERT INTO public.event_log VALUES (3, 'opsession-ca42c686', '2026-10-25 08:56:00+00', 2, 'telemetry', 'telemetry.received', NULL, 'deploy-57e5fbdf', '{"is_new": true, "asset_id": "snapshot-drone-01", "sequence_no": 2, "latest_updated": true}', '2026-10-25 08:56:08.48986+00');
INSERT INTO public.event_log VALUES (4, 'opsession-ca42c686', '2026-10-25 08:56:09.089075+00', 1, 'command', 'command.CREATED', 'snap-cmd-1', 'deploy-57e5fbdf', '{"command_id": "snap-cmd-1", "target_asset_id": "snapshot-drone-01"}', '2026-10-25 08:56:09.110843+00');
INSERT INTO public.event_log VALUES (5, 'opsession-ca42c686', '2026-10-25 08:56:09.484235+00', 2, 'command', 'command.APPROVED', 'snap-cmd-1', 'deploy-57e5fbdf', '{"actor": "approver-1", "command_id": "snap-cmd-1", "target_asset_id": "snapshot-drone-01"}', '2026-10-25 08:56:09.510368+00');
INSERT INTO public.event_log VALUES (6, 'opsession-ca42c686', '2026-10-25 08:56:09.543834+00', 3, 'command', 'command.DISPATCHED', 'snap-cmd-1', 'deploy-57e5fbdf', '{"actor": "system", "command_id": "snap-cmd-1", "target_asset_id": "snapshot-drone-01"}', '2026-10-25 08:56:09.560324+00');

--
-- Data for Name: geofences; Type: TABLE DATA; Schema: public; Owner: -
--

--
-- Data for Name: mission_routes; Type: TABLE DATA; Schema: public; Owner: -
--

--
-- Data for Name: missions; Type: TABLE DATA; Schema: public; Owner: -
--

--
-- Data for Name: operation_sessions; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.operation_sessions VALUES ('opsession-ca42c686', 'deploy-57e5fbdf', '2026-10-25 08:56:06.313634+00', NULL, NULL, '2026-10-25 08:56:06.313634+00');

--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: -
--

--
-- Data for Name: sync_sessions; Type: TABLE DATA; Schema: public; Owner: -
--

--
-- Data for Name: telemetry_frames; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.telemetry_frames VALUES (1, 'snapshot-drone-01', NULL, 1, '2026-10-25 08:55:57+00', '2026-10-25 08:56:07.527063+00', 0, 37.3947, 127.1112, 50, '01010000A0E61000002CD49AE61DC75F4098DD938785B242400000000000004940', NULL, NULL, NULL, NULL, NULL, 90, -70, 'AUTO', '2026-10-25 08:56:07.551983+00');
INSERT INTO public.telemetry_frames VALUES (2, 'snapshot-drone-01', NULL, 1, '2026-10-25 08:55:58+00', '2026-10-25 08:56:07.944716+00', 1, 37.3947, 127.1112, 51, '01010000A0E61000002CD49AE61DC75F4098DD938785B242400000000000804940', NULL, NULL, NULL, NULL, NULL, 89, -70, 'AUTO', '2026-10-25 08:56:08.02923+00');
INSERT INTO public.telemetry_frames VALUES (3, 'snapshot-drone-01', NULL, 1, '2026-10-25 08:56:00+00', '2026-10-25 08:56:08.381686+00', 2, 37.3947, 127.1112, 52, '01010000A0E61000002CD49AE61DC75F4098DD938785B242400000000000004A40', NULL, NULL, NULL, NULL, NULL, 88, -70, 'AUTO', '2026-10-25 08:56:08.392653+00');

--
-- Name: alerts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.alerts_id_seq', 1, false);

--
-- Name: audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.audit_logs_id_seq', 2, true);

--
-- Name: command_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.command_events_id_seq', 3, true);

--
-- Name: event_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.event_log_id_seq', 6, true);

--
-- Name: mission_routes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.mission_routes_id_seq', 1, false);

--
-- Name: sync_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sync_sessions_id_seq', 1, false);

--
-- Name: telemetry_frames_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.telemetry_frames_id_seq', 3, true);

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);

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
