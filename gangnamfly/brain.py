"""Thin adapter to pinned DOOMFLY native state and ABI, not a new kernel."""

import hashlib
import sys
import time

import numpy as np

from .config import DOOM, GRAPH
from .mapping import Mapping
from .plasticity import Plasticity


class MaleCNSAdapter:
    def __init__(self):
        sys.path.insert(0, str(DOOM))
        from doom.native import NativeBrain, _f

        self.native = NativeBrain(GRAPH)
        self.advance = _f
        self.mapping = Mapping(self.native.ids)
        b = self.native
        selected = np.zeros(b.n, bool)
        selected[self.mapping.motor_indices] = True
        edges = np.flatnonzero(selected[b.post])
        # CSR pre indices only for plastic edges, no per-synapse Python objects.
        pre = np.searchsorted(b.ptr, edges, side="right").astype(np.int32) - 1
        self.plasticity = Plasticity(b.weight, edges, pre, b.post[edges])
        with GRAPH.open("rb") as stream:
            self.graph_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        self.initial = {
            k: getattr(b, k).copy()
            for k in [
                "v",
                "g",
                "drive",
                "previous_drive",
                "refractory",
                "queue",
                "queue_count",
                "counts",
                "active",
                "active_flag",
                "nactive",
                "last",
            ]
        }

    def reset(self):
        b = self.native
        for key, value in self.initial.items():
            getattr(b, key)[:] = value
        b.cursor = 0
        b.sim_ms = 0.0
        b.total_spikes = 0
        self.plasticity.reset_traces()

    def step(self, currents, seconds=0.02):
        b = self.native
        values = np.asarray(currents, np.float32)
        if values.shape != (len(self.mapping.sensory),) or not np.isfinite(values).all():
            raise ValueError("Invalid sensory currents")
        steps = round(seconds * 1000 / b.dt)
        if steps < 1 or abs(steps * b.dt - seconds * 1000) > 1e-6:
            raise ValueError("Neural interval must be positive integer kernel ticks")
        b.drive.fill(0)
        for pool, current in zip(self.mapping.sensory, values):
            b.drive[pool["indices"]] += current
        b.counts.fill(0)
        clock = np.asarray([b.cursor], np.int64)
        arrays = [
            b.ptr,
            b.post,
            b.weight,
            b.v,
            b.g,
            b.refractory,
            b.drive,
            b.previous_drive,
            b.queue,
            b.queue_count,
            clock,
        ]
        start = time.perf_counter()
        self.advance(
            b.n,
            *[a.ctypes.data for a in arrays],
            steps,
            b.dt,
            *[getattr(b, k).ctypes.data for k in ["counts", "active", "active_flag", "nactive", "last"]],
        )
        b.cursor = int(clock[0])
        b.sim_ms = b.cursor * b.dt
        b.total_spikes += int(b.counts.sum())
        return b.counts, time.perf_counter() - start
