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

async function assertNoHorizontalScroll(page) {
  const overflows = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(overflows).toBe(false);
}

test.beforeEach(async ({ page }) => {
  const now = Date.now();
  const iso = (offset) => new Date(now - offset).toISOString();
  // Mock /api so CI needs no database or internet (issue #40).
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/api/kp-1m")) {
      await route.fulfill({
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
      });
      return;
    }
    if (url.includes("/api/kp-gfz")) {
      await route.fulfill({
        json: pageBody([
          {
            time_tag: iso(3 * 3_600_000),
            kp: 5.33,
            a_running: 32,
            station_count: 8,
          },
        ]),
      });
      return;
    }
    await route.fulfill({ status: 404, body: "unmocked" });
  });
});

test("layout at 375, 768, and 1280 with no horizontal scroll at 320", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("5.20");
  await expect(page.getByRole("link", { name: "About" }).first()).toBeVisible();

  const day = page.getByRole("heading", { name: "One day" });
  const month = page.getByRole("heading", { name: "30 days" });
  const year = page.getByRole("heading", { name: "One year" });

  await page.setViewportSize({ width: 320, height: 700 });
  await assertNoHorizontalScroll(page);

  await page.setViewportSize({ width: 375, height: 812 });
  await assertNoHorizontalScroll(page);
  const dayPhone = await day.boundingBox();
  const monthPhone = await month.boundingBox();
  const yearPhone = await year.boundingBox();
  expect(dayPhone.y).toBeLessThan(monthPhone.y);
  expect(monthPhone.y).toBeGreaterThan(dayPhone.y + dayPhone.height - 1);
  expect(yearPhone.y).toBeGreaterThan(monthPhone.y + monthPhone.height - 1);

  await page.setViewportSize({ width: 768, height: 900 });
  await assertNoHorizontalScroll(page);
  const dayTablet = await day.boundingBox();
  const monthTablet = await month.boundingBox();
  const yearTablet = await year.boundingBox();
  expect(monthTablet.y).toBeGreaterThan(dayTablet.y + dayTablet.height - 1);
  expect(yearTablet.y).toBeGreaterThan(monthTablet.y + monthTablet.height - 1);

  await page.setViewportSize({ width: 1280, height: 900 });
  const dayWide = await day.boundingBox();
  const monthWide = await month.boundingBox();
  const yearWide = await year.boundingBox();
  expect(monthWide.x).toBeGreaterThan(dayWide.x + 100);
  expect(yearWide.x).toBeGreaterThan(monthWide.x + 100);
  expect(Math.abs(monthWide.y - dayWide.y)).toBeLessThan(24);
  expect(Math.abs(yearWide.y - dayWide.y)).toBeLessThan(24);
});

test("About markdown renders at mobile and desktop widths", async ({ page }) => {
  for (const width of [375, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/about/space-weather");
    await expect(page.getByRole("heading", { level: 1 })).toContainText("Space weather");
    await expect(page.getByText("docs/about/space-weather.md")).toBeVisible();
    await expect(page.getByRole("heading", { name: "1. Purpose" })).toBeVisible();
    await assertNoHorizontalScroll(page);
  }

  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/about/space-weather");
  await assertNoHorizontalScroll(page);
});

test("shows an empty ring when the API fails", async ({ page }) => {
  await page.route("**/api/**", (route) => route.fulfill({ status: 503, body: "nope" }));
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("did not return Kp");
  await expect(page.getByText("No stored values in this window.").first()).toBeVisible();
});
