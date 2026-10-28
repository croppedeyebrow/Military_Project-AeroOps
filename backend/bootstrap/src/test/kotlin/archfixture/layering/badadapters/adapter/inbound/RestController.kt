package archfixture.layering.badadapters.adapter.inbound

import archfixture.layering.badadapters.adapter.outbound.JpaStore

/** 규칙 위반: inbound 어댑터가 outbound 어댑터에 직접 의존한다(application·domain 규칙 우회). */
class RestController(val store: JpaStore)
