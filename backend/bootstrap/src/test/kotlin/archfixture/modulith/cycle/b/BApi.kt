package archfixture.modulith.cycle.b

import archfixture.modulith.cycle.a.AApi

/** b가 a를 안다(b → a). a → b와 합쳐져 순환이 된다. */
class BApi(val a: AApi?)
