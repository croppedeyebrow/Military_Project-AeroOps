package archfixture.modulith.internalaccess.b

import archfixture.modulith.internalaccess.a.internal.Hidden

/** 규칙 위반: 모듈 b가 a의 내부 타입 Hidden을 직접 쥐고 있다. */
class BService(val hidden: Hidden)
