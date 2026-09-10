# Observed MaleCNS activity map

Major frontend feature. No repository-root `AGENTS.md` contract exists; the
vendored DOOMFLY contract does not apply because no vendor file is changed.
Apply the global major-change workflow and frontend-quality requirements. Keep
the active native training process, Python sources, neural dynamics, weights and
checkpoints untouched.

## Problem and scientific boundary

The frontend publishes real rates but a numeric heatmap does not show where the
observed populations belong in the brain/VNC loop. MaleCNS's normalized neuron
table supplies IDs and annotations but no soma, skeleton or neuropil coordinates.
The first map must therefore be an explicitly topological schematic, not a 3D
reconstruction or anatomical whole-brain activity image.

## Decisions

Render an accessible SVG inside the existing neural panel. Place the six actual
single-cell descending observers (DNg100, DNa02 and DNg13, left/right) in a brain
outline and the six existing leg-motor population means in left/right T1, T2 and
T3 VNC segments. Color only those twelve measured channels on a fixed 0–100 Hz
scale. Keep optic lobes and other unlabeled brain areas neutral and explicitly
mark them as lacking published channels. Preserve the last observed sample while
the chart is locally or server-paused, and clear on the same episode, replay,
offline and DEMO boundaries as the activity history.

The SVG must expose channel names and rates in text/ARIA, work at 360 px without
horizontal scrolling, use color plus labels/intensity values, reserve stable
space and avoid continuous animation. Reuse the existing read-only `/api/state`
payload; no API, backend or dependency changes.

## Plan

1. Add failing unit tests for exact channel mapping, invalid/missing rates and
   summaries with no inferred regional activity.
2. Implement a small pure snapshot mapper and an SVG presenter, then integrate it
   with `NeuralActivity` so both views share identical samples and boundaries.
3. Add a browser test for live color/rate changes, clear/DEMO behavior, mobile
   layout and accessible descriptions. Run focused tests, formatting, build and
   a read-only live-server check. Record verification evidence.

## Acceptance criteria

- [AC-1] The map uses only the twelve already-published rates and preserves their
  exact numeric values; no rate, neuron, coordinate or regional activation is
  inferred.
- [AC-2] DN observers and VNC T1/T2/T3 motor populations have stable, labeled
  topological positions and use the same explicit 0–100 Hz color scale.
- [AC-3] Missing, invalid, cleared, replay/offline and DEMO states cannot display
  stale or fabricated activation.
- [AC-4] The map is understandable without color, keyboard-safe, screen-reader
  described and legible at 360 px.
- [AC-5] Active training, Python source hashes, checkpoints and server state are
  unchanged by the read-only frontend addition.
