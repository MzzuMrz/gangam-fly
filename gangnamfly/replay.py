"""Validate a complete physical trajectory before accepting a replay command."""

import json

import numpy as np


def history(root):
    records = []
    for path in sorted(root.glob("*/summary.json"))[-100:]:
        if path.parent.is_symlink() or path.is_symlink():
            continue
        try:
            record = json.loads(path.read_text())
            if (
                isinstance(record, dict)
                and record.get("id") == path.parent.name
                and record.get("replayable", record.get("seconds", 0) > 0)
                and (path.parent / "telemetry.npz").is_file()
            ):
                records.append(record)
        except (OSError, ValueError, TypeError):
            # A partial historical record must not disable the live experiment.
            continue
    return records


def load(path, environment):
    m = environment.model
    with np.load(path / "telemetry.npz", allow_pickle=False) as archive:
        if "time" not in archive:
            raise ValueError("El episodio no contiene pasos físicos")
        times = archive["time"]
        n = len(times)
        if times.shape != (n,) or not 0 < n <= 6000:
            raise ValueError("Duración de replay inválida")
        shapes = {
            "time": (n,),
            "qpos": (n, m.nq),
            "qvel": (n, m.nv),
            "act": (n, m.na),
            "ctrl": (n, m.nu),
            "reward": (n,),
            "tracking_error": (n,),
            "changed_edges": (n,),
            "motor_rates": (n, len(environment.names), 2),
            "dn_counts": (n, 6),
        }
        result = {}
        for key, shape in shapes.items():
            if key not in archive:
                raise ValueError(f"Telemetría incompleta: {key}")
            value = archive[key]
            if value.shape != shape or value.dtype.kind not in "fiu" or not np.isfinite(value).all():
                raise ValueError(f"Telemetría inválida: {key}")
            result[key] = value
        if np.any(np.diff(times) <= 0) or np.any(
            np.abs(np.linalg.norm(result["qpos"][:, 3:7], axis=1) - 1) > 1e-4
        ):
            raise ValueError("Tiempo u orientación inválidos")
    return result
