import { expect, test, type Page } from "@playwright/test";

const user = {
  id: "user-1",
  username: "tester",
  email: "tester@example.com",
  is_admin: false,
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

async function mockDashboardApis(page: Page, documents: typeof uploadedDocument[] = []) {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({ json: user });
  });

  await page.route("**/api/v1/documents/", async (route) => {
    await route.fulfill({
      json: {
        items: documents,
        total: documents.length,
        page: 1,
        pages: documents.length > 0 ? 1 : 0,
      },
    });
  });
}

test.describe("Frontend Snapshot Tests", () => {
  test("login page snapshot", async ({ page }) => {
    await page.goto("/login");
    await page.waitForSelector("#login-email");
    
    if (!process.env.CI) {
      await expect(page).toHaveScreenshot("login-page.png", {
        maxDiffPixelRatio: 0.1,
        threshold: 0.2,
      });
    } else {
      await expect(page.locator("#login-email")).toBeVisible();
    }
  });

  test("register page snapshot", async ({ page }) => {
    await page.goto("/register");
    await page.waitForSelector("#reg-username");
    
    if (!process.env.CI) {
      await expect(page).toHaveScreenshot("register-page.png", {
        maxDiffPixelRatio: 0.1,
        threshold: 0.2,
      });
    } else {
      await expect(page.locator("#reg-username")).toBeVisible();
    }
  });

  test("dashboard empty page snapshot", async ({ page }) => {
    // Set mock token
    await page.addInitScript(() => {
      localStorage.setItem("token", "access-token");
      localStorage.setItem("refresh_token", "refresh-token");
    });

    await mockDashboardApis(page, []);
    await page.goto("/dashboard");
    await page.waitForSelector("text=No documents yet");

    if (!process.env.CI) {
      await expect(page).toHaveScreenshot("dashboard-empty.png", {
        maxDiffPixelRatio: 0.1,
        threshold: 0.2,
      });
    } else {
      await expect(page.locator("text=No documents yet")).toBeVisible();
    }
  });

  test("dashboard with document page snapshot", async ({ page }) => {
    // Set mock token
    await page.addInitScript(() => {
      localStorage.setItem("token", "access-token");
      localStorage.setItem("refresh_token", "refresh-token");
    });

    await mockDashboardApis(page, [uploadedDocument]);
    await page.goto("/dashboard");
    await page.waitForSelector("text=notes.txt");

    if (!process.env.CI) {
      await expect(page).toHaveScreenshot("dashboard-with-doc.png", {
        maxDiffPixelRatio: 0.1,
        threshold: 0.2,
      });
    } else {
      await expect(page.locator("text=notes.txt")).toBeVisible();
    }
  });
});
