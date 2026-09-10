"""Kinematic human-to-fly retargeting, exclusively for the explicitly labeled DEMO.

Captured body displacement and limb targets drive bounded anatomical joint IK.
The extra middle limbs follow a reduced arm gesture beside the abdomen. This is
an artistic six-limb adaptation, not a neuromuscular model or physical controller.
"""

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from .prepare_demo import CAPTURE, validate_capture

GROUND = -0.132
LEGS = [(segment, side) for segment in ["T1", "T2", "T3"] for side in ["left", "right"]]


def smooth(value):
    v = np.clip(value, 0, 1)
    return v * v * (3 - 2 * v)


class CapturedDance:
    """Sample in chronological order; replay/scrubbing uses the frozen clip.

    Bounded IK warm-starts from the preceding pose, with a fixed seed for its
    initial branch search. Results are deterministic for the same sample schedule.
    """

    stand_seconds = 2.5
    finish_seconds = 2.5

    def __init__(self, model):
        if not CAPTURE.is_file():
            raise RuntimeError("Prepare the dance first: python -m gangnamfly.prepare_demo")
        with np.load(CAPTURE, allow_pickle=False) as source:
            self.times = source["time"]
            self.positions = source["positions"]
            self.orientations = source["orientations"]
            self.segments = list(source["segments"])
            validate_capture(
                self.times, self.positions, self.orientations, source["segments"], source["source_sha256"]
            )
            self.positions = self.positions.astype(float)
            self.orientations = self.orientations.astype(float)
        self.source_duration = float(self.times[-1])
        self.duration = self.stand_seconds + self.source_duration + self.finish_seconds
        self.model, self.data = model, mujoco.MjData(model)
        self.rest = model.qpos_spring.copy()
        self.limited = np.flatnonzero(model.jnt_limited)
        self.addresses = model.jnt_qposadr[self.limited]
        self.lower, self.upper = model.jnt_range[self.limited].T
        self.rest[self.addresses] = np.clip(self.rest[self.addresses], self.lower, self.upper)
        self.data.qpos[:] = self.rest
        self.previous = self.rest.copy()
        initial_rotation = Rotation.from_quat(self.orientations[0, 0, [1, 2, 3, 0]])
        self.align = Rotation.from_euler("z", -initial_rotation.as_euler("xyz")[2])
        self.origin = self.positions[0, 0].copy()
        self.origin[2] = 0
        self.leg_scale, self.arm_scale = 0.24, 0.24
        self.chains = []
        for segment, side in LEGS:
            suffix = f"{segment}_{side}"
            joints = [
                model.joint(f"{name}_{suffix}").id
                for name in ["coxa_abduct", "coxa_twist", "coxa", "femur", "tibia"]
            ]
            self.chains.append(
                (
                    model.jnt_qposadr[joints],
                    model.jnt_dofadr[joints],
                    model.jnt_range[joints],
                    model.body(f"tarsus4_{suffix}").id,
                    model.body(f"tibia_{suffix}").id,
                )
            )
        self.jac = np.zeros((3, model.nv))
        self.elbow_jac = np.zeros_like(self.jac)
        # Initial branch selection avoids trapping folded fly limbs at a joint
        # limit when the human starts with relaxed, downward-pointing arms.
        root, rotation, targets, elbows = self.targets(0)
        self.data.qpos[:3] = root
        self.data.qpos[3:7] = rotation.as_quat()[[3, 0, 1, 2]]
        rng = np.random.default_rng(64)
        for i, chain in enumerate(self.chains):
            qadr, _, limits, _, _ = chain
            best = self.solve(chain, targets[i], elbows[i], self.rest[qadr], 70)
            for seed in rng.uniform(limits[:, 0], limits[:, 1], (7, len(qadr))):
                result = self.solve(chain, targets[i], elbows[i], seed, 70)
                if result.cost < best.cost:
                    best = result
            self.data.qpos[qadr] = best.x
        self.previous[:] = self.data.qpos

    def solve(self, chain, target, elbow_target, seed, iterations):
        qadr, dofs, limits, end, elbow = chain
        seed = np.clip(seed, limits[:, 0] + 1e-9, limits[:, 1] - 1e-9)

        def residual(joints):
            self.data.qpos[qadr] = joints
            mujoco.mj_kinematics(self.model, self.data)
            return np.r_[
                self.data.xpos[end] - target,
                (self.data.xpos[elbow] - elbow_target) * 0.12,
                (joints - seed) * 0.0005,
            ]

        def jacobian(joints):
            self.data.qpos[qadr] = joints
            mujoco.mj_kinematics(self.model, self.data)
            mujoco.mj_comPos(self.model, self.data)
            mujoco.mj_jacBody(self.model, self.data, self.jac, None, end)
            mujoco.mj_jacBody(self.model, self.data, self.elbow_jac, None, elbow)
            return np.vstack([self.jac[:, dofs], self.elbow_jac[:, dofs] * 0.12, np.eye(len(dofs)) * 0.0005])

        return least_squares(
            residual,
            seed,
            jac=jacobian,
            bounds=limits.T,
            max_nfev=iterations,
            ftol=1e-6,
            xtol=1e-6,
            gtol=1e-8,
        )

    def sample(self, seconds):
        t = np.clip(seconds, 0, self.source_duration)
        i = min(max(0, np.searchsorted(self.times, t, side="right") - 1), len(self.times) - 2)
        w = (t - self.times[i]) / (self.times[i + 1] - self.times[i])
        pos = self.positions[i] * (1 - w) + self.positions[i + 1] * w
        qa, qb = self.orientations[i, 0], self.orientations[i + 1, 0]
        if np.dot(qa, qb) < 0:
            qb = -qb
        q = qa * (1 - w) + qb * w
        return pos, Rotation.from_quat(q[[1, 2, 3, 0]])

    def targets(self, seconds):
        p, rotation = self.sample(seconds)
        aligned = self.align.apply(p - self.origin)
        pelvis = aligned[0]
        root = pelvis * self.leg_scale + [0, 0, GROUND + 0.05]
        rotation = self.align * rotation
        orientation = rotation * Rotation.from_euler("y", -np.deg2rad(80))
        targets, elbows = [], []
        for segment, side in LEGS:
            label = side.title()
            sign = 1 if side == "left" else -1
            if segment == "T3":
                toe = aligned[self.segments.index(f"{label}Toe")]
                knee = aligned[self.segments.index(f"{label}LowerLeg")]
                target = toe * self.leg_scale + [0.025, 0, GROUND + 0.005]
                target[2] = max(GROUND + 0.005, target[2])
                elbow = knee * self.leg_scale + [0.025, 0, GROUND + 0.005]
            else:
                hand = aligned[self.segments.index(f"{label}Hand")] - aligned[4]
                forearm = aligned[self.segments.index(f"{label}ForeArm")] - aligned[4]
                if segment == "T1":
                    offset = rotation.apply([0.04, 0, 0.035])
                    target = root + offset + hand * self.arm_scale
                    elbow = root + offset + forearm * self.arm_scale
                else:
                    target = root + rotation.apply([0.095, sign * 0.055, -0.055]) + hand * 0.045
                    elbow = root + rotation.apply([0.035, sign * 0.085, -0.005])
            targets.append(target)
            elbows.append(elbow)
        return root, orientation, np.array(targets), np.array(elbows)

    def pose(self, seconds):
        source_time = np.clip(seconds - self.stand_seconds, 0, self.source_duration)
        root, orientation, targets, elbows = self.targets(source_time)
        self.data.qpos[:] = self.previous
        self.data.qpos[:3] = root
        self.data.qpos[3:7] = orientation.as_quat()[[3, 0, 1, 2]]
        for i, chain in enumerate(self.chains):
            qadr = chain[0]
            result = self.solve(chain, targets[i], elbows[i], self.previous[qadr], 24)
            self.data.qpos[qadr] = result.x
        self.previous[:] = self.data.qpos
        # Smoothly lift from the original six-legged posture and return at the end.
        envelope = smooth(seconds / self.stand_seconds) * smooth(
            (self.duration - seconds) / self.finish_seconds
        )
        result = self.rest * (1 - envelope) + self.data.qpos * envelope
        q = self.data.qpos[3:7].copy()
        if q[0] < 0:
            q *= -1
        result[3:7] = np.array([1, 0, 0, 0]) * (1 - envelope) + q * envelope
        result[3:7] /= np.linalg.norm(result[3:7])
        result[self.addresses] = np.clip(result[self.addresses], self.lower, self.upper)
        return result
