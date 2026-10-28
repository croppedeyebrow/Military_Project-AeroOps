/*
 * incident 모듈 — 경계 컨텍스트 "Incident Management"(경보·사건·중복 억제·조치 이력).
 *
 * 왜 의존성이 4개인가: 경보는 관측을 규칙에 대입해 만들어진다.
 *   - operational-picture: 규칙 입력(배터리·RSSI 등 관측)
 *   - safety-policy: 지오펜스 이탈 규칙이 쓰는 구역·정책
 *   - mission: 경보가 영향을 주는 임무를 연결
 *   - audit: 경보 확인·해제 기록
 *   command-control은 일부러 뺐다 — 경보는 명령 실행 여부에 좌우되면 안 되고(독립성), 반대로
 *   command-control이 incident를 아는 것도 금지한다(양쪽 모두 허용하면 순환 위험).
 * 연관: IncidentModule.kt의 allowedDependencies와 일치, 현행 대응은 legacy-backend/app/modules/alert
 *       (규칙 엔진 rules.py), 소유할 테이블은 alerts(incidents는 이후 단계).
 */
plugins {
    id("java-library")
}

dependencies {
    implementation(project(":shared-kernel"))
    implementation(project(":operational-picture"))
    implementation(project(":safety-policy"))
    implementation(project(":mission"))
    implementation(project(":audit"))
    implementation("org.springframework.modulith:spring-modulith-api")
}
