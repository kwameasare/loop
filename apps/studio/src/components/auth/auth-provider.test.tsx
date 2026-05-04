/**
 * P0.3: AuthProvider production gate.
 *
 * In dev/test/preview the provider degrades gracefully when Auth0 env
 * vars are missing so unit tests don't need a live tenant. In
 * production a missing tenant must fail loud — silently rendering a
 * no-auth studio in prod is the bug we're closing.
 */

import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "./auth-provider";

describe("AuthProvider", () => {
  it("renders children when env vars are missing in dev/test", () => {
    const { getByText } = render(
      <AuthProvider envName="development" config={{ domain: "", clientId: "" }}>
        <div>child</div>
      </AuthProvider>,
    );
    expect(getByText("child")).toBeInTheDocument();
  });

  it("throws when env vars are missing in production", () => {
    expect(() =>
      render(
        <AuthProvider
          envName="production"
          config={{ domain: "", clientId: "" }}
        >
          <div>child</div>
        </AuthProvider>,
      ),
    ).toThrow("Auth0 config required in production");
  });

  it("does not throw in production when config is supplied", () => {
    expect(() =>
      render(
        <AuthProvider
          envName="production"
          config={{
            domain: "example.auth0.com",
            clientId: "abc",
            audience: "loop",
            redirectUri: "https://app.example/auth/callback",
          }}
        >
          <div>child</div>
        </AuthProvider>,
      ),
    ).not.toThrow();
  });
});
