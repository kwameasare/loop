import http from "k6/http";
import { check, sleep } from "k6";

const RUNTIME_SSE_P95_MS = 3000;
const CONCURRENT_TURNS = 1000;
const BASE_URL = (__ENV.LOOP_RUNTIME_SSE_BASE_URL || "http://127.0.0.1:18082").replace(/\/$/, "");

export const options = {
  scenarios: {
    runtime_sse_1000: {
      executor: "constant-vus",
      vus: CONCURRENT_TURNS,
      duration: "45s",
      gracefulStop: "20s",
    },
  },
  thresholds: {
    checks: ["rate>0.999"],
    http_req_failed: ["rate<0.001"],
    http_req_duration: [`p(95)<${RUNTIME_SSE_P95_MS}`],
  },
};

export default function () {
  const response = http.post(
    `${BASE_URL}/v1/turns/stream`,
    JSON.stringify({
      workspace_id: "11111111-1111-4111-8111-111111111111",
      conversation_id: "22222222-2222-4222-8222-222222222222",
      user_id: "runtime-sse-k6",
      channel: "web",
      input: "hello from S844 runtime SSE concurrency gate",
      metadata: { smoke: "runtime-sse-1000", path: "sse" },
    }),
    {
      headers: { accept: "text/event-stream", "content-type": "application/json" },
      tags: { path: "runtime_sse" },
      timeout: "15s",
    },
  );

  check(response, {
    "sse response is 200": (res) => res.status === 200,
    "sse content-type": (res) => String(res.headers["Content-Type"] || "").includes("text/event-stream"),
    "sse stream completes": (res) => String(res.body || "").includes("event: done"),
  });
  sleep(0.05);
}
