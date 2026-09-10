from types import SimpleNamespace

import numpy as np
import pytest

from gangnamfly.curriculum import STAGES, CurriculumObjective
from gangnamfly.environment import FlybodyEnvironment


def fixture():
    pose = np.array([0.0, 0.0, 0.15, np.sqrt(0.5), 0.0, -np.sqrt(0.5), 0.0, 0.3])
    base = SimpleNamespace(duration=36.07, fingerprint="source", source={}, sample=lambda _: pose.copy())
    env = SimpleNamespace(
        qadr=np.array([7]),
        data=SimpleNamespace(qvel=np.zeros(7)),
        support_loads=lambda: {"foot_load_fraction": 1.0, "other_load_fraction": 0.0},
    )
    return base, env, pose


# AC-1, AC-3: only real upright/stable/supported body state passes standing.
def test_standing_is_not_pose_imitation_or_one_good_frame():
    base, env, pose = fixture()
    objective = CurriculumObjective(base, env, 0)
    rows = [objective.measure(pose, t) for t in np.arange(0.02, 4.001, 0.02)]
    assert objective.quality(rows, 4.0)["passed"]
    # Legs may find their own supported pose: no exact captured joint matching.
    other = pose.copy()
    other[7] = 2.0
    assert objective.measure(other, 4.0)["reward"] == objective.measure(pose, 4.0)["reward"]
    assert not objective.quality(rows[-1:], 4.0)["passed"]
    assert not objective.quality(rows[:100], 2.0)["passed"]
    fallen = pose.copy()
    fallen[3:7] = [1, 0, 0, 0]
    bad = objective.measure(fallen, 3.5)
    assert not bad["standing_ok"]
    rows[174] = bad
    assert not objective.quality(rows, 4.0)["passed"]
    env.support_loads = lambda: {"foot_load_fraction": 1e-9, "other_load_fraction": 0.0}
    assert not objective.measure(pose, 4.0)["standing_ok"]
    env.support_loads = lambda: {"foot_load_fraction": 1.0, "other_load_fraction": 0.0}
    env.data.qvel[3] = 20.0
    assert not objective.measure(pose, 4.0)["standing_ok"]


# AC-2, AC-3: motion tracking cannot erase the standing prerequisite.
def test_motion_prefix_and_full_target_keep_prerequisite_and_complete_source():
    base, env, pose = fixture()
    for index in range(2, len(STAGES)):
        objective = CurriculumObjective(base, env, index)
        end = objective.target.duration
        rows = [objective.measure(pose, t) for t in np.arange(0.02, end + 0.02, 0.02)]
        assert objective.quality(rows, rows[-1]["objective_time"])["passed"]
        rows[130]["standing_ok"] = False
        assert not objective.quality(rows, rows[-1]["objective_time"])["passed"]
    full = CurriculumObjective(base, env, len(STAGES) - 1)
    assert full.target.duration == pytest.approx(base.duration + 1.0)
    assert full.target.fingerprint != base.fingerprint


# AC-3: initial self contacts cannot masquerade as ground support.
def test_support_uses_loaded_floor_foot_contacts_and_readonly_measurement():
    env = FlybodyEnvironment()
    before = env.data.qpos.copy()
    assert env.data.ncon > 0
    assert env.support_loads()["foot_load_fraction"] == 0
    for _ in range(5):
        env.step(env.rest)
    # Inspect the actual contacts independently of the method under test.
    import mujoco

    floor = env.model.geom("floor").id
    loaded = []
    for i, c in enumerate(env.data.contact):
        if floor not in (c.geom1, c.geom2):
            continue
        other = int(c.geom2 if c.geom1 == floor else c.geom1)
        force = np.zeros(6)
        mujoco.mj_contactForce(env.model, env.data, i, force)
        name = env.model.geom(other).name or ""
        if name.startswith(("tarsus", "tarsal_claw")) and force[0] > 1e-9:
            loaded.append(force[0])
    q = env.data.qpos.copy()
    assert env.support_loads()["foot_load_fraction"] == pytest.approx(
        sum(loaded) / (env.model.body_mass.sum() * np.linalg.norm(env.model.opt.gravity))
    )
    np.testing.assert_array_equal(q, env.data.qpos)
    assert not np.array_equal(before, q)


def test_body_supported_stand_does_not_pass_and_prefix_time_mapping():
    from gangnamfly.curriculum import StageTarget

    base, env, pose = fixture()
    env.support_loads = lambda: {"foot_load_fraction": 0.51, "other_load_fraction": 0.49}
    assert not CurriculumObjective(base, env, 0).measure(pose, 4.0)["standing_ok"]
    base.sample = lambda t: t
    for stage in STAGES[2:-1]:
        target = StageTarget(base, stage)
        assert target.sample(1.0) == 1.0
        assert target.sample(2.5) == target.sample(3.5) == 2.5
        assert target.sample(3.6) == pytest.approx(2.6)
        end = 2.5 + stage["motion_seconds"]
        assert target.sample(target.duration - 1.0) == end
        assert target.sample(target.duration) == end
    assert StageTarget(base, STAGES[-1]).sample(base.duration + 1.0) == base.duration
