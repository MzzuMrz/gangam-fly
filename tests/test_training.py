import json
from types import SimpleNamespace

import numpy as np
import pytest

from gangnamfly.objective import CapturedObjective
from gangnamfly.training import TrainingSession


# AC-3: a short perfect pose or reward alone cannot establish mastery.
def test_quality_requires_whole_capture_and_physical_tracking():
    pose = np.array([0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.3])
    target = SimpleNamespace(duration=2.0, sample=lambda _: pose.copy(), fingerprint="target", source={})
    objective = CapturedObjective(target, np.array([7]))
    good = objective.measure(pose, 0.02)
    assert good["tracking_ok"] and good["reward"] == 1
    assert not objective.quality([good], 0.02)["passed"]
    assert objective.quality([good] * 100, 2.0)["passed"]
    fallen = pose.copy()
    fallen[3:7] = [0.0, 1.0, 0.0, 0.0]
    bad = objective.measure(fallen, 1.0)
    assert not bad["tracking_ok"]
    assert not objective.quality([bad] * 100, 2.0)["passed"]


# AC-1, AC-3, AC-5: real episode boundaries, reserved seeds, persistent weights.
def test_session_rollover_freeze_and_restore(tmp_path):
    weights = np.array([1.0, -2.0], np.float32)
    session = TrainingSession(tmp_path, {"hash": "a"}, seed=64, eval_every=2)
    session.start()
    baseline_seeds = []
    summary = {"id": "test", "seconds": 2.0, "score": 0.1, "passed": False}
    for _ in range(2):
        mode, seed = session.trial()
        assert mode == "observe"
        baseline_seeds.append(seed)
        session.complete(summary, weights)
    for i in range(2):
        mode, seed = session.trial()
        assert mode == "train" and seed not in baseline_seeds
        weights += [0.01, -0.01]
        session.complete({**summary, "score": 0.9}, weights)
    assert session.active and session.phase == "evaluate"
    for seed in baseline_seeds:
        assert session.trial() == ("observe", seed)
        session.complete({**summary, "score": 0.9, "passed": False}, weights)
    assert session.phase == "train"  # Reward rose, but body failed objective criteria.
    session.stop(weights)
    restored = TrainingSession(tmp_path, {"hash": "a"}, seed=64, eval_every=2)
    np.testing.assert_array_equal(restored.saved_weights, weights)
    assert not restored.active and restored.state["completed_trials"] == 6
    restored.start()
    assert restored.trial()[0] == "train"
    with pytest.raises(ValueError, match="provenance"):
        TrainingSession(tmp_path, {"hash": "tampered"}, seed=64)


def test_session_only_completes_after_two_successful_frozen_evaluations(tmp_path):
    session = TrainingSession(tmp_path, {}, eval_every=1)
    session.start()
    weights = np.ones(1)
    baseline = {"id": "a", "score": 0.1, "seconds": 36.08, "passed": False}
    for _ in range(3):
        session.complete(baseline, weights)
    success = {**baseline, "score": 0.95, "passed": True}
    session.complete(success, weights)
    assert session.active
    session.complete(success, weights)
    assert not session.active and session.phase == "complete"
    with np.load(tmp_path / "checkpoint.npz", allow_pickle=False) as z:
        assert json.loads(str(z["state"]))["phase"] == "complete"


# AC-5: a valid provenance label cannot hide malformed persistent state.
@pytest.mark.parametrize(
    "field,value",
    [
        ("eval_every", 0),
        ("attempt", -1),
        ("seed", True),
        ("history", None),
        ("evaluation_index", 10),
        ("baseline_score", float("nan")),
    ],
)
def test_malformed_checkpoint_rejected_before_use(tmp_path, field, value):
    session = TrainingSession(tmp_path, {})
    session.state[field] = value
    # Construct a malformed input externally; public checkpoint writes validate too.
    np.savez(
        tmp_path / "checkpoint.npz",
        state=np.array(json.dumps(session.state)),
        signature=np.array("{}"),
        weights=np.ones(1),
    )
    with pytest.raises(ValueError, match="checkpoint"):
        TrainingSession(tmp_path, {})


# AC-5: write boundaries must not follow links outside the session.
def test_checkpoint_and_journal_symlinks_are_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "linked"
    root.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="link"):
        TrainingSession(root, {})
    root = tmp_path / "session"
    root.mkdir()
    (root / "checkpoint.partial").symlink_to(outside / "data")
    with pytest.raises(ValueError, match="link"):
        TrainingSession(root, {})
    assert not (outside / "data").exists()


# AC-1, AC-5: a journal-write failure is repaired from committed state once.
def test_completed_trial_journal_recovers_without_duplicates(tmp_path, monkeypatch):
    from gangnamfly import training

    session = TrainingSession(tmp_path, {})
    session.start()

    def fail(*_):
        raise OSError("simulated interrupted journal write")

    original = training.save_json
    monkeypatch.setattr(training, "save_json", fail)
    with pytest.raises(OSError):
        session.complete({"id": "test", "seconds": 0.1, "score": 0.1, "passed": False}, np.ones(1))
    monkeypatch.setattr(training, "save_json", original)
    restored = TrainingSession(tmp_path, {})
    assert restored.state["completed_trials"] == 1
    assert len(list((tmp_path / "history").glob("*.json"))) == 1
    assert restored.trial() == ("observe", 66)
    TrainingSession(tmp_path, {})
    assert len(list((tmp_path / "history").glob("*.json"))) == 1


# Curriculum AC-2, AC-5: frozen qualification and atomic stage restoration.
def test_curriculum_promotes_atomically_on_frozen_physical_success(tmp_path):
    from gangnamfly.curriculum import STAGES

    weights = np.array([1.0, -2.0], np.float32)
    session = TrainingSession(tmp_path, {}, stages=STAGES, eval_every=1)
    session.start()
    bad = {"id": "trial", "seconds": 4.0, "score": 0.9, "passed": False}
    good = dict(bad, passed=True)
    reserved = []
    for _ in range(2):
        reserved.append(session.trial()[1])
        session.complete(bad, weights)
    assert session.state["stage_index"] == 0
    assert session.trial()[1] not in reserved
    session.complete(good, weights)  # Training success alone cannot promote.
    assert session.state["stage_index"] == 0
    for seed in reserved:
        assert session.trial() == ("observe", seed)
        session.complete(good, weights)
    assert session.phase == "baseline" and session.state["stage_index"] == 1
    assert session.state["baseline_score"] is None
    restored = TrainingSession(tmp_path, {}, stages=STAGES, eval_every=1)
    assert restored.state["stage_index"] == 1 and restored.phase == "baseline"
    np.testing.assert_array_equal(restored.saved_weights, weights)
    assert restored.trial()[1] not in reserved
    assert len(restored.state["stage_results"]) == 1
    restored.start()
    # Already-mastered baseline may advance, explicitly recorded as pre-existing.
    for index in range(1, len(STAGES)):
        assert restored.state["stage_index"] == index
        restored.complete(good, weights)
        restored.complete(good, weights)
    assert restored.phase == "complete" and not restored.active
    assert restored.state["stage_results"][-1]["qualification"] == "baseline"
    TrainingSession(tmp_path, {}, stages=STAGES, eval_every=1)


def test_curriculum_binds_stage_order_and_rejects_corrupt_certificates(tmp_path):
    from gangnamfly.curriculum import STAGES

    session = TrainingSession(tmp_path, {}, stages=STAGES)
    session.checkpoint(np.ones(1))
    with pytest.raises(ValueError, match="provenance"):
        TrainingSession(tmp_path, {}, stages=list(reversed(STAGES)))
    session.state["stage_index"] = 1
    with pytest.raises(ValueError, match="checkpoint"):
        session.checkpoint(np.ones(1))


# Curriculum AC-5: read-only compatible legacy weight transfer.
def test_warm_start_checks_compatibility_and_preserves_legacy(tmp_path):
    from gangnamfly.training import import_legacy_weights

    path = tmp_path / "checkpoint.npz"
    signature = {
        "graph": "g",
        "mapping": "m",
        "provenance": {
            "body_assets": {"body": "x"},
            "kernel": {"sha": "k"},
            "dynamics_sources": {"brain.py": "b", "plasticity.py": "p"},
        },
    }
    weights = np.array([1.0, -2.0])
    np.savez(path, signature=np.array(json.dumps(signature)), weights=weights)
    before = path.read_bytes()
    result, metadata = import_legacy_weights(path, signature)
    np.testing.assert_array_equal(result, weights)
    assert len(metadata["sha256"]) == 64 and path.read_bytes() == before
    with pytest.raises(ValueError, match="incompatible"):
        import_legacy_weights(path, {**signature, "mapping": "different"})


# Curriculum AC-5: same-sized weights cannot be reassigned to different synapses.
def test_legacy_import_rejects_changed_edge_selection(tmp_path):
    from gangnamfly.training import import_legacy_weights

    signature = {
        "graph": "g",
        "mapping": "m",
        "provenance": {
            "body_assets": {},
            "kernel": {},
            "dynamics_sources": {"brain.py": "old", "plasticity.py": "p"},
        },
    }
    path = tmp_path / "checkpoint.npz"
    np.savez(path, signature=np.array(json.dumps(signature)), weights=np.ones(1))
    signature["provenance"]["dynamics_sources"]["brain.py"] = "changed"
    with pytest.raises(ValueError, match="incompatible"):
        import_legacy_weights(path, signature)


# Curriculum AC-2, AC-5: certificates remain validated after history rollover.
def test_curriculum_certificates_and_initialization_are_validated(tmp_path):
    from gangnamfly.curriculum import STAGES

    session = TrainingSession(tmp_path, {}, stages=STAGES)
    good = {"id": "a", "seconds": 4.0, "score": 0.8, "passed": True}
    for _ in range(2):
        session.complete(good, np.ones(1))
    assert session.state["stage_results"][0]["score"] == 0.8
    certificate = session.state["stage_results"][0]
    certificate["evaluations"][0] = {**certificate["evaluations"][0], "score": float("nan")}
    with pytest.raises(ValueError, match="checkpoint"):
        session.checkpoint(np.ones(1))
    certificate["evaluations"][0]["score"] = 0.8
    session.state["initialization"] = {"sha256": "bad"}
    with pytest.raises(ValueError, match="checkpoint"):
        session.checkpoint(np.ones(1))


# Micro AC-4: latest curriculum import binds actual plastic-edge ordering.
def test_micro_import_requires_edge_identity_and_keeps_source(tmp_path):
    from gangnamfly.training import import_legacy_weights

    root = tmp_path / "_training_curriculum"
    root.mkdir()
    path = root / "checkpoint.npz"
    signature = {
        "graph": "g",
        "mapping": "m",
        "plastic_edges": "edges",
        "provenance": {
            "body_assets": {},
            "kernel": {},
            "dynamics_sources": {"brain.py": "b", "plasticity.py": "p"},
        },
    }
    np.savez(path, signature=np.array(json.dumps(signature)), weights=np.ones(2))
    before = path.read_bytes()
    _, meta = import_legacy_weights(path, signature)
    assert meta["source"] == "_training_curriculum/checkpoint.npz" and path.read_bytes() == before
    with pytest.raises(ValueError, match="incompatible"):
        import_legacy_weights(path, {**signature, "plastic_edges": "reordered"})
