package com.aeroops.c2

import archfixture.modulith.cycle.FixtureApp as CycleApp
import archfixture.modulith.internalaccess.FixtureApp as InternalAccessApp
import archfixture.modulith.undeclared.FixtureApp as UndeclaredApp
import archfixture.modulith.valid.FixtureApp as ValidApp
import com.aeroops.c2.audit.AuditModule
import com.aeroops.c2.commandcontrol.CommandControlModule
import com.aeroops.c2.incident.IncidentModule
import com.aeroops.c2.mission.MissionModule
import com.aeroops.c2.operationalpicture.OperationalPictureModule
import com.aeroops.c2.safetypolicy.SafetyPolicyModule
import com.tngtech.archunit.core.importer.ImportOption
import org.springframework.modulith.ApplicationModule
import org.springframework.modulith.core.ApplicationModules
import org.springframework.modulith.core.Violations
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

/**
 * 경계 컨텍스트 "사이"의 규칙(Spring Modulith)을 검증하는 시험.
 *
 * 무엇을 보나: ① 실제 코드가 모듈 규칙(순환 금지, 다른 모듈 내부 접근 금지, 선언하지 않은 모듈 의존 금지)을
 * 지키는지, ② 각 컨텍스트가 허용받은 의존 대상(= Context Map의 방향)이 문서와 같은지, ③ 규칙이 위반을
 * **실제로 잡는지**(위반 샘플).
 *
 * 왜 ③이 필요한가: 지금 실제 코드에는 모듈 간 import가 아직 없어서 ①은 비어 있는 채로도 통과한다. 위반
 * 샘플(`archfixture.modulith.*`)에서 검증이 실패하고 정상 대조군에서 통과해야 비로소 "검증이 작동한다"고
 * 말할 수 있다. 실제 코드에 모듈 간 의존이 생기는 3단계부터는 ①이 실질적인 방어선이 된다.
 *
 * 연관 코드: 각 컨텍스트 `*Module.kt`(allowedDependencies 선언), Gradle 의존성(각 모듈 build.gradle.kts),
 * 샘플 `archfixture.modulith.*`, 레이어(모듈 안) 규칙은 `LayeringRulesTest`, Context Map 근거는
 * docs/planning/10 §4와 docs/planning/13 §2.
 */
class ModularityTest {

    /**
     * Context Map이 정하는 "의존해도 되는 모듈". 키는 하류(의존하는 쪽), 값은 상류(의존 대상).
     * 문서(docs/planning/10 §4)의 방향이 바뀌면 이 표와 각 `*Module.kt`를 함께 바꿔야 한다 — 한쪽만
     * 바뀌면 아래 시험이 실패해 불일치를 알려준다.
     */
    private val expectedAllowed: Map<String, Set<String>> = mapOf(
        "mission" to emptySet(),
        "operationalpicture" to emptySet(),
        "safetypolicy" to emptySet(),
        "audit" to emptySet(),
        "commandcontrol" to setOf("mission", "safetypolicy", "operationalpicture", "audit"),
        "incident" to setOf("operationalpicture", "safetypolicy", "mission", "audit"),
    )

    private fun declared(type: Class<*>): Set<String> =
        type.getAnnotation(ApplicationModule::class.java).allowedDependencies.toSet()

    /**
     * 위반 샘플(`archfixture.modulith.*`)용 모듈 분석기.
     *
     * 왜 ImportOption이 필요한가: Modulith는 기본적으로 시험 소스의 클래스를 분석에서 제외한다.
     * 샘플은 시험 소스에 있으므로 모든 위치를 포함하도록 옵션을 준다("No classes found" 방지).
     * 실제 코드 검증(`ApplicationModules.of(AeroOpsC2Application)`)에는 이 옵션을 쓰지 않는다 —
     * 시험 코드가 실제 검증 결과에 섞이면 안 되기 때문이다.
     */
    private fun fixtureModules(root: Class<*>): ApplicationModules =
        ApplicationModules.of(root, ImportOption { true })

    // ① 실제 코드 ---------------------------------------------------------------------------

    @Test
    fun `실제 코드베이스는 모듈 규칙을 위반하지 않는다`() {
        ApplicationModules.of(AeroOpsC2Application::class.java).verify()
    }

    @Test
    fun `컨텍스트 6개와 공유 커널이 모듈로 탐지된다`() {
        val names = ApplicationModules.of(AeroOpsC2Application::class.java)
            .stream().map { it.identifier.toString() }.toList().toSet()
        assertEquals(expectedAllowed.keys + "shared", names)
    }

    // ② 선언된 허용 목록 = Context Map -------------------------------------------------------

    @Test
    fun `각 컨텍스트가 선언한 허용 의존 목록이 Context Map과 같다`() {
        val actual = mapOf(
            "mission" to declared(MissionModule::class.java),
            "operationalpicture" to declared(OperationalPictureModule::class.java),
            "safetypolicy" to declared(SafetyPolicyModule::class.java),
            "audit" to declared(AuditModule::class.java),
            "commandcontrol" to declared(CommandControlModule::class.java),
            "incident" to declared(IncidentModule::class.java),
        )
        assertEquals(expectedAllowed, actual)
    }

    @Test
    fun `선언된 의존 그래프에는 순환이 없다`() {
        // 모듈 사이 순환은 Modulith가 "실제 import"에서 잡지만, 선언 자체가 순환이면 어떤 코드를 짜도
        // 설계가 모순이다. 설계 단계에서 먼저 막기 위해 선언 그래프도 직접 검사한다.
        fun hasCycleFrom(start: String, path: Set<String>): Boolean =
            expectedAllowed.getValue(start).any { next -> next in path || hasCycleFrom(next, path + next) }
        expectedAllowed.keys.forEach { node ->
            assertTrue(!hasCycleFrom(node, setOf(node)), "선언 그래프에 순환이 있다: $node")
        }
    }

    @Test
    fun `command-control과 incident는 서로를 알지 못한다(독립성)`() {
        // 경보는 명령 처리와 독립이어야 한다(IncidentModule.kt 주석). 허용 목록에 서로가 없음을 직접 고정.
        assertTrue("incident" !in expectedAllowed.getValue("commandcontrol"))
        assertTrue("commandcontrol" !in expectedAllowed.getValue("incident"))
    }

    // ③ 위반 샘플: 검증이 실제로 잡는지 -----------------------------------------------------------

    @Test
    fun `다른 모듈의 내부 타입을 쓰면 검증이 실패한다`() {
        val error = assertFailsWith<Violations> {
            fixtureModules(InternalAccessApp::class.java).verify()
        }
        assertTrue(error.message.contains("Hidden"), error.message)
    }

    @Test
    fun `모듈 순환 의존이 있으면 검증이 실패한다`() {
        val error = assertFailsWith<Violations> {
            fixtureModules(CycleApp::class.java).verify()
        }
        assertTrue(error.message.contains("ycle"), error.message) // "Cycle"/"cycle" 둘 다 허용
    }

    @Test
    fun `선언하지 않은 모듈에 의존하면 검증이 실패한다`() {
        val error = assertFailsWith<Violations> {
            fixtureModules(UndeclaredApp::class.java).verify()
        }
        assertTrue(error.message.contains("BApi"), error.message)
    }

    // ④ 정상 대조군 --------------------------------------------------------------------------

    @Test
    fun `선언한 대로만 의존하면 검증이 통과한다`() {
        fixtureModules(ValidApp::class.java).verify()
    }
}
