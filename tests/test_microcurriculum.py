import itertools
from types import SimpleNamespace

import numpy as np
import pytest

from gangnamfly.microcurriculum import STAGES, MicroObjective, MicroTarget


def fixture(index=0):
    pose = np.array([0.0, 0.0, -0.05, 1.0, 0.0, 0.0, 0.0, 0.3])
    upright = pose.copy()
    upright[2] = 0.128
    upright[3:7] = [np.sqrt(0.5), 0.0, -np.sqrt(0.5), 0.0]
    base = SimpleNamespace(duration=36.07, fingerprint="source", source={}, sample=lambda _: upright.copy())
    loads = {"foot_load_fraction": 0.02, "other_load_fraction": 0.98}
    env = SimpleNamespace(
        qadr=np.array([7]),
        data=SimpleNamespace(qvel=np.zeros(7)),
        model=SimpleNamespace(geom=lambda _: SimpleNamespace(pos=np.array([0.0, 0.0, -0.132]))),
        support_loads=lambda: loads.copy(),
    )
    return MicroObjective(base, env, index), pose, loads


# Micro AC-1, AC-3: partial foot support yields a gradient; it is not standing.
def test_support_reward_is_dense_and_stage_pass_is_not_standing():
    obj, pose, loads = fixture()
    low = obj.measure(pose, 4.0)
    loads.update(foot_load_fraction=0.11, other_load_fraction=0.89)
    good = obj.measure(pose, 4.0)
    assert 0 < low["reward"] < good["reward"] <= 1
    assert good["stage_ok"] and not good["standing_ok"]
    times = np.arange(0.02, obj.target.duration + 0.001, 0.02)
    rows = [obj.measure(pose, t) for t in times]
    result = obj.quality(rows, obj.target.duration)
    assert result["passed"] and result["stage_fraction"] == 1 and result["standing_fraction"] == 0
    assert not obj.quality(rows[-1:], obj.target.duration)["passed"]
    rows[-2]["stage_ok"] = False
    assert not obj.quality(rows, obj.target.duration)["passed"]
    loads.update(foot_load_fraction=0.0, other_load_fraction=0.0)
    assert not obj.measure(pose, 4.0)["stage_ok"]


# Micro AC-2: constraints never relax; motion extends by at most .25 seconds.
def test_stage_constraints_are_monotone_and_use_control_tick_windows():
    assert len(STAGES) > 100
    assert len({s["id"] for s in STAGES}) == len(STAGES)
    physical = [s for s in STAGES if s["motion_seconds"] == 0]
    for previous, current in itertools.pairwise(physical):
        for key in ["foot_min", "height_fraction"]:
            assert current["criteria"][key] >= previous["criteria"][key]
        for key in ["other_max", "tilt_max", "speed_max", "angular_max", "height_error_max"]:
            assert current["criteria"][key] <= previous["criteria"][key]
        assert current["hold_seconds"] >= previous["hold_seconds"]
    motion = [s for s in STAGES if s["motion_seconds"] > 0]
    assert np.max(np.diff([0] + [s["motion_seconds"] for s in motion])) <= 0.250001
    assert motion[-1]["motion_seconds"] == pytest.approx(31.07)
    for s in STAGES:
        assert s["hold_seconds"] / 0.02 == pytest.approx(round(s["hold_seconds"] / 0.02))


# Micro AC-2, AC-5: reference pauses are explicit; no missing capture tail.
def test_micro_reference_and_standing_prerequisite():
    _obj, _, _ = fixture()
    base = SimpleNamespace(duration=36.07, source={}, fingerprint="x", sample=lambda t: t)
    for s in [next(s for s in STAGES if s["motion_seconds"]), STAGES[-1]]:
        target = MicroTarget(base, s)
        assert target.sample(2.5) == target.sample(5.5) == 2.5
        assert target.sample(5.6) == pytest.approx(2.6)
    assert MicroTarget(base, STAGES[-1]).sample(39.07) == 36.07


# Micro AC-2: a good preamble cannot conceal failure of every short motion frame.
def test_short_motion_cannot_pass_from_preamble_alone():
    index = next(i for i, s in enumerate(STAGES) if s["motion_seconds"])
    obj, pose, loads = fixture(index)
    pose[2] = 0.128
    pose[3:7] = [np.sqrt(0.5), 0.0, -np.sqrt(0.5), 0.0]
    loads.update(foot_load_fraction=1.0, other_load_fraction=0.0)
    end = np.ceil(obj.target.duration / 0.02) * 0.02
    rows = [obj.measure(pose, t) for t in np.arange(0.02, end + 0.001, 0.02)]
    assert obj.quality(rows, end)["passed"]
    for row in rows:
        if 5.5 < row["objective_time"] <= 5.76:
            row["tracking_ok"] = False
    result = obj.quality(rows, end)
    assert not result["passed"] and result["motion_tracking_fraction"] == 0.0


# Micro AC-1, AC-5: every cumulative constraint provides finite graded feedback.
def test_each_deficit_improvement_raises_reward_without_mutating_world():
    index = next(i for i, s in enumerate(STAGES) if s["label"].startswith("Sostener"))
    obj, pose, loads = fixture(index)
    pose[2] = obj.minimum_height - 0.04
    pose[3:7] = [1.0, 0.0, 0.0, 0.0]
    loads.update(foot_load_fraction=0.1, other_load_fraction=0.9)
    obj.environment.data.qvel[:6] = [2, 0, 0, 12, 0, 0]
    before = pose.copy()
    v = obj.environment.data.qvel.copy()
    initial = obj.measure(pose, 4.0)["reward"]
    assert 0 < initial < 1
    for field, better in [("foot_load_fraction", 0.2), ("other_load_fraction", 0.8)]:
        original = loads[field]
        loads[field] = better
        assert obj.measure(pose, 4.0)["reward"] > initial
        loads[field] = original
    for component in [0, 3]:
        obj.environment.data.qvel[component] -= 0.5
        assert obj.measure(pose, 4.0)["reward"] > initial
        obj.environment.data.qvel[:] = v
    raised = pose.copy()
    raised[2] += 0.01
    assert obj.measure(raised, 4.0)["reward"] > initial
    tilted = pose.copy()
    tilted[3:7] = [np.cos(0.05), 0.0, -np.sin(0.05), 0.0]
    assert obj.measure(tilted, 4.0)["reward"] > initial
    np.testing.assert_array_equal(pose, before)
    np.testing.assert_array_equal(obj.environment.data.qvel, v)


# Micro AC-2, AC-3: a complete final window cannot replace a complete episode.
def test_missing_preamble_or_prerequisite_samples_cannot_qualify():
    obj, pose, loads = fixture()
    loads.update(foot_load_fraction=0.2, other_load_fraction=0.8)
    rows = [obj.measure(pose, t) for t in np.arange(0.02, 4.001, 0.02)]
    assert obj.quality(rows, 4.0)["passed"]
    assert not obj.quality(rows[-10:], 4.0)["passed"]


# Micro AC-2: the full stage must actually perform its return-to-rest tail.
def test_full_stage_cannot_skip_every_return_to_rest_frame():
    obj, pose, loads = fixture(len(STAGES) - 1)
    pose[2] = 0.128
    pose[3:7] = [np.sqrt(0.5), 0.0, -np.sqrt(0.5), 0.0]
    loads.update(foot_load_fraction=1.0, other_load_fraction=0.0)
    end = np.ceil(obj.target.duration / 0.02) * 0.02
    rows = [obj.measure(pose, t) for t in np.arange(0.02, end + 0.001, 0.02)]
    assert obj.quality(rows, end)["passed"]
    for row in rows:
        if row["objective_time"] > 36.58:
            row["tracking_ok"] = False
    assert not obj.quality(rows, end)["passed"]
