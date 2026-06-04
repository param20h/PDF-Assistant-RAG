import { expect, test, type Page } from "@playwright/test";

const user = {
  id: "user-1",
  username: "tester",
  email: "tester@example.com",
  is_admin: false,
  created_at: "2026-05-28T00:00:00Z",
};

const existingDoc = {
  id: "doc-existing",
  original_name: "report.pdf",
  file_size: 1200,
  page_count: 1,
  chunk_count: 1,
  status: "ready",
  error_message: null,
  uploaded_at: "2026-05-28T00:00:00Z",
};

async function mockDashboard(page: Page, documents: typeof existingDoc[]) {
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({ json: user });
  });

  await page.route("**/api/v1/chat/sessions", async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.route("**/api/v1/documents/", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
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

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("token", "access-token");
    localStorage.setItem("refresh_token", "refresh-token");
  });
});

test("shows replace modal on duplicate upload (409)", async ({ page }) => {
  const documents = [{ ...existingDoc }];
  await mockDashboard(page, documents);

  await page.route("**/api/v1/documents/upload", async (route) => {
    await route.fulfill({
      status: 409,
      json: {
        detail: {
          conflict: true,
          existing_id: existingDoc.id,
          original_name: existingDoc.original_name,
        },
      },
    });
  });

  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

  await page.locator('input[type="file"]').setInputFiles({
    name: "report.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n"),
  });

  const dialog = page.getByRole("dialog", { name: "Replace existing document?" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText("report.pdf")).toBeVisible();
  expect(documents).toHaveLength(1);
});

test("replace confirm calls PUT replace and refreshes list", async ({ page }) => {
  const documents = [{ ...existingDoc }];
  let replaceCalled = false;

  await mockDashboard(page, documents);

  await page.route("**/api/v1/documents/upload", async (route) => {
    await route.fulfill({
      status: 409,
      json: {
        detail: {
          conflict: true,
          existing_id: existingDoc.id,
          original_name: existingDoc.original_name,
        },
      },
    });
  });

  await page.route(`**/api/v1/documents/${existingDoc.id}/replace`, async (route) => {
    replaceCalled = true;
    expect(route.request().method()).toBe("PUT");
    documents[0] = { ...existingDoc, status: "pending" };
    await route.fulfill({
      status: 202,
      json: { ...existingDoc, status: "pending" },
    });
  });

  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

  await page.locator('input[type="file"]').setInputFiles({
    name: "report.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n"),
  });

  const replaceResponse = page.waitForResponse(
    (res) =>
      res.request().method() === "PUT" &&
      res.url().includes(`/api/v1/documents/${existingDoc.id}/replace`)
  );
  await page
    .getByRole("dialog", { name: "Replace existing document?" })
    .getByRole("button", { name: "Replace" })
    .click();
  await replaceResponse;
  await expect(page.getByRole("dialog")).toBeHidden({ timeout: 10_000 });
  expect(replaceCalled).toBe(true);
});

test("replace shows error on 423 while processing", async ({ page }) => {
  await mockDashboard(page, [{ ...existingDoc }]);

  await page.route("**/api/v1/documents/upload", async (route) => {
    await route.fulfill({
      status: 409,
      json: {
        detail: {
          conflict: true,
          existing_id: existingDoc.id,
          original_name: existingDoc.original_name,
        },
      },
    });
  });

  await page.route(`**/api/v1/documents/${existingDoc.id}/replace`, async (route) => {
    await route.fulfill({
      status: 423,
      json: {
        detail: "This document is still being processed. Please wait before replacing it.",
      },
    });
  });

  await page.goto("/dashboard", { waitUntil: "domcontentloaded" });

  await page.locator('input[type="file"]').setInputFiles({
    name: "report.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n"),
  });

  await page
    .getByRole("dialog", { name: "Replace existing document?" })
    .getByRole("button", { name: "Replace" })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByText("This document is still being processed. Please wait before replacing it.")
  ).toBeVisible();
});
