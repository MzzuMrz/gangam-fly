# Reference animation demo

Historical initial design, superseded by [demo-choreography.md](demo-choreography.md)
after the user rejected the fixed-root short exercise. The current demo uses the
full continuous Xsens capture with an upright moving root.

New feature; major under the global contract. No local AGENTS.md exists.
Use existing frontend-quality and web-security-baseline guidance.

## Design and boundaries

Add an experiment/DEMO view switch. The demo previews the existing DanceReference
on the actual Flybody meshes with its root fixed. This is prescribed kinematics,
not physical integration, neural control, learning, or a saved neural episode.
Provide looped playback, pause/resume, restart, seek, and speed selection.

Create a read-only /api/demo clip using an independent MjData on the same loaded
Flybody model. Do not change Experiment, its data, neural state or weights. Do not
call mj_step. Existing model geometry is reused; clip contains sampled geometric
transforms and is interpolated by the browser between samples. Label demo clearly
and hide live neural metrics while viewing the reference. Returning to the live
view restores current server state without sending a control command.

## Implementation plan

1. Test clip periodicity/finite transforms/root fixed, animated limbs and unchanged
   original environment state. Implement isolated clip builder and GET endpoint.
2. Add a DEMO section using the existing viewer, with explicit mode label and local
   playback controls. Test that entering/leaving cannot mutate training state.
3. Verify build, lint/typecheck, runtime regression tests, browser demo motion,
   pause/seek/restart/speed, mobile layout and accessibility. Independent review.

## Acceptance Criteria

- [AC-1] Preview visibly moves the real Flybody limbs using the existing reference, with bounded deterministic periodic samples and a fixed root.
- [AC-2] Entering, playing and leaving DEMO sends no mutation command, creates no episode, and preserves the live experiment and neural weights.
- [AC-3] DEMO is labeled as prescribed kinematics; reward, physics and neural-rate telemetry are not presented as demo measurements.
- [AC-4] Playback can pause, restart, seek and change speed; normal controls still operate after returning to the experiment.
