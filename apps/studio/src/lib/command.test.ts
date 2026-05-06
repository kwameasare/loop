import { describe, expect, it } from "vitest";

import {
  CANONICAL_COMMANDS,
  CHATOPS_COMMANDS,
  filterChatOps,
  filterCommands,
  parsePrefix,
} from "@/lib/command";

describe("parsePrefix", () => {
  it("recognises canonical typed prefixes", () => {
    expect(parsePrefix("agent: support")).toEqual({
      prefix: "agent",
      rest: "support",
    });
    expect(parsePrefix("trace:t-9b23")).toEqual({
      prefix: "trace",
      rest: "t-9b23",
    });
  });

  it("ignores unknown prefixes", () => {
    expect(parsePrefix("project:foo")).toEqual({
      prefix: null,
      rest: "project:foo",
    });
  });

  it("returns the original query when no prefix is present", () => {
    expect(parsePrefix("rollback")).toEqual({ prefix: null, rest: "rollback" });
  });
});

describe("filterCommands", () => {
  it("returns every canonical command when the query is empty", () => {
    const { entries } = filterCommands("");
    expect(entries.length).toBeGreaterThanOrEqual(CANONICAL_COMMANDS.length);
  });

  it("restricts results when a prefix is used", () => {
    const { entries, prefix } = filterCommands("trace: refund");
    expect(prefix).toBe("trace");
    expect(entries.every((entry) => entry.domain === "traces")).toBe(true);
  });

  it("matches keyword tokens that are not in the label", () => {
    const { entries } = filterCommands("botpress");
    expect(entries.some((entry) => entry.id === "cmd_import_project")).toBe(true);
  });

  it("returns no entries for unknown queries", () => {
    const { entries } = filterCommands("zzz nonexistent quux");
    expect(entries).toHaveLength(0);
  });

  it("ranks label-prefix matches above mid-string matches", () => {
    const { entries } = filterCommands("Run");
    expect(entries[0]?.id).toBe("cmd_run_eval");
  });
});

describe("filterChatOps", () => {
  it("returns nothing when the query is not a slash command", () => {
    expect(filterChatOps("swap")).toHaveLength(0);
  });

  it("matches by trigger prefix", () => {
    expect(filterChatOps("/sw")).toEqual([
      CHATOPS_COMMANDS.find((cmd) => cmd.trigger === "/swap"),
    ]);
  });

  it("returns the full set for a bare slash", () => {
    expect(filterChatOps("/")).toHaveLength(CHATOPS_COMMANDS.length);
  });
});
