"use strict";
// Shared helpers for the browser checks. No browser is downloaded: it uses the Chrome or
// Edge already on the machine (set BROWSER_PATH to choose another).
const fs = require("fs");
const { chromium } = require("playwright-core");

const BASE = process.env.BASE_URL || "http://localhost:8000";

const CANDIDATES = [
  process.env.BROWSER_PATH,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);

function browserPath() {
  const found = CANDIDATES.find((p) => fs.existsSync(p));
  if (!found) throw new Error("No Chrome or Edge found. Set BROWSER_PATH to its executable.");
  return found;
}

function launch() {
  return chromium.launch({ executablePath: browserPath() });
}

function check(name, ok) {
  console.log((ok ? "PASS " : "FAIL ") + name);
  if (!ok) process.exitCode = 1;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** The pod names a few fresh WebSocket connections land on (read from each connection's hello). */
async function podsSeen(code, tries = 8) {
  const seen = new Set();
  await Promise.all(
    Array.from({ length: tries }, () => new Promise((resolve) => {
      const ws = new WebSocket(BASE.replace(/^http/, "ws") + `/ws/rooms/${code}?role=probe`);
      const timer = setTimeout(() => { ws.close(); resolve(); }, 4000);
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "hello") seen.add(message.data.pod);
        } catch (e) { /* ignore */ }
        clearTimeout(timer);
        ws.close();
        resolve();
      };
      ws.onerror = () => { clearTimeout(timer); resolve(); };
    })),
  );
  return seen;
}

/**
 * Waits until a new connection can land on at least two different pods or containers. A pod that
 * was just created can be Ready before the load balancer sends it traffic, and the checks that
 * hop between pods need both. Works on Compose and on Kubernetes (it needs no special header).
 */
async function waitForBothContainers(seconds = 90) {
  const created = await fetch(BASE + "/api/rooms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "probe" }),
  }).then((r) => r.json());
  for (let i = 0; i < seconds; i++) {
    try {
      if ((await podsSeen(created.code)).size >= 2) return;
    } catch (e) { /* not up yet */ }
    await sleep(1000);
  }
  throw new Error("the stack does not reach two app pods: is it fully started?");
}

/** Waits until the page's connection badge is live and returns the pod name it shows. */
async function podOf(page) {
  await page.waitForSelector("#status.live", { timeout: 15000 });
  const match = (await page.textContent("#status")).match(/pod (\S+)/);
  return match ? match[1] : null;
}

module.exports = { BASE, launch, check, sleep, podOf, waitForBothContainers };
