import numpy as np
import pytest

from gangnamfly.experiment import Experiment


# AC: AC-1, AC-2, AC-3, AC-4, AC-6
@pytest.mark.integration
def test_full_connectome_loop_repeatability_and_motor_causality(tmp_path):
    e = Experiment(tmp_path)
    b = e.brain
    assert b.native.n == 166700
    assert len(b.native.post) == 25582938
    assert len(b.plasticity.edges) == 56850
    assert set(b.native.ids[np.concatenate([p["indices"] for p in b.mapping.dn])]) == {
        10045,
        10056,
        10360,
        523769,
        11074,
        512006,
    }
    e.begin(duration=0.1)
    first = []
    for _ in range(5):
        e.step()
        first.append(e.environment.data.qpos.copy())
    assert e.last_counts[b.mapping.motor_indices].sum() > 0
    assert (
        np.count_nonzero(b.native.drive[np.setdiff1d(np.arange(b.native.n), b.mapping.sensory_indices)]) == 0
    )
    assert b.plasticity.changed == 0
    summary = e.finish()
    e.begin(duration=0.1)
    for q in first:
        e.step()
        np.testing.assert_array_equal(e.environment.data.qpos, q)
    e.finish()
    assert (tmp_path / summary["id"] / "telemetry.npz").exists()
    # A silenced neural readout cannot keep executing a target choreography.
    e.motor.rates.fill(0)
    np.testing.assert_array_equal(e.motor.decode(np.zeros(b.native.n), 0.02), e.environment.rest)


# Curriculum AC-1: reward targets cannot act as a hidden motor policy.
@pytest.mark.integration
def test_curriculum_reward_cannot_supply_same_step_motor_commands(tmp_path):
    from types import SimpleNamespace

    from gangnamfly.microcurriculum import STAGES, MicroObjective

    e = Experiment(tmp_path)
    pose = e.environment.data.qpos.copy()
    pose[3:7] = [np.sqrt(0.5), 0.0, -np.sqrt(0.5), 0.0]
    base = SimpleNamespace(duration=36.07, fingerprint="test", source={}, sample=lambda _: pose.copy())
    e.objective = MicroObjective(base, e.environment, 0)
    initial = e.brain.plasticity.base.copy()
    e.begin("train", duration=0.02, initial_weights=initial)
    e.step()
    first = (e.environment.data.ctrl.copy(), e.environment.data.qpos.copy(), e.score)
    e.finish()
    # Same neural/physical initial conditions, incompatible reward target.
    pose[3:7] = [1.0, 0.0, 0.0, 0.0]
    e.objective = MicroObjective(
        base, e.environment, next(i for i, s in enumerate(STAGES) if s["motion_seconds"])
    )
    e.begin("train", duration=0.02, initial_weights=initial)
    e.step()
    np.testing.assert_array_equal(e.environment.data.ctrl, first[0])
    np.testing.assert_array_equal(e.environment.data.qpos, first[1])
    assert e.score != first[2]
    e.finish()
