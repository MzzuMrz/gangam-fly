# Microcurriculum evidence

## Tests and checks

- Python full suite: 45 passed (79.34 s). Added the missing-whole-episode regression afterward; all six micro-objective tests then passed. After the tail and physical-verifier regressions, all9 micro/verifier tests passed; total49 tests exercised successfully across those runs.
- Browser suite: 7 passed (54.4 s), including actual DEMO isolation/viewer/replay and synthetic 176-stage UI with distinct stage/standing labels.
- Ruff, mypy, format and frontend/Python builds pass. Existing Vite warning: Three.js bundle exceeds500 kB. Dependencies unchanged; dependency audits were not rerun.
- Acceptance criteria mapped to inspected assertions in `microcurriculum-dod.json`.

## Bounded physical experiment

Pre-review smoke `episodes/micro-proof/20260910T130933-5cad49ca`: latest validated curriculum weights,
seed64, first support microstage, plasticity enabled, 4 simulated seconds /200 control samples.

- Mean reward0.990654; stage fraction1.0 over the final0.2 s.
- Upright standing fraction0.0. Passing this support task does not mean standing.
- 5,965 eligible weights differ between start/end. The summary's12,525 changed
  edges is relative to the original connectome weights, including previous learning.
- Runtime36.43 wall seconds. This is a single measured episode, not a convergence estimate.

A successful training trial alone cannot promote the session; it requires two
reserved-seed frozen trials. High early reward is expected for an easy microtask
and is not comparable to old upright-standing rewards.

## Preservation

The previous session was stopped and saved at21 completed trials. The old
checkpoint hash is recorded in `pre-micro-checkpoint.json`. The new namespace
is `_training_micro`; transfer checks concrete plastic-edge ordering and the
previous graph/mapping/body/kernel/brain/plasticity identities. Prior episodes
and stage/reward histories remain untouched. Exact verification of previous
dynamics requires their source snapshot; physical trajectory replay remains available.


## Final review and live handoff

Independent read-only review findings about tail dilution and unverified physical
qualification were addressed with failing/passing regressions. No high/medium
issues remain in the bounded follow-up. The server now runs the microcurriculum
at `http://127.0.0.1:8765`; an actual browser click began its frozen baseline.
`microcurriculum-live.png` records the real viewer and compact stage panel.
Old checkpoint bytes stayed identical and new initial weights matched exactly
before starting. Idle sleep prevention is tied to server PID73787.

No git repository exists, so no commit/PR/Copilot review/merge was performed.

Enhanced native verification PASSED for live episode `20260910T131518-58ce971e`:200 ticks, exact physical state, controls, motor spikes, reward, weights, every objective metric and recomputed summary. See `microcurriculum-verification.json`. This frozen baseline qualified only the first foot-support microstage, with0% upright-standing samples.
