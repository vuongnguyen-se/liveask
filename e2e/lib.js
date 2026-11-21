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

/**
 * Waits until nginx reaches BOTH app containers. A container that was just re-created can be
 * healthy before nginx sends it traffic, and the checks that hop between containers need both.
 */
async function waitForBothContainers(seconds = 90) {
  for (let i = 0; i < seconds; i++) {
    const seen = new Set();
    for (let k = 0; k < 6; k++) {
      try {
        const res = await fetch(BASE + "/healthz");
        const upstream = res.headers.get("x-upstream");
        if (res.ok && upstream) seen.add(upstream.split(",").pop().trim());
      } catch (e) {
        /* not up yet */
      }
    }
    if (seen.size >= 2) return;
    await sleep(1000);
  }
  throw new Error("nginx does not reach two app containers: is `docker compose up -d` finished?");
}

/** Waits until the page's connection badge is live and returns the pod name it shows. */
async function podOf(page) {
  await page.waitForSelector("#status.live", { timeout: 15000 });
  const match = (await page.textContent("#status")).match(/pod (\S+)/);
  return match ? match[1] : null;
}

module.exports = { BASE, launch, check, sleep, podOf, waitForBothContainers };
