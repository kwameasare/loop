# @loop/web-channel-js

Browser SDK for talking to a Loop agent over the Web channel.

## Install

```sh
npm install @loop/web-channel-js
```

## Usage

```ts
import { WebChannelClient } from "@loop/web-channel-js";

const client = new WebChannelClient({
  baseUrl: "https://api.loop.dev/v1",
  agentId: "agt_42",
  token: "<bearer>",
});

for await (const event of client.send("Hello!")) {
  if (event.type === "token") process.stdout.write(event.text);
  if (event.type === "complete") console.log("\n[done]", event.text);
}
```

## Build

```sh
pnpm install
pnpm build      # runs tsup → dist/{index.js,index.cjs,index.d.ts}
npm pack --dry-run
```

The package ships ESM (`dist/index.js`), CJS (`dist/index.cjs`), and
`.d.ts` types, gated by the conditional `exports` map.
