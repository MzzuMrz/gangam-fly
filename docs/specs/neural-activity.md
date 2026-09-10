# Live neural activity and DOOMFLY training audit

Major frontend feature; no local AGENTS.md. Apply frontend-quality and acceptance
coverage checks. Keep the running native experiment, weights, protocol and
checkpoint signatures untouched. Use the existing read-only /api/state payload;
no backend/dynamics edits or new HTTP handlers.

## Decisions

Show an explicit live neural panel using six real descending observer rates and
six VNC leg population means already exposed by the server. Display a bounded
four-simulated-second heatmap, numeric rates, total graph spike counter and mean
graph spikes/s computed from counter deltas over observed simulated intervals.
These are sampled rates, not a raster of all166,700 individual neurons, anatomical
coordinates, wing frequencies, or invented spikes. Missing sampled intervals stay
blank. Never synthesize activity while paused/offline, extrapolate polls, mix
sessions, or present live counters as recorded replay. VNC means are the existing
80 ms filtered motor-rate aggregates. Group color saturates at100 Hz and numeric
values preserve larger rates. Keep200 samples max. Reset on episode/replay boundary.

DEMO hides this panel; returning clears its display history rather than attributing
animation motion to MaleCNS. A client-only pause freezes just this chart. Accessible
numeric rate table accompanies the canvas, and mobile content fits the viewport.

Research current DOOMFLY docs, source and saved outcomes without changing vendor.
Document actual training interventions, control arms, failed hypotheses and
measured wall/neural time. No unverified faster-learning claim; do not switch our
plasticity rule based solely on a different task's protocol.

## Plan

1. RED unit tests for bounded sampled activity, counter resets, no duplicate
   paused ticks and replay/offline handling. Implement `web/src/neural-activity.js`.
2. RED browser tests for actual rate updates, chart pixels, accessible table,
   pause/reset/DEMO boundaries. Wire main.js/styles; build and verify against live
   server while preserving its session. Reviewer checks numerical honesty and UI.
3. Write `docs/research/doomfly-training.md` with source attribution and actionable
   comparisons. Inspect scientific claims against saved results. Capture real UI
   and summarize verified feature and research limitations.

## Acceptance Criteria

- [AC-1] Displayed rates/counter-derived activity match existing native telemetry; no fabricated individual events or anatomy.
- [AC-2] History is bounded and simulation-time based; duplicate polls, pause, episode changes, offline and replay cannot fabricate continuity.
- [AC-3] The front exposes legible rate history and numeric alternatives on desktop/mobile; DEMO stays separate.
- [AC-4] Running training/session/checkpoint remain intact; all controls are local visualization controls.
- [AC-5] DOOMFLY findings distinguish measured throughput, synaptic updates and demonstrated learning, with direct reproducible sources.
