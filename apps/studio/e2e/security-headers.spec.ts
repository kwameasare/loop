import { expect, test } from "@playwright/test";

test("studio responses include hardened security headers", async ({ request }) => {
  const response = await request.get("/");
  expect(response.ok()).toBeTruthy();

  const headers = response.headers();
  expect(headers["strict-transport-security"]).toBe(
    "max-age=63072000; includeSubDomains; preload",
  );
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(headers["content-security-policy"]).toContain("default-src 'self'");
});
