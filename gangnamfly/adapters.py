import numpy as np


class ProvisionalProprioceptionAdapter:
    """Joint signals and rhythm cue enter annotated sensory cells only."""

    def __init__(self, mapping, seed=64):
        self.mapping = mapping
        self.rng = np.random.default_rng(seed)

    def encode(self, environment, seconds, exploration=False):
        currents = []
        for pool in self.mapping.sensory:
            if pool["kind"] == "leg":
                name = f"tibia_{pool['segment']}_{pool['side']}"
                joint = environment.model.joint(name)
                q = float(environment.data.qpos[joint.qposadr[0]])
                v = float(environment.data.qvel[joint.dofadr[0]])
                signal = pool["sign"] * (q + 1.0 + 0.02 * v)
                value = 14 + 10 * np.tanh(signal)
            elif pool["kind"] == "angular":
                value = 14 + 10 * np.tanh(pool["sign"] * environment.data.qvel[3])
            else:
                value = 12 + 12 * max(0.0, np.sin(2 * np.pi * 132 / 60 * seconds))
            if exploration:
                value += self.rng.normal(0, 2.0)
            currents.append(np.clip(value, 0, 30))
        return np.asarray(currents, np.float32)


class MotorAdapter:
    """Fixed opponent population spike rates -> existing joint actuator targets.

    No phase, world state, target pose, reward or trainable parameters enter decode.
    Rest targets are static actuator calibration, not a balance or dance policy.
    """

    def __init__(self, mapping, rest, limits, gain=0.012):
        self.mapping, self.rest, self.limits, self.gain = mapping, rest.copy(), limits, gain
        self.rates = np.zeros((len(mapping.motor), 2))

    def decode(self, counts, seconds):
        if seconds <= 0 or not np.isfinite(counts).all():
            raise ValueError("Invalid motor observation")
        rates = np.asarray(
            [[float(counts[p].mean()) / seconds for p in m["pools"]] for m in self.mapping.motor]
        )
        alpha = 1 - np.exp(-seconds / 0.08)
        self.rates += alpha * (rates - self.rates)
        signal = np.tanh(self.gain * (self.rates[:, 0] - self.rates[:, 1]))
        span = np.where(signal >= 0, self.limits[:, 1] - self.rest, self.rest - self.limits[:, 0])
        command = self.rest + signal * span
        return np.clip(command, self.limits[:, 0], self.limits[:, 1])
