package com.aeroops.c2

import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.springframework.context.ApplicationEventPublisher
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Import
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.modulith.events.ApplicationModuleListener
import org.springframework.transaction.PlatformTransactionManager
import org.springframework.transaction.support.TransactionTemplate
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/**
 * Transactional Outbox(이벤트 발행 기록)가 실제로 동작하는지 확인한다.
 *
 * 왜 중요한가(근거): "상태 전이와 이벤트 발행은 같은 커밋"이 명령 처리의 불변조건이다
 * (docs/planning/02 "명령 불변조건"). legacy에서는 원본 저장 커밋 **이후** 단계가 실패하면 그 사실이
 * 재생 기록에 남지 않는 구멍이 있었다(docs/planning/13 §6). Kotlin에서는 Modulith의 발행 기록을 써서
 * 업무 트랜잭션과 같은 커밋으로 "보낼 이벤트"를 남기고, 전달은 그 뒤에 일어나게 한다.
 *
 * 이 시험이 증명하는 것:
 * 1. 이벤트를 발행하면 `event_publication`에 기록이 남는다(= 트랜잭션에 참여한다).
 * 2. 리스너가 성공하면 완료 처리된다(archive 모드라 보관 테이블로 옮겨진다).
 * 3. **업무 트랜잭션이 롤백되면 이벤트도 남지 않는다** — 같은 커밋이라는 말의 핵심.
 * 4. 리스너가 실패하면 기록이 미완료로 남는다(= 유실되지 않고 재시도 대상이 된다).
 *
 * 연관 코드: 스키마는 `db/migration/V2__event_publication_outbox.sql`, 설정은 `application.yml`의
 * `spring.modulith.events`, 실제 사용은 4단계(Command 상태 전이).
 */
@Testcontainers(disabledWithoutDocker = true)
@SpringBootTest
@Import(EventPublicationOutboxTest.ListenerConfig::class)
class EventPublicationOutboxTest(
    @Autowired private val publisher: ApplicationEventPublisher,
    @Autowired private val jdbc: JdbcTemplate,
    @Autowired private val transactionTemplate: TransactionTemplate,
    @Autowired private val probe: EventProbe,
) {
    companion object {
        @Container
        @ServiceConnection
        @JvmStatic
        val database = PostgisContainers.empty()
    }

    /** 시험용 도메인 이벤트. 실제로는 각 컨텍스트가 자기 이벤트를 정의한다(4단계). */
    data class SampleEvent(val id: String, val shouldFail: Boolean = false)

    /**
     * 리스너의 실행 상태를 담는 별도 객체.
     *
     * 왜 리스너 안에 두지 않나: `@ApplicationModuleListener`가 붙은 리스너는 Spring이 CGLIB 프록시로 감싼다.
     * 프록시는 대상 객체의 **필드를 복사하지 않으므로**, 시험이 주입받은 빈(프록시)의 필드를 직접 읽으면
     * 초기화되지 않은 값(null)을 본다. 실제로 이 시험을 처음 돌렸을 때 그 때문에 NPE가 났다.
     * 상태를 별도 빈으로 빼면 프록시와 무관하게 같은 객체를 리스너와 시험이 함께 본다.
     */
    class EventProbe {
        val handled = AtomicInteger(0)
        @Volatile
        var latch = CountDownLatch(1)
    }

    /**
     * 시험용 리스너.
     *
     * `@ApplicationModuleListener`는 Modulith가 제공하는 조합 어노테이션이다 — 트랜잭션 커밋 **이후**에
     * 비동기로 실행되며, 실행 전후로 발행 기록의 완료 여부를 관리한다. 이것이 "업무 커밋과 전달의 분리"다.
     */
    open class SampleEventListener(private val probe: EventProbe) {
        // open: @ApplicationModuleListener는 @Async·@Transactional을 포함하므로 Spring이 프록시를 만든다.
        // Kotlin 클래스·메서드는 기본이 final이라 그대로 두면 프록시 생성이 실패한다(실제로 확인).
        @ApplicationModuleListener
        open fun on(event: SampleEvent) {
            probe.handled.incrementAndGet()
            try {
                // 전달 실패(예: Redis 장애)를 흉내낸다 — 기록이 미완료로 남아야 한다.
                check(!event.shouldFail) { "의도된 전달 실패: ${event.id}" }
            } finally {
                probe.latch.countDown()
            }
        }
    }

    /** 시험 전용 빈 등록. 실제 앱에는 포함되지 않는다(test 소스셋). */
    class ListenerConfig {
        @Bean
        fun eventProbe() = EventProbe()

        @Bean
        fun sampleEventListener(probe: EventProbe) = SampleEventListener(probe)

        /** 트랜잭션 경계를 시험이 직접 제어하기 위해 필요하다(Spring Boot가 자동 등록하지는 않는다). */
        @Bean
        fun testTransactionTemplate(manager: PlatformTransactionManager) = TransactionTemplate(manager)
    }

    private fun countFor(table: String, id: String): Int = jdbc.queryForObject(
        "select count(*) from $table where serialized_event like ?",
        Int::class.java,
        "%$id%",
    )!!

    private fun publishInTransaction(event: SampleEvent, thenFail: Boolean = false) {
        probe.latch = CountDownLatch(1)
        runCatching {
            transactionTemplate.execute {
                publisher.publishEvent(event)
                check(!thenFail) { "의도된 업무 트랜잭션 실패" }
            }
        }
    }

    @Test
    fun `이벤트를 발행하면 기록이 남고 리스너 성공 후 완료 처리된다`() {
        val id = "ok-${System.nanoTime()}"
        publishInTransaction(SampleEvent(id))

        assertTrue(probe.latch.await(10, TimeUnit.SECONDS), "리스너가 실행되지 않았다")
        // archive 모드: 완료되면 본 테이블에서 사라지고 보관 테이블로 옮겨진다.
        val moved = (1..50).any {
            Thread.sleep(100)
            countFor("event_publication_archive", id) == 1 && countFor("event_publication", id) == 0
        }
        assertTrue(moved, "완료된 발행이 보관 테이블로 옮겨지지 않았다")
    }

    @Test
    fun `업무 트랜잭션이 롤백되면 이벤트 기록도 남지 않는다`() {
        val id = "rollback-${System.nanoTime()}"
        val before = probe.handled.get()

        publishInTransaction(SampleEvent(id), thenFail = true)

        Thread.sleep(1000) // 비동기 리스너가 실행될 기회를 준 뒤 확인한다
        assertEquals(0, countFor("event_publication", id), "롤백됐는데 발행 기록이 남았다")
        assertEquals(0, countFor("event_publication_archive", id), "롤백됐는데 보관 기록이 남았다")
        assertEquals(before, probe.handled.get(), "롤백됐는데 리스너가 실행됐다")
    }

    @Test
    fun `리스너가 실패하면 기록이 미완료로 남아 재시도 대상이 된다`() {
        val id = "fail-${System.nanoTime()}"
        publishInTransaction(SampleEvent(id, shouldFail = true))

        assertTrue(probe.latch.await(10, TimeUnit.SECONDS), "리스너가 실행되지 않았다")
        Thread.sleep(500)
        // 실패했으므로 완료되지 않는다 — 기록이 본 테이블에 남아 있어야 유실되지 않는다.
        assertEquals(1, countFor("event_publication", id), "실패한 발행 기록이 남아 있지 않다")
        assertEquals(0, countFor("event_publication_archive", id), "실패했는데 완료 처리됐다")
    }
}
