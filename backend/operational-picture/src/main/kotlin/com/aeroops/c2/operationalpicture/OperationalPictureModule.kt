package com.aeroops.c2.operationalpicture

import org.springframework.modulith.ApplicationModule
import org.springframework.modulith.PackageInfo

/**
 * "Operational Picture" 경계 컨텍스트의 Modulith 모듈 메타데이터(구조 설명은 MissionModule.kt 참고).
 *
 * 목적: 관측 사실(위치·자세·배터리·통신)과 그 신선도·품질을 소유하고, 다른 컨텍스트에는 공개 API
 * (조회 Port, 관측 이벤트)로만 제공한다. 의존 대상이 없는 이유는 상류 컨텍스트라서다.
 *
 * 연관 코드:
 * - 레이어: `domain`(순수 규칙, 예: ObservationKey), `application`(유스케이스), `adapter.inbound`
 *   (REST/WebSocket/Redis 수신), `adapter.outbound`(JPA 저장). 규칙은 bootstrap의 `LayeringRulesTest`.
 * - 이 모듈을 쓰는 쪽: command-control(Dispatch 직전 Freshness 재검증, docs/planning/13 불변조건 4번),
 *   incident(관측 기반 경보 규칙).
 * - 이관 비교 기준: Golden Replay의 telemetry 시나리오 11종(tests/contracts/golden).
 */
@PackageInfo
@ApplicationModule(displayName = "Operational Picture", allowedDependencies = [])
class OperationalPictureModule
