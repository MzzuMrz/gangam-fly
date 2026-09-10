# FlyBike milestone 1

Inspection completed before implementation, 2026-09-09. Major task; no existing
local AGENTS.md or verification suite. Superpowers unavailable in this session.

## Reuse
- DOOMFLY 71ecf53d78eaffaf1a57ed7b0ccf5d458abc9f33: `doom.connectome`
  verified Feather importer, `doom.prepare` all-edge CSR and inferred retina,
  `doom.build_kernel`, `doom.native.NativeBrain` state and `neural_advance` ABI.
- DOOMFLY `doom.game.retinal_samples`: extract the MIT-licensed pure function
  with attribution to avoid importing ViZDoom. No learning modules imported.
- Fly64 f2f4114e53eaa326e54129f27a5383f93c6957af: inspected as reference only;
  its 20 ms normalized CSC model is different from DOOMFLY's 0.1 ms LIF.
- Full tracked DOOMFLY inventory: docs/evidence/doomfly-file-inventory.txt.
  `doom/` is runtime/import/kernel; `doom-ui/` browser spectator;
  `doom_learning*` seven learning generations (excluded); `tests/` numerical
  and game checks; `outputs/`, `docs/`, `research/`, `data-provenance/` evidence;
  `deploy/` containers; `licenses/` notices. No reusable MuJoCo world/UI.

## Mappings verified in official annotations
Motor IDs: DNg100 L=10045 R=10056 (drive); DNa02 L=523769 R=10360;
DNg13 L=11074 R=512006 (steering R-L). Both `type` and `flywireType` agree;
all six superclass=descending_neuron. These bicycle assignments are engineering
hypotheses, not established natural functions. DOOMFLY's default BCI instead
uses DNp20/DNpe017. Use our explicit configurable decoder, not that game decoder.

ProvisionalMechanosensoryAdapter: roll -> cb_sensory/mechanosensory/wind_gravity;
body angular roll velocity -> sensory_ascending/mechanosensory_proprioceptive/
haltere; signed forward velocity -> sensory_ascending/mechanosensory_proprioceptive/
chordotonal organ. Split by rootSide L/R. Channel signs, tonic input, current
units and gains are artificial. Resolve every ID and save mappings.json; no
unannotated neuron or DN stimulation. Replacement requires only encode(state).

## New components and assumptions
Separate MaleCNSAdapter, SensoryAdapter, MotorAdapter, BicycleEnvironment.
Free-root bicycle with cylinder wheels, steering hinge, rear torque, gravity and
contacts; slight seeded initial lean, no balance aid. Fixed 100 Hz physics,
50 Hz brain callbacks integrating 200 native 0.1 ms ticks, 60 Hz rendering,
optional 10 Hz agent RGB. Slow wall execution never drops physics/brain ticks.
GLFW main-thread rendering supports ordinary Python on macOS; independent
spectator orbit camera and fixed onboard camera; readable MuJoCo HUD.
Automatic chunked disk logging plus telemetry.npz, seeds/config/asset and kernel
hashes, per-step full MuJoCo state and sparse sensory/motor observations.
Optional full spike-count recordings. Visual replay and deterministic rerun
checks are separate. No learning, rewards or external neural policy.

## Risks
Native private ABI pinned to exact revision; tests must exercise injected
currents, delayed propagation and deterministic output. Dataset ~1.1 GB raw,
preparation peak must be measured sequentially. Unknown circuit behavior may
mean zero DN output; do not tune against falling. Physics is an artificial
bicycle, not validated bicycle dynamics. Retina is an inferred LIF proxy.
Viewer timing may be slower than real time; report measured rates.

## Implementation sequence and verification
1. Prepare pinned graph/kernel, hash datasets, save exact mapping inventory;
   test IDs, signs, graph dimensions and sensory-only drive injection.
2. Build physical bicycle and deterministic adapters/scheduler; test free fall,
   ground contact, actuator response, no state-to-motor bypass, fixed tick ratios.
3. Add automatic bounded logging/replay and main-thread viewer/HUD; test saved
   arrays, cleanup on interruption and exact headless episode reproduction.
4. Connect optional extracted retinal sampler; test pixel sensitivity and camera
   independence. Run full MaleCNS headless and visible episodes, measure RSS and
   wall frequencies; independent review, lint/typecheck/build/security audit.
