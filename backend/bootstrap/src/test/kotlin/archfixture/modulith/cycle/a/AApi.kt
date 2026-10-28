package archfixture.modulith.cycle.a

import archfixture.modulith.cycle.b.BApi

/** a가 b를 안다(a → b). */
class AApi(val b: BApi?)
