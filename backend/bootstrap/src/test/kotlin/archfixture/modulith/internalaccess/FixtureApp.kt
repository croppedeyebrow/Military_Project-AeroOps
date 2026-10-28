package archfixture.modulith.internalaccess

import org.springframework.modulith.Modulithic

/*
 * [위반 샘플 — 시험 전용] 모듈 internal 접근: b가 a의 내부 타입(a.internal.Hidden)을 사용한다. Modulith 검증이 실패해야 한다.
 * 목적: 아키텍처 규칙이 실제로 위반을 잡는지(= 규칙이 형식뿐이 아님을) 증명하기 위해 일부러 규칙을 어기거나
 *       지키는 코드를 둔다. 실제 업무 코드가 아니며 com.aeroops.c2 바깥(archfixture)에 있어 실제 모듈
 *       탐색·분석(ModularityTest, LayeringRulesTest의 실제 코드 검사)에 섞이지 않는다.
 * 연관: 이 샘플을 사용하는 시험은 bootstrap/src/test/.../ModularityTest.kt 또는 LayeringRulesTest.kt.
 */
/** Modulith가 이 패키지를 애플리케이션 루트로 삼는 기준점. Modulith는 루트 타입에 @Modulithic(또는 @SpringBootApplication)을 요구한다. */
@Modulithic
class FixtureApp
