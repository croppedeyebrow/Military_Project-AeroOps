package archfixture.layering.goodlayers.adapter.inbound

import archfixture.layering.goodlayers.application.OrderPort

/** inbound 어댑터: 포트만 사용하고 outbound 어댑터 구현은 모른다. */
class OrderController(val port: OrderPort)
