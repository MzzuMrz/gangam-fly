"""Bounded exports of completed episodes. Hashes permit auditing, not attestation."""

import io
import json
import re
import zipfile

from .provenance import digest

FILES = (
    "config.json",
    "summary.json",
    "telemetry.npz",
    "initial_weights.npz",
    "weights.npz",
    "mappings.json",
    "plastic_edge_indices.npy",
)
ID = re.compile(r"[0-9]{8}T[0-9]{6}-[0-9a-f]{8}")
LIMIT = 128 * 1024 * 1024


def selected_files(path):
    files = [path / name for name in FILES]
    source = path / "source"
    if source.is_symlink():
        raise ValueError("Linked evidence directories are not allowed")
    if source.is_dir():
        files.extend(sorted(source.glob("*.py")))
    for file in files:
        if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(path.resolve()):
            raise ValueError("Evidence is incomplete or contains linked files")
    if sum(f.stat().st_size for f in files) > LIMIT:
        raise ValueError("Evidence exceeds 128 MiB; inspect the local episode directory")
    return files


def file_hashes(path):
    return {str(f.relative_to(path)): digest(f) for f in selected_files(path)}


def verification_status(path):
    try:
        if path.is_symlink():
            return False
        report = path / "verification.json"
        if report.is_symlink() or report.stat().st_size > 128 * 1024:
            return False
        value = json.loads(report.read_text())
        return value.get("passed") is True and value.get("files") == file_hashes(path)
    except (OSError, ValueError, TypeError):
        return False


def bundle(root, episode_id):
    if not ID.fullmatch(episode_id):
        raise ValueError("Invalid episode ID")
    path = root / episode_id
    if path.is_symlink() or not path.is_dir() or path.resolve().parent != root.resolve():
        raise ValueError("Episode not found")
    files = selected_files(path)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for file in files:
            archive.write(file, str(file.relative_to(path)))
        if verification_status(path):
            archive.write(path / "verification.json", "verification.json")
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "files": file_hashes(path),
                    "meaning": "Locally generated hashes, not third-party attestation.",
                },
                indent=2,
            ),
        )
        archive.writestr(
            "REPRODUCE.txt",
            "Use the recorded source/ files as the gangnamfly package in the project,\n"
            "install pinned dependencies and prepare the source assets per README.md.\n"
            f"Extract this episode under episodes/{episode_id}/, then run:\n"
            f"python -m gangnamfly.verify episodes/{episode_id}\n"
            "This re-runs the full graph and physics from the saved seed and initial weights.\n"
            "A replay video alone does not prove training or improved dancing.\n",
        )
    return payload.getvalue()
