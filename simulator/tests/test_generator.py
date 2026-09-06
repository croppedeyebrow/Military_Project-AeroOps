"""seed 재현성과 10대 × 1Hz 정상 데이터 생성 요건을 검증한다."""
from datetime import datetime, timezone

from simulator.generator import build_fleet, generate_frames, scenario_run_id

START_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _generate_all(seed: int, num_drones: int = 10, duration_s: float = 5.0):
    fleet = build_fleet(seed=seed, num_drones=num_drones, scenario_name="circle")
    return {
        drone.asset_id: generate_frames(
            drone, start_time=START_TIME, frequency_hz=1.0, duration_s=duration_s
        )
        for drone in fleet
    }


def test_same_seed_produces_identical_output():
    run_a = _generate_all(seed=42)
    run_b = _generate_all(seed=42)

    assert run_a.keys() == run_b.keys()
    for asset_id in run_a:
        dump_a = [f.model_dump(mode="json") for f in run_a[asset_id]]
        dump_b = [f.model_dump(mode="json") for f in run_b[asset_id]]
        assert dump_a == dump_b


def test_different_seed_produces_different_output():
    run_a = _generate_all(seed=42)
    run_b = _generate_all(seed=43)

    first_asset = "drone-01"
    dump_a = [f.model_dump(mode="json") for f in run_a[first_asset]]
    dump_b = [f.model_dump(mode="json") for f in run_b[first_asset]]
    assert dump_a != dump_b


def test_ten_drones_one_hz_generates_expected_frame_count():
    fleet_frames = _generate_all(seed=1, num_drones=10, duration_s=20 * 60.0)
    assert len(fleet_frames) == 10
    for frames in fleet_frames.values():
        assert len(frames) == 20 * 60  # 20분 × 1Hz


def test_scenario_run_id_encodes_scenario_and_seed():
    assert scenario_run_id("circle", 42) == "circle-seed42"
