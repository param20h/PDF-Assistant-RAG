import { expect, test, type Page } from "@playwright/test";

const user = {
  id: "user-1",
  username: "tester",
  email: "tester@example.com",
  is_admin: false,
  created_at: "2026-05-28T00:00:00Z",
};

const readyDoc = {
  id: "doc-1",
  original_name: "notes.txt",
  file_size: 11,
  page_count: 1,
  chunk_count: 1,
  status: "ready",
  error_message: null,
  uploaded_at: "2026-05-28T00:00:00Z",
  summary: "Test summary",
};

async function mockDashboard(page: Page, documents: typeof readyDoc[] = [readyDoc]) {
  await page.addInitScript(() => {
    localStorage.setItem("token", "access-token");
    localStorage.setItem("refresh_token", "refresh-token");
  });

  await page.route(/\/api\/v1\//, async (route) => {
    const path = new URL(route.request().url()).pathname;

    if (path.endsWith("/auth/me")) {
      await route.fulfill({ json: user });
      return;
    }
    if (path.endsWith("/documents/") || path.endsWith("/documents")) {
      await route.fulfill({
        json: { items: documents, total: documents.length, page: 1, pages: 1 },
      });
      return;
    }
    if (path.includes("/chat/sessions")) {
      await route.fulfill({ json: [] });
      return;
    }

    await route.fulfill({ status: 200, json: {} });
  });
}

async function gotoDashboard(page: Page) {
  await mockDashboard(page);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.locator("#document-sidebar")).toBeAttached({ timeout: 15_000 });
}

test.describe("mobile sidebar drawer (390px)", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("hidden on load, hamburger opens drawer, backdrop/Escape/select close", async ({
    page,
  }) => {
    await gotoDashboard(page);

    const sidebar = page.locator("#document-sidebar");
    const openBtn = page.getByRole("button", { name: "Open document sidebar" });
    await expect(openBtn).toBeVisible();

    await expect(sidebar).toHaveClass(/-translate-x-full/);
    await expect(sidebar).not.toBeInViewport();

    await openBtn.click();
    await expect(sidebar).toHaveClass(/translate-x-0/);
    await expect(sidebar).toBeInViewport();
    await page.waitForTimeout(350);

    await page.locator("body > div.fixed.inset-0.z-\\[100\\]").click({
      position: { x: 350, y: 400 },
    });
    await expect(sidebar).toHaveClass(/-translate-x-full/);

    await openBtn.click();
    await page.keyboard.press("Escape");
    await expect(sidebar).toHaveClass(/-translate-x-full/);

    await openBtn.click();
    await page.getByRole("button", { name: /Select document notes\.txt/i }).click();
    await expect(sidebar).toHaveClass(/-translate-x-full/);
  });

  test("only one mobile menu button (dashboard hamburger, not Header sheet)", async ({
    page,
  }) => {
    await gotoDashboard(page);
    await expect(page.getByRole("button", { name: "Open document sidebar" })).toHaveCount(1);
    await expect(page.getByRole("button", { name: "Open document navigation" })).toHaveCount(0);
  });
});

test.describe("desktop sidebar (≥768px)", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("sidebar visible, no mobile hamburger", async ({ page }) => {
    await gotoDashboard(page);

    const sidebar = page.locator("#document-sidebar");
    await expect(sidebar).toBeVisible();
    await expect(sidebar).toHaveClass(/md:static/);

    await expect(
      page.getByRole("button", { name: "Open document sidebar" })
    ).toBeHidden();

    const box = await sidebar.boundingBox();
    expect(box?.width).toBeGreaterThan(250);
  });
});
