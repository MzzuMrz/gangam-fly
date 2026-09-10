"""Serial, unlimited trials with held-out frozen evaluations and atomic checkpoints."""

import hashlib
import json
import uuid

import numpy as np

from .episode import save_json, save_npz
from .objective import CRITERION


class TrainingSession:
    def __init__(self, root, signature, seed=64, eval_every=5, stages=None):
        self.stages = stages
        signature = (
            {**signature, "stages": stages, "seed_scheme": "stage-residue-even-evaluation-v1"}
            if stages
            else signature
        )
        self.root, self.signature = root, signature
        self.check_paths()
        root.mkdir(parents=True, exist_ok=True)
        (root / "history").mkdir(exist_ok=True)
        self.saved_weights = None
        self.active = False
        self.state = {
            "session_id": uuid.uuid4().hex[:16],
            "phase": "baseline",
            "seed": seed,
            "eval_every": eval_every,
            "evaluation_index": 0,
            "attempt": 0,
            "completed_trials": 0,
            "simulated_seconds": 0.0,
            "interrupted_seconds": 0.0,
            "baseline": [],
            "evaluation": [],
            "baseline_score": None,
            "best_score": None,
            "history": [],
        }
        if stages:
            self.state.update(stage_index=0, stage_results=[], initialization=None)
        checkpoint = root / "checkpoint.npz"
        if checkpoint.exists():
            with np.load(checkpoint, allow_pickle=False) as z:
                if json.loads(str(z["signature"])) != signature:
                    raise ValueError(
                        "Training checkpoint provenance differs; keep it and use a new session directory"
                    )
                state = json.loads(str(z["state"]))
                self.validate_state(state)
                self.state = state
                self.saved_weights = z["weights"].copy()
                if self.saved_weights.ndim != 1 or not np.isfinite(self.saved_weights).all():
                    raise ValueError("Invalid checkpoint weights")
            self.repair_history()
        self.validate_state(self.state)

    def check_paths(self):
        paths = [self.root, self.root / "history"]
        for name in ("checkpoint.npz", "checkpoint.partial", "best_weights.npz", "best_weights.partial"):
            paths.append(self.root / name)
        if any(p.is_symlink() for p in paths):
            raise ValueError("Training checkpoint paths cannot be symbolic links")

    def validate_state(self, state):
        def number(value, minimum=0.0, maximum=float("inf")):
            return type(value) in (int, float) and np.isfinite(value) and minimum <= value <= maximum

        def validate_row(row):
            if (
                not isinstance(row, dict)
                or not number(row["score"], 0, 1)
                or not number(row["seconds"], 0, 120)
            ):
                raise ValueError("trial values")
            if not isinstance(row["id"], str) or not row["id"] or any(c in row["id"] for c in "/\\"):
                raise ValueError("trial id")
            if row["phase"] not in ("baseline", "train", "evaluate"):
                raise ValueError("trial phase")
            if any(type(row[k]) is not int or row[k] < 0 for k in ("seed", "attempt")):
                raise ValueError("trial counters")
            if "passed" in row and type(row["passed"]) is not bool:
                raise ValueError("trial result")

        try:
            if not isinstance(state, dict) or set(state) != set(self.state):
                raise ValueError("schema")
            for key in ("seed", "eval_every", "evaluation_index", "attempt", "completed_trials"):
                if type(state[key]) is not int or state[key] < (1 if key == "eval_every" else 0):
                    raise ValueError(key)
            if not isinstance(state["session_id"], str) or len(state["session_id"]) != 16:
                raise ValueError("session id")
            for key in ("simulated_seconds", "interrupted_seconds"):
                if not number(state[key]):
                    raise ValueError(key)
            for key in ("baseline_score", "best_score"):
                if state[key] is not None and not number(state[key], 0, 1):
                    raise ValueError(key)
            for key, maximum in (("baseline", 2), ("evaluation", 2), ("history", 100)):
                rows = state[key]
                if not isinstance(rows, list) or len(rows) > maximum:
                    raise ValueError(key)
                for row in rows:
                    validate_row(row)
            if len(state["history"]) != min(100, state["completed_trials"]):
                raise ValueError("history length")
            if self.stages:
                initialization = state["initialization"]
                if initialization is not None and (
                    not isinstance(initialization, dict)
                    or set(initialization) != {"source", "sha256", "kind"}
                    or initialization["source"]
                    not in ("_training/checkpoint.npz", "_training_curriculum/checkpoint.npz")
                    or initialization["kind"] != "weights-only warm start; new objective baseline required"
                    or not isinstance(initialization["sha256"], str)
                    or len(initialization["sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in initialization["sha256"])
                ):
                    raise ValueError("initialization provenance")
                stage = state["stage_index"]
                certificates = state["stage_results"]
                if type(stage) is not int or not 0 <= stage < len(self.stages):
                    raise ValueError("stage index")
                expected = stage + (state["phase"] == "complete")
                if not isinstance(certificates, list) or len(certificates) != expected:
                    raise ValueError("stage certificates")
                for i, certificate in enumerate(certificates):
                    rows = certificate["evaluations"]
                    if not isinstance(rows, list) or not number(certificate["score"], 0, 1):
                        raise ValueError("certificate values")
                    for row in rows:
                        validate_row(row)
                    if not rows or certificate["score"] != float(np.mean([r["score"] for r in rows])):
                        raise ValueError("certificate mean")
                    if (
                        certificate["stage_id"] != self.stages[i]["id"]
                        or certificate["qualification"] not in ("baseline", "evaluate")
                        or len(rows) != 2
                        or not all(r.get("passed") is True for r in rows)
                        or [r["seed"] for r in rows]
                        != [state["seed"] + i + len(self.stages) * 2 * j for j in range(2)]
                        or any(
                            r["phase"] != certificate["qualification"] or r["stage_index"] != i for r in rows
                        )
                    ):
                        raise ValueError("stage certificate")
                for key in ("baseline", "evaluation", "history"):
                    for row in state[key]:
                        ri = row["stage_index"]
                        if (
                            type(ri) is not int
                            or not 0 <= ri <= stage
                            or row["stage_id"] != self.stages[ri]["id"]
                        ):
                            raise ValueError("trial stage")
                        if key != "history" and ri != stage:
                            raise ValueError("current trial stage")
            phase, index = state["phase"], state["evaluation_index"]
            if phase == "baseline":
                valid = (
                    index in (0, 1)
                    and len(state["baseline"]) == index
                    and state["baseline_score"] is None
                    and state["attempt"] == 0
                    and not state["evaluation"]
                )
            else:
                valid = (
                    len(state["baseline"]) == 2
                    and state["baseline_score"] is not None
                    and state["attempt"] >= 1
                )
                if phase == "train":
                    valid = valid and index == 0 and not state["evaluation"]
                elif phase in ("evaluate", "complete"):
                    valid = (
                        valid
                        and state["attempt"] % state["eval_every"] == 0
                        and len(state["evaluation"]) == index
                        and index in ((0, 1) if phase == "evaluate" else (2,))
                    )
                    if phase == "complete":
                        valid = (
                            valid
                            and all(r.get("passed") is True for r in state["evaluation"])
                            and np.mean([r["score"] for r in state["evaluation"]])
                            > state["baseline_score"] + 0.001
                        )
                else:
                    valid = False
            if self.stages and phase == "complete":
                valid = (
                    state["stage_index"] == len(self.stages) - 1
                    and index == 2
                    and len(state["stage_results"]) == len(self.stages)
                )
            if not valid:
                raise ValueError("phase invariants")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Invalid training checkpoint: {exc}") from exc

    def repair_history(self):
        # The atomic checkpoint is authoritative. A crash after its rename is
        # repaired idempotently into a stable sequence-numbered journal record.
        if self.state["history"]:
            self.check_paths()
            path = self.root / "history" / f"{self.state['completed_trials']:012d}.json"
            if path.is_symlink() or path.with_suffix(".json.partial").is_symlink():
                raise ValueError("Training history cannot be symbolic links")
            save_json(path, self.state["history"][-1])

    @property
    def phase(self):
        return self.state["phase"]

    def start(self):
        self.active = self.phase != "complete"

    def trial(self):
        s = self.state
        multiplier = len(self.stages) if self.stages else 1
        base = s["seed"] + s.get("stage_index", 0)
        if self.phase in ("baseline", "evaluate"):
            return "observe", base + multiplier * 2 * s["evaluation_index"]
        return "train", base + multiplier * (2 * s["attempt"] + 1)

    def checkpoint(self, weights):
        self.check_paths()
        self.validate_state(self.state)
        save_npz(
            self.root / "checkpoint.npz",
            weights=weights,
            state=np.array(json.dumps(self.state)),
            signature=np.array(json.dumps(self.signature)),
        )

    def stop(self, weights, seconds=0.0):
        self.state["interrupted_seconds"] += seconds
        self.active = False
        self.checkpoint(weights)

    def complete(self, summary, weights):
        s = self.state
        row = {**summary, "phase": self.phase, "attempt": s["attempt"], "seed": self.trial()[1]}
        if self.stages:
            row.update(stage_index=s["stage_index"], stage_id=self.stages[s["stage_index"]]["id"])
        s["history"] = (s["history"] + [row])[-100:]
        s["completed_trials"] += 1
        s["simulated_seconds"] += summary["seconds"]
        if self.phase in ("baseline", "evaluate"):
            key = "baseline" if self.phase == "baseline" else "evaluation"
            s[key].append(row)
            s["evaluation_index"] += 1
            if s["evaluation_index"] == 2:
                score = float(np.mean([r["score"] for r in s[key]]))
                if self.stages and all(r.get("passed") is True for r in s[key]):
                    s["stage_results"].append(
                        {
                            "stage_id": self.stages[s["stage_index"]]["id"],
                            "qualification": self.phase,
                            "score": score,
                            "evaluations": list(s[key]),
                            "baseline_score": s["baseline_score"],
                        }
                    )
                    s["best_score"] = score
                    if key == "baseline":
                        s["baseline_score"] = score
                    if s["stage_index"] + 1 == len(self.stages):
                        s["phase"], self.active = "complete", False
                    else:
                        s.update(
                            stage_index=s["stage_index"] + 1,
                            phase="baseline",
                            attempt=0,
                            evaluation_index=0,
                            baseline=[],
                            evaluation=[],
                            baseline_score=None,
                            best_score=None,
                        )
                    # Promotion and its certificates commit in the same atomic file.
                    self.checkpoint(weights)
                    self.repair_history()
                    return
                if key == "baseline":
                    s["baseline_score"] = score
                else:
                    if s["best_score"] is None or score > s["best_score"]:
                        s["best_score"] = score
                        save_npz(
                            self.root / "best_weights.npz",
                            weights=weights,
                            stage_index=np.array(s.get("stage_index", -1)),
                            score=np.array(score),
                            signature=np.array(json.dumps(self.signature)),
                        )
                    if all(r.get("passed", False) for r in s[key]) and score > s["baseline_score"] + 0.001:
                        s["phase"], self.active = "complete", False
                        self.checkpoint(weights)
                        self.repair_history()
                        return
                    s["evaluation"] = []
                s["evaluation_index"] = 0
                s["phase"] = "train"
                s["attempt"] += 1
        else:
            if s["attempt"] % s["eval_every"] == 0:
                s["phase"] = "evaluate"
                s["evaluation_index"] = 0
            else:
                s["attempt"] += 1
        self.checkpoint(weights)
        self.repair_history()

    def snapshot(self):
        return {
            **self.state,
            "active": self.active,
            "phase": self.phase if self.active or self.phase == "complete" else "stopped",
            "criterion": CRITERION,
        }


def import_legacy_weights(path, signature):
    """Import only compatible weights; old objectives and reward history stay separate."""
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Legacy checkpoint cannot be a symbolic link")
    before = path.read_bytes()
    import io

    with np.load(io.BytesIO(before), allow_pickle=False) as z:
        old = json.loads(str(z["signature"]))
        compatible = all(old[k] == signature[k] for k in ("graph", "mapping")) and all(
            old["provenance"][k] == signature["provenance"][k] for k in ("body_assets", "kernel")
        )
        compatible = compatible and all(
            old["provenance"].get("dynamics_sources", {}).get(name) is not None
            and old["provenance"]["dynamics_sources"][name]
            == signature["provenance"]["dynamics_sources"][name]
            for name in ("brain.py", "plasticity.py")
        )
        if path.parent.name == "_training_curriculum":
            compatible = (
                compatible
                and old.get("plastic_edges") is not None
                and old["plastic_edges"] == signature.get("plastic_edges")
            )
        if not compatible:
            raise ValueError("Legacy checkpoint is incompatible with current graph, mapping, body or kernel")
        weights = z["weights"].copy()
    return weights, {
        "source": "_training_curriculum/checkpoint.npz"
        if path.parent.name == "_training_curriculum"
        else "_training/checkpoint.npz",
        "sha256": hashlib.sha256(before).hexdigest(),
        "kind": "weights-only warm start; new objective baseline required",
    }
