import numpy as np

from gangnamfly.environment import FlybodyEnvironment


# AC: AC-1, AC-3
def test_native_body_and_physics_are_real():
    e = FlybodyEnvironment()
    assert e.model.nq == 109 and e.model.nu == 78
    assert e.model.opt.timestep == 0.0001
    before = e.data.qpos.copy()
    for _ in range(5):
        e.step(e.rest)
    assert e.data.time > 0.099
    assert np.isfinite(e.data.qpos).all()
    assert np.any(e.data.qpos != before)
    assert len(e.geometry()["geoms"]) > 50
