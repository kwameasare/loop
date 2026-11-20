/**
 * P0.3: AuthProvider production gate.
 *
 * In dev/test/preview the provider degrades gracefully when Auth0 env
 * vars are missing so unit tests don't need a live tenant. In
 * production a missing tenant must fail loud — silently rendering a
 * no-auth studio in prod is the bug we're closing.
 */

import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

const auth0ProviderProps = vi.hoisted(() => ({
  current: null as null | {
    onRedirectCallback?: (appState?: { returnTo?: string }) => void;
    children?: ReactNode;
  },
}));

vi.mock("@auth0/auth0-react", () => ({
  Auth0Provider: (props: {
    onRedirectCallback?: (appState?: { returnTo?: string }) => void;
    children?: ReactNode;
  }) => {
    auth0ProviderProps.current = props;
    return <>{props.children}</>;
  },
}));

import { AuthProvider } from "./auth-provider";

describe("AuthProvider", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders children when env vars are missing in dev/test", () => {
    const { getByText } = render(
      <AuthProvider envName="development" config={{ domain: "", clientId: "" }}>
        <div>child</div>
      </AuthProvider>,
    );
    expect(getByText("child")).toBeInTheDocument();
  });

  it("throws when env vars are missing in production", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
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

  it("keeps Auth0 callback mounted until the Loop session exchange completes", () => {
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
    );

    auth0ProviderProps.current?.onRedirectCallback?.({
      returnTo: "/agents/agt_42",
    });

    expect(window.location.pathname).toBe("/auth/callback");
    expect(window.location.search).toBe("?returnTo=%2Fagents%2Fagt_42");
  });
});
