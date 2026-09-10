# Continuous connectome training with reproducible evidence

Major extension requested while finishing the upright DEMO. Entrenar must keep
running attempts until paused/stopped or objective evaluation succeeds. The user
wants visible, shareable evidence distinguishing live learning from animation.
No external neural policy, PPO/SAC, hidden balance aid or prescribed live poses.

## Design

- Reuse the verified Xsens take as the training target. Retarget only joints that
  the existing MaleCNS motor interface can control; the DEMO and evaluator share
  the resulting versioned target. Target poses go exclusively into reward and
  evaluation, never into actuator commands or live qpos. Body starts from the
  ordinary physical reset. Extend the fixed rate-to-angle decoder to the actual
  actuator ranges so its old +/-0.65 rad envelope does not make the task
  unreachable by construction. Existing population identities stay unchanged.
- A continuous session runs an initial frozen baseline, training attempts with
  retained weights and reproducible varying seeds, and periodic frozen
  evaluations on reserved seeds. No maximum attempt count. Pausing retains
  in-process state; stopping saves; restarting can restore validated learned
  weights at an episode boundary, not pretend to restore unsaved neural state.
- Full attempts cover stand-up, complete capture and ending. Quality measures
  actual controlled-joint error, torso orientation/position and complete temporal
  coverage. Success requires strong performance in frozen evaluations on two
  reserved seeds plus improvement over baseline. Configurable numerical criteria
  are logged; reward increase or changed weights alone never means mastery.
- Show phase/attempt count, running duration, loss/reward curves, current/best
  frozen result, changed weights and real example edge deltas. Keep DEMO visibly
  labeled and independent. Produce a per-episode evidence bundle with provenance,
  telemetry, initial/final weights and a deterministic verification command.
- Record bounded per-step telemetry and append session history. Save checkpoints
  at trial boundaries and on stop. No deletion of previous evidence, cloud spend
  or automatic public posting. No promise that this plasticity rule converges.

## Implementation plan

1. Source/target worker: authenticate derived arrays, validate the full retargeted
   take, expose a compact cached target usable by DEMO and evaluator. Restrict IK
   to the existing controlled joints. Fix optional-DEMO startup failure isolation
   in the runtime (primary owns runtime). Preserve source attribution.
2. Primary: tests for the continuous state machine, frozen evaluation/genuine
   quality criteria, retained/checkpointed weights and target causality. Implement
   target scoring and continuous sessions, integrate serial runtime pause/stop.
3. Frontend: live training/evaluation labels, actual history/progress/edge updates,
   pause/stop and evidence download. Keep compact experimental presentation.
4. Verify real full-graph short rollover smoke plus deterministic episode rerun;
   test full target coverage/criteria separately without claiming the short smoke
   proves dancing. Browser real-state tests, provenance/tamper checks, lint/build,
   read-only review, evidence and documentation. Never mark an unsuccessful
   physical dance successful to satisfy a UI test.

## Acceptance Criteria

- [AC-1] One Entrenar command starts recurring attempts; weights carry over and pause/stop work without losing completed episodes or checkpoints.
- [AC-2] Live actuators receive only deterministic decoding of real MaleCNS spikes; the complete captured target is used only for scoring/evaluation.
- [AC-3] Success requires full-duration physical tracking and repeatable frozen evaluation on reserved seeds; changed weights or a short good pose cannot trigger success.
- [AC-4] UI displays measured training/evaluation progress and weight changes, clearly distinguishes DEMO, and provides reproducible evidence for a saved episode.
- [AC-5] Checkpoints/provenance are validated, failures remain visible, no unauthenticated arbitrary file access is added, and real-loop/replay tests pass.

## Verification outcome

Implemented and reviewed. 29 Python tests and five browser tests pass; targeted
UI checks passed again after the final overlay placement fix. A bounded visual
smoke ran two baselines, five learning trials and two frozen evaluations with the
full connectome. Its one-second trial duration is explicitly labeled and bound
to checkpoint provenance. A recorded training episode from that video matched
all 50 ticks in an independent exact rerun. See `docs/evidence/RESULTS.md` for
numbers, artifacts, retargeting limitations and acceptance-test mapping. Learned
full choreography remains unestablished; the normal button uses full 36.08-second
attempts with no count limit. No public posting or external deployment occurred.
