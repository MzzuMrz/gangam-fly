# Curriculum implementation evidence

The live learner now uses ordered stand/balance/2 s/4 s/8 s/full-capture objectives. No motor decoder, neural kernel, graph topology or plasticity rule changed. No pose, support force or external policy drives the live body.

## Verification

- Initial full Python suite: 36 passed. New reward/motor causality test subsequently passed with the existing native causality test (2 passed). Two additional checkpoint identity/certificate regressions passed with session/runtime suite (18 passed). There are now 39 Python tests, all exercised successfully across these runs.
- Browser suite: 6 passed, including DEMO isolation, actual anatomical viewer, replay, evidence and synthetic stage progression. The curriculum UI test was rerun after adding completed-stage means and passed.
- Ruff lint/format, mypy and frontend production build pass. Vite retains the existing >500 kB Three.js bundle warning.
- Independent native 4 s training smoke: `episodes/curriculum-proof/20260910T124141-bfd0a0d7`, 200 control ticks, 6,345 changed weights, mean reward 0.00206923, standing fraction 0, physical success false. It uses original weights, not the overnight warm start.
- `python -m gangnamfly.verify episodes/curriculum-proof/20260910T124141-bfd0a0d7` passed exact qpos/qvel/ctrl/motor spikes/reward/final-weight comparison for all 200 ticks.
- Measured training time: 24.28 wall seconds for 4 simulated seconds; peak process RSS ~1.49 GB. This is a local single-episode measurement, not a convergence estimate.
- Acceptance coverage: `curriculum-dod.json`. Independent read-only review checked physical support and checkpoint/provenance boundaries; findings were addressed with regression tests.

## Interpretation

This verifies execution and reproducibility of staged learning, not learned standing or dancing. Early stand reward is expected to be much lower than full-dance reward because it evaluates a different objective. Compare frozen measurements within the same stage. The retargeted capture and the plasticity rule remain unvalidated for physical attainability/convergence.

The old `_training` checkpoint and its reward history are preserved. Warm start requires identical graph, mapping, body, kernel and brain/plasticity source hashes, plus valid weight shape/sign/bounds. Each new trial embeds the original checkpoint SHA256; new session signatures also bind the ordered plastic-edge index array.

## Live handoff

The server on `http://127.0.0.1:8765` was restarted with the curriculum. A real browser click started stage 1; `curriculum-live.png` and `curriculum-live-state.json` record the observed baseline. Old checkpoint bytes are unchanged and imported weights matched exactly before starting. Live episode configuration contains the verified warm-start hash. The session remains running; an idle-sleep assertion is tied to server PID 70933. The independent reviewer reported no remaining high/medium findings after the four persistence/provenance fixes. Python source/wheel build also passed.

No git repository is present, so no commit, PR, Copilot review or merge was performed. Dependency versions were unchanged; prior dependency audit results were not rerun for this feature.
