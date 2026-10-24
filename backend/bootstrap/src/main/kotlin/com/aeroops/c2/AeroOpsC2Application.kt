package com.aeroops.c2

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

/**
 * Kotlin C2 Core 진입점(ADR 0004). 전환 기간에는 legacy FastAPI(8000)와 나란히 떠야 하므로
 * 포트를 8080으로 분리한다(`application.yml`).
 */
@SpringBootApplication
class AeroOpsC2Application

fun main(args: Array<String>) {
    runApplication<AeroOpsC2Application>(*args)
}
