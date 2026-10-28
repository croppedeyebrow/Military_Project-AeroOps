package com.aeroops.c2

import com.tngtech.archunit.core.importer.ClassFileImporter
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

/**
 * 모듈 안 레이어 규칙(`LayeringRules`)을 실행하는 시험.
 *
 * 구성이 두 겹인 이유: "규칙이 실제 코드에 통과한다"만으로는 규칙이 아무것도 잡지 못해도(또는 검사 대상이
 * 비어 있어도) 통과한다. 그래서 ① 실제 코드에 규칙을 적용하고, ② 일부러 규칙을 어긴 샘플
 * (`archfixture.layering.*`)에서 규칙이 **실패하는지**, 지킨 대조군에서는 **통과하는지** 함께 확인한다.
 * 이 두 겹이 있어야 "규칙이 작동한다"는 주장이 성립한다.
 *
 * 연관 코드: 규칙 정의 `LayeringRules`, 샘플 `archfixture.layering.*`(같은 test 소스셋),
 * 실제 domain 코드 첫 사례 `operationalpicture/domain/ObservationKey`, 모듈 간 경계는 `ModularityTest`.
 */
class LayeringRulesTest {
    private val importer = ClassFileImporter()

    private fun fixture(name: String) = importer.importPackages("archfixture.layering.$name")

    // ① 실제 코드 ---------------------------------------------------------------------------

    @Test
    fun `실제 코드는 모든 레이어 규칙을 지킨다`() {
        val real = importer.importPackages("com.aeroops.c2")
        LayeringRules.all.forEach { (_, rule) -> rule.check(real) }
    }

    @Test
    fun `실제 domain 코드가 검사 대상에 실제로 포함된다(규칙이 빈 집합에 통과하는 것이 아니다)`() {
        val real = importer.importPackages("com.aeroops.c2")
        // ObservationKey는 첫 실제 domain 코드다. 이것이 잡히지 않으면 위 시험은 아무것도 검사하지 않은 것.
        val domainClasses = real.filter { it.packageName.endsWith(".domain") }
        assertTrue(
            domainClasses.any { it.simpleName == "ObservationKey" },
            "domain 레이어 클래스가 분석 대상에 없다: ${domainClasses.map { it.name }}",
        )
    }

    // ② 위반 샘플: 규칙이 실제로 잡는지 -----------------------------------------------------------

    @Test
    fun `domain이 Spring을 알면 규칙이 실패한다`() {
        val error = assertFailsWith<AssertionError> {
            LayeringRules.domainIsFrameworkFree.check(fixture("baddomain"))
        }
        assertTrue(error.message!!.contains("SpringAwareDomain"), error.message)
    }

    @Test
    fun `application이 adapter 구현을 직접 쥐면 규칙이 실패한다`() {
        val error = assertFailsWith<AssertionError> {
            LayeringRules.applicationDoesNotDependOnAdapters.check(fixture("badapplication"))
        }
        assertTrue(error.message!!.contains("UseCase"), error.message)
    }

    @Test
    fun `inbound 어댑터가 outbound 어댑터를 직접 쥐면 규칙이 실패한다`() {
        val error = assertFailsWith<AssertionError> {
            LayeringRules.inboundAndOutboundAdaptersAreIndependent.check(fixture("badadapters"))
        }
        assertTrue(error.message!!.contains("RestController"), error.message)
    }

    // ③ 정상 대조군: 규칙이 무조건 실패하는 것이 아님 -------------------------------------------------

    @Test
    fun `규칙을 모두 지킨 구성은 전체 규칙을 통과한다`() {
        val good = fixture("goodlayers")
        LayeringRules.all.forEach { (_, rule) -> rule.check(good) }
    }

    @Test
    fun `규칙이 세 개 정의되어 있다`() {
        // 규칙을 실수로 지우거나 목록에서 빠뜨리면 알 수 있도록 개수를 고정한다.
        assertEquals(3, LayeringRules.all.size)
    }
}
