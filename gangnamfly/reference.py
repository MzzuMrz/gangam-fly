"""Authored joint-space dance exercise, not human motion capture.

Horse-riding arm motif and alternating leg lifts inspired by Gangnam Style.
This reference is consumed only by reward/evaluation, never execution.
"""

import numpy as np


class DanceReference:
    def __init__(self, names, rest, limits, bpm=132.0):
        self.names, self.rest, self.limits = names, rest.copy(), limits
        self.period = 4 * 60 / bpm

    def target(self, seconds):
        beat = 2 * np.pi * seconds / (self.period / 4)
        target = self.rest.copy()
        for i, name in enumerate(self.names):
            side = 1 if name.endswith("left") else -1
            if "T1" in name:
                if name.startswith("coxa_abduct"):
                    target[i] += 0.3 + 0.3 * np.sin(beat)
                elif name.startswith("femur_"):
                    target[i] += 0.65 + 0.25 * np.cos(beat)
                elif name.startswith("tibia_"):
                    target[i] += 0.5 + 0.4 * np.sin(beat)
                elif name.startswith("coxa_twist"):
                    target[i] += 0.25 * side * np.sin(beat / 4)
            elif name.startswith(("femur_", "tibia_")):
                target[i] += 0.35 * max(0, side * np.sin(beat / 2))
        return np.clip(target, self.limits[:, 0], self.limits[:, 1])

    def error(self, actual, seconds):
        return float(np.mean(np.square(actual - self.target(seconds))))
