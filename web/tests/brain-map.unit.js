import { test } from "node:test";
import assert from "node:assert/strict";
import { brainActivitySnapshot, activityColor } from "../src/brain-map.js";

test("maps only published DN and VNC channels without changing their rates", () => {
  const snapshot = brainActivitySnapshot([
    "DN · DNg100_L",
    "DN · DNa02_R",
    "VNC · T2_L",
    "VNC · T3_R",
    "DN · invented_L",
  ], [25, 101.5, 12.25, 0, 99]);

  assert.deepEqual(
    snapshot.nodes.map(({ name, rate }) => ({ name, rate })),
    [
      { name: "DNg100_L", rate: 25 },
      { name: "DNa02_R", rate: 101.5 },
      { name: "T2_L", rate: 12.25 },
      { name: "T3_R", rate: 0 },
    ],
  );
  assert.equal(snapshot.active.length, 3);
  assert.equal(snapshot.active[0].name, "DNa02_R");
  assert.equal(snapshot.observed, 4);
});

test("missing and invalid values remain unobserved rather than inferred", () => {
  const snapshot = brainActivitySnapshot(
    ["DN · DNg13_L", "VNC · T1_R", "DN · DNa02_L"],
    [null, Number.NaN, -2],
  );
  assert.equal(snapshot.observed, 0);
  assert.equal(snapshot.active.length, 0);
  assert.match(snapshot.summary, /Sin actividad válida/);
});

test("color scale saturates visually at 100 Hz without clipping numeric rate", () => {
  assert.equal(activityColor(null), "#26312c");
  assert.equal(activityColor(0), activityColor(null));
  assert.equal(activityColor(100), activityColor(400));
  assert.notEqual(activityColor(25), activityColor(75));
});
