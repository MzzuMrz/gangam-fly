# Fine-grained physical curriculum

Major: changes objectives, checkpoint protocol and evidence presentation. No local AGENTS.md. Keep anatomy, neural kernel, motor decoder, plasticity and native physics unchanged. No reset to target poses or balancing forces. User authorized continuation and weight preservation.

## Decisions

Use many physically measurable steps rather than one-tick/artificial success. Ordered support fractions in 10% increments; progressively unload non-foot floor contact; floor-relative height in five small increments (5% of the floor-to-upright height gap per increment); head-up elevation in 5-degree increments; progressively tighten speed bounds; extend continuous holds to 3 s; then extend captured movement in 0.25 s increments through the available 31.07 s capture. Every step retains previous constraints. Motion quality counts only motion samples, never the preamble. Fractional endpoints include the next 20 ms sample with the source endpoint clamped. All movement steps recheck a 3 s upright prerequisite, with an explicit inserted hold in the reference. Height uses the actual floor plane, not zero world height. Dense per-constraint deficit rewards remain nonzero near failing states; physical qualification remains strict and separate from reward. Early support progress must never be labeled upright standing.

Two frozen reserved-seed trials qualify each stage; existing abilities can qualify at baseline. Preserve latest weights from `_training_curriculum/checkpoint.npz` into new `_training_micro/checkpoint.npz`, validating graph, mapping, edge selection, body, kernel and bounds; record source hash in every trial. Never reinterpret old rewards/stage certificates. Namespace seed scheme and stage definitions are signature-bound. Existing curricula remain inspectable via their saved sources. No convergence/physical feasibility claim.

## Plan

1. Add failing tests for dense rewards, incremental constraints, sustained pass windows, distinction between support/standing, and captured timing. Implement `microcurriculum.py` without changing the old objective implementation.
2. Wire runtime, provenance, verifier and validated warm import. Add checkpoint migration and native smoke coverage. Stop/save active old session before switching code.
3. Adapt UI to many stages: show current/next steps, expandable complete list, stage success vs actual standing. Browser tests, deterministic verification, lint/typecheck/build and independent review.
4. Restore exact latest weights, resume continuous microtraining, save measured evidence. No user approval needed for reversible local steps.

## Acceptance Criteria

- [AC-1] First objective rewards incremental loaded-foot support without requiring upright posture; small physical improvements improve its reward.
- [AC-2] Stages progress monotonically through support, height, angle, stability, hold and capture length; no skipped stage or incomplete frozen episode can promote.
- [AC-3] Stage pass and upright standing are distinct in logs/UI; all criteria require complete sustained windows and loaded contact.
- [AC-4] Old session remains intact; exact compatible latest weights transfer with per-episode provenance, and new checkpoints resume their stage.
- [AC-5] Long stage lists remain usable; actual native episodes and exact verification demonstrate the new objective without supplying motor commands.


## Implemented schedule

176 total: 8 foot-load thresholds, 5 non-foot unloading thresholds, 5 height steps,
14 thorax-elevation thresholds (5–70 degrees), 1 final height band, 4 speed/angular
limits, 14 holds (0.4–3 s, after initial0.2 s), 124 quarter-second motion prefixes,
and the exact31.07 s capture endpoint. Stages remain engineering hypotheses.
Certificates refer to all recorded20 ms control samples, not unobserved0.1 ms
physics substeps. A complete episode timeline is required in addition to the
qualifying final window.


Review fixes: the full stage has a separate >=90% complete return-to-rest tracking
window; a good preamble or main dance cannot conceal a failed tail. Exact reruns
compare every recorded objective metric and recompute physical qualification
against the stored summary before producing a verification certificate.
