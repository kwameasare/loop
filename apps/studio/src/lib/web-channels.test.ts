/**
 * Tests for the web-channel helper. The fixture path (no baseUrl) is
 * exercised first so the UX never crashes when running studio standalone.
 * The live path verifies the cp-api request shape and parsing.
 */
import { describe, expect, it, vi } from "vitest";
import {
  buildEmbedSnippet,
  disableWebChannel,
  enableWebChannel,
  getWebChannel,
} from "./web-channels";

describe("web-channels (fixture mode)", () => {
  it("getWebChannel returns disabled when no baseUrl", async () => {
    const binding = await getWebChannel("agt_demo");
    expect(binding.status).toBe("disabled");
    expect(binding.token).toBeNull();
  });

  it("enableWebChannel mints a token without baseUrl", async () => {
    const binding = await enableWebChannel("agt_demo");
    expect(binding.status).toBe("enabled");
    expect(binding.token).toMatch(/^wct_/);
    expect(binding.channelId).toMatch(/^wch_/);
    expect(binding.enabledAt).not.toBeNull();
  });

  it("disableWebChannel returns disabled without baseUrl", async () => {
    const binding = await disableWebChannel("agt_demo");
    expect(binding.status).toBe("disabled");
    expect(binding.token).toBeNull();
  });
});

describe("web-channels (cp-api mode)", () => {
  it("enableWebChannel POSTs the right URL and parses response", async () => {
    const fetcher = vi.fn<(
      input: RequestInfo | URL,
      init?: RequestInit,
    ) => Promise<Response>>(async () =>
      new Response(
        JSON.stringify({
          agentId: "agt_demo",
          status: "enabled",
          channelId: "wch_xyz",
          token: "wct_real",
          enabledAt: "2026-05-01T00:00:00Z",
        }),
        { status: 200 },
      ),
    );
    const binding = await enableWebChannel("agt_demo", {
      fetcher: fetcher as unknown as typeof fetch,
      baseUrl: "https://api.example.com",
      token: "studio-token",
    });
    expect(binding.token).toBe("wct_real");
    const [url, init] = fetcher.mock.calls[0]!;
    if (!init) throw new Error("missing fetch init");
    expect(String(url)).toBe(
      "https://api.example.com/v1/agents/agt_demo/channels/web/enable",
    );
    expect(init.method).toBe("POST");
    const headers = init.headers as Record<string, string>;
    expect(headers.authorization).toBe("Bearer studio-token");
  });

  it("getWebChannel maps 404 to disabled binding", async () => {
    const fetcher = vi.fn(async () => new Response("", { status: 404 }));
    const binding = await getWebChannel("agt_demo", {
      fetcher: fetcher as unknown as typeof fetch,
      baseUrl: "https://api.example.com/v1",
    });
    expect(binding.status).toBe("disabled");
  });

  it("disableWebChannel surfaces non-2xx as Error", async () => {
    const fetcher = vi.fn(async () => new Response("", { status: 500 }));
    await expect(
      disableWebChannel("agt_demo", {
        fetcher: fetcher as unknown as typeof fetch,
        baseUrl: "https://api.example.com",
      }),
    ).rejects.toThrow(/500/);
  });
});

describe("buildEmbedSnippet", () => {
  it("renders a script tag with agent id + token", () => {
    const snippet = buildEmbedSnippet({
      agentId: "agt_demo",
      token: "wct_abc",
      scriptUrl: "https://cdn.example/web-channel.js",
    });
    expect(snippet).toContain('src="https://cdn.example/web-channel.js"');
    expect(snippet).toContain('data-agent-id="agt_demo"');
    expect(snippet).toContain('data-token="wct_abc"');
    expect(snippet).toMatch(/^<script async/);
    expect(snippet.trim().endsWith("</script>")).toBe(true);
  });

  it("includes data-api-url when supplied", () => {
    const snippet = buildEmbedSnippet({
      agentId: "agt_demo",
      token: "wct_abc",
      apiUrl: "https://api.loop.dev/v1",
    });
    expect(snippet).toContain('data-api-url="https://api.loop.dev/v1"');
  });

  it("escapes attribute-breaking characters", () => {
    const snippet = buildEmbedSnippet({
      agentId: 'agt"x',
      token: "<bad>",
    });
    expect(snippet).toContain('data-agent-id="agt&quot;x"');
    expect(snippet).toContain('data-token="&lt;bad&gt;"');
  });
});
