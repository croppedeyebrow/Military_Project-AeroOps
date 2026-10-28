rootProject.name = "aeroops-c2-core"

/*
 * 멀티모듈 구성 — docs/planning/02_백엔드_아키텍처.md "코드 구조"와 docs/new_roadmap/02 (Day 2~3).
 *
 * 왜 Gradle 모듈로 나누나: 경계 컨텍스트가 서로의 내부를 몰래 쓰는 것을 "사람의 주의"가 아니라
 *   빌드가 막게 하기 위해서다. 모듈 A의 build.gradle.kts가 모듈 B를 의존성으로 선언하지 않으면 A의
 *   코드는 B의 클래스를 컴파일할 수 없다. 이 1차 방어선 위에, 같은 규칙을 Spring Modulith 검증이
 *   (bootstrap의 ModularityTest) 2차로 확인한다.
 *
 * 컨텍스트 ↔ 모듈 대응(docs/planning/13 §2 Context Map):
 *   mission(Mission Operations) / command-control(Command & Control) /
 *   operational-picture(Operational Picture) / safety-policy(Safety & Policy) /
 *   incident(Incident Management) / audit(Identity & Audit의 감사 부분)
 * Communications Resilience·Deployment Registry는 이후 단계(Rust 경계·배포 등록)에서 추가한다.
 */
include("shared-kernel")

include("mission")
include("operational-picture")
include("safety-policy")
include("audit")
include("command-control")
include("incident")

// 실행·조립 모듈은 마지막에 둔다(모든 컨텍스트 모듈을 조립하므로).
include("bootstrap")
