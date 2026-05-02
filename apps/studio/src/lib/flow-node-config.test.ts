import { describe, expect, it } from "vitest";

import { defaultConfigFor, validateNodeConfig } from "./flow-node-config";

describe("flow-node-config", () => {
  it("defaultConfigFor returns sensible empties per type", () => {
    expect(defaultConfigFor("start")).toEqual({});
    expect(defaultConfigFor("end")).toEqual({});
    expect(defaultConfigFor("message")).toEqual({ body: "" });
    expect(defaultConfigFor("condition")).toEqual({ expression: "" });
    expect(defaultConfigFor("ai-task")).toEqual({
      prompt: "",
      model: "gpt-4o-mini",
    });
    expect(defaultConfigFor("http")).toEqual({ method: "GET", url: "" });
    expect(defaultConfigFor("code")).toEqual({ source: "" });
  });

  it("validateNodeConfig flags empty required fields", () => {
    expect(validateNodeConfig("message", { body: "" })).toEqual({
      body: "Message body is required.",
    });
    expect(validateNodeConfig("condition", { expression: "  " })).toEqual({
      expression: "Expression is required.",
    });
    expect(
      validateNodeConfig("ai-task", { prompt: "", model: "" }),
    ).toEqual({
      prompt: "Prompt is required.",
      model: "Model is required.",
    });
    expect(
      validateNodeConfig("http", { method: "GET", url: "not-a-url" }),
    ).toEqual({
      url: "URL must be a valid absolute URL.",
    });
    expect(validateNodeConfig("code", { source: "" })).toEqual({
      source: "Code body is required.",
    });
  });

  it("validateNodeConfig accepts well-formed config", () => {
    expect(validateNodeConfig("message", { body: "Hello" })).toEqual({});
    expect(
      validateNodeConfig("http", {
        method: "POST",
        url: "https://example.com/x",
      }),
    ).toEqual({});
    expect(validateNodeConfig("start", {})).toEqual({});
    expect(validateNodeConfig("end", {})).toEqual({});
  });
});
