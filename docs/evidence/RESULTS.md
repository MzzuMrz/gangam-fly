# Measured results, 2026-09-09

## Superseded initial pilot, not demonstrated dancing

Historical implementation with a zero-initialized reward baseline (replaced after review; not evidence of learning). One seed (64), 2 seconds per episode, original graph followed by one plastic
attempt and a frozen-weight evaluation:

| Arm | Mean reward | Mean joint error (rad²) | Changed edges | Wall seconds |
| --- | ---: | ---: | ---: | ---: |
| Original frozen | 0.198957 | 0.096328 | 0 | 19.16 |
| Plastic + sensory exploration | 0.546051 | 0.094112 | 5987 | 17.08 |
| Frozen after training | 0.488160 | 0.086672 | 5987 | 13.65 |

The frozen score improved by 0.2892 and mean joint error decreased about 10%.
Much of the score difference reflects body orientation. This short same-seed
comparison is not held-out generalization, does not identify reward-specific
learning versus incidental perturbations, and is not evidence of recognizable
Gangnam Style. Future experiments need multiple seeds, shuffled-reward controls,
longer frozen evaluation and a better motion reference. Negative results must
remain visible.

Historical report: pilot-report.json; original CLI output: comparison.log.

## Performance and reproducibility

Native full-loop smoke: ~1.36 GB peak RSS. Pilot peak RSS: 1.28 GB.
End-to-end speed in the pilot: roughly 0.10–0.15× real time, ~5–7 brain callbacks
per wall second. Physics still integrates 200 original 0.1 ms steps for each
20 ms brain callback. No skipped physics, dropped edges or artificially enlarged
time steps. Loading and browser model serialization can have a different peak.

The original verifier exactly matched 100 frozen evaluation steps: qpos, qvel,
controls, motor spike counts, rewards and final plastic weights. See
`determinism.log`. This establishes local repeatability, not portability across
MuJoCo/compiler/hardware versions.

## Viewer and checks

- Real anatomical meshes visible in browser: frontend-idle.png and
  frontend-training.png. No uncaught browser JS errors in the smoke test.
- Training command advanced simulation; pause confirmed from backend state.
- Playwright desktop/mobile + replay checks passed. Axe found no violations in
  the tested page. No manual VoiceOver or physical-phone test was performed.
- Initial automated browser screenshot used software/headless rendering; its
  displayed FPS is not a hardware-GPU benchmark.
- Ten Python tests passed, including the full-connectome repeatability check.
- Ruff lint/format and mypy checks passed. Python wheel/sdist built.
- npm audit: no vulnerabilities. pip-audit: no known dependency vulnerabilities
  after PyArrow 20.0.0 → 23.0.1; the local GangnamFly package itself is not on PyPI.
- Frontend bundle ~142 KB gzip. Vite warns about >500 KB uncompressed Three.js
  chunk; no suppression was added.

## Acceptance evidence

AC-1: tests/test_environment.py, tests/test_integration.py and native smoke.
AC-2: tests/test_core.py, tests/test_integration.py and pilot checkpoints.
AC-3: tests/test_core.py reference scoring and the zero-readout causality check.
AC-4: tests/test_episode.py, saved pilot episodes and deterministic rerun.
AC-5: tests/test_server.py and web/tests/viewer.spec.js plus browser smoke.
AC-6: tests/test_integration.py, pilot-report.json and determinism.log.

## Reviewed rule: reward controls and held-out initial pose

The baseline now initializes from the first teaching signal. A seeded 0.005 rad
initial joint perturbation makes seed 65 a different initial physical state from
training seed 64. Eleven 2-second episodes were run, restoring original weights
before each training arm; frozen tests reuse only that arm's resulting weights.

| Frozen arm | Seed | Reward | Joint error rad² | Changed edges |
| --- | ---: | ---: | ---: | ---: |
| Original | 64 | 0.520807 | 0.089181 | 0 |
| Original | 65 | 0.446412 | 0.079868 | 0 |
| Target teaching | 64 | 0.515075 | 0.089748 | 5870 |
| Target teaching | 65 | 0.510856 | 0.090011 | 5870 |
| Constant teaching | 64 | 0.520807 | 0.089181 | 0 |
| Constant teaching | 65 | 0.446412 | 0.079868 | 0 |
| Inverted teaching | 64 | 0.450008 | 0.080681 | 5188 |
| Inverted teaching | 65 | 0.451338 | 0.081580 | 5188 |

Constant reward changes no weights and reproduces both original evaluations
exactly. Target teaching improves the held-out *composite* score but worsens
joint tracking error in both seeds. This supports neither a claim of learned
choreography nor reliable reward-specific motor learning. Uprightness and
sensitive physical dynamics materially affect the score. The experiment is
working; recognizable dancing remains unachieved.

Controlled process peak RSS: 1.02 GB. See controlled-report.json and
controlled.log. The v2 verifier checks body assets, dynamics source, kernel and
versions before loading/reexecuting and records its result in determinism-v2.log.

## Independent review

Read-only deep reviewer inspected causality, local-server boundaries, physical
model usage and persistence. Resolved findings: initial positive-reward bias;
missing control arms; undisclosed static servo boundary; incomplete body hashes;
verification output polluting episode history; malformed/empty replay crashing
the worker. Reviewer confirmed the persistence blocker resolved, with no
remaining concrete issue in that follow-up. Fixed rest/zero actuators are now
listed per episode; this is not a complete biological neuromuscular mapping.

## Historical initial DEMO verification (superseded)

The separate DEMO previews the authored reference on actual Flybody meshes.
Its 111 samples cover a 1.81818 s periodic clip, encoded once as 296,076 gzip
bytes. The root is fixed; only kinematics is evaluated on independent MuJoCo
data. Browser playback interpolates poses and never submits a mutation command.
It is not an episode, a physical feasibility test or evidence of learned dance.

- Eleven Python tests passed, including periodicity, moving limb geometry,
  finite positions, fixed root and unchanged original qpos/qvel/ctrl/activation/time.
- Three actual-server Playwright tests passed: demo, desktop/mobile viewer and
  replay. Demo checks different rendered poses when seeking, pause/resume,
  restart, speed selection, hidden live telemetry, no POST and exact server-state
  equality before/after viewing against an idle server.
- Axe desktop checks reported no violations. Mobile width 390 px had no
  horizontal overflow. Screenshots: demo-desktop.png and demo-mobile.png.
- An initial accessibility check caught insufficient contrast in new tabs;
  shared button styling fixed it before the passing run.
- Ruff/mypy/Prettier passed for active code. The initial broad format command
  also checked historical bicycle code, which has pre-existing formatting drift;
  the documented command excludes tests/archive and passed.
- Frontend build passed, ~143.5 KB gzip. The existing >500 KB uncompressed
  Three.js chunk warning remains. Headless screenshots show software-rendered
  FPS; they are not a hardware performance benchmark.
- Python wheel/sdist built successfully with the standard isolated build.
  An initial --no-isolation attempt lacked setuptools in the runtime virtualenv;
  the documented build command supplied it in an isolated build environment.
- Acceptance coverage for docs/specs/demo-preview.md: AC-1/AC-2 in
  tests/test_demo.py and web/tests/demo.spec.js; AC-3/AC-4 in the browser test.
  The definition-of-done coverage check passed. No local workflow contract exists.
- The independent read-only reviewer found no concrete blocker or missing
  acceptance evidence in kinematic isolation, local HTTP boundaries or playback.

The VNC panel now spells out ventral nerve cord and explains that its Hz values
are averaged, smoothed neural spikes per simulated second, not limb frequency or
force. T1/T2/T3 and L/R are labeled. The active paused episode at deployment was
saved with its checkpoint before the server restarted; that earlier server reset in-memory weights to baseline. Continuous training now
persists validated checkpoints; see the subsequent results below.

## Continuous captured-target training and visible evidence

The current browser target is the authenticated Xsens continuous 31.07-second
capture, plus 2.5-second stand-up and ending. DEMO and the physical evaluator
share exactly the same retargeted 30-joint poses. The decoder now spans actual
actuator limits and receives only MaleCNS spike counts. The target is used only
for scoring after physics integration. Earlier pilot scores above describe the
legacy motif/decoder and are not directly comparable to current runs.

Entrenar has no attempt limit. It runs two frozen baseline trials, five training
trials and two frozen evaluation trials, then repeats training/evaluation. Each
normal attempt covers 36.08 simulated seconds. Pause preserves neural state;
stop saves the partial episode and learned weights. Atomic protocol-bound
checkpoints and sequence-numbered, recoverable history preserve progress across
restarts. Incompatible protocols require a separate `--episodes-dir`, preserving
prior evidence.

A real full-graph smoke ran nine **one-second** episodes. Its frozen baseline
mean reward was 0.4971804834 and frozen post-training mean was 0.6516054464 on the
same two reserved pose seeds. 7,458 of 56,850 eligible existing weights differed
from the original graph after five learning trials. Frozen trials changed no
weights. These runs cover only 2.77% of the target; none passed the dance criterion.
A reward difference on this short prefix is not evidence of mastering the dance.
The recorded Python process peaked 1.45–1.60 GB RSS across the repeated recordings; this excludes the separate
browser processes. Native callbacks were approximately 6 per wall-clock second,
about 0.12x simulated real time during the visual smoke. Browser software rendering
and simultaneous verification are not an M4 GPU benchmark.

`continuous-smoke.json` contains actual trial scores and flags. The visual files
`training-live.png`, `training-results.png`, and `training-real.mp4` (also WebM) come from the
real local worker with explicit short-test labeling. `scripts/record_training_proof.py`
recreates this bounded recording; it requires the Playwright Chromium browser.
It does not change the normal unlimited/full-duration Entrenar behavior.

Episode `20260910T011138-d6978218` was independently reexecuted from its saved seed
and initial weights. All 50 ticks matched **exactly** for qpos/qvel/ctrl, motor
spikes, reward and final plastic weights. See `continuous-verification.log` and
`training-episode.zip`, which includes telemetry, mappings, weights, code snapshots,
file hashes, and the successful verification report. This is reproducible local
evidence, not a third-party attestation. No video/results were posted publicly.

The complete retarget was also measured (`retarget-report.json`): maximum limb
endpoint residual 0.0531 cm, RMS 0.00921 cm, maximum sampled endpoint penetration
0.0246 cm, and largest joint change 1.882 rad between adjacent 60 Hz samples.
These expose remaining IK/retargeting limitations; the kinematic preview is not a
validated physically feasible trajectory. Training success and recognizable
physical dancing have not been demonstrated. More iterations cannot guarantee
convergence of this experimental plasticity rule.

Verification of the current implementation:

- 29 Python tests passed, including nine real short trial rollovers, retained
  weights, frozen evaluations, pause/resume/stop, missing-reference isolation,
  malformed checkpoints, interrupted journal repair, symlink boundaries and
  authenticated capture tampering.
- Exact replay validation passed for the independent episode above.
- Ruff, mypy, Prettier, Python wheel/sdist and frontend build passed. The existing
  Three.js uncompressed chunk warning remains (~146 KB gzip application JS).
- npm audit found no vulnerabilities; pip-audit found no known dependency
  vulnerabilities, excluding the local unpublished GangnamFly package.
- Independent read-only review found checkpoint validation, write consistency,
  symlink, elapsed-time and protocol-signature issues. They were fixed with
  regression tests; bounded follow-up reported no remaining findings.
- An initial recording completed its nine trials but its final Playwright wait
  violated the CSP `unsafe-eval` restriction. Locator assertions fixed the
  recorder without weakening CSP. A browser isolation test also caught an
  independently copied episode changing history during its before/after window;
  the test is rerun against a stable idle server, not weakened.

Acceptance mapping for `docs/specs/continuous-training.md`: AC-1 is covered by
`test_training.py` and native `test_runtime.py`; AC-2 by `test_integration.py`,
`test_runtime.py` and `test_core.py`; AC-3 by `test_training.py` and native trial
quality flags; AC-4 by `test_evidence.py`, `web/tests/training.spec.js` (explicit
synthetic UI contract fixtures) and the actual browser recording; AC-5 by
checkpoint/server/evidence/runtime tests and exact rerun. All five criteria have
assertions; no repository-local business-workflow contract exists.

Final rerun: all 29 Python tests and all five Playwright tests passed, including
actual evidence ZIP download and the unchanged-state DEMO check on an idle
server. The latest visual recording repeats the same nine one-second trials
with a compact live spike/update overlay. Trial duration is also bound into the
checkpoint signature, so short-smoke baselines cannot resume as full-length
training sessions. No learning-success claim is made from those recordings.
