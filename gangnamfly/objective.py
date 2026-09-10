"""Score physical poses against a reference; never emit actuator commands."""

import numpy as np

CRITERION = {
    "joint_rmse_max": 0.25,
    "orientation_error_max": 0.35,
    "position_error_max": 0.05,  # Flybody uses centimeters.
    "tracking_fraction_min": 0.9,
}


class CapturedObjective:
    def __init__(self, target, qadr, criterion=None):
        self.target, self.qadr = target, qadr
        self.criterion = dict(CRITERION if criterion is None else criterion)

    def measure(self, qpos, seconds):
        target = self.target.sample(seconds)
        joint = float(np.sqrt(np.mean((qpos[self.qadr] - target[self.qadr]) ** 2)))
        orientation = float(2 * np.arccos(np.clip(abs(np.dot(qpos[3:7], target[3:7])), 0, 1)))
        position = float(np.linalg.norm(qpos[:3] - target[:3]))
        c = self.criterion
        return {
            "joint_rmse": joint,
            "orientation_error": orientation,
            "position_error": position,
            "tracking_ok": bool(
                joint <= c["joint_rmse_max"]
                and orientation <= c["orientation_error_max"]
                and position <= c["position_error_max"]
            ),
            "reward": float(
                0.45 * np.exp(-((joint / 0.8) ** 2))
                + 0.35 * np.exp(-(orientation**2))
                + 0.20 * np.exp(-((position / 0.15) ** 2))
            ),
        }

    def quality(self, rows, seconds):
        if not rows:
            return {"passed": False, "coverage": 0.0, "tracking_fraction": 0.0}
        fraction = float(np.mean([r["tracking_ok"] for r in rows]))
        coverage = min(1.0, seconds / self.target.duration)
        return {
            "joint_rmse": float(np.sqrt(np.mean([r["joint_rmse"] ** 2 for r in rows]))),
            "orientation_error": float(np.sqrt(np.mean([r["orientation_error"] ** 2 for r in rows]))),
            "position_error": float(np.sqrt(np.mean([r["position_error"] ** 2 for r in rows]))),
            "tracking_fraction": fraction,
            "coverage": coverage,
            "passed": coverage >= 1 and fraction >= self.criterion["tracking_fraction_min"],
        }
