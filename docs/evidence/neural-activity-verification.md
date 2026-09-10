# Neural activity verification

Verified 2026-09-10 against the existing local server without restarting Python.

| Acceptance criterion | Evidence |
| --- | --- |
| AC-1: native rates and counter-derived activity | Four passing Node unit tests in `web/tests/neural-activity.unit.js`; browser telemetry fixture assertions; `neural-activity-live.png` captured from the native session |
| AC-2: bounded history and honest boundaries | Unit coverage of simulation time, duplicate polls, episode/counter resets, offline, replay and fresh idle; browser pause/reset checks |
| AC-3: desktop/mobile readability and DEMO separation | Two passing targeted Playwright tests in `web/tests/neural-activity.spec.js`, including 375 px DPR sizing and touch targets; `neural-activity-mobile.png` uses fixture telemetry; earlier read-only browser suite passed seven tests including viewer accessibility and DEMO isolation |
| AC-4: preserve training | `neural-activity-session.json` records active session `65c3c27ad43649ec` and unchanged Python source hashes against its episode snapshot; UI controls issue no POST requests |
| AC-5: reproducible research | `docs/research/doomfly-training.md` cites pinned source, distinct pilot artifacts, rule parameters and corrected throughput findings |

Final Node run: four tests passed. Targeted browser run after review fixes: two
tests passed. Vite production build passed, retaining the existing bundle-size
warning. Prettier check of `src` and `tests` passed after formatting the new test.
The read-only reviewer confirmed all three reported findings and touch-target
concerns resolved, with no remaining high/medium finding in the bounded follow-up.

The server-mutating replay selection browser test was deliberately excluded to
preserve the active training session. Replay display isolation is covered with
fixtures. Python tests were not rerun: no Python source, dependencies, neural
rule, checkpoint or physical model changed. No PR or Copilot review was performed;
the working root has no Git repository.

The panel exposes twelve sampled population channels and a whole-graph spike
counter. It does not expose an individual-neuron raster or demonstrate successful
learning. UI polling can miss rate bins; the chart leaves those intervals blank.
