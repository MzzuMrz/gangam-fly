import numpy as np

from gangnamfly.episode import Episode


# AC: AC-4
def test_episode_recovers_chunks_and_final_arrays(tmp_path):
    e = Episode(tmp_path, {"seed": 64, "mode": "observe"}, np.ones(3))
    for i in range(3):
        e.add(time=i * 0.02, qpos=np.array([i, 0.0]), qvel=np.zeros(2), reward=0.5)
    e.finish(np.ones(3), "complete", 0)
    a = np.load(e.path / "telemetry.npz", allow_pickle=False)
    np.testing.assert_array_equal(a["qpos"][:, 0], [0, 1, 2])
    assert a["time"].shape == (3,)
    assert (e.path / "config.json").exists()
    assert (e.path / "weights.npz").exists()


# AC: AC-4, AC-6
def test_verifier_rejects_provenance_before_loading_body(tmp_path, monkeypatch):
    import json

    import pytest

    from gangnamfly import verify

    (tmp_path / "config.json").write_text(json.dumps({"provenance": {"body_assets": "changed"}}))
    np.savez(tmp_path / "initial_weights.npz", weights=np.ones(1))
    np.savez(tmp_path / "telemetry.npz", time=np.zeros(1))
    monkeypatch.setattr(verify, "provenance", lambda: {"body_assets": "original"})

    def unexpected(*_):
        raise AssertionError("Body was loaded before checking provenance")

    monkeypatch.setattr(verify, "Experiment", unexpected)
    with pytest.raises(ValueError, match="body assets"):
        verify.verify(tmp_path)


# AC: AC-4, AC-5
def test_empty_or_corrupt_episode_cannot_break_history_or_replay(tmp_path):
    import pytest

    from gangnamfly.environment import FlybodyEnvironment
    from gangnamfly.replay import history, load

    e = Episode(tmp_path, {"mode": "observe"}, np.ones(1))
    result = e.finish(np.ones(1), "interrupted", 0)
    assert result["replayable"] is False
    assert history(tmp_path) == []
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "summary.json").write_text("{")
    assert history(tmp_path) == []
    with pytest.raises(ValueError, match="pasos físicos"):
        load(e.path, FlybodyEnvironment())
    assert not (e.path / "summary.json.partial").exists()
