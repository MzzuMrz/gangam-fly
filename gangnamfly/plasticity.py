"""Experimental reward-modulated rate eligibility on existing edges only.

Not a validated fly learning rule. The scalar teaching signal is external;
no target/phase/state is used by motor decoding. Signs and topology stay fixed.
"""

import numpy as np


class Plasticity:
    def __init__(self, weights, edges, pre, post, eta=0.02):
        self.weights, self.edges, self.pre, self.post = weights, edges, pre, post
        self.base = weights[edges].copy()
        self.eligibility = np.zeros(len(edges), np.float32)
        self.eta = eta
        self.baseline: float | None = None
        self.changed_this_step = 0
        self.update_l1 = 0.0

    def reset_traces(self):
        self.eligibility.fill(0)
        self.baseline = None
        self.changed_this_step = 0
        self.update_l1 = 0.0

    def update(self, counts, reward, enabled):
        self.changed_this_step = 0
        self.update_l1 = 0.0
        if not enabled:
            return
        if not np.isfinite(reward):
            raise ValueError("Nonfinite reward")
        # 20 ms binned coactivity, exponential eligibility ~400 ms.
        # Saturation makes high-rate bursts finite; this is not spike-time STDP.
        pair = np.tanh(counts[self.pre]) * np.tanh(counts[self.post])
        self.eligibility *= 0.95
        self.eligibility += 0.05 * pair
        if self.baseline is None:
            self.baseline = float(reward)
        delta = reward - self.baseline
        self.baseline += 0.02 * delta
        before = self.weights[self.edges].copy()
        ratio = before / self.base
        ratio += self.eta * delta * self.eligibility
        self.weights[self.edges] = self.base * np.clip(ratio, 0.5, 1.5)
        difference = self.weights[self.edges] - before
        self.changed_this_step = int(np.count_nonzero(difference))
        self.update_l1 = float(np.abs(difference).sum())

    @property
    def changed(self):
        return int(np.count_nonzero(self.weights[self.edges] != self.base))
