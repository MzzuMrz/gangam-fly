import json
import time

import numpy as np
import pytest

from gangnamfly.runtime import Runtime


def wait_for(runtime, predicate, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = runtime.read()
        assert state["status"] != "error", runtime.error
        if predicate(state):
            return state
        time.sleep(0.02)
    raise AssertionError(f"Runtime timeout: {runtime.read().get('message')}")


# AC-1, AC-2, AC-3, AC-4, AC-5: short trial duration is a real-loop smoke, not mastery.
@pytest.mark.integration
def test_native_continuous_training_pause_stop_and_evidence(tmp_path):
    runtime = Runtime(tmp_path, auto=False, training_seconds=0.12)
    try:
        wait_for(runtime, lambda s: s["status"] == "idle")
        assert runtime.training_error is None
        assert runtime.read()["training"]["stage"]["id"] == "micro_000"
        runtime.submit("train")
        wait_for(runtime, lambda s: s.get("training", {}).get("completed_trials", 0) >= 3)
        runtime.submit("pause")
        paused = wait_for(runtime, lambda s: s["status"] == "paused")
        time.sleep(0.1)
        assert runtime.read()["sim_time"] == paused["sim_time"]
        runtime.submit("train")  # Resume, never create a second simultaneous learner.
        state = wait_for(runtime, lambda s: s.get("training", {}).get("completed_trials", 0) >= 9)
        assert state["training"]["active"] and state["training"]["phase"] != "complete"
        runtime.submit("stop")
        state = wait_for(runtime, lambda s: s["status"] == "idle")
        assert not state["training"]["active"]
        assert state["evidence"]["last_episode_id"] and not state["evidence"]["verified"]
        rows = [
            json.loads(p.read_text()) for p in sorted((tmp_path / "_training_micro/history").glob("*.json"))
        ]
        assert [r["phase"] for r in rows[:9]] == ["baseline"] * 2 + ["train"] * 5 + ["evaluate"] * 2
        changed = 0
        previous = None
        for row in rows[:9]:
            path = tmp_path / row["id"]
            with (
                np.load(path / "initial_weights.npz") as a,
                np.load(path / "weights.npz") as b,
                np.load(path / "telemetry.npz") as t,
            ):
                if previous is not None:
                    np.testing.assert_array_equal(a["weights"], previous)
                if row["phase"] != "train":
                    np.testing.assert_array_equal(a["weights"], b["weights"])
                    assert not t["learning_enabled"].any() and not t["changed_this_step"].any()
                else:
                    changed += int(np.count_nonzero(a["weights"] != b["weights"]))
                    assert t["learning_enabled"].all()
                assert "standing_ok" in t and "foot_support" in t and "stage_ok" in t
                assert t["total_spikes"].sum() > 0 and not row["passed"]
                previous = b["weights"].copy()
        assert changed > 0
        assert (tmp_path / "_training_micro/checkpoint.npz").is_file()
    finally:
        runtime.close()


# AC-5: optional DEMO failure cannot take down observation or saved replay.
@pytest.mark.integration
def test_optional_reference_failure_leaves_physics_available(tmp_path, monkeypatch):
    from gangnamfly import runtime as module

    def missing(_):
        raise ValueError("capture absent")

    monkeypatch.setattr(module, "load_target", missing)
    runtime = Runtime(tmp_path, auto=False, duration=0.04)
    try:
        wait_for(runtime, lambda s: s["status"] == "idle")
        assert runtime.demo is None and "capture absent" in runtime.demo_error
        runtime.submit("observe")
        wait_for(runtime, lambda s: bool(s["episodes"]))
        assert runtime.error is None
    finally:
        runtime.close()
