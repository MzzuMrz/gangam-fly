"""Automatic bounded episode recording with atomic, recoverable NPZ chunks."""

import json
import uuid
from datetime import UTC, datetime

import numpy as np


def save_npz(path, **arrays):
    temporary = path.with_suffix(".partial")
    with temporary.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    temporary.replace(path)


def save_json(path, value):
    temporary = path.with_suffix(".json.partial")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


class Episode:
    def __init__(self, root, config, starting_weights):
        name = datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
        self.path = root / name
        self.path.mkdir(parents=True)
        self.config = config
        save_json(self.path / "config.json", config)
        save_npz(self.path / "initial_weights.npz", weights=starting_weights)
        self.rows = []
        self.chunks = []

    def add(self, **row):
        self.rows.append({k: np.asarray(v).copy() for k, v in row.items()})
        if len(self.rows) >= 50:
            self.flush()

    def flush(self):
        if not self.rows:
            return
        path = self.path / f"chunk-{len(self.chunks):05d}.npz"
        save_npz(path, **{k: np.stack([r[k] for r in self.rows]) for k in self.rows[0]})
        self.chunks.append(path)
        self.rows.clear()

    def finish(self, weights, reason, changed):
        self.flush()
        save_npz(self.path / "weights.npz", weights=weights)
        arrays: dict[str, list[np.ndarray]] = {}
        for path in self.chunks:
            with np.load(path, allow_pickle=False) as chunk:
                for key in chunk.files:
                    arrays.setdefault(key, []).append(chunk[key])
        joined = {k: np.concatenate(v) for k, v in arrays.items()}
        save_npz(self.path / "telemetry.npz", **joined)
        reward = joined.get("reward", np.array([]))
        summary = {
            "id": self.path.name,
            "mode": self.config["mode"],
            "score": float(reward.mean()) if len(reward) else 0.0,
            "seconds": float(joined["time"][-1]) if len(reward) else 0.0,
            "changed_edges": changed,
            "reason": reason,
            "replayable": bool(len(reward)),
        }
        save_json(self.path / "summary.json", summary)
        return summary
