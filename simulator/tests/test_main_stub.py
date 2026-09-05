"""1단계에서는 CLI가 정상적으로 임포트되는지만 확인한다."""
from simulator.main import app


def test_app_exists():
    assert app is not None
