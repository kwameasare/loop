import { expect, test, type Page } from "@playwright/test";

const AUTH0_DOMAIN = "auth0.test";

async function mockAuth(page: Page) {
  await page.route(`https://${AUTH0_DOMAIN}/authorize**`, async (route) => {
    const url = new URL(route.request().url());
    const redirectUri = url.searchParams.get("redirect_uri") ?? "";
    const state = url.searchParams.get("state") ?? "state";
    await route.fulfill({
      status: 302,
      headers: {
        Location: `${redirectUri}?code=test-code&state=${state}`,
      },
    });
  });

  await page.route(`https://${AUTH0_DOMAIN}/oauth/token**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "auth0-access",
        id_token: "id-token-smoke",
        token_type: "Bearer",
        expires_in: 3600,
      }),
    });
  });

  await page.route("**/__cp/v1/auth/exchange", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "loop-session-smoke",
        session_token: "loop-session-smoke",
        refresh_token: "refresh-smoke",
        token_type: "Bearer",
        expires_in: 1800,
      }),
    });
  });
}

test("smoke: unauthenticated /agents redirects through /login", async ({ page }) => {
  await mockAuth(page);

  let sawLogin = false;
  page.on("framenavigated", (frame) => {
    if (frame === page.mainFrame() && frame.url().includes("/login")) {
      sawLogin = true;
    }
  });

  await page.goto("/agents");
  await expect(page).toHaveURL(/\/agents$/);
  expect(sawLogin).toBeTruthy();
});

test("smoke: agents list page renders", async ({ page }) => {
  await mockAuth(page);
  await page.goto("/agents");

  await expect(
    page.getByRole("heading", { name: "Agents" }),
  ).toBeVisible();
  await expect(page.getByTestId("new-agent-button")).toBeVisible();
});

test("smoke: member add flow renders and submits", async ({ page }) => {
  await mockAuth(page);

  const members = [
    {
      workspace_id: "ws_acme",
      user_sub: "00000000-0000-0000-0000-000000000001",
      role: "owner",
    },
  ];

  await page.route("**/__cp/v1/workspaces/ws_acme/members**", async (route) => {
    const request = route.request();
    const method = request.method();

    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: members }),
      });
      return;
    }

    if (method === "POST") {
      const payload = request.postDataJSON() as {
        user_sub: string;
        role: string;
      };
      members.push({
        workspace_id: "ws_acme",
        user_sub: payload.user_sub,
        role: payload.role,
      });
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(members[members.length - 1]),
      });
      return;
    }

    await route.fulfill({ status: 200, body: "{}" });
  });

  await page.goto("/workspaces/ws_acme/members");
  await expect(page.getByTestId("add-member-form")).toBeVisible();

  await page.getByLabel(/User sub/i).fill("00000000-0000-0000-0000-000000000222");
  await page.getByLabel(/Role/i).selectOption("admin");
  await page.getByTestId("add-member-submit").click();

  await expect(page.getByText("00000000-0000-0000-0000-000000000222")).toBeVisible();
});

test("smoke: eval-suite create form opens with required fields", async ({ page }) => {
  await mockAuth(page);
  await page.goto("/evals");

  await page.getByTestId("new-suite-open").click();
  await expect(page.getByTestId("new-suite-form")).toBeVisible();
  await expect(page.getByTestId("new-suite-dataset-ref")).toBeVisible();
  await expect(page.getByTestId("new-suite-metric-accuracy")).toBeVisible();
});
