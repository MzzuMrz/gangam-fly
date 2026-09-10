"""One deterministic target built from authenticated capture; no disk-cache trust."""

import hashlib
from dataclasses import dataclass

import mujoco
import numpy as np

from .choreography import GROUND, CapturedDance
from .prepare_demo import SOURCE_PAGE, SOURCE_SHA256


@dataclass
class CapturedTarget:
    time: np.ndarray
    qpos: np.ndarray
    duration: float
    source: dict
    fingerprint: str
    report: dict

    def sample(self, seconds):
        t = float(np.clip(seconds, 0, self.duration))
        i = min(max(1, int(np.searchsorted(self.time, t, side="right"))), len(self.time) - 1)
        weight = (t - self.time[i - 1]) / (self.time[i] - self.time[i - 1])
        out = self.qpos[i - 1] * (1 - weight) + self.qpos[i] * weight
        # Adjacent quaternion signs are canonicalized when the target is built.
        out[3:7] /= np.linalg.norm(out[3:7])
        return out


def load_target(environment):
    """Build once per environment. Source arrays have pinned external digests."""
    if hasattr(environment, "_captured_target"):
        return environment._captured_target
    dance = CapturedDance(environment.model)
    time = np.append(np.arange(0, dance.duration, 1 / 60), dance.duration)
    qpos: list[np.ndarray] = []
    residuals, feet_z = [], []
    for seconds in time:
        pose = dance.pose(float(seconds))
        if qpos and np.dot(qpos[-1][3:7], pose[3:7]) < 0:
            pose[3:7] *= -1
        qpos.append(pose)
        dance.data.qpos[:] = pose
        mujoco.mj_kinematics(dance.model, dance.data)
        feet_z.append(min(dance.data.xpos[c[3], 2] for c in dance.chains))
        if dance.stand_seconds <= seconds <= dance.duration - dance.finish_seconds:
            targets = dance.targets(seconds - dance.stand_seconds)[2]
            residuals.append(
                [np.linalg.norm(dance.data.xpos[c[3]] - t) for c, t in zip(dance.chains, targets)]
            )
    q = np.asarray(qpos)
    if q.shape != (len(time), environment.model.nq) or not np.isfinite(q).all():
        raise ValueError("Retargeted capture contains invalid poses")
    if not np.allclose(np.linalg.norm(q[:, 3:7], axis=1), 1, atol=1e-10):
        raise ValueError("Retargeted capture has invalid root quaternions")
    fingerprint = hashlib.sha256(time.tobytes() + q.tobytes()).hexdigest()
    report = {
        "finite": True,
        "sample_hz": 60,
        "duration_exact": bool(time[-1] == dance.duration),
        "time_strict": bool(np.all(np.diff(time) > 0)),
        "max_joint_step_radians": float(np.abs(np.diff(q[:, environment.qadr], axis=0)).max()),
        "max_root_step_radians": float(
            (2 * np.arccos(np.clip(np.abs(np.sum(q[:-1, 3:7] * q[1:, 3:7], axis=1)), 0, 1))).max()
        ),
        "endpoint_residual_max_cm": float(np.max(residuals)),
        "endpoint_residual_rms_cm": float(np.sqrt(np.mean(np.square(residuals)))),
        "endpoint_floor_penetration_max_cm": max(0.0, float(GROUND - min(feet_z))),
        "interpretation": "Artistic constrained retargeting; kinematic reference does not establish physical feasibility.",
    }
    target = CapturedTarget(
        time,
        q,
        dance.duration,
        {
            "title": "Xsens · Gangnam Style",
            "url": SOURCE_PAGE,
            "sha256": SOURCE_SHA256,
            "duration": dance.source_duration,
            "frames": len(dance.times),
        },
        fingerprint,
        report,
    )
    environment._captured_target = target
    return target
