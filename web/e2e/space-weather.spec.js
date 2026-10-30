import { expect, test } from "@playwright/test";

function pageBody(rows) {
  return {
    processing_level: "real-time",
    time_from: "2026-10-26T00:00:00Z",
    time_to: "2026-10-27T00:00:00Z",
    limit: 2000,
    rows,
  };
}

test.beforeEach(async ({ page }) => {
  const now = Date.now();
  const iso = (offset) => new Date(now - offset).toISOString();
  await page.route("**/api/kp-1m**", (route) =>
    route.fulfill({
      json: pageBody([
        {
          time_tag: iso(60_000),
          kp_index: 5,
          estimated_kp: 5.2,
          kp: "5Z",
        },
        {
          time_tag: iso(3_600_000),
          kp_index: 2,
          estimated_kp: 2.4,
          kp: "2Z",
        },
      ]),
    }),
  );
  await page.route("**/api/kp-gfz**", (route) =>
    route.fulfill({
      json: pageBody([
        {
          time_tag: iso(3 * 3_600_000),
          kp: 5.33,
          a_running: 32,
          station_count: 8,
        },
      ]),
    }),
  );
});

test("stacks on a phone and sits in a row on a laptop", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("5.20");
  await expect(page.getByRole("button", { name: "Download CSV" })).toHaveCount(4);

  const day = page.getByRole("heading", { name: "One day" });
  const year = page.getByRole("heading", { name: "One year" });
  const dayBox = await day.boundingBox();
  const yearBox = await year.boundingBox();
  expect(yearBox.y).toBeGreaterThan(dayBox.y + dayBox.height);

  for (const width of [320, 390]) {
    await page.setViewportSize({ width, height: 700 });
    const overflows = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflows).toBe(false);
  }

  for (const width of [1280, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const dayWide = await day.boundingBox();
    const yearWide = await year.boundingBox();
    expect(yearWide.x).toBeGreaterThan(dayWide.x + 100);
    expect(Math.abs(yearWide.y - dayWide.y)).toBeLessThan(24);
  }
});

test("shows an empty ring when the API fails", async ({ page }) => {
  await page.route("**/api/kp-1m**", (route) =>
    route.fulfill({ status: 503, body: "nope" }),
  );
  await page.route("**/api/kp-gfz**", (route) =>
    route.fulfill({ status: 503, body: "nope" }),
  );
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("did not return Kp");
  await expect(page.getByText("No stored values in this window.").first()).toBeVisible();
});
