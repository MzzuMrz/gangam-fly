import { test } from "node:test";
import assert from "node:assert/strict";
import { ActivityHistory } from "../src/neural-activity.js";
const state = (t, total = 100) => ({
  status: "running",
  mode: "train",
  episode_id: "one",
  sim_time: t,
  evidence: { total_spikes: total },
  motor_rates: [{ name: "DNa02_L", rate: 50 }],
  vnc_rates: [{ name: "T1_L", rate: 12 }],
});

// AC-1, AC-2: rates are observations, counters are interval-averaged graph spikes.
test("native samples use simulation time and bounded counter differences", () => {
  const h = new ActivityHistory();
  h.update(state(0.02, 100));
  assert.equal(h.graphRate, null);
  h.update(state(0.04, 160));
  assert.ok(Math.abs(h.graphRate - 3000) < 1e-8);
  assert.equal(h.samples[1].rates[0], 50);
  h.update(state(0.04, 160));
  assert.equal(h.samples.length, 2);
  for (let i = 3; i < 600; i++) h.update(state(i * 0.02, i * 100));
  assert.ok(h.samples.length <= 200);
  assert.ok(h.samples.every((s) => s.time >= h.samples.at(-1).time - 4));
});

// AC-2, AC-4: local chart state cannot leak stale activity across episodes/replay.
test("new episodes, counter regression, offline and replay clear continuity", () => {
  const h = new ActivityHistory();
  h.update(state(0.02));
  h.update(state(0.04, 200));
  h.update({ ...state(0.02, 10), episode_id: "two" });
  assert.equal(h.samples.length, 1);
  assert.equal(h.graphRate, null);
  h.update({ ...state(0.04, 5), episode_id: "two" });
  assert.equal(h.graphRate, null);
  h.update({ ...state(0.06), mode: "replay", status: "replay" });
  assert.equal(h.samples.length, 0);
  h.update(state(0.08));
  h.update({ ...state(0.1), status: "offline" });
  assert.equal(h.samples.length, 0);
});

// AC-2: repeated paused/idle state cannot accumulate a fake raster.
test("paused polls freeze samples and invalid values are excluded", () => {
  const h = new ActivityHistory();
  h.update(state(0.02));
  const frozen = { ...state(0.02), status: "paused" };
  for (let i = 0; i < 50; i++) h.update(frozen);
  assert.equal(h.samples.length, 1);
  h.update({ ...state(0.04), motor_rates: [{ name: "DNa02_L", rate: NaN }] });
  assert.equal(h.samples.at(-1).rates[0], null);
});

// AC-1, AC-2: a saved episode ID is not a live neural sample on idle startup.
test("fresh idle is empty and finishing retains only observed samples", () => {
  const h = new ActivityHistory();
  h.update({
    ...state(0, 0),
    status: "idle",
    episode_id: null,
    evidence: { total_spikes: 0, last_episode_id: "saved" },
  });
  assert.equal(h.samples.length, 0);
  h.update(state(0.02, 100));
  h.update({
    ...state(0.04, 200),
    status: "idle",
    episode_id: null,
    evidence: { total_spikes: 200, last_episode_id: "one" },
  });
  assert.equal(h.samples.length, 1);
  assert.equal(h.total, 100);
});
