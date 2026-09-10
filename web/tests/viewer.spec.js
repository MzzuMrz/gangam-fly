import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// AC: AC-5 -- actual server, real anatomy and UI controls; no mocked physics.
test("actual anatomical viewer, controls and accessible mobile layout", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(page.locator("#modelMessage")).toContainText("arrastrá", {
    timeout: 80000,
  });
  await expect(page.locator("#scene canvas")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Observar", exact: true }),
  ).toBeEnabled();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../docs/evidence/frontend-mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("replay selects a recorded episode and labels it", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".episode").first()).toBeVisible();
  await page.locator(".episode").first().click();
  await expect(page.locator("#modePill")).toHaveText("REPLAY");
  await expect(page.locator("#runMessage")).toContainText("Replay");
});
