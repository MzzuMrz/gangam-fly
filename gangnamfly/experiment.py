"""Serial sensor -> native graph -> fixed decoder -> physical body experiment."""

import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path

import numpy as np

from .adapters import MotorAdapter, ProvisionalProprioceptionAdapter
from .brain import MaleCNSAdapter
from .config import BODY, DOOM, DT, EPISODES, SEED
from .environment import FlybodyEnvironment
from .episode import Episode, save_json
from .provenance import provenance
from .reference import DanceReference


class Experiment:
    def __init__(self, root=EPISODES, record_spikes=False):
        self.record_spikes = record_spikes
        self.sources = {p.name: p.read_bytes() for p in Path(__file__).parent.glob("*.py")}
        self.objective = None
        self.quality_rows = []
        self.last_episode_id = None
        self.replay_changed = None
        self.environment = FlybodyEnvironment()
        self.provenance = provenance()
        self.brain = MaleCNSAdapter()
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.brain.mapping.save(self.root / "mappings.json")
        self.mapping_hash = hashlib.sha256((self.root / "mappings.json").read_bytes()).hexdigest()
        e = self.environment
        self.reference = DanceReference(e.names, e.rest, e.limits)
        self.episode = None
        self.mode = "observe"
        self.tick = 0
        self.score = 0.0
        self.reward_sum = 0.0
        self.error = 0.0
        self.wall = 0.0
        self.last_counts = np.zeros(self.brain.native.n, np.int32)
        self.motor = MotorAdapter(self.brain.mapping, e.rest, e.limits)
        self.sensory = ProvisionalProprioceptionAdapter(self.brain.mapping)

    def begin(
        self,
        mode="observe",
        seed=SEED,
        duration=4.0,
        initial_weights=None,
        teaching="target",
        jitter=0.005,
        trial=None,
    ):
        if self.episode is not None:
            self.finish("interrupted")
        if mode not in ("observe", "train") or not 0 < duration <= 120:
            raise ValueError("Invalid mode or episode duration")
        if teaching not in ("target", "constant", "inverted"):
            raise ValueError("Unknown teaching control")
        self.teaching = teaching
        e, b = self.environment, self.brain
        if initial_weights is not None:
            self.restore_weights(initial_weights)
        self.quality_rows = []
        self.reward_sum = 0.0
        self.starting_weights = b.native.weight[b.plasticity.edges].copy()
        b.reset()
        e.reset(seed, jitter)
        self.motor = MotorAdapter(b.mapping, e.rest, e.limits)
        self.sensory = ProvisionalProprioceptionAdapter(b.mapping, seed)
        self.mode, self.tick, self.wall = mode, 0, 0.0
        self.max_ticks = round(duration / DT)
        if self.max_ticks < 1:
            raise ValueError("Episode is shorter than one control tick")
        config = {
            "schema": 3,
            "trial": trial,
            "objective": None
            if self.objective is None
            else {
                "target_hash": self.objective.target.fingerprint,
                "source": self.objective.target.source,
                "duration": self.objective.target.duration,
                "criterion": self.objective.criterion,
                "stage": self.objective.descriptor() if hasattr(self.objective, "descriptor") else None,
                "reward": "1 / (1 + mean normalized cumulative constraint deficits) (microcurriculum.py)"
                if getattr(self.objective, "stage", {}).get("protocol") == "micro-v1"
                and self.objective.stand_only
                else "anatomical alignment * stability * foot support (curriculum.py)"
                if getattr(self.objective, "stand_only", False)
                else "0.45 exp(-(joint_rmse/0.8)^2) + 0.35 exp(-orientation^2) + 0.20 exp(-(position_cm/0.15)^2)",
            },
            "decoder": "fixed-opponent-rates-full-actuator-range-v2",
            "provenance": self.provenance,
            "teaching": teaching,
            "initial_joint_jitter_radians": jitter,
            "static_actuators": [
                {"name": e.model.actuator(i).name, "command": float(e.data.ctrl[i])}
                for i in range(e.model.nu)
                if i not in e.actuators
            ],
            "mode": mode,
            "seed": seed,
            "duration": self.max_ticks * DT,
            "brain_step_seconds": DT,
            "native_dt_ms": 0.1,
            "physics_dt_seconds": e.model.opt.timestep,
            "graph_sha256": b.graph_hash,
            "mapping_sha256": self.mapping_hash,
            "body_sha256": hashlib.sha256((BODY / "fruitfly.xml").read_bytes()).hexdigest(),
            "kernel": json.loads((DOOM / "outputs/doom/libneural.dylib.json").read_text())
            if sys.platform == "darwin"
            else json.loads((DOOM / "outputs/doom/libneural.so.json").read_text()),
            "versions": {name: importlib.metadata.version(name) for name in ["numpy", "mujoco", "numba"]},
            "plasticity": {
                "rule": "bounded-reward-modulated-binned-Hebbian",
                "eta": b.plasticity.eta,
                "edges": len(b.plasticity.edges),
                "bounds": [0.5, 1.5],
            },
            "reference": "Xsens retargeted continuous take"
            if self.objective
            else "legacy authored joint motif",
            "bpm": 132,
            "motor_gain": self.motor.gain,
            "full_spikes": self.record_spikes,
            "source_sha256": {
                name: hashlib.sha256(content).hexdigest() for name, content in self.sources.items()
            },
        }
        self.episode = Episode(self.root, config, b.native.weight[b.plasticity.edges])
        b.mapping.save(self.episode.path / "mappings.json")
        np.save(self.episode.path / "plastic_edge_indices.npy", b.plasticity.edges)
        # Source snapshot makes code hashes reviewable after future local edits.
        source = self.episode.path / "source"
        source.mkdir()
        for name, content in self.sources.items():
            (source / name).write_bytes(content)
        self.last_counts.fill(0)
        self.replay_changed = None
        self.error = self.reference.error(e.data.qpos[e.qadr], 0.0)
        self.score = float(np.exp(-4 * self.error))
        if self.objective is not None:
            measured = self.objective.measure(e.data.qpos, 0.0)
            self.score, self.error = measured["reward"], measured["joint_rmse"] ** 2

    def step(self):
        if self.episode is None:
            raise RuntimeError("No active episode")
        start = time.perf_counter()
        e, b = self.environment, self.brain
        t = self.tick * DT
        sensory = self.sensory.encode(e, t, exploration=self.mode == "train")
        counts, brain_seconds = b.step(sensory, DT)
        command = self.motor.decode(counts, DT)
        e.step(command)
        self.tick += 1
        t = self.tick * DT
        self.error = self.reference.error(e.data.qpos[e.qadr], t)
        # Error is actual joint tracking, not target control similarity.
        # Upright term penalizes lying down without applying balance forces.
        upright = max(0.0, float(e.data.xmat[e.model.body("thorax").id, 8]))
        self.score = float(np.exp(-4 * self.error) * (0.25 + 0.75 * upright))
        measured = {}
        if self.objective is not None:
            measured = self.objective.measure(e.data.qpos, t)
            self.quality_rows.append(measured)
            self.error, self.score = measured["joint_rmse"] ** 2, measured["reward"]
        self.reward_sum += self.score
        teaching_reward = (
            0.5
            if self.teaching == "constant"
            else 1 - self.score
            if self.teaching == "inverted"
            else self.score
        )
        b.plasticity.update(counts, teaching_reward, enabled=self.mode == "train")
        self.last_counts = counts
        self.wall += time.perf_counter() - start
        self.episode.add(
            time=t,
            qpos=e.data.qpos,
            qvel=e.data.qvel,
            act=e.data.act,
            ctrl=e.data.ctrl,
            sensory=sensory,
            motor_rates=self.motor.rates,
            motor_counts=counts[b.mapping.motor_indices],
            dn_counts=np.asarray([counts[p["indices"]].sum() for p in b.mapping.dn]),
            motor_voltage=b.native.v[b.mapping.motor_indices],
            command=command,
            reward=self.score,
            teaching_reward=teaching_reward,
            tracking_error=self.error,
            brain_seconds=brain_seconds,
            total_spikes=int(counts.sum()),
            changed_edges=b.plasticity.changed,
            learning_enabled=self.mode == "train",
            changed_this_step=b.plasticity.changed_this_step,
            weight_update_l1=b.plasticity.update_l1,
            **{k: v for k, v in measured.items() if k != "reward"},
            **({"full_counts": counts.astype(np.uint16)} if self.record_spikes else {}),
        )
        return self.tick >= self.max_ticks

    def finish(self, reason="complete"):
        if self.episode is None:
            return None
        p = self.brain.plasticity
        summary = self.episode.finish(self.brain.native.weight[p.edges], reason, p.changed)
        if self.objective is not None:
            summary.update(self.objective.quality(self.quality_rows, self.tick * DT))
        if reason != "complete":
            summary["passed"] = False
        save_json(self.episode.path / "summary.json", summary)
        self.last_episode_id = summary["id"]
        self.episode = None
        return summary

    def restore_weights(self, weights):
        p = self.brain.plasticity
        value = np.asarray(weights)
        if value.shape != p.base.shape or not np.isfinite(value).all():
            raise ValueError("Invalid checkpoint shape/values")
        ratio = value / p.base
        if np.any(ratio < 0.5) or np.any(ratio > 1.5):
            raise ValueError("Checkpoint changes signs or exceeds bounds")
        self.brain.native.weight[p.edges] = value

    def evidence(self):
        b, p = self.brain, self.brain.plasticity
        current = b.native.weight[p.edges]
        before = getattr(self, "starting_weights", p.base)
        chosen = np.flatnonzero(current != before)[:5]
        return {
            "source": "MaleCNS → MuJoCo",
            "target_hash": self.objective.target.fingerprint if self.objective else None,
            "graph_hash": b.graph_hash,
            "kernel_hash": self.provenance["kernel"]["binary_sha256"],
            "total_spikes": b.native.total_spikes,
            "changed_this_step": p.changed_this_step,
            "update_l1": p.update_l1,
            "weight_examples": [
                {
                    "pre_id": int(b.native.ids[p.pre[i]]),
                    "post_id": int(b.native.ids[p.post[i]]),
                    "before": float(before[i]),
                    "after": float(current[i]),
                    "delta": float(current[i] - before[i]),
                }
                for i in chosen
            ],
            "last_episode_id": self.last_episode_id,
            "verified": False,
        }

    def snapshot(self):
        e, b = self.environment, self.brain
        return {
            "objective_metrics": self.quality_rows[-1]
            if self.quality_rows and self.mode != "replay"
            else None,
            "mode": self.mode,
            "evidence": self.evidence(),
            "sim_time": self.tick * DT,
            "wall_time": self.wall,
            "brain_hz": self.tick / self.wall if self.wall else 0.0,
            "physics_hz": self.tick * DT / e.model.opt.timestep / self.wall if self.wall else 0.0,
            "realtime_factor": self.tick * DT / self.wall if self.wall else 0.0,
            "reward": self.score,
            "reward_mean": self.reward_sum / self.tick if self.tick else None,
            "tracking_error": self.error,
            "changed_edges": self.replay_changed if self.mode == "replay" else b.plasticity.changed,
            "neurons": b.native.n,
            "edges": len(b.native.post),
            "geoms": e.transforms(),
            "speed": float(np.linalg.norm(e.data.qvel[:3])),
            "motor_rates": [
                {"name": p["name"], "rate": float(self.last_counts[p["indices"]].mean()) / DT}
                for p in b.mapping.dn
            ],
            "vnc_rates": [
                {"name": f"{segment}_{side}", "rate": float(self.motor.rates[i * 5 : (i + 1) * 5].mean())}
                for i, (segment, side) in enumerate((s, d) for s in ["T1", "T2", "T3"] for d in ["L", "R"])
            ],
            "episode_id": self.episode.path.name if self.episode else None,
        }
