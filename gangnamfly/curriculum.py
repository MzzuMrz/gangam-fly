"""Physical prerequisites and captured prefixes; scoring never supplies controls."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from .config import DT
from .objective import CapturedObjective

STAND_CRITERION = {
    "tilt_max": 0.35,
    "height_error_max_cm": 0.03,
    "speed_max_cm_s": 0.2,
    "angular_speed_max_rad_s": 2.0,
    "foot_load_fraction_min": 0.5,
    "other_load_fraction_max": 0.05,
    "required_fraction": 1.0,
}
STAGES = [
    {"id": "stand", "label": "Incorporarse", "duration": 4.0, "hold_seconds": 1.0, "motion_seconds": 0.0},
    {
        "id": "balance",
        "label": "Mantener el equilibrio",
        "duration": 8.0,
        "hold_seconds": 3.0,
        "motion_seconds": 0.0,
    },
    {
        "id": "gesture",
        "label": "Primer movimiento · 2 s",
        "duration": 6.5,
        "hold_seconds": 1.0,
        "motion_seconds": 2.0,
    },
    {
        "id": "sequence4",
        "label": "Secuencia · 4 s",
        "duration": 8.5,
        "hold_seconds": 1.0,
        "motion_seconds": 4.0,
    },
    {
        "id": "sequence8",
        "label": "Secuencia · 8 s",
        "duration": 12.5,
        "hold_seconds": 1.0,
        "motion_seconds": 8.0,
    },
    {
        "id": "full",
        "label": "Captura completa",
        "duration": 37.07,
        "hold_seconds": 1.0,
        "motion_seconds": 31.07,
    },
]


@dataclass
class StageTarget:
    base: Any
    stage: dict

    @property
    def duration(self):
        return self.base.duration + 1.0 if self.stage["id"] == "full" else self.stage["duration"]

    @property
    def source(self):
        return self.base.source

    @property
    def fingerprint(self):
        return hashlib.sha256(
            (self.base.fingerprint + json.dumps(self.stage, sort_keys=True)).encode()
        ).hexdigest()

    def sample(self, seconds):
        seconds = float(np.clip(seconds, 0, self.duration))
        if not self.stage["motion_seconds"] or seconds <= 3.5:
            source_time = min(seconds, 2.5)
        else:
            source_time = seconds - 1.0
            if self.stage["id"] != "full":
                source_time = min(source_time, 2.5 + self.stage["motion_seconds"])
        return self.base.sample(source_time)


class CurriculumObjective(CapturedObjective):
    def __init__(self, base, environment, stage_index):
        if type(stage_index) is not int or not 0 <= stage_index < len(STAGES):
            raise ValueError("Invalid curriculum stage")
        self.stage_index, self.stage = stage_index, dict(STAGES[stage_index])
        self.environment = environment
        super().__init__(StageTarget(base, self.stage), environment.qadr)
        self.upright_height = float(base.sample(2.5)[2])
        self.stand_only = not bool(self.stage["motion_seconds"])

    def descriptor(self):
        label = (
            (
                "Cabeza hacia arriba ≤0,35 rad; altura ±0,03 cm; velocidad ≤0,2 cm/s; "
                "giro ≤2 rad/s; patas soportan ≥50% del peso y resto del cuerpo ≤5% durante todo el último "
                f"{self.stage['hold_seconds']:g} s."
            )
            if self.stand_only
            else (
                "Seguimiento de ≥90% del tramo y 1 s de postura erguida estable "
                "con apoyo de patas antes del movimiento."
            )
        )
        return {
            **self.stage,
            "duration": self.target.duration,
            "index": self.stage_index,
            "count": len(STAGES),
            "criterion_label": label,
            "stand_criterion": STAND_CRITERION,
            "tracking_criterion": self.criterion,
            "target_hash": self.target.fingerprint,
        }

    def measure(self, qpos, seconds):
        measured = super().measure(qpos, seconds)
        w, x, y, z = qpos[3:7]
        tilt = float(np.arccos(np.clip(2 * (x * z - w * y), -1, 1)))  # anatomical +X dot world +Z
        height_error = abs(float(qpos[2]) - self.upright_height)
        velocity = self.environment.data.qvel
        speed = float(np.linalg.norm(velocity[:3]))
        angular = float(np.linalg.norm(velocity[3:6]))
        loads = self.environment.support_loads()
        c = STAND_CRITERION
        support = bool(
            loads["foot_load_fraction"] >= c["foot_load_fraction_min"]
            and loads["other_load_fraction"] <= c["other_load_fraction_max"]
        )
        standing = bool(
            tilt <= c["tilt_max"]
            and height_error <= c["height_error_max_cm"]
            and speed <= c["speed_max_cm_s"]
            and angular <= c["angular_speed_max_rad_s"]
            and support
        )
        measured.update(
            objective_time=float(seconds),
            axis_tilt=tilt,
            height_error=height_error,
            linear_speed=speed,
            angular_speed=angular,
            foot_support=support,
            standing_ok=standing,
            **loads,
        )
        if self.stand_only:
            alignment = 0.65 * np.exp(-((tilt / 0.7) ** 2)) + 0.35 * np.exp(-((height_error / 0.08) ** 2))
            stability = 0.5 + 0.25 * np.exp(-((speed / 0.3) ** 2)) + 0.25 * np.exp(-((angular / 3.0) ** 2))
            measured["reward"] = float(alignment * stability * (0.5 + 0.5 * support))
            measured["tracking_ok"] = standing
        return measured

    def quality(self, rows, seconds):
        measured = super().quality(rows, seconds)
        start, end = (
            (self.target.duration - self.stage["hold_seconds"], self.target.duration)
            if self.stand_only
            else (2.5, 3.5)
        )
        window = [r for r in rows if start + 1e-8 < r["objective_time"] <= end + 1e-8]
        times = np.asarray([r["objective_time"] for r in window])
        expected = np.arange(round(start / DT) + 1, round(end / DT) + 1) * DT
        complete = len(times) == len(expected) and np.allclose(times, expected, atol=1e-8, rtol=0)
        sustained = complete and all(r["standing_ok"] for r in window)
        measured.update(
            standing_fraction=float(np.mean([r["standing_ok"] for r in window])) if window else 0.0,
            standing_window_seconds=end - start,
            stage_id=self.stage["id"],
            stage_index=self.stage_index,
        )
        if self.stand_only:
            measured["tracking_fraction"] = measured["standing_fraction"]
            measured["passed"] = bool(seconds + 1e-8 >= self.target.duration and sustained)
        else:
            measured["passed"] = bool(measured["passed"] and sustained)
        return measured
