/*
 * mission 모듈 — 경계 컨텍스트 "Mission Operations"(임무·경로·단계).
 *
 * 왜 의존성이 shared-kernel뿐인가: Context Map(docs/planning/10 §4)에서 Mission Operations는
 *   Command & Control의 상류(Published Language: mission/phase ID)이다. 상류는 하류를 알면 안 된다 —
 *   그러면 순환이 생기고 임무 규칙이 명령 규칙에 끌려간다.
 * 연관: 선언은 src/main/.../MissionModule.kt의 allowedDependencies와 반드시 일치해야 하며(불일치는
 *   bootstrap의 ModularityTest가 잡는다), 이 모듈을 쓰는 쪽은 command-control, incident다.
 */
plugins {
    id("java-library")
}

dependencies {
    implementation(project(":shared-kernel"))
    // @ApplicationModule / @PackageInfo 어노테이션만 필요하다(런타임 기능은 bootstrap이 가져온다).
    implementation("org.springframework.modulith:spring-modulith-api")
}
