# Upright continuous dance demo

Major feature correction. The old fixed-root 1.8-second procedural exercise
does not meet the user's visual intent. No local AGENTS.md exists. The user
selected a continuous dance version instead of edited music-video shots.

## Source and boundaries

Use the full 31.07-second continuous Xsens Gangnam Style motion capture:
https://www.xsens.com/resources/news/motion-capture-files-for-psy-gangnam-style
https://www.xsens.com/hubfs/Downloads/Data/Gangnam%20Style.zip
Inspect the actual MVNX segments, frames, coordinate conventions and timestamps.
Pin source hash, retain attribution and keep downloaded assets outside tracked
source. This is the whole available capture, not the entire song or video.

Keep the original Flybody geometry/joint topology. Retarget captured human
positions/orientations into upright fly root motion and anatomical joint angles.
Use front legs as arms, hind legs as primary legs; explicitly author the middle
leg adaptation. Add stand-up and finish transitions. The demo remains prescribed
kinematics on independent MjData, not physical feasibility or learned control.
Do not change the neural reward/reference, weights, motor adapter or experiment.

## Plan

1. Inspect/download the source with pinned checksum; add a reproducible optional
   preparation helper and compact source data. Confirm complete time coverage.
2. Test stand-up/root motion, capture coverage, finite bounded articulated poses,
   ground placement and isolation. Implement bounded joint retargeting in
   gangnamfly/choreography.py and replace gangnamfly/demo.py's old short clip.
3. Update web/src/demo.js/main.js: suitable upright camera framing, full timeline,
   source/duration and phase labels. Keep pause/seek/speed and local-only playback.
4. Run Python/browser checks and inspect multiple actual rendered dance poses,
   including crossed front limbs and overhead gesture. Independent read-only
   review. Record any retargeting limitations rather than claiming exact human
   joint correspondence or successful neural learning.

## Acceptance Criteria

- [AC-1] DEMO shows the real Flybody standing upright and playing the entire continuous 31.07-second source capture, with a stand-up and ending transition.
- [AC-2] Root and limbs follow captured motion through articulated poses; the source timing, provenance and insect-specific adaptation are explicit.
- [AC-3] Demo building/playback does not modify experiment qpos/qvel/controls/neural state or send mutation commands.
- [AC-4] Playback, seeking and speed controls work across the complete timeline; framing and readable phase/source labels support visual inspection on desktop and mobile.

Validation: pytest, ruff, mypy, frontend build/Prettier, real-server Playwright,
image inspection, acceptance coverage check and reviewer. No PR/publication.
