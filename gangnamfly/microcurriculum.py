"""Fine physical milestones. Targets score observations and never emit controls."""

from typing import Any

import numpy as np

from .config import DT
from .curriculum import CurriculumObjective, StageTarget
from .objective import CapturedObjective

PROTOCOL = "micro-v1"


def build_stages():
    stages: list[dict[str, Any]] = []
    criteria = {
        "foot_min": 0.1,
        "other_max": 0.95,
        "tilt_max": float(np.deg2rad(100)),
        "height_fraction": 0.0,
        "height_error_max": 1e6,
        "speed_max": 1.0,
        "angular_max": 10.0,
    }

    def add(label, hold=0.2, motion=0.0, full=False):
        stages.append(
            {
                "id": "full" if full else f"micro_{len(stages):03d}",
                "label": label,
                "duration": 39.07 if full else (6.5 + motion if motion else max(4.0, 3.0 + hold)),
                "hold_seconds": hold,
                "motion_seconds": motion,
                "criteria": dict(criteria),
                "protocol": PROTOCOL,
            }
        )

    for percent in range(10, 81, 10):
        criteria.update(foot_min=percent / 100, other_max=(105 - percent) / 100)
        add(f"Apoyar patas · {percent}% del peso")
    for percent in [20, 15, 10, 5, 2]:
        criteria["other_max"] = percent / 100
        add(f"Descargar cuerpo · apoyo corporal ≤{percent}%")
    for percent in [5, 10, 15, 20, 25]:
        criteria["height_fraction"] = percent / 100
        add(f"Elevar cuerpo · paso {percent // 5}/5")
    for degrees in range(5, 71, 5):
        criteria.update(tilt_max=float(np.deg2rad(90 - degrees)), height_fraction=0.25 + 0.75 * degrees / 70)
        add(f"Incorporarse · elevación ≥{degrees}°")
    # The original strict standing tolerance is retained at the final physical stages.
    criteria["height_error_max"] = 0.03
    add("Ajustar altura erguida")
    for speed, angular in [(0.8, 8.0), (0.6, 6.0), (0.4, 4.0), (0.2, 2.0)]:
        criteria.update(speed_max=speed, angular_max=angular)
        add(f"Estabilizar · ≤{speed:g} cm/s y ≤{angular:g} rad/s")
    for ticks in [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]:
        add(f"Sostener postura · {ticks * DT:g} s", hold=ticks * DT)
    for quarter in range(1, 125):
        seconds = quarter * 0.25
        add(f"Coreografía · primeros {seconds:g} s", hold=3.0, motion=seconds)
    add("Captura completa · 31,07 s", hold=3.0, motion=31.07, full=True)
    return stages


STAGES = build_stages()


class MicroTarget(StageTarget):
    @property
    def duration(self):
        return self.base.duration + 3.0 if self.stage["id"] == "full" else self.stage["duration"]

    def sample(self, seconds):
        seconds = float(np.clip(seconds, 0, self.duration))
        source_time = (
            min(seconds, 2.5) if not self.stage["motion_seconds"] or seconds <= 5.5 else seconds - 3.0
        )
        if self.stage["motion_seconds"] and (
            self.stage["id"] != "full" or seconds <= np.ceil((5.5 + self.stage["motion_seconds"]) / DT) * DT
        ):
            source_time = min(source_time, 2.5 + self.stage["motion_seconds"])
        return self.base.sample(source_time)


class MicroObjective(CurriculumObjective):
    stage: dict[str, Any]

    def __init__(self, base, environment, stage_index):
        if type(stage_index) is not int or not 0 <= stage_index < len(STAGES):
            raise ValueError("Invalid microcurriculum stage")
        self.stage_index, self.stage = stage_index, dict(STAGES[stage_index])
        self.environment = environment
        CapturedObjective.__init__(self, MicroTarget(base, self.stage), environment.qadr)
        self.upright_height = float(base.sample(2.5)[2])
        self.floor = float(environment.model.geom("floor").pos[2])
        self.stand_only = not bool(self.stage["motion_seconds"])
        self.physical = self.stage["criteria"]
        # A 0.05 cm initial clearance is below observed normal root heights.
        self.minimum_height = (
            self.floor
            + 0.05
            + self.physical["height_fraction"] * (self.upright_height - 0.03 - self.floor - 0.05)
        )

    def descriptor(self):
        c = self.physical
        physical = (
            f"Patas ≥{100 * c['foot_min']:g}% del peso; cuerpo ≤{100 * c['other_max']:g}%; "
            f"altura sobre suelo ≥{self.minimum_height - self.floor:.3f} cm; "
            f"desvío de vertical ≤{np.rad2deg(c['tilt_max']):g}°; "
            f"velocidad ≤{c['speed_max']:g} cm/s y giro ≤{c['angular_max']:g} rad/s"
        )
        if c["height_error_max"] < 1:
            physical += f"; error de altura erguida ≤{c['height_error_max']:g} cm"
        label = (
            f"{physical} durante los últimos {self.stage['hold_seconds']:g} s."
            if self.stand_only
            else f"Seguimiento ≥90% del tramo; además, {physical} durante 3 s antes del movimiento."
        )
        if self.stage["id"] == "full":
            label += " El regreso al reposo debe cumplir ≥90% de su propio tramo."
        return {
            **self.stage,
            "duration": self.target.duration,
            "index": self.stage_index,
            "count": len(STAGES),
            "criterion_label": label,
            "minimum_root_height": self.minimum_height,
            "floor_height": self.floor,
            "tracking_criterion": self.criterion,
            "target_hash": self.target.fingerprint,
            "criteria_sample_seconds": DT,
            "motion_window_start": 5.5,
            "motion_window_end": float(np.ceil((5.5 + self.stage["motion_seconds"]) / DT) * DT),
        }

    def measure(self, qpos, seconds):
        m = super().measure(qpos, seconds)
        c = self.physical
        # Each deficit is smooth, including contact loads; no binary support multiplier.
        deficits = np.asarray(
            [
                max(0.0, c["foot_min"] - m["foot_load_fraction"]) / 0.1,
                max(0.0, m["other_load_fraction"] - c["other_max"]) / 0.1,
                max(0.0, m["axis_tilt"] - c["tilt_max"]) / 0.15,
                max(0.0, self.minimum_height - float(qpos[2])) / 0.02,
                max(0.0, m["height_error"] - c["height_error_max"]) / 0.02,
                max(0.0, m["linear_speed"] - c["speed_max"]) / 0.2,
                max(0.0, m["angular_speed"] - c["angular_max"]) / 2.0,
            ]
        )
        m["stage_ok"] = bool(np.all(deficits <= 1e-10))
        m["stage_deficit"] = float(deficits.mean())
        m["root_height_above_floor"] = float(qpos[2]) - self.floor
        if self.stand_only:
            # Sum of penalties avoids exponentially erasing the entire teaching signal.
            m["reward"] = float(1.0 / (1.0 + deficits.mean()))
            m["tracking_ok"] = m["stage_ok"]
        return m

    def quality(self, rows, seconds):
        result = CapturedObjective.quality(self, rows, seconds)
        observed_trial = np.asarray([r["objective_time"] for r in rows])
        expected_trial = np.arange(1, round(seconds / DT) + 1) * DT
        complete_trial = len(observed_trial) == len(expected_trial) and np.allclose(
            observed_trial, expected_trial, rtol=0, atol=1e-8
        )
        start, end = (
            (self.target.duration - self.stage["hold_seconds"], self.target.duration)
            if self.stand_only
            else (2.5, 5.5)
        )
        window = [r for r in rows if start + 1e-8 < r["objective_time"] <= end + 1e-8]
        times = np.asarray([r["objective_time"] for r in window])
        expected = np.arange(round(start / DT) + 1, round(end / DT) + 1) * DT
        complete = len(times) == len(expected) and np.allclose(times, expected, atol=1e-8, rtol=0)
        qualified = bool(complete and all(r["stage_ok"] for r in window))
        result.update(
            stage_id=self.stage["id"],
            stage_index=self.stage_index,
            stage_fraction=float(np.mean([r["stage_ok"] for r in window])) if window else 0.0,
            standing_fraction=float(np.mean([r["standing_ok"] for r in window])) if window else 0.0,
            standing_window_seconds=end - start,
        )
        motion_pass = True
        if not self.stand_only:
            motion_end = float(np.ceil((5.5 + self.stage["motion_seconds"]) / DT) * DT)
            motion = [r for r in rows if 5.5 + 1e-8 < r["objective_time"] <= motion_end + 1e-8]
            observed = np.asarray([r["objective_time"] for r in motion])
            expected_motion = np.arange(round(5.5 / DT) + 1, round(motion_end / DT) + 1) * DT
            motion_complete = len(observed) == len(expected_motion) and np.allclose(
                observed, expected_motion, rtol=0, atol=1e-8
            )
            fraction = float(np.mean([r["tracking_ok"] for r in motion])) if motion else 0.0
            result.update(
                motion_tracking_fraction=fraction,
                tracking_fraction=fraction,
                motion_window_start=5.5,
                motion_window_end=motion_end,
            )
            motion_pass = motion_complete and fraction >= self.criterion["tracking_fraction_min"]
            if self.stage["id"] == "full":
                tail_end = float(np.ceil(self.target.duration / DT) * DT)
                tail = [r for r in rows if motion_end + 1e-8 < r["objective_time"] <= tail_end + 1e-8]
                tail_times = np.asarray([r["objective_time"] for r in tail])
                expected_tail = np.arange(round(motion_end / DT) + 1, round(tail_end / DT) + 1) * DT
                tail_complete = len(tail_times) == len(expected_tail) and np.allclose(
                    tail_times, expected_tail, rtol=0, atol=1e-8
                )
                tail_fraction = float(np.mean([r["tracking_ok"] for r in tail])) if tail else 0.0
                result.update(
                    tail_tracking_fraction=tail_fraction,
                    tail_window_start=motion_end,
                    tail_window_end=tail_end,
                )
                motion_pass = (
                    motion_pass
                    and tail_complete
                    and tail_fraction >= self.criterion["tracking_fraction_min"]
                    and result["passed"]
                )
        result["passed"] = bool(
            seconds + 1e-8 >= self.target.duration and complete_trial and qualified and motion_pass
        )
        return result
