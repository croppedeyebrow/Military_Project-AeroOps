package archfixture.layering.badapplication.application

import archfixture.layering.badapplication.adapter.outbound.JpaStore

/** 규칙 위반: 유스케이스가 어댑터 구현(JpaStore)에 직접 의존한다. 올바른 구조는 application이 포트(인터페이스)를 정의하고 adapter가 구현하는 것. */
class UseCase(val store: JpaStore)
