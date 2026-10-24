import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.dsl.KotlinJvmProjectExtension

// 루트 빌드 — 모든 하위 모듈이 공유하는 규칙만 둔다(플러그인 버전은 gradle/libs.versions.toml).
plugins {
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.spring) apply false
    alias(libs.plugins.spring.boot) apply false
}

val springBootVersion = libs.versions.spring.boot.get()

allprojects {
    group = "com.aeroops"
    version = "0.1.0-SNAPSHOT"

    repositories {
        mavenCentral()
    }
}

subprojects {
    apply(plugin = "org.jetbrains.kotlin.jvm")

    extensions.configure<KotlinJvmProjectExtension> {
        jvmToolchain(21)
        compilerOptions {
            jvmTarget.set(JvmTarget.JVM_21)
            // Spring의 null 안전성 어노테이션(@Nullable 등)을 Kotlin 타입에 엄격히 반영한다.
            freeCompilerArgs.add("-Xjsr305=strict")
            // 생성자 파라미터의 @Autowired 같은 어노테이션을 프로퍼티·필드에도 적용하는 Kotlin의 차기
            // 기본 동작(KT-73255)을 미리 켜서, 경고(=오류) 없이 Spring 생성자 주입을 쓴다.
            freeCompilerArgs.add("-Xannotation-default-target=param-property")
            allWarningsAsErrors.set(true)
        }
    }

    dependencies {
        // Spring Boot가 관리하는 의존성 버전을 모든 모듈에 적용한다(Spring Boot 플러그인을 쓰지
        // 않는 순수 라이브러리 모듈도 같은 버전 집합을 쓰게 하려는 것).
        "implementation"(platform("org.springframework.boot:spring-boot-dependencies:$springBootVersion"))
        "testImplementation"("org.jetbrains.kotlin:kotlin-test-junit5")
        "testRuntimeOnly"("org.junit.platform:junit-platform-launcher") // Gradle 9는 런처를 명시해야 한다
    }

    tasks.withType<Test>().configureEach {
        useJUnitPlatform()
    }
}
