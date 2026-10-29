# Kotlin C2 Core 컨테이너 이미지.
#
# 왜 멀티스테이지인가: 빌드에는 JDK와 Gradle·의존성 캐시가 필요하지만, 실행에는 JRE와 jar만 있으면 된다.
# 한 단계로 만들면 최종 이미지에 빌드 도구가 그대로 남아 크기와 공격면이 커진다(8단계 보안 점검 대상).
#
# 연관: 로컬 개발은 ../backend/README.md의 ./gradlew bootRun, 서비스 정의는 infra/docker-compose.yml의
# c2-core, 수집 설정은 infra/prometheus/prometheus.yml.

# --- 빌드 단계 ---------------------------------------------------------------------------------
FROM eclipse-temurin:21-jdk AS build

WORKDIR /src

# 의존성 선언만 먼저 복사해 받아둔다. 소스만 바뀐 재빌드에서 의존성 다운로드를 건너뛰기 위함이다
# (Docker 레이어 캐시는 "바뀐 파일이 있는 레이어부터" 다시 만든다).
COPY gradle/ gradle/
COPY gradlew settings.gradle.kts build.gradle.kts ./
COPY shared-kernel/build.gradle.kts shared-kernel/
COPY mission/build.gradle.kts mission/
COPY operational-picture/build.gradle.kts operational-picture/
COPY safety-policy/build.gradle.kts safety-policy/
COPY audit/build.gradle.kts audit/
COPY command-control/build.gradle.kts command-control/
COPY incident/build.gradle.kts incident/
COPY bootstrap/build.gradle.kts bootstrap/
RUN chmod +x gradlew && ./gradlew --no-daemon dependencies --quiet || true

COPY . .
# 시험은 Testcontainers(= Docker)가 필요하므로 이미지 빌드 중에는 돌리지 않는다. 시험은 CI에서 돈다
# (.github/workflows/ci.yml의 backend 잡).
RUN ./gradlew --no-daemon bootJar -x test

# --- 실행 단계 ---------------------------------------------------------------------------------
FROM eclipse-temurin:21-jre

WORKDIR /app

# 루트로 실행하지 않는다(컨테이너 탈출 시 피해를 줄이기 위한 기본 조치).
RUN useradd --system --create-home --uid 10001 aeroops
USER aeroops

COPY --from=build --chown=aeroops:aeroops /src/bootstrap/build/libs/*-SNAPSHOT.jar app.jar

# legacy FastAPI가 8000을 쓰므로 전환 기간에는 8080으로 나란히 띄운다(application.yml).
EXPOSE 8080

# 컨테이너 환경에서는 로그 수집기가 읽기 좋은 JSON으로 내보낸다(로컬 개발은 사람이 읽는 기본 형식).
ENV C2_LOG_FORMAT=ecs

ENTRYPOINT ["java", "-jar", "app.jar"]
