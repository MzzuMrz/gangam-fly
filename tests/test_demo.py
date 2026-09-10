import numpy as np

from gangnamfly.demo import build_clip
from gangnamfly.environment import FlybodyEnvironment


# AC: AC-1, AC-2, AC-3 (docs/specs/demo-choreography.md)
def test_demo_moves_limbs_periodically_without_mutating_environment():
    env = FlybodyEnvironment()
    env.step(env.rest)
    original = {k: getattr(env.data, k).copy() for k in ["qpos", "qvel", "ctrl", "act"]}
    time = env.data.time
    clip = build_clip(env, fps=5)
    assert clip["kind"] == "kinematic-reference"
    assert clip["source"]["duration"] == 31.07
    assert clip["source"]["frames"] == 7451
    first, last = clip["frames"][0], clip["frames"][-1]
    assert last["time"] == clip["duration"]
    assert clip["duration"] == 36.07
    for a, b in zip(first["geoms"], last["geoms"]):
        np.testing.assert_allclose(a["pos"], b["pos"], atol=1e-10)
        np.testing.assert_allclose(a["quat"], b["quat"], atol=1e-10)
    positions = np.array([[g["pos"] for g in f["geoms"]] for f in clip["frames"]])
    assert np.isfinite(positions).all()
    assert np.max(np.ptp(positions, axis=0)) > 0.01
    assert np.ptp([f["root"][2] for f in clip["frames"]]) > 0.1
    assert min(f["source_time"] for f in clip["frames"]) == 0
    assert max(f["source_time"] for f in clip["frames"]) == 31.07
    for name, array in original.items():
        np.testing.assert_array_equal(getattr(env.data, name), array)
    assert env.data.time == time
