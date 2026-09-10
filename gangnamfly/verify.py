"""Re-simulate an episode from its seed and initial weights and compare arrays."""

import argparse
import json
import tempfile
from pathlib import Path

import numpy as np

from .config import DT, EPISODES
from .episode import save_json
from .evidence import file_hashes
from .experiment import Experiment
from .provenance import provenance


def verify(path: Path):
    config = json.loads((path / "config.json").read_text())
    with np.load(path / "initial_weights.npz", allow_pickle=False) as saved:
        weights = saved["weights"]
    if config.get("provenance") != provenance():
        raise ValueError("Dynamics, body assets, kernel or runtime versions differ from this checkpoint")
    with (
        tempfile.TemporaryDirectory(prefix="gangnamfly-verify-") as scratch,
        np.load(path / "telemetry.npz", allow_pickle=False) as expected,
    ):
        hashes = file_hashes(path)
        result = verify_with_data(path, config, weights, Path(scratch), expected)
        if hashes != file_hashes(path):
            raise ValueError("Episode files changed during verification")
        save_json(path / "verification.json", {**result, "files": hashes})
        return result


def verify_with_data(path, config, weights, scratch, expected):
    experiment = Experiment(scratch)
    if (
        config["graph_sha256"] != experiment.brain.graph_hash
        or config["mapping_sha256"] != experiment.mapping_hash
    ):
        raise ValueError("Graph or mapping differs from recorded episode")
    if config.get("objective"):
        from .captured_target import load_target
        from .objective import CapturedObjective

        target = load_target(experiment.environment)
        if config["objective"].get("stage"):
            from .curriculum import CurriculumObjective
            from .microcurriculum import MicroObjective

            cls = (
                MicroObjective
                if config["objective"]["stage"].get("protocol") == "micro-v1"
                else CurriculumObjective
            )
            experiment.objective = cls(target, experiment.environment, config["objective"]["stage"]["index"])
            if experiment.objective.descriptor() != config["objective"]["stage"]:
                raise ValueError("Curriculum stage differs from recorded episode")
        else:
            experiment.objective = CapturedObjective(
                target, experiment.environment.qadr, config["objective"]["criterion"]
            )
        if experiment.objective.target.fingerprint != config["objective"]["target_hash"]:
            raise ValueError("Captured target differs from recorded episode")
    experiment.begin(
        config["mode"],
        config["seed"],
        config["duration"],
        initial_weights=weights,
        teaching=config["teaching"],
        jitter=config["initial_joint_jitter_radians"],
    )
    try:
        for i in range(len(expected["time"])):
            experiment.step()
            e = experiment.environment
            for name, value in [("qpos", e.data.qpos), ("qvel", e.data.qvel), ("ctrl", e.data.ctrl)]:
                np.testing.assert_array_equal(value, expected[name][i], err_msg=f"{name} differs at tick {i}")
            np.testing.assert_array_equal(
                experiment.last_counts[experiment.brain.mapping.motor_indices], expected["motor_counts"][i]
            )
            np.testing.assert_equal(experiment.score, expected["reward"][i])
            compare_objective_metrics(experiment, expected, i)
        with np.load(path / "weights.npz", allow_pickle=False) as final:
            np.testing.assert_array_equal(
                experiment.brain.native.weight[experiment.brain.plasticity.edges], final["weights"]
            )
        compare_summary(experiment, path, expected)
        result = {
            "passed": True,
            "ticks": len(expected["time"]),
            "episode": path.name,
            "comparison": "exact qpos/qvel/ctrl/motor spikes/reward/final weights/objective metrics/summary",
        }
        print(json.dumps(result))
        return result
    finally:
        experiment.finish("verification")


def compare_objective_metrics(experiment, expected, tick):
    if experiment.objective is not None:
        for name, value in experiment.quality_rows[-1].items():
            np.testing.assert_equal(value, expected[name][tick], err_msg=f"{name} differs at tick {tick}")


def compare_summary(experiment, path, expected):
    summary = json.loads((path / "summary.json").read_text())
    np.testing.assert_equal(summary["mode"], experiment.mode)
    np.testing.assert_equal(summary["seconds"], experiment.tick * DT)
    np.testing.assert_equal(summary["score"], float(expected["reward"].mean()))
    if experiment.objective is not None:
        quality = experiment.objective.quality(experiment.quality_rows, experiment.tick * DT)
        if summary["reason"] != "complete":
            quality["passed"] = False
        for name, value in quality.items():
            np.testing.assert_equal(value, summary[name], err_msg=f"Summary {name} differs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("episode", help="Recorded episode directory or ID")
    args = parser.parse_args()
    path = Path(args.episode)
    if not path.is_dir():
        path = EPISODES / args.episode
    verify(path)


if __name__ == "__main__":
    main()
