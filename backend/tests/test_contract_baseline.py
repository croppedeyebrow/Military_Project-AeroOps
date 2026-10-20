"""현행 외부 계약이 `tests/contracts/baseline/` 기준선과 달라지면 실패한다.

계약을 의도적으로 바꿨다면 `python scripts/export_contract_baseline.py`로 기준선을 다시
만들어 변경 이유와 함께 커밋한다(Kotlin 전환 중 비교 기준이 조용히 바뀌는 것을 막는다).
"""
import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_contract_baseline.py"
_spec = importlib.util.spec_from_file_location("export_contract_baseline", _SCRIPT)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize("name", sorted(_module.build_baseline()))
def test_contract_matches_baseline(name: str):
    expected_path = _module.BASELINE_DIR / name
    assert expected_path.exists(), f"기준선 파일 없음: {expected_path} (export 스크립트 실행 필요)"
    actual = _module.render(_module.build_baseline()[name])
    assert expected_path.read_text(encoding="utf-8") == actual
