import { expect, test, type Page } from "@playwright/test";

const user = {
  id: "user-1",
  username: "tester",
  email: "tester@example.com",
  is_admin: false,
  created_at: "2026-05-28T00:00:00Z",
};

const tokenResponse = {
  access_token: "access-token",
  refresh_token: "refresh-token",
  token_type: "bearer",
  user,
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

test("logs in with email and password", async ({ page }) => {
  await mockDashboardApis(page);
  await page.route("**/api/v1/auth/login", async (route) => {
    const body = route.request().postDataJSON() as { email: string };
    expect(body.email).toBe(user.email);
    await route.fulfill({ json: tokenResponse });
  });

  await page.goto("/login");
  await page.locator("#login-email").fill(user.email);
  await page.locator("#login-password").fill("password123");
  await page.getByRole("button", { name: "Sign In" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("No documents yet")).toBeVisible();
});

test("creates an account from the signup form", async ({ page }) => {
  await mockDashboardApis(page);
  await page.route("**/api/v1/auth/register", async (route) => {
    const body = route.request().postDataJSON() as { username: string; email: string };
    expect(body.username).toBe(user.username);
    expect(body.email).toBe(user.email);
    await route.fulfill({ status: 201, json: tokenResponse });
  });

  await page.goto("/register");
  await page.locator("#reg-username").fill(user.username);
  await page.locator("#reg-email").fill(user.email);
  await page.locator("#reg-password").fill("password123");
  await page.getByRole("button", { name: "Create Account" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("No documents yet")).toBeVisible();
});

test("uploads a document and chats with it", async ({ page }) => {
  const documents: typeof uploadedDocument[] = [];
  const markdownAnswer = [
    "A short summary.",
    "",
    "| Field | Value |",
    "| --- | --- |",
    "| Pages | 1 |",
    "",
    "```ts",
    "const answer = 42;",
    "```",
  ].join("\n");

  await page.addInitScript(() => {
    localStorage.setItem("token", "access-token");
    localStorage.setItem("refresh_token", "refresh-token");
  });

  await mockDashboardApis(page, documents);

  await page.route("**/api/v1/documents/upload", async (route) => {
    documents.push(uploadedDocument);
    await route.fulfill({ status: 202, json: uploadedDocument });
  });

  await page.route("**/api/v1/chat/history/doc-1", async (route) => {
    await route.fulfill({ json: { messages: [], document_id: "doc-1" } });
  });

  await page.route("**/api/v1/chat/ask/stream", async (route) => {
    await route.fulfill({
      status: 200,
      headers: { "content-type": "text/event-stream" },
      body: [
        `data: ${JSON.stringify({ type: "token", data: markdownAnswer })}\n\n`,
        `data: ${JSON.stringify({ type: "sources", data: [] })}\n\n`,
        `data: ${JSON.stringify({ type: "done" })}\n\n`,
      ].join(""),
    });
  });

  await page.goto("/dashboard");
  await page.locator('input[type="file"]').setInputFiles({
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("hello world"),
  });

  const documentButton = page.getByRole("button", { name: /notes\.txt/ });
  await expect(documentButton).toBeVisible();
  await documentButton.click();
  await expect(page.getByText("Ask about your document")).toBeVisible();

  await page.locator("#chat-input").fill("Summarize this document");
  await page.locator("#send-btn").click();

  await expect(page.getByText("Summarize this document")).toBeVisible();
  await expect(page.getByText("A short summary.")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Field" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Pages" })).toBeVisible();
  await expect(page.getByText("const answer = 42;")).toBeVisible();
});
