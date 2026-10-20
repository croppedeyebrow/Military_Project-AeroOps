# Kotlin·Spring Boot·DDD

## 적용 위치

Mission Operations, Command & Control, Operational Picture, Safety & Policy, Incident, Identity & Audit를 소유한다.

## 공부할 개념

- Kotlin null safety, sealed interface, value/data class
- Aggregate, Entity, Value Object, Domain Service, Repository Port
- Spring Boot DI·Configuration·Lifecycle
- Spring Modulith 모듈 경계·Event·Module Test
- Spring MVC, Validation, Security
- JPA 영속성 Context, Lock, Transaction Propagation
- Transactional Outbox와 낙관적 잠금
- JUnit, Kotest, Testcontainers, ArchUnit

## 적용 원칙

- Domain은 Spring·JPA·통신 DTO를 모른다.
- Context 간 JPA Entity·Repository 공유를 금지한다.
- 명령 상태를 문자열과 nullable 값으로 표현하지 않는다.
- Coroutine을 Blocking JPA의 성능 해결책으로 오용하지 않는다.

## 실습

Command Aggregate에 동시 승인, 만료, ACK 손실과 효과 검증을 구현하고 불법 전이가 DB에 Commit되지 않는지 시험한다.
