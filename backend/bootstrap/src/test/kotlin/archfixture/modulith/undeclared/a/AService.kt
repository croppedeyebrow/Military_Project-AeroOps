package archfixture.modulith.undeclared.a

import archfixture.modulith.undeclared.b.BApi

/** 규칙 위반: 허용 목록이 빈 a가 b를 사용한다(b의 API 자체는 공개라 '내부 접근'은 아니지만 선언 밖이다). */
class AService(val b: BApi)
