package archfixture.layering.badadapters.adapter.outbound

/*
 * [위반 샘플 — 시험 전용] 어댑터끼리 결합: inbound(컨트롤러)가 outbound(저장소)를 직접 쥔다. 어댑터는 application을 거쳐서만 만나야 한다.
 * 목적: 아키텍처 규칙이 실제로 위반을 잡는지(= 규칙이 형식뿐이 아님을) 증명하기 위해 일부러 규칙을 어기거나
 *       지키는 코드를 둔다. 실제 업무 코드가 아니며 com.aeroops.c2 바깥(archfixture)에 있어 실제 모듈
 *       탐색·분석(ModularityTest, LayeringRulesTest의 실제 코드 검사)에 섞이지 않는다.
 * 연관: 이 샘플을 사용하는 시험은 bootstrap/src/test/.../ModularityTest.kt 또는 LayeringRulesTest.kt.
 */

/** outbound 어댑터 구현. */
class JpaStore
