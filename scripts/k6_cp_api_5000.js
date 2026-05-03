import http from "k6/http";
import { check } from "k6";

const CP_API_TARGET_RPS = 5000;
const CP_API_P95_MS = 100;
const BASE_URL = (__ENV.LOOP_CP_API_BASE_URL || "http://127.0.0.1:18080").replace(/\/$/, "");

export const options = {
  scenarios: {
    cp_api_5000_rps: {
      executor: "constant-arrival-rate",
      rate: CP_API_TARGET_RPS,
      timeUnit: "1s",
      duration: "60s",
      preAllocatedVUs: 200,
      maxVUs: 1000,
    },
  },
  thresholds: {
    checks: ["rate>0.999"],
    http_req_failed: ["rate<0.001"],
    http_req_duration: [`p(95)<${CP_API_P95_MS}`],
  },
};

export default function () {
  const response = http.get(`${BASE_URL}/healthz`, {
    tags: { path: "cp_api_healthz" },
    timeout: "2s",
  });
  check(response, {
    "cp-api health is 200": (res) => res.status === 200,
    "cp-api health is ok": (res) => res.json("ok") === true,
  });
}
