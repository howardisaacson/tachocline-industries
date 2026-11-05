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
    if (url.includes("/api/v1/kp-interpretation")) {
      await route.fulfill({
        json: {
          computed_at: new Date().toISOString(),
          spans: [
            {
              span: "day",
              sentence:
                "Today's space weather is about average for the last 7 days. Mean Kp is 3.40.",
              category: "average",
            },
            {
              span: "month",
              sentence: "The last 30 days are about average for the previous year. Mean Kp is 2.50.",
              category: "average",
            },
            {
              span: "year",
              sentence: "The last 365 days are about average for years since 1932. Mean Kp is 2.80.",
              category: "average",
            },
            {
              span: "solar",
              sentence:
                "The last 11 years are about average for earlier 11-year stretches since 1932. Mean Kp is 2.70.",
              category: "average",
            },
          ],
        },
      });
      return;
    }
    if (url.includes("/api/v1/kp-1m")) {
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
    if (url.includes("/api/v1/satellite-perigee")) {
      const sats = [
        [25544, "ISS (ZARYA)", 414],
        [39084, "LANDSAT 8", 701],
        [49260, "LANDSAT 9", 702],
        [20580, "HST", 468],
        [28485, "SWIFT", 230],
      ];
      await route.fulfill({
        json: pageBody(
          sats.flatMap(([id, name, km]) => [
            {
              epoch: iso(2 * 86_400_000),
              norad_cat_id: id,
              object_name: name,
              object_id: "1998-067A",
              perigee_altitude_km: km + 1,
              apogee_altitude_km: km + 2,
            },
            {
              epoch: iso(86_400_000),
              norad_cat_id: id,
              object_name: name,
              object_id: "1998-067A",
              perigee_altitude_km: km,
              apogee_altitude_km: km + 1,
            },
          ]),
        ),
      });
      return;
    }
    if (url.includes("/api/v1/solar-rv")) {
      await route.fulfill({
        json: {
          processing_level: "solar-l2-rv",
          unit: "m/s",
          time_from: new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString(),
          time_to: new Date(now).toISOString(),
          limit: 5000,
          rows: [
            {
              time_tag: iso(2 * 24 * 60 * 60 * 1000),
              instrument: "neid",
              rv_m_s: -640.1,
              rv_error_m_s: 0.3,
              snr: 400,
              exptime_s: 55,
              archive_jd: 2461000.5,
              archive_time_scale: "BJD",
            },
            {
              time_tag: iso(2 * 24 * 60 * 60 * 1000 - 2 * 60 * 1000),
              instrument: "neid",
              rv_m_s: -641,
              rv_error_m_s: 0.3,
              snr: 400,
              exptime_s: 55,
              archive_jd: 2461000.5,
              archive_time_scale: "BJD",
            },
            {
              time_tag: iso(2 * 24 * 60 * 60 * 1000),
              instrument: "expres",
              rv_m_s: -650.2,
              rv_error_m_s: 0.2,
              snr: 360,
              exptime_s: 180,
              archive_jd: 2461000.5,
              archive_time_scale: "JD",
            },
          ],
        },
      });
      return;
    }
    if (url.includes("/api/v1/kp-gfz")) {
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
  await expect(page.getByRole("link", { name: "Satellite Tracking" }).first()).toBeVisible();
  await expect(page.locator(".logo-mark")).toHaveAttribute("src", "/brand/ti-logo.svg");
  const favicon = await page.evaluate(() => {
    const link = document.querySelector('link[rel="icon"][href="/favicon.ico"]');
    return link ? link.getAttribute("href") : null;
  });
  expect(favicon).toBe("/favicon.ico");

  const day = page.getByRole("heading", { name: "One day" });
  const month = page.getByRole("heading", { name: "30 days" });
  const year = page.getByRole("heading", { name: "One year" });

  await page.setViewportSize({ width: 320, height: 700 });
  await assertNoHorizontalScroll(page);

  await page.setViewportSize({ width: 375, height: 812 });
  await assertNoHorizontalScroll(page);
  await expect(page.getByText("about average for the last 7 days")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sun-as-a-star radial velocity" })).toBeVisible();
  await expect(
    page.getByRole("img", { name: /radial velocity in meters per second/ }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "How is this worked out?" }).first()).toBeVisible();
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
  await expect(page.getByText("about average for the last 7 days")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sun-as-a-star radial velocity" })).toBeVisible();
  await assertNoHorizontalScroll(page);
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
    await expect(page.getByRole("heading", { name: "License" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Trademark policy" })).toBeVisible();
    await assertNoHorizontalScroll(page);
  }

  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/about/space-weather");
  await expect(page.getByRole("heading", { name: "License" })).toBeVisible();
  await assertNoHorizontalScroll(page);
});

test("workflow page layout and Mermaid at 375, 768, 1280", async ({ page }) => {
  for (const width of [375, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/workflow");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "data science workflow",
    );
    await expect(page.locator('nav[aria-label="Primary"] a[href="/workflow"]')).toBeVisible();
    await expect(page.locator('a[href="/about/data-science-workflow"]').first()).toBeVisible();
    await expect(page.locator(".mermaid-wrap svg").first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("heading", { name: "February 2022 backtest" })).toBeVisible();
    await assertNoHorizontalScroll(page);
  }

  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/workflow");
  await assertNoHorizontalScroll(page);

  await page.goto("/about/data-science-workflow");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "How the science is done",
  );
});

test("links page lists data sources at 375, 768, 1280", async ({ page }) => {
  for (const width of [375, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/links");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "where TI's data comes from",
    );
    await expect(page.locator('nav[aria-label="Primary"] a[href="/links"]')).toBeVisible();
    await expect(page.getByRole("heading", { name: "Solar wind (NOAA SWPC)" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Credits and terms" })).toBeVisible();
    const plasma = page.getByRole("link", { name: "Real-time solar wind, 1-minute plasma" });
    const mag = page.getByRole("link", { name: "Real-time solar wind, 1-minute magnetic field" });
    await expect(plasma).toBeVisible();
    await expect(plasma).toHaveAttribute("href", "https://www.swpc.noaa.gov/products/solar-wind");
    await expect(mag).toHaveAttribute("href", "https://www.swpc.noaa.gov/products/solar-wind");
    await expect(page.locator('footer a[href="/links"]')).toBeVisible();
    await assertNoHorizontalScroll(page);
  }

  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/links");
  await assertNoHorizontalScroll(page);

  await page.goto("/about/data-links");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Links");
});

test("satellite tracking page at 320, 375, and 1280", async ({ page }) => {
  for (const width of [320, 375, 1280]) {
    await page.setViewportSize({ width, height: width === 320 ? 700 : 900 });
    await page.goto("/");
    await page.getByRole("link", { name: "Satellite Tracking" }).first().click();
    await expect(page).toHaveURL(/\/satellites$/);
    const title = page.getByRole("heading", { level: 1, name: "Satellite Tracking" });
    await expect(title).toBeVisible();
    const headerBox = await page.locator(".site-header").boundingBox();
    const titleBox = await title.boundingBox();
    expect(titleBox.y).toBeGreaterThan(headerBox.y + headerBox.height - 1);
    await expect(page.getByRole("img", { name: /Perigee altitude/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "Tracking ISS (ZARYA)" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Homepage SWIFT" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Tracking ISS (ZARYA)" })).toHaveAttribute(
      "href",
      "https://www.n2yo.com/satellite/?s=25544",
    );
    await expect(page.getByRole("link", { name: "Homepage HST" })).toHaveAttribute(
      "href",
      "https://science.nasa.gov/mission/hubble/",
    );
    await assertNoHorizontalScroll(page);
  }
});

test("shows an empty ring when the API fails", async ({ page }) => {
  await page.route("**/api/**", (route) => route.fulfill({ status: 503, body: "nope" }));
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("did not return Kp");
  await expect(page.getByText("No stored value on this lap.").first()).toBeVisible();
});

test("Change Data View toggles independently on mobile and desktop", async ({ page }) => {
  for (const width of [375, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const dayToggle = page.getByRole("button", { name: "Change Data View" }).first();
    const monthToggle = page.getByRole("button", { name: "Change Data View" }).nth(1);
    await expect(dayToggle).toHaveAttribute("aria-pressed", "false");
    await expect(monthToggle).toHaveAttribute("aria-pressed", "false");
    await dayToggle.click();
    await expect(dayToggle).toHaveAttribute("aria-pressed", "true");
    await expect(monthToggle).toHaveAttribute("aria-pressed", "false");
    await dayToggle.click();
    await expect(dayToggle).toHaveAttribute("aria-pressed", "false");
    await assertNoHorizontalScroll(page);
  }
});
