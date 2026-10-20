# 2단계 — Kotlin·Spring Boot 기반 (Day 2~3)

## 목표

Kotlin C2 Core의 실행·모듈·DB·보안·관측성 기반을 만든다.

## 작업

- JDK 21, Kotlin, Spring Boot, Gradle Kotlin DSL 구성
- Spring Modulith 경계: mission, command-control, operational-picture, safety-policy, incident, audit
- 각 모듈에 `domain/application/adapter-in/adapter-out` 구조 적용
- Spring Modulith·ArchUnit 의존성 검사
- Spring MVC, Validation, Security OIDC/JWT 골격
- Spring Data JPA, PostgreSQL/PostGIS, Flyway Baseline
- Transactional Outbox 기반 테이블과 Publisher 골격
- Actuator, Micrometer, OpenTelemetry, JSON Log
- JUnit/Kotest/Testcontainers와 CI Job

## 완료 게이트

빈 DB와 기존 DB Snapshot 모두에서 Migration이 성공하고, 모듈 금지 의존성이 CI에서 차단된다.
