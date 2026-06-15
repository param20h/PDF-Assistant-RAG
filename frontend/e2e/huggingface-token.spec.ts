import { expect, test, type Page } from "@playwright/test";

// ── Shared fixtures ────────────────────────────────────────────────────────────

const user = {
  id: "user-1",
  username: "tester",
  email: "tester@example.com",
  is_admin: false,
  is_verified: true,
  role: "user",
  created_at: "2026-01-01T00:00:00Z",
};

const userWithToken = {
  ...user,
  hf_token: "hf_existingToken1234567890",
};

const tokenResponse = {
  access_token: "access-token",
  refresh_token: "refresh-token",
  token_type: "bearer",
  user,
};

// ── Helpers ────────────────────────────────────────────────────────────────────

/** Seed localStorage so the app boots as logged-in */
async function seedAuth(page: Page, withHfToken = false) {
  await page.addInitScript(
    ({ withHfToken }) => {
      localStorage.setItem("token", "access-token");
      localStorage.setItem("refresh_token", "refresh-token");
      if (withHfToken) {
        // Simulate a session where the user already has a token stored
        (window as unknown as Record<string, unknown>).__hf_token_preset__ =
          true;
      }
    },
    { withHfToken },
  );
}

/** Mock all APIs needed for the dashboard + settings page to load */
async function mockBaseApis(page: Page, currentUser = user) {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ json: currentUser }),
  );
  await page.route("**/api/v1/documents/", (route) =>
    route.fulfill({
      json: {
        items: [],
        total: 0,
        page: 1,
        pages: 0,
        total_pages: 0,
        limit: 20,
      },
    }),
  );
  await page.route("**/api/v1/chat/sessions", (route) =>
    route.fulfill({ json: [] }),
  );
}

/** Open the HuggingFace Token modal via the user-menu on the dashboard */
async function openHfModal(page: Page) {
  await page.getByRole("button", { name: user.username }).click();
  await page.getByRole("menuitem", { name: /huggingface token/i }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
}

// ── Tests ──────────────────────────────────────────────────────────────────────

test.describe("HuggingFace Token Flow", () => {
  test("saves a valid token and stores it encrypted via the API", async ({
    page,
  }) => {
    let capturedBody: Record<string, string> | null = null;

    await seedAuth(page);
    await mockBaseApis(page);

    // The PUT /hf-token endpoint — assert payload and return updated user
    await page.route("**/api/v1/auth/hf-token", async (route) => {
      expect(route.request().method()).toBe("PUT");
      capturedBody = route.request().postDataJSON() as Record<string, string>;
      await route.fulfill({
        json: { ...user, hf_token: capturedBody.hf_token },
      });
    });

    await page.goto("/dashboard");
    await openHfModal(page);

    // Fill a valid token
    await page
      .getByLabel("HuggingFace API Token")
      .fill("hf_validTokenForTesting1234");
    await page.getByRole("button", { name: "Save Token" }).click();

    // Success banner visible
    await expect(page.getByText("Token saved successfully")).toBeVisible();

    // API was called with the correct field name and token value
    expect(capturedBody).not.toBeNull();
    expect(capturedBody!.hf_token).toBe("hf_validTokenForTesting1234");
  });

  test("shows a validation error for a token that does not start with hf_", async ({
    page,
  }) => {
    await seedAuth(page);
    await mockBaseApis(page);

    await page.goto("/dashboard");
    await openHfModal(page);

    await page.getByLabel("HuggingFace API Token").fill("sk-invalidToken12345");
    await page.getByRole("button", { name: "Save Token" }).click();

    await expect(page.getByText("Token must start with 'hf_'")).toBeVisible();
    // Dialog stays open — no API call was made
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("shows a validation error for a token that is too short", async ({
    page,
  }) => {
    await seedAuth(page);
    await mockBaseApis(page);

    await page.goto("/dashboard");
    await openHfModal(page);

    await page.getByLabel("HuggingFace API Token").fill("hf_short");
    await page.getByRole("button", { name: "Save Token" }).click();

    await expect(page.getByText(/too short/i)).toBeVisible();
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("shows a validation error when the input is empty", async ({ page }) => {
    await seedAuth(page);
    await mockBaseApis(page);

    await page.goto("/dashboard");
    await openHfModal(page);

    // Save button must be disabled when input is empty
    await expect(
      page.getByRole("button", { name: "Save Token" }),
    ).toBeDisabled();
  });

  test("shows an API error when the backend rejects the token", async ({
    page,
  }) => {
    await seedAuth(page);
    await mockBaseApis(page);

    await page.route("**/api/v1/auth/hf-token", async (route) => {
      await route.fulfill({
        status: 400,
        json: { detail: "Invalid HuggingFace token" },
      });
    });

    await page.goto("/dashboard");
    await openHfModal(page);

    await page
      .getByLabel("HuggingFace API Token")
      .fill("hf_validLengthButRejected1234");
    await page.getByRole("button", { name: "Save Token" }).click();

    await expect(page.getByText("Invalid HuggingFace token")).toBeVisible();
    // Dialog stays open so the user can correct the token
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("toggles token visibility with the show/hide button", async ({
    page,
  }) => {
    await seedAuth(page);
    await mockBaseApis(page);

    await page.goto("/dashboard");
    await openHfModal(page);

    const input = page.getByLabel("HuggingFace API Token");
    await input.fill("hf_validTokenForTesting1234");

    // Default — masked
    await expect(input).toHaveAttribute("type", "password");

    // Show
    await page.getByRole("button", { name: "Show token" }).click();
    await expect(input).toHaveAttribute("type", "text");

    // Hide again
    await page.getByRole("button", { name: "Hide token" }).click();
    await expect(input).toHaveAttribute("type", "password");
  });

  test("displays existing token preview when user already has a token", async ({
    page,
  }) => {
    await seedAuth(page, true);
    // Return the user with a pre-existing token
    await mockBaseApis(page, userWithToken);

    await page.goto("/dashboard");
    await openHfModal(page);

    // Modal shows the "Token configured" badge
    await expect(page.getByText("Token configured")).toBeVisible();
    // Shows the masked preview: first 7 chars + **** + last 4
    await expect(
      page.getByText(/hf_exis\*{4}\d{4}|hf_exis\*{4}7890/),
    ).toBeVisible();
    // Save button says "Update Token" for existing tokens
    await expect(
      page.getByRole("button", { name: "Update Token" }),
    ).toBeVisible();
  });

  test("removes an existing token successfully", async ({ page }) => {
    let removeCalled = false;

    await seedAuth(page, true);
    await mockBaseApis(page, userWithToken);

    await page.route("**/api/v1/auth/hf-token", async (route) => {
      expect(route.request().method()).toBe("PUT");
      const body = route.request().postDataJSON() as Record<string, string>;
      expect(body.hf_token).toBe("");
      removeCalled = true;
      await route.fulfill({
        json: { ...user, hf_token: "" },
      });
    });

    await page.goto("/dashboard");
    await openHfModal(page);

    await page.getByRole("button", { name: /remove/i }).click();

    await expect(page.getByText("Token removed successfully")).toBeVisible();

    expect(removeCalled).toBe(true);
  });

  test("cancel button closes the modal without making any API call", async ({
    page,
  }) => {
    let apiCalled = false;

    await seedAuth(page);
    await mockBaseApis(page);

    await page.route("**/api/v1/auth/hf-token", async (route) => {
      apiCalled = true;
      await route.fulfill({ json: user });
    });

    await page.goto("/dashboard");
    await openHfModal(page);

    await page
      .getByLabel("HuggingFace API Token")
      .fill("hf_someToken1234567890");
    await page.getByRole("button", { name: "Cancel" }).click();

    await expect(page.getByRole("dialog")).not.toBeVisible();
    expect(apiCalled).toBe(false);
  });

  test("updates an existing token with a new valid token", async ({ page }) => {
    let capturedBody: Record<string, string> | null = null;

    await seedAuth(page, true);
    await mockBaseApis(page, userWithToken);

    await page.route("**/api/v1/auth/hf-token", async (route) => {
      capturedBody = route.request().postDataJSON() as Record<string, string>;
      await route.fulfill({
        json: { ...user, hf_token: capturedBody.hf_token },
      });
    });

    await page.goto("/dashboard");
    await openHfModal(page);

    // Clear and type a new token
    await page
      .getByLabel("HuggingFace API Token")
      .fill("hf_newReplacementToken12345");
    await page.getByRole("button", { name: "Update Token" }).click();

    await expect(page.getByText("Token saved successfully")).toBeVisible();
    expect(capturedBody!.hf_token).toBe("hf_newReplacementToken12345");
  });
});
