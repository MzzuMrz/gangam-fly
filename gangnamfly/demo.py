"""Read-only kinematic reference preview, isolated from neural/physical execution."""

import math

import mujoco
import numpy as np

from .captured_target import load_target
from .prepare_demo import SOURCE_PAGE, SOURCE_SHA256


def build_clip(environment, fps=60):
    if not 1 <= fps <= 120:
        raise ValueError("Preview FPS must be within 1..120")
    model = environment.model
    data = mujoco.MjData(model)
    dance = load_target(environment)
    steps = math.ceil(dance.duration * fps)
    frames = []
    for seconds in np.linspace(0, dance.duration, steps + 1):
        data.qpos[:] = dance.sample(float(seconds))
        # Only compute Cartesian geometry. No integration, neural access or actuator commands.
        mujoco.mj_kinematics(model, data)
        geoms = []
        for index in environment.mesh_geoms:
            quaternion = np.empty(4)
            mujoco.mju_mat2Quat(quaternion, data.geom_xmat[index])
            geoms.append({"id": index, "pos": data.geom_xpos[index].tolist(), "quat": quaternion.tolist()})
        frames.append(
            {
                "time": float(seconds),
                "source_time": float(np.clip(seconds - 2.5, 0, dance.source["duration"])),
                "root": data.qpos[:7].tolist(),
                "geoms": geoms,
            }
        )
    return {
        "kind": "kinematic-reference",
        "duration": dance.duration,
        "stand_seconds": 2.5,
        "finish_seconds": 2.5,
        "source": {
            "title": "Xsens · Gangnam Style",
            "url": SOURCE_PAGE,
            "sha256": SOURCE_SHA256,
            "duration": dance.source["duration"],
            "frames": dance.source["frames"],
        },
        "target_hash": dance.fingerprint,
        "retarget_report": dance.report,
        "sample_hz": steps / dance.duration,
        "frames": frames,
    }
