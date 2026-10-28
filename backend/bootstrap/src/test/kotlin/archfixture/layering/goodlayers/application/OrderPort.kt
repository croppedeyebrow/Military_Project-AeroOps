package archfixture.layering.goodlayers.application

import archfixture.layering.goodlayers.domain.Order

/** application이 정의한 포트(인터페이스). 어댑터가 이를 구현한다. */
interface OrderPort {
    fun find(id: String): Order?
}
