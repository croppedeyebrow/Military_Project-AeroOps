package archfixture.layering.goodlayers.adapter.outbound

import archfixture.layering.goodlayers.application.OrderPort
import archfixture.layering.goodlayers.domain.Order

/** outbound 어댑터: 포트를 구현한다(의존 방향 adapter → application → domain). */
class JpaOrderPort : OrderPort {
    override fun find(id: String): Order? = null
}
