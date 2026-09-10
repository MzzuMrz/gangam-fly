"""Micro AC-3, AC-5: physical qualification cannot be forged independently of poses."""

import json
from types import SimpleNamespace

import numpy as np
import pytest

from gangnamfly.verify import compare_objective_metrics, compare_summary


def test_objective_qualification_and_loads_are_verified_exactly():
    row = {"reward": 0.7, "stage_ok": False, "standing_ok": False, "foot_load_fraction": 0.01}
    experiment = SimpleNamespace(objective=True, quality_rows=[row])
    expected = {k: np.asarray([v]) for k, v in row.items()}
    compare_objective_metrics(experiment, expected, 0)
    for name, value in [("stage_ok", True), ("foot_load_fraction", 1.0)]:
        changed = {**expected, name: np.asarray([value])}
        with pytest.raises(AssertionError):
            compare_objective_metrics(experiment, changed, 0)


def test_summary_requires_recomputed_physical_pass(tmp_path):
    quality = {"passed": False, "stage_fraction": 0.0, "standing_fraction": 0.0}
    experiment = SimpleNamespace(
        objective=SimpleNamespace(quality=lambda *_: quality), quality_rows=[], tick=200, mode="train"
    )
    expected = {"time": np.arange(1, 201) * 0.02, "reward": np.full(200, 0.5)}
    summary = {"mode": "train", "seconds": 4.0, "score": 0.5, "reason": "complete", **quality}
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary))
    compare_summary(experiment, tmp_path, expected)
    path.write_text(json.dumps({**summary, "passed": True}))
    with pytest.raises(AssertionError):
        compare_summary(experiment, tmp_path, expected)
