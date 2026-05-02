/**
 * Unit tests for the enterprise lib (S615).
 *
 * Covers type guards, fixture values, and the postIdpMetadata API helper.
 */

import { describe, expect, it, vi } from "vitest";

import {
  FIXTURE_IDP_CONNECTED,
  FIXTURE_IDP_NOT_CONFIGURED,
  FIXTURE_IDP_PENDING,
  postIdpMetadata,
} from "./enterprise";

describe("enterprise fixtures", () => {
  it("not_configured fixture has null entity_id", () => {
    expect(FIXTURE_IDP_NOT_CONFIGURED.status).toBe("not_configured");
    expect(FIXTURE_IDP_NOT_CONFIGURED.entity_id).toBeNull();
    expect(FIXTURE_IDP_NOT_CONFIGURED.acs_url).toBeNull();
    expect(FIXTURE_IDP_NOT_CONFIGURED.connected_at).toBeNull();
  });

  it("pending fixture has entity_id and acs_url but no connected_at", () => {
    expect(FIXTURE_IDP_PENDING.status).toBe("pending_verification");
    expect(FIXTURE_IDP_PENDING.entity_id).toMatch(/okta/);
    expect(FIXTURE_IDP_PENDING.acs_url).toMatch(/loop\.dev/);
    expect(FIXTURE_IDP_PENDING.connected_at).toBeNull();
  });

  it("connected fixture has all fields populated", () => {
    expect(FIXTURE_IDP_CONNECTED.status).toBe("connected");
    expect(FIXTURE_IDP_CONNECTED.entity_id).toBeTruthy();
    expect(FIXTURE_IDP_CONNECTED.acs_url).toBeTruthy();
    expect(FIXTURE_IDP_CONNECTED.connected_at).toMatch(/2026/);
  });
});

describe("postIdpMetadata", () => {
  it("POSTs url source to the correct endpoint", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => FIXTURE_IDP_PENDING,
    });

    const result = await postIdpMetadata({
      source: { url: "https://idp.example.com/metadata" },
      fetcher: mockFetch,
      baseUrl: "https://api.example.com/v1",
    });

    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.com/v1/enterprise/idp/metadata",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ url: "https://idp.example.com/metadata" }),
      }),
    );
    expect(result.status).toBe("pending_verification");
  });

  it("POSTs xml source to the correct endpoint", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => FIXTURE_IDP_PENDING,
    });

    await postIdpMetadata({
      source: { xml: "<EntityDescriptor/>" },
      fetcher: mockFetch,
      baseUrl: "https://api.example.com/v1",
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        body: JSON.stringify({ xml: "<EntityDescriptor/>" }),
      }),
    );
  });

  it("strips trailing /v1 from baseUrl before reconstructing endpoint", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => FIXTURE_IDP_PENDING,
    });

    await postIdpMetadata({
      source: { url: "https://idp.example.com/m" },
      fetcher: mockFetch,
      // base already has /v1 suffix — should not produce /v1/v1/...
      baseUrl: "https://api.example.com/v1",
    });

    const called = mockFetch.mock.calls[0][0] as string;
    expect(called).toBe(
      "https://api.example.com/v1/enterprise/idp/metadata",
    );
    expect(called).not.toContain("/v1/v1/");
  });

  it("sets Authorization header when token is provided", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => FIXTURE_IDP_PENDING,
    });

    await postIdpMetadata({
      source: { url: "https://idp.example.com/m" },
      fetcher: mockFetch,
      baseUrl: "https://api.example.com/v1",
      token: "tok_test_abc123",
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer tok_test_abc123",
        }),
      }),
    );
  });

  it("throws on non-2xx response", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
    });

    await expect(
      postIdpMetadata({
        source: { url: "https://idp.example.com/m" },
        fetcher: mockFetch,
        baseUrl: "https://api.example.com/v1",
      }),
    ).rejects.toThrow("422");
  });
});
