// Storybook CSF v3 stories. We avoid importing @storybook/react types
// so the package compiles without storybook installed; types are
// inferred from the component's prop interface when Storybook loads.
import { ChatWidget } from "./widget";
import type { ChatMessage } from "./widget";
import type { WebChannelEvent } from "./index";

export default {
  title: "Web Channel / ChatWidget",
  component: ChatWidget,
  parameters: { layout: "centered" },
};

export const Empty = {
  args: {
    stream: async function* () {},
  },
};

const seed: ChatMessage[] = [
  { id: "s1", role: "user", text: "How do refunds work?", status: "complete" },
  {
    id: "s2",
    role: "assistant",
    text: "Refunds run nightly via the ledger reconciliation job.",
    status: "complete",
  },
];

export const Conversation = {
  args: {
    initialMessages: seed,
    stream: async function* () {},
  },
};

export const Streaming = {
  args: {
    stream: async function* () {
      const chunks: WebChannelEvent[] = [
        { type: "token", text: "I'm" },
        { type: "token", text: " thinking" },
        { type: "token", text: "…" },
        { type: "complete", text: "I'm thinking…" },
      ];
      for (const c of chunks) {
        yield c;
        await new Promise((r) => setTimeout(r, 250));
      }
    },
  },
};

export const Errored = {
  args: {
    stream: async function* () {
      yield {
        type: "error" as const,
        message: "Loop returned 500",
        status: 500,
        requestId: "req_xyz",
      };
    },
  },
};
