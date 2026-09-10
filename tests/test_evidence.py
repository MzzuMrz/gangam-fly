import io
import json
import zipfile

import pytest

from gangnamfly.evidence import bundle, file_hashes, verification_status


# AC-4, AC-5: data is downloadable, verification cannot survive edited telemetry.
def test_bundle_and_verification_are_bound_to_saved_arrays(tmp_path):
    episode = tmp_path / "20260909T120000-abcdef12"
    episode.mkdir()
    for name in (
        "config.json",
        "summary.json",
        "telemetry.npz",
        "initial_weights.npz",
        "weights.npz",
        "mappings.json",
        "plastic_edge_indices.npy",
    ):
        (episode / name).write_bytes(b"fixture bytes")
    assert not verification_status(episode)
    (episode / "verification.json").write_text(json.dumps({"passed": True, "files": file_hashes(episode)}))
    assert verification_status(episode)
    with zipfile.ZipFile(io.BytesIO(bundle(tmp_path, episode.name))) as archive:
        assert "telemetry.npz" in archive.namelist()
        assert "REPRODUCE.txt" in archive.namelist()
        assert "manifest.json" in archive.namelist()
    (episode / "telemetry.npz").write_bytes(b"changed")
    assert not verification_status(episode)
    with pytest.raises(ValueError):
        bundle(tmp_path, "../secret")
    (episode / "weights.npz").unlink()
    (episode / "weights.npz").symlink_to(tmp_path / "secret")
    with pytest.raises(ValueError):
        bundle(tmp_path, episode.name)


# AC-5: status and export apply the same directory boundary.
def test_verified_status_rejects_linked_episode(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    for name in (
        "config.json",
        "summary.json",
        "telemetry.npz",
        "initial_weights.npz",
        "weights.npz",
        "mappings.json",
        "plastic_edge_indices.npy",
    ):
        (outside / name).write_bytes(b"fixture")
    (outside / "verification.json").write_text(json.dumps({"passed": True, "files": file_hashes(outside)}))
    assert verification_status(outside)
    link = tmp_path / "linked"
    link.symlink_to(outside, target_is_directory=True)
    assert not verification_status(link)
