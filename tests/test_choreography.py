import mujoco
import numpy as np

from gangnamfly.choreography import CapturedDance
from gangnamfly.environment import FlybodyEnvironment


# AC: AC-1, AC-2, AC-3 (docs/specs/demo-choreography.md)
def test_complete_capture_retargets_upright_without_mutating_live_state():
    env = FlybodyEnvironment()
    original = env.data.qpos.copy()
    dance = CapturedDance(env.model)
    assert dance.source_duration == 31.07
    assert dance.duration > dance.source_duration + 3
    poses = [dance.pose(t) for t in [0, 2.5, 5, 10, 15, 22, 30, dance.duration]]
    assert all(np.isfinite(q).all() for q in poses)
    # Upright long body axis: local +X points predominantly upward.
    from scipy.spatial.transform import Rotation

    for q in poses[1:-1]:
        up = Rotation.from_quat(q[[4, 5, 6, 3]]).apply([1, 0, 0])
        assert up[2] > 0.7
    assert np.ptp(np.array(poses[1:-1])[:, 2]) > 0.01
    assert np.max(np.ptp(np.array(poses[1:-1])[:, 7:], axis=0)) > 0.5
    for j in range(env.model.njnt):
        if env.model.jnt_limited[j]:
            values = np.array(poses)[:, env.model.jnt_qposadr[j]]
            assert np.all(values >= env.model.jnt_range[j, 0] - 1e-8)
            assert np.all(values <= env.model.jnt_range[j, 1] + 1e-8)
    np.testing.assert_allclose(poses[0], poses[-1], atol=1e-8)
    np.testing.assert_array_equal(original, env.data.qpos)


# AC: AC-1, AC-2 (docs/specs/demo-choreography.md)
def test_crossed_front_limbs_and_alternating_hind_step_follow_capture():
    env = FlybodyEnvironment()
    dance = CapturedDance(env.model)
    for seconds in np.linspace(0, 6, 120):
        env.data.qpos[:] = dance.pose(seconds)
    mujoco.mj_kinematics(env.model, env.data)
    expected = dance.targets(3.5)[2]
    actual = np.array([env.data.xpos[chain[3]] for chain in dance.chains])
    np.testing.assert_allclose(actual, expected, atol=0.003)
    # Left forelimb crosses right; one hind foot is lifted during this captured step.
    assert actual[0, 1] < actual[1, 1]
    assert actual[4, 2] - actual[5, 2] > 0.05


# AC-2, AC-5: a source label cannot authenticate edited arrays.
def test_capture_rejects_modified_payload_with_original_hash():
    import pytest

    from gangnamfly.prepare_demo import CAPTURE, validate_capture

    with np.load(CAPTURE, allow_pickle=False) as z:
        positions = z["positions"].copy()
        positions[100, 0, 0] += 0.01
        with pytest.raises(ValueError, match="array mismatch"):
            validate_capture(z["time"], positions, z["orientations"], z["segments"], z["source_sha256"])
