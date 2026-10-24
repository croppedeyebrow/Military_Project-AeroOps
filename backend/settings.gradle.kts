rootProject.name = "aeroops-c2-core"

// docs/planning/02_백엔드_아키텍처.md "코드 구조"의 멀티모듈 배치. 2-1에서는 실행 모듈(bootstrap)과
// 공유 커널만 만들고, 경계 컨텍스트 모듈(mission-operations 등)은 2-2에서 추가한다.
include("shared-kernel")
include("bootstrap")
