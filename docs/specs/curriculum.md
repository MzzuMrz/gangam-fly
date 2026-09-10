# Staged connectome learning

Major feature: replace all-at-once browser learning with prerequisites. No local
AGENTS.md contract exists. Keep native MaleCNS, graph topology, plasticity rule,
motor decoding and unchanged physical Flybody. No policy, teleportation, support
forces, target control commands or prescribed live poses are introduced.

## Decisions

- Ordered stages: stand up (4 s), sustain upright balance (8 s), first 2/4/8 s of
  captured movement, then the entire capture. Prefixes are seconds, not claimed
  beat-aligned labels. Motion stages include a one-second standing pause after
  the 2.5 s introduction to recheck the prerequisite before movement.
- Stand/balance reward measures head-up anatomical local +X alignment, thorax
  height, root speed and angular speed, and real positively loaded floor/tarsal
  contacts. No prescribed leg configuration is required. Success demands every
  sample of the final 1 s (stand) / 3 s (balance) meet explicit thresholds: tilt
  <=0.35 rad, height error <=0.03 cm, speed <=0.2 cm/s, angular speed <=2 rad/s,
  tarsal floor load >=50% of body weight and non-foot floor load <=5%. This is an engineering task, not
  validated biological standing. Physical attainability is not assumed.
- Motion stages retain captured pose tracking criteria and must also pass the
  one-second upright prerequisite window. Full capture includes its final return
  to rest; no upright requirement is imposed on that intentional ending.
- Two reserved, frozen seeds must pass the current stage. Baseline already passing
  both seeds can establish a pre-existing skill; do not call that newly learned.
  Otherwise repeat five learning trials / two frozen trials without an attempt
  limit. Promotion preserves weights and atomically resets only stage-local
  baseline, evaluations, best score and attempt counters. Earlier stage results
  remain separate and visible. Seed residues namespace stages without collisions.
- New checkpoint namespace `_training_curriculum`; retain old `_training` and
  all episodes. On first creation, explicitly carry the old final weights after
  graph/mapping/body/kernel/brain+plasticity source/bounds validation and record the source checkpoint
  hash in both session and episode configuration. Never reinterpret old rewards or completion flags under the new task.
- Frontend shows current stage, locked next stages, physical pass criteria,
  instantaneous versus running-mean reward and stage-local frozen comparisons.
  DEMO stays separate. Training target stage/hash and all new metrics are saved;
  exact verification reconstructs the recorded objective.

## Plan

1. Add tests then pure stage targets/objectives in `gangnamfly/curriculum.py` and
   actual loaded-foot contact measurement in `environment.py`. Test sustained
   windows, airborne/lying poses, short trials, target coverage and no live mutation.
2. Extend `training.py` with optional ordered stages, validated stage state and
   atomic promotion. Test failures stay locked, two successes advance once,
   repeated baseline semantics, preserved weights, seeds and recovery.
3. Wire `runtime.py`, `experiment.py`, `verify.py` and provenance. Stop/save the
   previous run before restarting; validate explicit weight transfer. Test full
   native short-loop execution and independent deterministic verification.
4. Update frontend and docs; browser stage/criteria/reward separation tests,
   native contact/standing observations, lint/typecheck/build and independent
   read-only review. Resume the user's continuous session on stage one.

## Acceptance Criteria

- [AC-1] Training begins with physical stand-up trials and never requires full dance poses to earn stand-up reward.
- [AC-2] Later stages remain locked until two complete frozen trials pass sustained physical criteria; weights persist across atomic promotions.
- [AC-3] Standing requires real foot support, height/orientation and stability throughout the prescribed final window; airborne, fallen and short episodes cannot pass.
- [AC-4] UI and saved episodes identify the current stage, criteria, meaningful reward averages and stage-specific evaluations; DEMO is distinct.
- [AC-5] Old checkpoints/episodes remain intact, transferred weights are validated, new sessions resume the correct stage and deterministic verification reconstructs it.


Review refinements: standing reward uses the final upright anatomical axis and height from the first tick; the initial 2.5 s source ramp is only a diagnostic motion reference, not a reward ramp or motor command. This avoids awarding a high initial score for remaining horizontal. Standing support requires tarsal floor normal load >=50% of total body weight and non-foot floor load <=5%, recorded independently at every tick. These are engineering thresholds, not established fly balance criteria.
