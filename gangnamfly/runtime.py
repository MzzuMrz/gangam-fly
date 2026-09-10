"""One owner for mutable simulation state; HTTP threads exchange snapshots only."""

import gzip
import hashlib
import json
import math
import queue
import threading
import time
import traceback
import zipfile
import zlib

import mujoco

from .captured_target import load_target
from .config import DT, EPISODES
from .curriculum import STAND_CRITERION
from .demo import build_clip
from .evidence import verification_status
from .experiment import Experiment
from .microcurriculum import STAGES, MicroObjective
from .objective import CapturedObjective
from .replay import history
from .replay import load as load_replay
from .training import TrainingSession, import_legacy_weights


class Runtime:
    def __init__(
        self,
        root=EPISODES,
        duration=4.0,
        auto=True,
        seed=64,
        record_spikes=False,
        training_seconds=None,
        curriculum=True,
    ):
        self.curriculum = curriculum
        self.target = None
        self.seed, self.record_spikes = seed, record_spikes
        self.training_seconds = training_seconds
        self.training = None
        self.training_error = None
        self.demo_error = None
        self.proof_checked_at = 0.0
        self.proof_verified = False
        self.proof_episode = None
        self.root, self.duration = root, duration
        self.commands: queue.Queue[tuple[str, str | None]] = queue.Queue(maxsize=8)
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.model = None
        self.demo = None
        self.state = {
            "status": "loading",
            "mode": "observe",
            "message": "Cargando Flybody y MaleCNS verificado…",
            "episodes": [],
            "geoms": [],
        }
        self.error = None
        self.auto = auto
        self.thread = threading.Thread(target=self.run, daemon=True, name="gangnamfly-simulation")
        self.thread.start()

    def read(self):
        with self.lock:
            return self.state

    def submit(self, action, episode=None):
        if action not in ("observe", "train", "pause", "stop", "replay"):
            raise ValueError("Acción desconocida")
        if episode is not None and (
            not isinstance(episode, str)
            or len(episode) > 80
            or any(c not in "0123456789T-" + "abcdef" for c in episode)
        ):
            raise ValueError("Identificador de episodio inválido")
        if self.read()["status"] in ("loading", "error"):
            raise ValueError("La simulación todavía no está disponible")
        self.commands.put_nowait((action, episode))

    def history(self):
        return history(self.root)

    def publish(self, experiment, status, message=""):
        state = experiment.snapshot()
        state.update(status=status, message=message, episodes=self.history())
        if self.training:
            state["training"] = self.training.snapshot()
            state["training"]["current_trial_seconds"] = experiment.tick * DT if self.training.active else 0
            state["training"]["trial_duration"] = (
                self.training_seconds or math.ceil(experiment.objective.target.duration / DT) * DT
            )
            state["training"]["target_duration"] = experiment.objective.target.duration
            if self.curriculum:
                stage = self.training.state["stage_index"]
                state["training"]["stage"] = experiment.objective.descriptor()
                state["training"]["stages"] = [
                    {
                        "id": s["id"],
                        "label": s["label"],
                        "active": i == stage,
                        "completed": i < len(self.training.state["stage_results"]),
                        "score": self.training.state["stage_results"][i]["score"]
                        if i < len(self.training.state["stage_results"])
                        else None,
                    }
                    for i, s in enumerate(STAGES)
                ]
        state["training_error"] = self.training_error
        state["demo_error"] = self.demo_error
        last_id = state["evidence"]["last_episode_id"]
        if last_id and (last_id != self.proof_episode or time.monotonic() - self.proof_checked_at > 2):
            self.proof_verified = verification_status(self.root / last_id)
            self.proof_episode = last_id
            self.proof_checked_at = time.monotonic()
        state["evidence"]["verified"] = self.proof_verified if last_id else False
        with self.lock:
            self.state = state

    def run(self):
        experiment = None
        try:
            experiment = Experiment(self.root, record_spikes=self.record_spikes)
            # Serialize once. Browser receives native MuJoCo mesh coordinates.
            payload = json.dumps(experiment.environment.geometry(), separators=(",", ":")).encode()
            self.model = gzip.compress(payload, compresslevel=3)
            del payload
            try:
                target = self.target = load_target(experiment.environment)
                experiment.objective = CapturedObjective(target, experiment.environment.qadr)
                signature = {
                    "provenance": experiment.provenance,
                    "graph": experiment.brain.graph_hash,
                    "mapping": experiment.mapping_hash,
                    "plastic_edges": hashlib.sha256(experiment.brain.plasticity.edges.tobytes()).hexdigest(),
                    "target": target.fingerprint,
                    "criterion": experiment.objective.criterion,
                    "trial_duration": self.training_seconds or math.ceil(target.duration / DT) * DT,
                    "protocol": {
                        name: hashlib.sha256(experiment.sources[name]).hexdigest()
                        for name in ("training.py", "runtime.py")
                    },
                }
                try:
                    if self.curriculum:
                        signature.update(
                            stand_criterion=STAND_CRITERION, trial_override=self.training_seconds
                        )
                    self.training = TrainingSession(
                        self.root / ("_training_micro" if self.curriculum else "_training"),
                        signature,
                        seed=self.seed,
                        stages=STAGES if self.curriculum else None,
                    )
                    legacy = self.root / "_training_curriculum/checkpoint.npz"
                    if not legacy.exists():
                        legacy = self.root / "_training/checkpoint.npz"
                    if self.curriculum and self.training.saved_weights is None and legacy.exists():
                        weights, metadata = import_legacy_weights(legacy, signature)
                        experiment.restore_weights(
                            weights
                        )  # Validate shape, signs and bounds before writing.
                        self.training.state["initialization"] = metadata
                        self.training.checkpoint(weights)
                        self.training.saved_weights = weights
                    self.set_objective(experiment)
                    if self.training.saved_weights is not None:
                        experiment.restore_weights(self.training.saved_weights)
                    if self.training.state["history"]:
                        experiment.last_episode_id = self.training.state["history"][-1]["id"]
                except (
                    ValueError,
                    OSError,
                    KeyError,
                    TypeError,
                    EOFError,
                    zipfile.BadZipFile,
                    zlib.error,
                ) as exc:
                    self.training = None
                    self.training_error = f"Checkpoint no cargado: {exc}"
                self.demo = gzip.compress(
                    json.dumps(build_clip(experiment.environment), separators=(",", ":")).encode(),
                    compresslevel=3,
                )
            except Exception as exc:  # noqa: BLE001 - optional preview boundary
                self.demo_error = f"Referencia no disponible: {exc}"
                self.training_error = self.demo_error if experiment.objective is None else self.training_error
                traceback.print_exc()
            status = "idle"
            replay = None
            cursor = 0
            paused = False
            message = (
                self.training_error
                or "Listo. MaleCNS controla 30 actuadores; los restantes conservan comandos estáticos."
            )
            if self.training and self.training.saved_weights is not None:
                message = "Checkpoint restaurado. Entrenar continúa con esos pesos desde el inicio del intento pendiente."
            if not experiment.last_episode_id and self.history():
                experiment.last_episode_id = self.history()[-1]["id"]
            if self.auto:
                experiment.begin(duration=self.duration, seed=self.seed)
                status = "running"
            self.publish(experiment, status, message)
            while not self.stop.is_set():
                try:
                    action, episode = self.commands.get_nowait()
                except queue.Empty:
                    action = None
                if action == "pause":
                    if status in ("running", "replay"):
                        paused = not paused
                elif action == "stop":
                    self.stop_training(experiment, "stopped")
                    replay, paused, status = None, False, "idle"
                    message = "Detenido. Episodio y pesos guardados."
                elif action == "train":
                    if self.training is None:
                        message = self.training_error or "La referencia de entrenamiento no está disponible."
                    elif self.training.active:
                        paused = False
                    else:
                        experiment.finish("interrupted")
                        self.training.start()
                        replay, paused = None, False
                        if self.training.active:
                            self.begin_trial(experiment)
                            status = "running"
                            message = "Sesión continua: baseline congelado, intentos y evaluaciones medidas."
                        else:
                            message = "La sesión alcanzó el criterio registrado."
                elif action == "observe":
                    if self.training and self.training.active:
                        self.stop_training(experiment, "interrupted")
                    replay, paused = None, False
                    experiment.begin(action, duration=self.duration, seed=self.seed)
                    status = "running"
                    message = (
                        "Entrenando plasticidad en conexiones existentes."
                        if action == "train"
                        else "Observando con pesos congelados."
                    )
                elif action == "replay":
                    history = self.history()
                    selected = episode or (history[-1]["id"] if history else None)
                    if selected not in {h["id"] for h in history}:
                        message = "No hay un episodio disponible para reproducir."
                    else:
                        try:
                            candidate = load_replay(self.root / selected, experiment.environment)
                        except (
                            ValueError,
                            OSError,
                            KeyError,
                            TypeError,
                            EOFError,
                            zipfile.BadZipFile,
                            zlib.error,
                        ) as exc:
                            message = f"No se puede reproducir el episodio: {exc}"
                            self.publish(experiment, status, message)
                            continue
                        self.stop_training(experiment, "interrupted")
                        replay = candidate
                        cursor, paused, status = 0, False, "replay"
                        experiment.mode = "replay"
                        message = f"Replay de física registrada: {selected}. No es entrenamiento en vivo."
                if paused:
                    self.publish(experiment, "paused", message)
                    self.stop.wait(0.05)
                    continue
                if status == "running":
                    done = experiment.step()
                    if done:
                        summary = experiment.finish()
                        if self.training and self.training.active:
                            self.training.complete(
                                summary, experiment.brain.native.weight[experiment.brain.plasticity.edges]
                            )
                            if self.training.active:
                                self.begin_trial(experiment)
                            else:
                                status = "idle"
                                message = "Criterio físico alcanzado en dos evaluaciones congeladas."
                        else:
                            status = "idle"
                            message = "Episodio guardado."
                elif status == "replay" and replay is not None:
                    if cursor >= len(replay["time"]):
                        replay, status = None, "idle"
                        message = "Replay finalizado."
                    else:
                        e = experiment.environment
                        e.data.qpos[:] = replay["qpos"][cursor]
                        e.data.qvel[:] = replay["qvel"][cursor]
                        e.data.ctrl[:] = replay["ctrl"][cursor]
                        e.data.act[:] = replay["act"][cursor]
                        e.data.time = float(replay["time"][cursor])
                        mujoco.mj_forward(e.model, e.data)
                        experiment.tick = round(e.data.time / DT)
                        experiment.score = float(replay["reward"][cursor])
                        experiment.reward_sum = float(replay["reward"][: cursor + 1].sum())
                        experiment.error = float(replay["tracking_error"][cursor])
                        experiment.wall = 0.0
                        experiment.replay_changed = int(replay["changed_edges"][cursor])
                        experiment.motor.rates[:] = replay["motor_rates"][cursor]
                        experiment.last_counts.fill(0)
                        # Recorded DN counts are group sums; groups are single cells here.
                        for p, count in zip(experiment.brain.mapping.dn, replay["dn_counts"][cursor]):
                            experiment.last_counts[p["indices"]] = int(count) // len(p["indices"])
                        cursor += 1
                        self.stop.wait(DT)
                else:
                    self.stop.wait(0.05)
                self.publish(experiment, status, message)
        except Exception as exc:  # noqa: BLE001 - worker boundary must save failed episodes
            traceback.print_exc()
            self.error = str(exc)
            with self.lock:
                self.state = {
                    **self.state,
                    "status": "error",
                    "message": "La simulación se detuvo. Revisá el log de la terminal.",
                }
        finally:
            if experiment is not None:
                self.stop_training(experiment, "shutdown" if self.error is None else "error")

    def stop_training(self, experiment, reason):
        summary = experiment.finish(reason)
        if self.training and self.training.active:
            self.training.stop(
                experiment.brain.native.weight[experiment.brain.plasticity.edges],
                seconds=summary["seconds"] if summary else 0.0,
            )

    def set_objective(self, experiment):
        assert self.training is not None
        if self.curriculum:
            experiment.objective = MicroObjective(
                self.target, experiment.environment, self.training.state["stage_index"]
            )

    def begin_trial(self, experiment):
        assert self.training is not None
        self.set_objective(experiment)
        mode, seed = self.training.trial()
        duration = self.training_seconds or math.ceil(experiment.objective.target.duration / DT) * DT
        experiment.begin(
            mode,
            seed=seed,
            duration=duration,
            trial={
                "session_id": self.training.state["session_id"],
                "phase": self.training.phase,
                "attempt": self.training.state["attempt"],
                "stage_index": self.training.state.get("stage_index"),
                "initialization": self.training.state.get("initialization"),
            },
        )

    def close(self):
        self.stop.set()
        self.thread.join(timeout=30)
        if self.thread.is_alive():
            raise RuntimeError("Simulation worker did not stop within 30 seconds")
