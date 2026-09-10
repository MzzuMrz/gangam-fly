# GangnamFly

A working local experiment: **MaleCNS → fixed motor adapter → Flybody →
proprioception → MaleCNS**, with optional plasticity on existing connectome edges
and an anatomical 3D browser viewer. The bicycle design is superseded.

The connectome has not demonstrated learned Gangnam Style. The current prototype can run
observable attempts, update connectome weights, freeze those weights for
comparison, and replay physical trajectories. No external neural policy,
learned decoder, scripted pose execution or balance controller drives an experiment episode.

## Run on this machine

The environment, verified data, native kernel and frontend are already prepared.
From the project directory:

```sh
source .venv/bin/activate
python -m gangnamfly.main
```

Open **http://127.0.0.1:8765**. The server is local only. Each attempt lasts four
simulation seconds by default, and can take around 30 seconds of wall time.
`Observar` freezes current weights; `Entrenar` enables plasticity and seeded
sensory exploration; `Pausar` toggles execution; selecting an episode replays its
saved physical state. Starting a new attempt saves the interrupted attempt.
Use the mouse or arrow keys on the focused canvas to orbit, +/- to zoom.
Ctrl+C stops the backend and saves the episode.

The **DEMO** section stands Flybody upright and plays the complete **31.07-second
continuous Xsens Gangnam Style capture**, with 2.5-second stand-up and ending
transitions (36.07 seconds total). It uses the original anatomical meshes and
bounded joint positions: front legs act as arms, hind legs follow captured foot
placements, and middle legs follow a smaller arm gesture beside the abdomen.
Body translation and orientation follow the capture. This is an artistic
human-to-insect adaptation of the complete available take, not the entire song.

DEMO has looped playback, pause, restart, seek and speed controls. Its positions
are prescribed kinematics without physical integration or neural control;
it tests the animation, not balance, force production or learned dancing. Its
read-only clip uses separate MuJoCo data. Opening/closing DEMO sends no experiment
commands, changes no weights and creates no episode. A running experiment
continues in the background; pause it in Experimento first if desired.
The later curriculum stages score prefixes of this capture, after a standing
prerequisite. DEMO previews the complete capture independently. Playback uses elapsed browser time; a
background tab catches up on return. Pausing DEMO freezes its timeline.

The first load prepares the full clip before starting an episode. Existing
installations can fetch the additional ~10 MB source with
`python -m gangnamfly.prepare_demo`; full setup below includes that step.

The **Actividad neuronal** panel plots a four-simulated-second history of the six
published descending observer rates and six VNC leg population means, plus the
full-network spike counter and its measured interval rate. This is sampled rate
telemetry, not an individual spike raster or anatomical brain map. Missing
intervals remain blank. Chart pause/clear controls affect only the viewer; episode,
DEMO, offline and replay boundaries clear display continuity. A numeric table
provides an accessible alternative. It uses the existing read-only API and does
not restart or alter the learner. See the audited
[DOOMFLY training comparison](docs/research/doomfly-training.md).

The VNC panel reports neural firing rates, in spikes per simulated second (Hz),
averaged over the selected motor pools for each leg and smoothed with an 80 ms
time constant. These are not movement frequencies or forces. VNC means ventral
nerve cord. T1/T2/T3 label front/middle/hind legs; L/R label left/right.

```sh
python -m gangnamfly.main --seconds 8 --seed 64
python -m gangnamfly.main --idle                  # wait for a browser command
python -m gangnamfly.main --compare --seconds 2   # baseline/train/frozen pilot
python -m gangnamfly.controls --seconds 2         # constant/inverted controls, two pose seeds
python -m gangnamfly.main --headless --train --seconds 4
python -m gangnamfly.main --record-spikes         # optional full spike counts
python -m gangnamfly.verify episodes/<id>        # exact deterministic rerun
```

Entrenar now uses **176 microstages**. The first asks for >=10% of body weight
on tarsal floor contacts, with limited body contact/motion, for the final 0.2 s
of a 4 s trial. It does not require upright standing. The ordered steps increase
foot support to 80%, reduce non-foot load, raise the body above the actual floor,
increase thorax-axis elevation in 5-degree increments, tighten stability and
extend holds to 3 s. Captured movement then increases in 0.25 s prefixes through
the available 31.07 s take. The full stage includes a 3 s standing pause and lasts
39.08 simulated seconds at the control timestep.

Dense rewards use normalized physical deficits: partial improvements produce a
teaching signal, while stage qualification remains strict. All criteria are
checked at 20 ms control samples; this does not certify unobserved substeps.
Motion tracking is evaluated within the movement interval so a successful
preamble cannot conceal failure of a short gesture. The GUI shows stage success
separately from actual upright standing, plus current foot/body support loads.
The complete stage list is expandable.

Two reserved-seed frozen trials qualify every microstage. A baseline that already
passes counts as pre-existing skill. Otherwise five learning trials alternate
with two evaluations without an attempt limit. Weights survive promotion;
baselines, attempt counters and reward comparisons restart per stage. More stages
do not guarantee faster convergence; physical attainability and this plasticity
rule remain unvalidated. No target leg pose, supporting force or policy is supplied.

Pausing preserves the current neural state in memory. Detener saves the partial
episode and weights. `episodes/_training_micro/checkpoint.npz` restores compatible
weights and microstage progress; interrupted trials restart at an episode boundary.
On first creation, latest `_training_curriculum/checkpoint.npz` weights are imported
with graph/mapping/body/kernel, brain/plasticity source, ordered plastic-edge hash,
and sign/bounds checks. The older `_training` weights are a fallback only if no
curriculum checkpoint exists. The source SHA256 is embedded in every trial.
Neither previous session nor its rewards/certificates are overwritten. Incompatible
checkpoints are rejected visibly. Use `--episodes-dir episodes-new` to start
separately without deleting evidence.

Every attempt saves its initial and final plastic weights.
Visual replay does not overwrite the current trained weights. Do not run several
full-graph experiments at once on a 16 GB machine.

## Reproduce setup

Requires Python 3.11, Node 22.12+ and a C++17 compiler (`clang++` on macOS).
Uses CPU/native code; no CUDA, TensorFlow, PyTorch or cloud account is required.

```sh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements-dev.lock
uv pip install --python .venv/bin/python --no-deps -e .
source .venv/bin/activate
python -m gangnamfly.prepare
cd web
npm ci
npm run build
cd ..
python -m gangnamfly.main
```

Preparation checks out pinned public repositories, verifies the three MaleCNS
SHA-256 hashes against DOOMFLY's provenance lock, runs its sequential importer
and graph preparation, and compiles its original kernel. Downloads are roughly
1.1 GB for MaleCNS, plus Flybody; allow several GB of disk space. PyArrow is
23.0.1 rather than upstream 20.0.0, which the dependency audit flagged as
vulnerable. The prepared graph and exact rerun were verified after this update.

## Scientific boundaries

- **Connectivity:** 166,700 retained MaleCNS neurons, 25,582,938 directed edges,
  including weak and self edges. No dense adjacency matrix or circuit cropping.
- **Dynamics:** original DOOMFLY LIF approximation, 0.1 ms internal steps.
  Transmitter signs, gains, delays and spiking sensory proxies are modeled.
- **Body:** unchanged Flybody MJCF/meshes, 78 actuators, 109 generalized position
  coordinates. Native physics dt is 0.1 ms; units are cm, grams, seconds.
- **Motor mapping:** 30 existing joint actuators, five antagonist comparisons per
  leg. Real VNC muscle annotations identify the populations. Joint correspondence,
  sign, low-pass rate filter and gain remain provisional. Other actuators have
  static rest/zero commands; wings and adhesion are not learned. The body has a
  free root and can fall. DNg100/DNa02/DNg13 are logged observers only.
- **Input:** real chordotonal, haltere and auditory cells. Opponent tuning and
  currents are artificial. A 132 BPM rhythm cue goes into auditory sensory cells.
  There is no visual encoder in this milestone and no audio recording.
- **Learning:** 56,850 existing incoming edges to mapped VNC motor cells are
  eligible for reward-modulated, binned Hebbian updates. The baseline starts from the first teaching signal; constant reward cannot spuriously potentiate weights. Original signs and
  topology are preserved; weights stay within 0.5–1.5× baseline. This is a new,
  unvalidated plasticity hypothesis, not DOOMFLY's KC→MBON learning mechanism.
- **Target:** the authenticated Xsens 31.07-second continuous take, with 2.5 seconds
  standing up and 2.5 seconds returning to rest. It is an artistic, constrained
  retarget to the 30 controllable joints, not the entire song or proof of physical
  feasibility. DEMO previews the same target that the evaluator scores. Target
  poses never enter live qpos or motor decoding. The fixed decoder spans the real
  actuator limits. `gangnamfly.controls` retains the legacy motif for historical
  control experiments; browser training uses the curriculum and headless `--train`
  tests its first support microstage. DEMO has no extra curriculum standing pause.
- **Quality:** at least 90% of the complete sequence must simultaneously stay
  within 0.25 rad controlled-joint RMSE, 0.35 rad root orientation and 0.05 cm root
  position error in motion stages, plus the standing prerequisite window. Two
  reserved-seed frozen trials must pass each stage. A reward increase alone cannot
  stop training as successful. These engineering thresholds are not biological
  validation, and this plasticity rule has no convergence guarantee.

See [PLAN.md](PLAN.md), [exact neuron IDs and mapping](docs/evidence/mappings.json),
[measured pilot](docs/evidence/RESULTS.md), and [source attribution](THIRD_PARTY.md).

## Recording and verification

Each `episodes/<id>/` contains `config.json`, `mappings.json`, initial/final
plastic weight checkpoints, plastic edge indices, `summary.json` and
`telemetry.npz`. Recorded every neural tick: time, full qpos/qvel/activation/ctrl,
sensory currents, motor spikes/rates/voltages, DN spikes, commands, reward,
tracking error, spike totals, changed-edge counts, per-step actual update counts/L1,
learning-enabled flags, physical objective errors, anatomical tilt, height error,
foot/non-foot load fractions, stage success, deficit, floor-relative height,
standing success and kernel duration. Episode config
records the exact stage definition and target hash. Optional
`full_counts` records every neuron's spike count as uint16.

Chunks flush every 50 ticks and are atomically replaced. JSON summaries are atomic; empty/malformed episodes are excluded from replay and trajectory arrays are validated before replacing the live run. Normal completion,
interruption and shutdown finalize telemetry. After an OS kill/power failure,
completed chunks remain but the in-memory tail may be lost; this is not a
mid-episode neural-state resume checkpoint. Replay is physical playback;
`gangnamfly.verify` separately reexecutes brain and physics in temporary storage. It first validates every body XML/OBJ, dynamics source, kernel and runtime version. Legacy pilots lacking complete provenance are rejected. Episodes recorded with
older dynamics require their saved source snapshot and matching dependencies for
exact reexecution; visual trajectory replay remains available.

The Aprendizaje medido panel shows actual progress, frozen results, spike totals
and real edge IDs with weight deltas. Download evidence exports allowlisted
recordings, initial/final weights, mappings, source snapshots and a SHA-256
manifest. After an exact rerun, `verification.json` binds the result to those files;
editing them invalidates the UI verification status. This is reproducible local
evidence, not third-party attestation or evidence of successful choreography.
No video or results are published automatically. A measured short recording and
its independently verified episode are available in
[training-real.mp4](docs/evidence/training-real.mp4) and
[training-episode.zip](docs/evidence/training-episode.zip). Recreate a bounded
nine-trial technical recording with `python scripts/record_training_proof.py`
from the project root (requires Playwright Chromium).

```sh
python -m pytest tests -q
ruff check gangnamfly tests --exclude tests/archive
ruff format --check gangnamfly tests --exclude tests/archive
mypy gangnamfly
pip-audit
python -m build
cd web
npm run build
npm audit
npx playwright test   # backend must be idle/paused with a saved episode
```

Core code is under `gangnamfly/`; `web/` is vanilla Three.js + Vite. The server
owns simulation state in one worker. Browser rendering is independent, receiving
actual mesh poses. No physics/neural steps are skipped to catch up with the
wall clock. Benchmark results and limitations are recorded rather than hidden.
# gangam-fly
