/**
 * S912: Playwright happy-path e2e for the Auth0 + cp-api session
 * exchange.
 *
 * The spec exercises the four AC bullet points without a live tenant
 * by intercepting the Auth0 universal-login redirect and the cp-api
 * exchange endpoint:
 *
 * 1. unauthenticated visitor → redirected to /login → Auth0
 * 2. Auth0 callback → POST /v1/auth/exchange → session stored
 * 3. authenticated landing renders the user menu
 * 4. clicking "Sign Out" clears the cp-api session
 *
 * To run live (with a real tenant) set ``LOOP_E2E_BASE_URL`` to the
 * deployed studio URL and remove the ``page.route`` stubs. Skipped
 * unless explicitly opted in via ``LOOP_E2E=1`` so day-to-day CI does
 * not need a Playwright browser download.
 */
import { expect, test } from "@playwright/test";

test.skip(
  process.env.LOOP_E2E !== "1",
  "Set LOOP_E2E=1 to run the studio Auth0 e2e smoke."
);

const AUTH0_DOMAIN = "auth0.test";
const ID_TOKEN = "header.payload.signature";

test("first-time login flow exchanges the Auth0 token and lands on /", async ({
  page,
  context,
}) => {
  // Stub the Auth0 universal-login redirect: as soon as the SDK posts
  // the user to ``/authorize`` we send them straight back to the
  // callback URL with a fake ``code`` + ``state``.
  await page.route(`https://${AUTH0_DOMAIN}/authorize**`, async (route) => {
    const url = new URL(route.request().url());
    const redirectUri = url.searchParams.get("redirect_uri")!;
    const state = url.searchParams.get("state") ?? "state";
    await route.fulfill({
      status: 302,
      headers: { Location: `${redirectUri}?code=test-code&state=${state}` },
    });
  });

  // Stub the Auth0 token endpoint with a synthetic id_token.
  await page.route(`https://${AUTH0_DOMAIN}/oauth/token`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "auth0-access",
        id_token: ID_TOKEN,
        token_type: "Bearer",
        expires_in: 3600,
      }),
    });
  });

  // Stub cp-api /v1/auth/exchange.
  let exchangeCalls = 0;
  await page.route("**/v1/auth/exchange", async (route) => {
    exchangeCalls += 1;
    expect(route.request().method()).toBe("POST");
    expect(JSON.parse(route.request().postData() || "{}")).toMatchObject({
      id_token: ID_TOKEN,
    });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "loop-session-e2e",
        session_token: "loop-session-e2e",
        token_type: "Bearer",
        expires_in: 1800,
      }),
    });
  });

  await page.goto("/");
  // Either the root or /login should kick the SDK off; once the stubs
  // chain runs we land on "/" with a session token in storage.
  await expect(page).toHaveURL(/\/$/, { timeout: 30_000 });
  await expect(page.getByTestId("user-menu")).toBeVisible();
  expect(exchangeCalls).toBe(1);

  const stored = await page.evaluate(() =>
    window.sessionStorage.getItem("loop.cp.session")
  );
  expect(stored).toContain("loop-session-e2e");

  // Sign out clears the cp-api session.
  await page.getByTestId("sign-out-button").click();
  const afterLogout = await page.evaluate(() =>
    window.sessionStorage.getItem("loop.cp.session")
  );
  expect(afterLogout).toBeNull();
});
