import path from "node:path";
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";

function contentType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".html") return "text/html; charset=utf-8";
  if (ext === ".js") return "text/javascript; charset=utf-8";
  if (ext === ".css") return "text/css; charset=utf-8";
  if (ext === ".json") return "application/json; charset=utf-8";
  return "application/octet-stream";
}

async function startStaticServer(rootDir: string): Promise<{
  origin: string;
  close: () => Promise<void>;
}> {
  return await new Promise((resolve, reject) => {
    const server = createServer(async (req, res) => {
      try {
        const reqUrl = new URL(req.url ?? "/", "http://127.0.0.1");
        const rawPath = decodeURIComponent(reqUrl.pathname);
        const relativePath = rawPath.replace(/^\/+/, "");
        const safePath = path.normalize(relativePath);
        if (safePath.startsWith("..")) {
          res.statusCode = 400;
          res.end("Bad path");
          return;
        }
        const diskPath = path.join(rootDir, safePath || "examples/web_widget_demo/index.html");
        const body = await readFile(diskPath);
        res.statusCode = 200;
        res.setHeader("content-type", contentType(diskPath));
        res.end(body);
      } catch {
        res.statusCode = 404;
        res.end("Not found");
      }
    });

    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        reject(new Error("Could not bind static server"));
        return;
      }
      resolve({
        origin: `http://127.0.0.1:${address.port}`,
        close: async () => {
          await new Promise<void>((resolveClose) => {
            server.close(() => resolveClose());
          });
        },
      });
    });
  });
}

test("web widget demo page loads and renders widget shell", async ({ page }) => {
  const repoRoot = path.resolve(__dirname, "../../..");
  const staticServer = await startStaticServer(repoRoot);
  try {
    await page.goto(`${staticServer.origin}/examples/web_widget_demo/index.html`);
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("widget-mount")).toBeVisible();
    await expect(page.getByTestId("chat-widget")).toBeVisible({ timeout: 20000 });
  } finally {
    await staticServer.close();
  }
});
