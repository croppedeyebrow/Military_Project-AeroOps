// Shared Kernel — 모든 경계 컨텍스트가 공유하는 ID·시간·단위 Value Object만 둔다(planning/02).
// 순수 Kotlin: Spring·JPA·통신 SDK에 의존하지 않는다(domain은 프레임워크를 모른다는 원칙).
plugins {
    // 루트에서 kotlin-jvm 플러그인을 적용하므로 별도 선언 없이 의존성만 정의한다.
    id("java-library")
}
