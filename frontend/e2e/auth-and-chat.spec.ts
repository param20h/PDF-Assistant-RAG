import { expect, test, type Page } from "@playwright/test";

const user = {
  id: "user-1",
  username: "tester",
  email: "tester@example.com",
  is_verified: true,
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
    const headers = route.request().headers();
    const hasAuth = headers["authorization"] || headers["cookie"];
    if (hasAuth) {
      await route.fulfill({ json: user });
    } else {
      await route.fulfill({ status: 401, json: { detail: "Not authenticated" } });
    }
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

  await page.route("**/api/v1/chat/sessions", async (route) => {
    await route.fulfill({ json: [] });
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
  await Promise.all([
    page.waitForURL("/dashboard"),
    page.locator("#sign-in-btn").click(),
  ]);
  await expect(page.getByText("No documents yet")).toBeVisible();
});

test("creates an account from the signup form", async ({ page }) => {
  await page.route("**/api/v1/auth/register", async (route) => {
    const body = route.request().postDataJSON() as { username: string; email: string };
    expect(body.username).toBe(user.username);
    expect(body.email).toBe(user.email);
    await route.fulfill({
      status: 201,
      json: {
        message: "Registration successful. Please check your email to verify your account before logging in.",
        email: user.email,
        verification_url: "/verify-email?token=test-token",
      },
    });
  });

  await page.goto("/register");
  await page.locator("#reg-username").fill(user.username);
  await page.locator("#reg-email").fill(user.email);
  await page.locator("#reg-password").fill("Password1!");
  await page.getByRole("button", { name: "Create Account" }).click();

  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByText("Check your email")).toBeVisible();
  await expect(page.getByText(`We sent a verification link to ${user.email}. Verify your email before signing in.`)).toBeVisible();
  await expect(page.getByRole("link", { name: "Open verification link" })).toHaveAttribute(
    "href",
    "/verify-email?token=test-token"
  );
});

test("uploads a PDF document and chats with it", async ({ page }) => {
  const documents: typeof uploadedDocument[] = [];
  const pdfDoc = { ...uploadedDocument, original_name: "test.pdf" };
  const markdownAnswer = [
    "A short summary of the PDF.",
    "",
    "| Field | Value |",
    "| --- | --- |",
    "| Format | PDF |",
    "",
    "```ts",
    "const isPdf = true;",
    "```",
  ].join("\n");

  await page.addInitScript(() => {
    localStorage.setItem("token", "access-token");
    localStorage.setItem("refresh_token", "refresh-token");
  });

  await mockDashboardApis(page, documents);

  await page.route("**/api/v1/documents/upload", async (route) => {
    documents.push(pdfDoc);
    await route.fulfill({ status: 202, json: pdfDoc });
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
  
  // Upload as a PDF
  await page.locator('input[type="file"]').setInputFiles({
    name: "test.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n%..."),
  });

  const documentButton = page.getByRole("button", { name: /test\.pdf/ });
  await expect(documentButton).toBeVisible();
  await documentButton.click();
  await expect(page.getByText("Ask about your document")).toBeVisible();

  await page.locator("#chat-input").fill("Summarize this PDF");
  await page.locator("#send-btn").click();

  await expect(page.getByText("Summarize this PDF")).toBeVisible();
  await expect(page.getByText("A short summary of the PDF.")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Field" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Format" })).toBeVisible();
  await expect(page.getByText("const isPdf = true;")).toBeVisible();
});

test("deletes a document successfully", async ({ page }) => {
  const documents = [{ ...uploadedDocument, original_name: "test.pdf" }];
  
  await page.addInitScript(() => {
    localStorage.setItem("token", "access-token");
    localStorage.setItem("refresh_token", "refresh-token");
  });

  await mockDashboardApis(page, documents);

  await page.route("**/api/v1/documents/doc-1", async (route) => {
    expect(route.request().method()).toBe("DELETE");
    documents.pop();
    await route.fulfill({ status: 200, json: { message: "deleted" } });
  });

  await page.goto("/dashboard");
  const documentButton = page.getByRole("button", { name: /test\.pdf/ });
  await expect(documentButton).toBeVisible();
  
  // Handle confirm dialog (must be registered BEFORE click)
  page.on('dialog', dialog => dialog.accept());

  // Delete the document
  await documentButton.hover();
  // Find the button with Trash2 icon
  await page.locator('button.shrink-0:has(svg.lucide-trash2)').click();

  await expect(page.getByText("No documents yet")).toBeVisible();
});

test("logs out successfully", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("token", "access-token");
    localStorage.setItem("refresh_token", "refresh-token");
  });

  await mockDashboardApis(page);

  await page.goto("/dashboard");
  await page.getByRole("button", { name: "tester" }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();

  await expect(page).toHaveURL(/\/login$/);
  const token = await page.evaluate(() => localStorage.getItem("token"));
  expect(token).toBeNull();
});
