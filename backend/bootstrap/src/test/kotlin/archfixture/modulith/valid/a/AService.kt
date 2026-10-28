package archfixture.modulith.valid.a

import archfixture.modulith.valid.b.BApi

/** 선언된 대로 b의 공개 API만 사용한다. */
class AService(val b: BApi)
