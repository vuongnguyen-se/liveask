"use strict";
// FR-7: a screen connected to one container survives that container being stopped and
// started again, and shows what it missed. Uses `docker compose` on the repo's own stack
// (the service name is also the pod name: api1 or api2).
const path = require("path");
const { execSync } = require("child_process");
const { BASE, launch, check, sleep, podOf } = require("./lib");

const ROOT = path.resolve(__dirname, "..");
const compose = (args) => execSync(`docker compose ${args}`, { cwd: ROOT, stdio: "pipe" }).toString();

async function waitReady(seconds = 40) {
  for (let i = 0; i < seconds * 5; i++) {
    try {
      if ((await fetch(BASE + "/readyz")).ok) return;
    } catch (e) {
      /* not up yet */
    }
    await sleep(200);
  }
  throw new Error("the stack did not become ready");
}

(async () => {
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

  compose(`stop ${pod}`);
  try {
    await screen.waitForFunction(() => document.querySelector("#status").textContent.includes("reconnecting"));
    check("the screen notices the container stopped and shows 'reconnecting'", true);

    // posted through the container that is still up, while ours is down
    const posted = await fetch(`${BASE}/api/rooms/${code}/questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Device-Id": "11111111-1111-4111-8111-111111111111" },
      body: JSON.stringify({ text: "Posted while the container was down" }),
    });
    check("the other container still accepts questions", posted.status === 201);
  } finally {
    compose(`start ${pod}`); // never leave the stack half stopped
  }

  await waitReady();
  await screen.waitForFunction(() => document.querySelector("#status").classList.contains("live"), null, { timeout: 40000 });
  check("the screen reconnects on its own", true);
  await screen.waitForSelector("#questions .question");
  check(
    "the screen resynced and shows the question it missed",
    (await screen.textContent("#questions .question .text")) === "Posted while the container was down",
  );
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
