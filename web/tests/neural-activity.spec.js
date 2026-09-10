import { test, expect } from "@playwright/test";

// AC-1..AC-4: fixtures validate display math and local controls, not learned behavior.
test("neural activity plots authentic fields and isolates pause replay and demo", async ({
  page,
  request,
}) => {
  const fixture = await (await request.get("/api/state")).json();
  fixture.status = "running";
  fixture.mode = "train";
  fixture.episode_id = "activity-test";
  fixture.sim_time = 0.02;
  fixture.evidence = { ...fixture.evidence, total_spikes: 100 };
  fixture.motor_rates = [{ name: "DNa02_L", rate: 50 }];
  fixture.vnc_rates = [{ name: "T1_L", rate: 12 }];
  const writes = [];
  page.on("request", (r) => {
    if (r.method() === "POST") writes.push(r.url());
  });
  await page.route("**/api/state", (r) => r.fulfill({ json: fixture }));
  await page.goto("/");
  await expect(page.locator("#neuralSamples")).toHaveText("1");
  await page.locator("#neuralActivity details summary").click();
  await expect(page.locator("#neuralRates")).toContainText("50.0");
  await expect(page.locator('[data-channel="DNa02_L"]')).toHaveAttribute(
    "data-rate",
    "50.0",
  );
  await expect(page.locator('[data-channel="T1_L"]')).toHaveAttribute(
    "data-rate",
    "12.0",
  );
  await expect(page.locator("#brainMapSummary")).toContainText("DNa02_L");
  const activeFill = await page
    .locator('[data-channel="DNa02_L"] .brain-map-signal')
    .getAttribute("fill");
  expect(activeFill).not.toBe("#26312c");
  const before = await page.locator("#neuralCanvas").screenshot();
  fixture.sim_time = 0.04;
  fixture.evidence.total_spikes = 160;
  fixture.motor_rates[0].rate = 75;
  await expect(page.locator("#neuralSamples")).toHaveText("2");
  await expect(page.locator("#neuralGraphRate")).toHaveText("3.000");
  await expect(page.locator('[data-channel="DNa02_L"]')).toHaveAttribute(
    "data-rate",
    "75.0",
  );
  expect(before.equals(await page.locator("#neuralCanvas").screenshot())).toBe(
    false,
  );
  await page.locator("#neuralPause").click();
  fixture.sim_time = 0.06;
  fixture.evidence.total_spikes = 240;
  await page.waitForTimeout(300);
  await expect(page.locator("#neuralSamples")).toHaveText("2");
  await expect(page.locator("#neuralMessage")).toContainText(
    "entrenamiento continúa",
  );
  await page.locator("#neuralPause").click();
  await expect(page.locator("#neuralSamples")).toHaveText("1");
  await page.locator("#neuralClear").click();
  await expect(page.locator('[data-channel="DNa02_L"]')).toHaveAttribute(
    "data-rate",
    "unobserved",
  );
  fixture.mode = "replay";
  fixture.status = "replay";
  await expect(page.locator("#neuralStatus")).toContainText("REPLAY");
  await expect(page.locator("#neuralSamples")).toHaveText("0");
  await page.getByRole("button", { name: "DEMO", exact: true }).click();
  await expect(page.locator("#neuralActivity")).toBeHidden();
  expect(writes).toEqual([]);
});

// AC-3: mobile uses readable CSS-sized text, not a downscaled desktop bitmap.
test("neural panel is readable on mobile and pause messages reflect actual mode", async ({
  page,
  request,
}) => {
  const fixture = await (await request.get("/api/state")).json();
  fixture.status = "paused";
  fixture.mode = "observe";
  fixture.episode_id = "mobile-neural";
  fixture.sim_time = 0.02;
  fixture.evidence = { ...fixture.evidence, total_spikes: 100 };
  await page.route("**/api/state", (r) => r.fulfill({ json: fixture }));
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto("/");
  await expect(page.locator("#neuralSamples")).toHaveText("1");
  await expect(page.locator("#brainActivityMap")).toBeVisible();
  const mapBox = await page.locator("#brainActivityMap").boundingBox();
  expect(mapBox.width).toBeLessThanOrEqual(343);
  expect(mapBox.height).toBeGreaterThan(190);
  const sizes = await page.locator("#neuralCanvas").evaluate((c) => ({
    width: c.width,
    cssWidth: c.getBoundingClientRect().width,
    height: c.getBoundingClientRect().height,
    dpr: Math.min(3, devicePixelRatio),
  }));
  expect(Math.abs(sizes.width / sizes.dpr - sizes.cssWidth)).toBeLessThan(2);
  expect(sizes.height).toBeGreaterThanOrEqual(300);
  expect(
    (await page.locator("#neuralPause").boundingBox()).height,
  ).toBeGreaterThanOrEqual(44);
  await page.locator("#neuralPause").click();
  await expect(page.locator("#neuralMessage")).not.toContainText(
    "entrenamiento continúa",
  );
  await page
    .locator("#neuralActivity")
    .screenshot({ path: "../docs/evidence/neural-activity-mobile.png" });
});
