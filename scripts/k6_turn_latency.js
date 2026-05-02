import http from "k6/http";
import { check, sleep } from "k6";

const TURN_LATENCY_P95_MS = 2000;
const BASE_URL = (__ENV.LOOP_TURN_LATENCY_BASE_URL || "http://127.0.0.1:18081").replace(/\/$/, "");

export const options = {
  scenarios: {
    text_turn_latency: {
      executor: "constant-vus",
      vus: 8,
      duration: "45s",
      gracefulStop: "10s",
    },
  },
  thresholds: {
    checks: ["rate>0.999"],
    http_req_failed: ["rate<0.001"],
    http_req_duration: [`p(95)<${TURN_LATENCY_P95_MS}`],
  },
};

export default function () {
  const response = http.post(
    `${BASE_URL}/v1/turns`,
    JSON.stringify({
      input: "hello from S840 turn latency gate",
      metadata: { smoke: "turn-latency-k6", path: "text" },
    }),
    {
      headers: { "content-type": "application/json" },
      tags: { path: "text_turn" },
      timeout: "10s",
    },
  );

  check(response, {
    "turn response is 200": (res) => res.status === 200,
    "turn response has text": (res) => String(res.json("reply.text") || "").length > 0,
  });
  sleep(0.1);
}
