package archfixture.modulith.valid

import org.springframework.modulith.Modulithic

/*
 * [위반 샘플 — 시험 전용] 정상 대조군: a가 선언된 대로 b의 공개 API만 쓴다. 검증이 통과해야 한다(규칙이 무조건 실패하는 것이 아님을 확인).
 * 목적: 아키텍처 규칙이 실제로 위반을 잡는지(= 규칙이 형식뿐이 아님을) 증명하기 위해 일부러 규칙을 어기거나
 *       지키는 코드를 둔다. 실제 업무 코드가 아니며 com.aeroops.c2 바깥(archfixture)에 있어 실제 모듈
 *       탐색·분석(ModularityTest, LayeringRulesTest의 실제 코드 검사)에 섞이지 않는다.
 * 연관: 이 샘플을 사용하는 시험은 bootstrap/src/test/.../ModularityTest.kt 또는 LayeringRulesTest.kt.
 */
/** 앱 루트 기준점. */
@Modulithic
class FixtureApp
