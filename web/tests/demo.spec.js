import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// AC: AC-1, AC-2, AC-3, AC-4 (docs/specs/demo-choreography.md). Real server and clip.
test("DEMO animates locally and preserves the experiment", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#modelMessage")).toContainText("arrastrá", {
    timeout: 80000,
  });
  const before = await (await page.request.get("/api/state")).json();
  const mutations = [];
  page.on("request", (request) => {
    if (request.method() === "POST") mutations.push(request.url());
  });
  await page
    .getByRole("button", { name: "DEMO", exact: true })
    .click({ timeout: 5000 });
  await expect(page.locator("#demoPause")).toBeEnabled();
  await expect(page.locator("#demoDescription")).toContainText(
    "Captura continua",
  );
  await expect(page.locator("#demoClock")).toContainText("36.07");
  await expect(page.locator("#liveTelemetry")).toBeHidden();
  await expect(page.locator("#liveControls")).toBeHidden();
  await page.locator("#demoPause").click();
  await expect(page.locator("#demoPause")).toHaveText("Reproducir");
  await page.locator("#demoRestart").click();
  await expect(page.locator("#demoClock")).toContainText("0.00");
  await expect(page.locator("#demoPhase")).toHaveText("Incorporación");
  const pose0 = await page.locator("#scene canvas").screenshot();
  await page.locator("#demoSeek").evaluate((input) => {
    input.value = input.max;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await expect(page.locator("#demoPhase")).toHaveText("Cierre");
  await expect(page.locator("#demoClock")).toHaveText("36.07 / 36.07 s");
  expect(pose0.equals(await page.locator("#scene canvas").screenshot())).toBe(
    true,
  );
  await page.locator("#demoSeek").evaluate((input) => {
    input.value = "6.00";
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await expect(page.locator("#demoClock")).toContainText("6.00");
  await expect(page.locator("#demoPhase")).toHaveText("Captura continua");
  const pose1 = await page.locator("#scene canvas").screenshot();
  expect(pose0.equals(pose1)).toBe(false);
  const pausedTime = await page.locator("#demoClock").textContent();
  await page.waitForTimeout(250);
  await expect(page.locator("#demoClock")).toHaveText(pausedTime);
  await page.locator("#demoSpeed").selectOption("0.5");
  await page.locator("#demoPause").click();
  await expect(page.locator("#demoClock")).not.toHaveText(pausedTime);
  await page.locator("#demoPause").click();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({
    path: "../docs/evidence/demo-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../docs/evidence/demo-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Experimento", exact: true }).click();
  await expect(page.locator("#liveTelemetry")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Observar", exact: true }),
  ).toBeEnabled();
  expect(mutations).toEqual([]);
  const after = await (await page.request.get("/api/state")).json();
  // With an active learner, time/weights may evolve independently of this read-only UI.
  if (["idle", "paused"].includes(before.status)) {
    expect(after).toEqual(before);
  } else {
    expect(after.training.session_id).toEqual(before.training.session_id);
    expect(after.training.completed_trials).toBeGreaterThanOrEqual(
      before.training.completed_trials,
    );
    expect(after.status).not.toBe("error");
  }
});
