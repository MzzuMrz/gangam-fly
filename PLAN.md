# GangnamFly implementation plan

Supersedes bicycle milestone at the operator's request. No bicycle model will be
implemented. Major: complete sensorimotor integration, experimental plasticity,
local server, frontend, persistent episodes. No local AGENTS.md exists.

## Inspected and reused
DOOMFLY `71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33`: verified official MaleCNS
importer and prepared CSR (166700 nodes, 25582938 edges), `NativeBrain` state and
exact `neural_advance` C ABI, native kernel build/hash validation. Internal dt
0.1 ms. Full inspection recorded in docs/evidence/doomfly-file-inventory.txt and
archived bicycle spec. Fly64 inspected for comparison only, not imported.
Flybody `d015e9bfe441bd90ae431bac24c55cb74bdbce26`: direct `floor.xml` includes
`fruitfly.xml` and anatomical OBJ meshes; Apache-2.0, unchanged. 109 qpos, 108
velocities, 78 actuators, 68 bodies, 160 geoms; timestep 0.0001 s, CGS units.
No TF/Ray/pretrained locomotion policy is needed or imported.

## Motor and sensory hypotheses
Resolve actual `vnc_motor`, subclasses fl/ml/hl, somaSide L/R, muscle type names.
Five fixed antagonist readouts per leg: coxa abduction (Pleural remotor/abductor
vs Sternal adductor), coxa twist (Sternal anterior vs posterior rotator), coxa
extension (Sternotrochanter vs Tergotr.), femur (Tr extensor vs Tr flexor), tibia
(Ti extensor vs Ti flexor). Anatomical labels exist; assignment to MJCF axis,
sign and gain remains provisional. Every exact ID saved in mappings.json.
DNa02/DNg13/DNg100 remain recorded observers, not direct joint controllers.
Proprioception enters real chordotonal sensory cells selected by entryNerve
ProCN/ProLN, MesoLN, MetaLN and rootSide. Split sorted IDs into opponent encoding
pools: declared artificial tuning. Haltere senses body angular velocity;
JO auditory cells receive a 132 BPM beat cue. Cue never enters motor decoder.

## Learning boundary
No trained motor policy/readout. Only existing connections onto mapped motor
neurons may change, with bounded sign-preserving reward-modulated Hebbian
eligibility at 20 ms observation boundaries. This is an experimental rule, not
DOOMFLY's KC/MBON learning mechanism and not validated biological plasticity.
Reference is a hand-authored fly-joint motif inspired by the horse-riding dance,
not motion-captured human Gangnam Style. Used by reward/evaluation in experiments
and by the separate, explicitly kinematic DEMO preview.
No target poses, phase or reward passed to motor decoder. No feedback balance policy. Unmapped actuators retain documented static rest/zero commands.
Reward-specific benefit requires constant/inverted teaching controls and frozen evaluation at both training and held-out pose seeds. Changed
weights do not establish learned dancing. Negative results remain visible.

## Components / sequence
1. Resolve/save mappings, bridge native brain with explicit sensory injection;
   test all-edge shape, native propagation, reset determinism, bounds and signs.
2. Load Flybody unchanged; adapter, reference and plasticity tests before code;
   smoke actual physics and full graph, measure memory and wall throughput.
3. Serial experiment worker + bounded commands, automatic episode NPZ/config/
   checkpoint; replay saved qpos and measured scores. Local loopback HTTP only,
   strict Host/Origin, finite allowlisted commands, no arbitrary filesystem API.
4. Web frontend (Three.js) renders actual compiled meshes and physical transforms;
   train/observe/pause/replay controls, honest live state, metrics and history,
   error/loading/disconnection states. Browser never advances fake physics.
5. Tests, deterministic rerun, visible browser smoke, lint/typecheck/build/audit;
   independent code/security review; record evidence and remaining limitations.

## Acceptance Criteria
- [AC-1] Real MaleCNS graph drives the unchanged articulated Flybody through fixed motor decoding, with proprioceptive feedback.
- [AC-2] Training updates only existing eligible graph weights, preserves topology/signs, and evaluation freezes learning.
- [AC-3] Reference motion is isolated from execution; reward reports actual physical tracking, not requested commands.
- [AC-4] Every episode records config, seed, physical state, sensory input, neural readouts, commands, reward and learned weight checkpoints; saved motion can be replayed.
- [AC-5] Local frontend shows anatomical fly geometry driven by server state, handles loading/errors, and controls training/observation/pause/replay.
- [AC-6] Deterministic checks, measured throughput/RSS and baseline-versus-training results are reported without claiming unverified dance mastery.

Review refinements: initialize the reward baseline from the first teaching signal. Constant reward must not change weights. Add 0.005-radian seeded initial joint perturbations. Hash all body XML/OBJ assets, dynamics code, kernel and versions. Validate replay arrays before interrupting a live run; empty or malformed history cannot stop the runtime.

## Interface correction

Operator requested an experiment console, not promotional presentation. Remove
slogans and the hero block; use a compact title, controls above the physical
viewer, telemetry beside it, and collapsible model notes. Keep runtime/control
behavior unchanged. Verify with the existing browser/accessibility tests and a
fresh desktop screenshot; no new tests are needed for this copy/layout edit.

## Reference preview

Implement the operator-requested DEMO view per docs/specs/demo-preview.md: actual
Flybody geometry, separate kinematic data, existing reference, read-only endpoint,
local playback controls, explicit labeling and no changes to running experiments.

The user rejected the short reference as unrecognizable. Supersede the initial
DEMO with docs/specs/demo-choreography.md: upright Flybody, full continuous Xsens
capture retargeted to real joints, stand-up/finish, unchanged neural experiment.

New user extension: continuous training and visible reproducible evidence per
docs/specs/continuous-training.md. Connect the corrected capture to evaluation,
repeat attempts with retained weights, validate frozen results and expose actual
measurements. DEMO remains isolated; no artificial motor policy is introduced.

## Staged learning

Implement docs/specs/curriculum.md: upright stand and balance prerequisites,
then growing motion prefixes and full capture. Physical sustained success gates,
stage-local frozen evaluation, atomic promotion and explicit preserved-weight
transfer replace the all-at-once training objective. Keep the overnight run as
comparison evidence; validate rather than claim improved learning.

Microcurriculum: see `docs/specs/microcurriculum.md`. Preserve current curriculum weights in a new namespace; TDD physical micro-objectives, wire replay/provenance, update large-stage UI, native deterministic smoke and review, then resume.

Live neural activity: `docs/specs/neural-activity.md`. Frontend-only visualization
of existing authentic telemetry, bounded timing-aware history, no session restart.
Parallel read-only DOOMFLY training audit; document control evidence and limitations.
# Observed brain/VNC activity map

Add an accessible SVG schematic to the existing live-neural panel. It maps only
the six published descending observers and six VNC leg-motor means, shares the
activity history's episode/replay/DEMO boundaries and labels the absent spatial
coordinates explicitly. See `docs/specs/brain-activity-map.md`.
