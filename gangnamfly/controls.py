"""Matched baseline, constant/inverted-reward controls and held-out pose seeds."""

import argparse
import json
import resource
import sys
import time

import numpy as np

from .config import EPISODES
from .experiment import Experiment


def run(seconds=2.0):
    e = Experiment()
    original = e.brain.plasticity.base.copy()
    rows = []

    def episode(label, mode, seed, weights, teaching="target"):
        e.begin(mode, seed, seconds, weights, teaching=teaching)
        start = time.perf_counter()
        try:
            while not e.step():
                pass
        except BaseException:
            e.finish("interrupted")
            raise
        summary = e.finish()
        with np.load(e.root / summary["id"] / "telemetry.npz") as a:
            summary["joint_error_mean"] = float(a["tracking_error"].mean())
        summary.update(label=label, seed=seed, wall_seconds=time.perf_counter() - start)
        rows.append(summary)
        print(json.dumps(summary), flush=True)
        return e.brain.native.weight[e.brain.plasticity.edges].copy()

    for seed in [64, 65]:
        episode("original", "observe", seed, original)
    for teaching in ["target", "constant", "inverted"]:
        learned = episode(teaching, "train", 64, original, teaching)
        for seed in [64, 65]:
            episode(f"{teaching}-frozen", "observe", seed, learned)
    report = {
        "episodes": rows,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        * (1 if sys.platform == "darwin" else 1024),
        "interpretation": "Small controlled pilot, two initial-pose seeds; no established dance learning. Only target reward versus controls can indicate reward-specific benefit.",
    }
    (EPISODES / "controlled-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seconds", type=float, default=2.0)
    args = p.parse_args()
    run(args.seconds)


if __name__ == "__main__":
    main()
