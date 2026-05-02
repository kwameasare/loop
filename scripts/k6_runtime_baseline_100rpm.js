import http from "k6/http";
import { check, sleep } from "k6";

const BASELINE_RATE_PER_MINUTE = 100;
const BASE_URL = (__ENV.LOOP_RUNTIME_BASELINE_URL || "http://127.0.0.1:18081").replace(/\/$/, "");

export const options = {
  scenarios: {
    runtime_baseline_100rpm: {
      executor: "constant-arrival-rate",
      rate: BASELINE_RATE_PER_MINUTE,
      timeUnit: "1m",
      duration: "5m",
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
  thresholds: {
    checks: ["rate>0.999"],
    http_req_failed: ["rate<0.001"],
  },
};

export default function () {
  const response = http.post(
    `${BASE_URL}/v1/turns`,
    JSON.stringify({
      input: "hello from S142 runtime baseline",
      metadata: { smoke: "runtime-baseline-100rpm" },
    }),
    {
      headers: { "content-type": "application/json" },
      tags: { path: "runtime_baseline" },
      timeout: "10s",
    },
  );
  check(response, {
    "turn response is 200": (res) => res.status === 200,
    "turn response has text": (res) => String(res.json("reply.text") || "").length > 0,
  });
  sleep(0.1);
}
