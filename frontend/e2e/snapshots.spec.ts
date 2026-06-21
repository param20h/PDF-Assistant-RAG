/**
 * Visual regression tests for the landing page and key UI surfaces.
 *
 * Snapshots are stored in e2e/snapshots.spec.ts-snapshots/ and committed
 * to the repository so CI can diff against them on every PR.
 *
 * To regenerate baselines (e.g. after an intentional UI change):
 *   npx playwright test snapshots.spec.ts --update-snapshots
 */
import { expect, test, type Page } from "@playwright/test";

// ── Shared fixtures ───────────────────────────────────────────────────────────

const user = {
  id: "user-1",
  username: "tester",
  email: "tester@example.com",
  is_verified: true,
  is_admin: false,
  role: "user",
  created_at: "2026-05-28T00:00:00Z",
};

const uploadedDocument = {
  id: "doc-1",
  original_name: "notes.txt",
  file_size: 11,
  page_count: 1,
  chunk_count: 1,
  status: "ready",
  error_message: null,
  uploaded_at: "2026-05-28T00:00:00Z",
};

async function mockAuthApis(page: Page) {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({ json: user });
  });
}

async function mockDashboardApis(
  page: Page,
  documents: typeof uploadedDocument[] = []
) {
  await mockAuthApis(page);
  await page.route("**/api/v1/documents/", async (route) => {
    await route.fulfill({
      json: {
        items: documents,
        total: documents.length,
        page: 1,
        pages: documents.length > 0 ? 1 : 0,
        total_pages: documents.length > 0 ? 1 : 0,
        limit: 20,
      },
    });
  });

  await page.route("**/api/v1/chat/sessions", async (route) => {
    await route.fulfill({ json: [] });
  });
}

/** Wait for network and CSS animations to settle before snapshotting. */
async function stabilise(page: Page) {
  await page.waitForLoadState("networkidle");
  // One rAF to let React finish any pending paint
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(r)));
}

// ── Landing page ──────────────────────────────────────────────────────────────

test.describe("Landing page visual regression", () => {
  test.beforeEach(async ({ page }) => {
    // Ensure unauthenticated state — no redirect to /dashboard
    await page.route("**/api/v1/auth/me", async (route) => {
      await route.fulfill({ status: 401, json: { detail: "Not authenticated" } });
    });
  });

  test("landing page — full page", async ({ page }) => {
    await page.goto("/");
    await stabilise(page);

    await expect(
      page.getByRole("heading", { name: /chat with your/i })
    ).toBeVisible();

    await expect(page).toHaveScreenshot("landing-full.png", {
      fullPage: true,
    });
  });

  test("landing page — hero section", async ({ page }) => {
    await page.goto("/");
    await stabilise(page);

    const hero = page.locator("section").first();
    await expect(hero).toHaveScreenshot("landing-hero.png");
  });

  test("landing page — feature cards grid", async ({ page }) => {
    await page.goto("/");
    await stabilise(page);

    // The feature cards grid is the last element inside the hero section
    const grid = page.locator("section .grid").first();
    await expect(grid).toHaveScreenshot("landing-feature-cards.png");
  });

  test("landing page — footer", async ({ page }) => {
    await page.goto("/");
    await stabilise(page);

    const footer = page.locator("footer");
    await expect(footer).toHaveScreenshot("landing-footer.png");
  });

  test("landing page — CTA buttons visible", async ({ page }) => {
    await page.goto("/");
    await stabilise(page);

    await expect(
      page.getByRole("link", { name: "Get Started Free" })
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "Sign In" })).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Developer API" })
    ).toBeVisible();
  });
});

// ── Auth pages ────────────────────────────────────────────────────────────────

test.describe("Auth pages visual regression", () => {
  test("login page — full page", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("#login-email");
    await stabilise(page);

    await expect(page).toHaveScreenshot("login-full.png", { fullPage: true });
  });

  test("login page — form", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("#login-email");
    await stabilise(page);

    const form = page.locator("form").first();
    await expect(form).toHaveScreenshot("login-form.png");
  });

  test("register page — full page", async ({ page }) => {
    await page.goto("/register");
    await page.waitForSelector("#reg-username");
    await stabilise(page);

    await expect(page).toHaveScreenshot("register-full.png", {
      fullPage: true,
    });
  });
});

// ── Dashboard ─────────────────────────────────────────────────────────────────

test.describe("Dashboard visual regression", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("token", "access-token");
      localStorage.setItem("refresh_token", "refresh-token");
    });
  });

  test("dashboard — empty state", async ({ page }) => {
    await mockDashboardApis(page, []);
    await page.goto("/dashboard");
    await page.waitForSelector("text=No documents yet");
    await stabilise(page);

    await expect(page).toHaveScreenshot("dashboard-empty.png", {
      fullPage: true,
    });
  });

  test("dashboard — with one document", async ({ page }) => {
    await mockDashboardApis(page, [uploadedDocument]);
    await page.goto("/dashboard");
    await page.waitForSelector("text=notes.txt");
    await stabilise(page);

    await expect(page).toHaveScreenshot("dashboard-with-doc.png", {
      fullPage: true,
    });
  });
});
