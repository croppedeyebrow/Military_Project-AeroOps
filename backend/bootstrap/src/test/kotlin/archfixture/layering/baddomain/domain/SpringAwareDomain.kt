package archfixture.layering.baddomain.domain

/*
 * [위반 샘플 — 시험 전용] domain이 프레임워크를 안다: domain 클래스에 Spring 스테레오타입이 붙어 있다. '도메인은 프레임워크 비의존' 규칙이 실패해야 한다.
 * 목적: 아키텍처 규칙이 실제로 위반을 잡는지(= 규칙이 형식뿐이 아님을) 증명하기 위해 일부러 규칙을 어기거나
 *       지키는 코드를 둔다. 실제 업무 코드가 아니며 com.aeroops.c2 바깥(archfixture)에 있어 실제 모듈
 *       탐색·분석(ModularityTest, LayeringRulesTest의 실제 코드 검사)에 섞이지 않는다.
 * 연관: 이 샘플을 사용하는 시험은 bootstrap/src/test/.../ModularityTest.kt 또는 LayeringRulesTest.kt.
 */

import org.springframework.stereotype.Component

/** 규칙 위반: 순수해야 할 domain이 Spring(@Component)에 의존한다. */
@Component
class SpringAwareDomain
