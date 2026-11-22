"use strict";
// FR-7: a screen connected to one container survives that container being stopped and
// started again, and shows what it missed. Uses `docker compose` on the repo's own stack
// (the service name is also the pod name: api1 or api2).
const path = require("path");
const { execSync } = require("child_process");
const { BASE, launch, check, sleep, podOf, waitForBothContainers } = require("./lib");

const ROOT = path.resolve(__dirname, "..");
const compose = (args) => execSync(`docker compose ${args}`, { cwd: ROOT, stdio: "pipe" }).toString();

/** Waits until this container itself is healthy (not just until some container answers). */
async function waitHealthy(service, seconds = 60) {
  for (let i = 0; i < seconds; i++) {
    const status = compose(`ps ${service} --format "{{.Status}}"`);
    if (status.includes("(healthy)")) return;
    await sleep(1000);
  }
  throw new Error(`${service} did not become healthy`);
}

(async () => {
  // Both containers must be healthy first: a previous run may have just restarted one.
  await waitHealthy("api1");
  await waitHealthy("api2");
  await waitForBothContainers();
  const browser = await launch();
  const created = await fetch(BASE + "/api/rooms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "Reconnect" }),
  });
  const { code } = await created.json();

  const screen = await (await browser.newContext()).newPage();
  await screen.goto(`${BASE}/screen/${code}`);
  const pod = await podOf(screen);
  check(`screen is live on ${pod}`, /^api[12]$/.test(pod));
  // Record every badge text from now on: when the other container takes over at once,
  // "reconnecting" shows for well under a second, too briefly to catch by polling.
  await screen.evaluate(() => {
    window.__badges = [];
    const badge = document.querySelector("#status");
    new MutationObserver(() => window.__badges.push(badge.textContent.trim())).observe(badge, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  });

  compose(`stop ${pod}`);
  try {
    // The screen moves to the container that is still up (a few seconds at most).
    await screen.waitForFunction(
      (old) => {
        const badge = document.querySelector("#status");
        return badge.classList.contains("live") && !badge.textContent.includes(old);
      },
      pod,
      { timeout: 20000 },
    );
    const badges = await screen.evaluate(() => window.__badges);
    check("the screen noticed the loss ('reconnecting' was shown)", badges.some((b) => b.includes("reconnecting")));
    check("the screen is live again on the other container", true);

    // A client retries when a request fails while a container is going away: nginx does not
    // resend a POST that timed out on the dead container (it cannot know whether it was
    // processed), so the first request may get a 504. The device id is new each run: the
    // server allows 5 questions a minute per device, and runs are close together.
    const device = crypto.randomUUID();
    let status = 0;
    for (let attempt = 0; attempt < 8 && status !== 201; attempt++) {
      if (attempt > 0) await sleep(1000);
      try {
        status = (
          await fetch(`${BASE}/api/rooms/${code}/questions`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Device-Id": device },
            body: JSON.stringify({ text: "Posted while the container was down" }),
          })
        ).status;
      } catch (e) {
        /* the connection failed: try again */
      }
    }
    check(`the other container accepts a question while one is down (status ${status})`, status === 201);
  } finally {
    compose(`start ${pod}`); // never leave the stack half stopped
  }

  await waitHealthy(pod);
  await waitForBothContainers();
  await screen.waitForFunction(() => document.querySelector("#status").classList.contains("live"), null, { timeout: 40000 });
  check("the screen is still live after the container is back", true);
  await screen.waitForSelector("#questions .question");
  check(
    "the screen shows the question posted while the container was down",
    (await screen.textContent("#questions .question .text")) === "Posted while the container was down",
  );
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
