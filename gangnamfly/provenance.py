"""Content hashes for dynamics and every unchanged Flybody geometry source."""

import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

from .config import BODY, DOOM

DYNAMICS = [
    "adapters.py",
    "brain.py",
    "environment.py",
    "mapping.py",
    "plasticity.py",
    "reference.py",
    "experiment.py",
    "config.py",
    "objective.py",
    "curriculum.py",
    "microcurriculum.py",
    "captured_target.py",
    "choreography.py",
    "prepare_demo.py",
]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def provenance():
    library = "libneural.dylib.json" if sys.platform == "darwin" else "libneural.so.json"
    return {
        "body_assets": {p.name: digest(p) for p in sorted(BODY.iterdir()) if p.suffix in (".xml", ".obj")},
        "dynamics_sources": {n: digest(Path(__file__).parent / n) for n in DYNAMICS},
        "kernel": json.loads((DOOM / "outputs/doom" / library).read_text()),
        "versions": {n: importlib.metadata.version(n) for n in ["numpy", "mujoco", "numba"]},
    }
