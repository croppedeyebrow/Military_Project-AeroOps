/*
 * operational-picture 모듈 — 경계 컨텍스트 "Operational Picture"(관측·최신 상황·신선도/품질).
 *
 * 왜 의존성이 shared-kernel뿐인가: 장비 Wire 프레임을 도메인 관측으로 바꾼 사실을 쥐는 상류다.
 *   Incident(경보)·Command(Dispatch 직전 신선도 재검증)가 이 모듈을 읽는다. 상류가 하류를 알면
 *   "경보가 있으니 이 관측은 무시" 같은 역방향 영향이 생겨 상황도가 오염된다.
 * 연관: OperationalPictureModule.kt, 도메인 핵심은 domain/ObservationKey.kt(ADR 0005),
 *       현행 대응은 legacy-backend의 telemetry·ingestion·realtime 모듈(docs/planning/13 §2),
 *       이 모듈이 소유할 테이블: assets, telemetry_frames, asset_latest_state.
 */
plugins {
    id("java-library")
}

dependencies {
    implementation(project(":shared-kernel"))
    implementation("org.springframework.modulith:spring-modulith-api")
}
