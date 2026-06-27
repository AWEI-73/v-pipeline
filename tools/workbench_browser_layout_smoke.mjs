#!/usr/bin/env node
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_VIEWPORTS = [
  { width: 1366, height: 900 },
  { width: 1920, height: 1080 },
];

function codexRuntimeNodeModules() {
  const home = process.env.USERPROFILE || process.env.HOME;
  if (!home) return null;
  return path.join(
    home,
    ".cache",
    "codex-runtimes",
    "codex-primary-runtime",
    "dependencies",
    "node",
    "node_modules",
  );
}

const FALLBACK_NODE_MODULES = [
  process.env.CODEX_NODE_MODULES,
  codexRuntimeNodeModules(),
].filter(Boolean);

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function parseArgs(argv) {
  const args = {
    artifactRoot: null,
    port: 0,
    python: process.env.PYTHON || "python",
    url: process.env.WORKBENCH_URL || "http://localhost:8765/workbench",
    viewports: DEFAULT_VIEWPORTS,
  };
  for (let index = 2; index < argv.length; index += 1) {
    const item = argv[index];
    if (item === "--url") {
      args.url = argv[index + 1];
      index += 1;
    } else if (item === "--artifact-root") {
      args.artifactRoot = argv[index + 1];
      index += 1;
    } else if (item === "--port") {
      args.port = Number(argv[index + 1] || 0);
      index += 1;
    } else if (item === "--python") {
      args.python = argv[index + 1];
      index += 1;
    } else if (item === "--viewport") {
      const value = argv[index + 1] || "";
      const [width, height] = value.split("x").map((part) => Number(part));
      if (!width || !height) {
        throw new Error(`Invalid --viewport value: ${value}`);
      }
      args.viewports = [{ width, height }];
      index += 1;
    }
  }
  return args;
}

function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => resolve(port));
    });
  });
}

function waitForHttp(url, timeoutMs = 15000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const response = await fetch(url);
        if (response.ok) {
          resolve();
          return;
        }
      } catch {
        // Server may still be starting.
      }
      if (Date.now() - started > timeoutMs) {
        reject(new Error(`Timed out waiting for ${url}`));
        return;
      }
      setTimeout(tick, 250);
    };
    tick();
  });
}

async function startWorkbenchServer(args) {
  if (!args.artifactRoot) return null;
  const port = args.port || await findFreePort();
  const url = `http://localhost:${port}/workbench`;
  const child = spawn(args.python, [
    "tools/workbench_server.py",
    "--artifact-root",
    args.artifactRoot,
    "--port",
    String(port),
  ], {
    cwd: REPO_ROOT,
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stderr = "";
  let spawnError = null;
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });
  child.on("error", (error) => {
    spawnError = error;
  });
  child.on("exit", (code) => {
    if (code !== null && code !== 0) {
      stderr += `\nworkbench_server exited with code ${code}`;
    }
  });
  await waitForHttp(url).catch((error) => {
    child.kill();
    if (spawnError) {
      throw new Error(`Failed to start workbench server with ${args.python}: ${spawnError.message}`);
    }
    throw new Error(`${error.message}${stderr ? `\n${stderr}` : ""}`);
  });
  return { child, url };
}

async function stopWorkbenchServer(handle) {
  if (!handle?.child || handle.child.killed) return;
  handle.child.kill();
  await new Promise((resolve) => {
    const timer = setTimeout(resolve, 3000);
    handle.child.once("exit", () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

function nearestFrame(page) {
  return page.frames().find((frame) => frame.url().includes("/workbench/index.html")) || page.mainFrame();
}

async function inspectLayout(frame) {
  return frame.evaluate(() => {
    const box = (selector) => {
      const el = document.querySelector(selector);
      if (!el) return null;
      const rect = el.getBoundingClientRect();
      return {
        width: rect.width,
        height: rect.height,
        overflowX: el.scrollWidth > el.clientWidth,
      };
    };
    const monitor = box(".wb-monitor");
    return {
      documentWidth: document.documentElement.clientWidth,
      documentScrollWidth: document.documentElement.scrollWidth,
      bodyOverflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      monitor,
      monitorRatio: monitor ? Number((monitor.width / monitor.height).toFixed(3)) : null,
      transport: box(".wb-transport"),
      hasPlayButton: Boolean(document.querySelector("#btn-play")),
      hasScrubber: Boolean(document.querySelector("#scrubber")),
      hasTimeLabel: Boolean(document.querySelector("#time-label")),
      timeline: box(".wb-timeline"),
      laneCount: document.querySelectorAll(".track-lane").length,
    };
  });
}

async function inspectHostLayout(page) {
  return page.evaluate(() => {
    const app = document.querySelector("#app");
    const shell = document.querySelector(".workbench-shell");
    const iframe = document.querySelector(".workbench-shell iframe");
    const forbiddenShellSelectors = [
      "monitor-box",
      "timeline-wrap",
      "clip-video",
      "wb-monitor",
      "wb-timeline",
      "track-lane",
      "lane-video",
    ];
    const rectFor = (el) => {
      if (!el) return null;
      const rect = el.getBoundingClientRect();
      return {
        top: rect.top,
        width: rect.width,
        height: rect.height,
        visibleInFirstViewport: rect.top < window.innerHeight && rect.bottom > 0,
      };
    };
    return {
      hostMode: app ? "spa_shell" : "native_direct",
      isSpaShell: Boolean(app),
      appWorkbench: Boolean(app?.classList.contains("app-workbench")),
      shell: rectFor(shell),
      iframe: rectFor(iframe),
      iframeSrc: iframe?.getAttribute("src") || "",
      forbiddenShellSelectors: forbiddenShellSelectors.filter((selector) => document.querySelector(`.${selector}, #${selector}`)),
    };
  });
}

function assertLayout(result, viewport) {
  assert.equal(result.bodyOverflowX, false, `${viewport.width}x${viewport.height}: page has horizontal overflow`);
  assert.ok(result.monitor, `${viewport.width}x${viewport.height}: missing .wb-monitor`);
  assert.ok(result.transport, `${viewport.width}x${viewport.height}: missing .wb-transport`);
  assert.ok(result.timeline, `${viewport.width}x${viewport.height}: missing .wb-timeline`);
  assert.equal(result.laneCount, 4, `${viewport.width}x${viewport.height}: expected four timeline lanes`);
  assert.equal(result.hasPlayButton, true, `${viewport.width}x${viewport.height}: missing #btn-play`);
  assert.equal(result.hasScrubber, true, `${viewport.width}x${viewport.height}: missing #scrubber`);
  assert.equal(result.hasTimeLabel, true, `${viewport.width}x${viewport.height}: missing #time-label`);
  assert.ok(
    Math.abs(result.monitorRatio - 1.778) <= 0.01,
    `${viewport.width}x${viewport.height}: monitor ratio ${result.monitorRatio} is not 16:9`,
  );
  assert.equal(result.monitor.overflowX, false, `${viewport.width}x${viewport.height}: monitor overflows horizontally`);
  assert.equal(result.transport.overflowX, false, `${viewport.width}x${viewport.height}: transport overflows horizontally`);
  assert.ok(result.transport.height >= 24, `${viewport.width}x${viewport.height}: transport is too short (${result.transport.height}px)`);
  assert.equal(result.timeline.overflowX, false, `${viewport.width}x${viewport.height}: timeline box overflows horizontally`);
}

function assertHostLayout(result, viewport) {
  if (!result.isSpaShell) return;
  assert.equal(result.appWorkbench, true, `${viewport.width}x${viewport.height}: SPA shell is missing app-workbench class`);
  assert.ok(result.shell, `${viewport.width}x${viewport.height}: SPA shell missing .workbench-shell`);
  assert.ok(result.iframe, `${viewport.width}x${viewport.height}: SPA shell missing .workbench-shell iframe`);
  assert.ok(
    result.iframeSrc.includes("/workbench/index.html"),
    `${viewport.width}x${viewport.height}: iframe src is not the native Workbench runtime: ${result.iframeSrc}`,
  );
  assert.ok(
    result.shell.visibleInFirstViewport,
    `${viewport.width}x${viewport.height}: Workbench iframe shell is not visible in the first viewport`,
  );
  assert.ok(result.iframe.width >= 480, `${viewport.width}x${viewport.height}: iframe is too narrow (${result.iframe.width}px)`);
  assert.ok(result.iframe.height >= 520, `${viewport.width}x${viewport.height}: iframe is too short (${result.iframe.height}px)`);
  assert.deepEqual(
    result.forbiddenShellSelectors,
    [],
    `${viewport.width}x${viewport.height}: SPA shell must not duplicate native monitor/timeline selectors`,
  );
}

async function main() {
  const { chromium } = await loadPlaywright();
  const args = parseArgs(process.argv);
  const server = await startWorkbenchServer(args);
  if (server) args.url = server.url;
  let browser = null;
  const reports = [];
  try {
    browser = await chromium.launch({ headless: true });
    for (const viewport of args.viewports) {
      const page = await browser.newPage({ viewport });
      await page.goto(args.url, { waitUntil: "networkidle", timeout: 30000 });
      const frame = nearestFrame(page);
      const host = await inspectHostLayout(page);
      assertHostLayout(host, viewport);
      const result = await inspectLayout(frame);
      assertLayout(result, viewport);
      reports.push({ viewport, host, result });
      await page.close();
    }
  } finally {
    if (browser) await browser.close();
    await stopWorkbenchServer(server);
  }
  console.log(JSON.stringify({
    ok: true,
    url: args.url,
    artifact_role: "workbench_browser_layout_smoke",
    reports,
  }, null, 2));
}

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch (firstError) {
    for (const nodeModules of FALLBACK_NODE_MODULES) {
      try {
        const require = createRequire(path.join(nodeModules, "..", "noop.js"));
        return require("playwright");
      } catch {
        // Try the next known runtime package root.
      }
      const pnpmRoot = path.join(nodeModules, ".pnpm");
      if (fs.existsSync(pnpmRoot)) {
        const packageDir = fs.readdirSync(pnpmRoot).find((name) => name.startsWith("playwright@"));
        if (packageDir) {
          try {
            const entry = path.join(pnpmRoot, packageDir, "node_modules", "playwright", "index.js");
            const require = createRequire(entry);
            return require(entry);
          } catch {
            // Fall through to the final actionable error.
          }
        }
      }
    }
    throw new Error(
      `Cannot load playwright. Install it for this repo or set CODEX_NODE_MODULES. Original error: ${firstError.message}`,
    );
  }
}

main().catch((error) => {
  console.error(`[workbench-layout-smoke] FAILED: ${error.message}`);
  process.exit(2);
});
