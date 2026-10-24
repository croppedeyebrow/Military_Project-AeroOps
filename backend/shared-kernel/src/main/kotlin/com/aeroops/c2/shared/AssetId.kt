package com.aeroops.c2.shared

/**
 * 관제 대상 기체의 식별자.
 *
 * 목적: `String`을 그대로 쓰면 `BootId`·`CommandId`와 순서를 바꿔 넘겨도 컴파일러가 모른다. 타입으로
 * 구분해 그런 실수를 컴파일 시점에 막는다. 규칙은 legacy 계약(`asset_id`: 최소 1자, 공백만으로 구성
 * 불가)과 동일하다 — 전환 중 Kotlin이 같은 입력을 같은 기준으로 받아야 하기 때문(Golden Replay).
 */
@JvmInline
value class AssetId(val value: String) {
    init {
        require(value.isNotBlank()) { "asset_id는 공백일 수 없다" }
    }

    override fun toString(): String = value
}
