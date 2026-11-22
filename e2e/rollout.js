"use strict";
// NFR-2: zero-downtime deploys. A screen stays open and questions keep arriving while
// `kubectl rollout restart deployment/liveask` replaces every pod. Nothing may be lost, the
// screen must reconnect on its own and catch up, and the Deployment must never drop below its
// replica count (maxUnavailable 0).
//
//   kubectl -n ingress-nginx port-forward svc/ingress-nginx-controller 8088:80    (one terminal)
//   BASE_URL=http://localhost:8088 node rollout.js                                (another)
const { execSync, spawn } = require("child_process");
const { BASE, launch, check, sleep, podOf, waitForBothContainers } = require("./lib");

const NS = process.env.K8S_NAMESPACE || "liveask";
const kubectl = (args) => execSync(`kubectl -n ${NS} ${args}`, { stdio: ["ignore", "pipe", "pipe"] }).toString().trim();

(async () => {
  await waitForBothContainers();
  const replicas = Number(kubectl("get deployment liveask -o jsonpath={.spec.replicas}"));

  const created = await fetch(BASE + "/api/rooms", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: "Rolling update" }),
  });
  const { code } = await created.json();

  const browser = await launch();
  const screen = await (await browser.newContext()).newPage();
  await screen.goto(`${BASE}/screen/${code}`);
  const podBefore = await podOf(screen);
  await screen.evaluate(() => {
    window.__badges = [];
    const badge = document.querySelector("#status");
    new MutationObserver(() => window.__badges.push(badge.textContent.trim())).observe(badge, {
      childList: true,
      characterData: true,
      subtree: true,
    });
  });
  console.log(`screen connected to ${podBefore}; deployment has ${replicas} replicas`);

  // A client posts a question every 400 ms and retries like a real one when a request fails.
  const accepted = [];
  let failedAttempts = 0;
  let posting = true;
  const poster = (async () => {
    for (let n = 1; posting; n++) {
      const text = `question ${n}`;
      let ok = false;
      for (let attempt = 0; attempt < 8 && !ok; attempt++) {
        try {
          const res = await fetch(`${BASE}/api/rooms/${code}/questions`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Device-Id": crypto.randomUUID() },
            body: JSON.stringify({ text }),
          });
          ok = res.status === 201;
          if (!ok) failedAttempts++;
        } catch (e) {
          failedAttempts++;
        }
        if (!ok) await sleep(500);
      }
      if (ok) accepted.push(text);
      await sleep(400);
    }
  })();

  // Watch the Deployment while it rolls: available replicas must never drop below the target.
  let minAvailable = Infinity;
  let watching = true;
  const watcher = (async () => {
    while (watching) {
      try {
        const available = Number(kubectl("get deployment liveask -o jsonpath={.status.availableReplicas}") || 0);
        minAvailable = Math.min(minAvailable, available);
      } catch (e) { /* ignore a single failed sample */ }
      await sleep(500);
    }
  })();

  await sleep(3000); // some traffic before the update
  console.log("kubectl rollout restart deployment/liveask ...");
  const started = Date.now();
  kubectl("rollout restart deployment/liveask");
  await new Promise((resolve, reject) => {
    const p = spawn("kubectl", ["-n", NS, "rollout", "status", "deployment/liveask", "--timeout=240s"], { stdio: "ignore" });
    p.on("exit", (code2) => (code2 === 0 ? resolve() : reject(new Error("rollout did not finish"))));
  });
  console.log(`rollout finished in ${((Date.now() - started) / 1000).toFixed(0)} s`);
  await sleep(6000); // traffic after the update
  posting = false;
  await poster;
  watching = false;
  await watcher;

  // The old pod keeps serving during its preStop sleep (10 s) and is then told to stop; only
  // then are its WebSockets closed (code 1012) and the screen moves. Wait for that to happen.
  await screen.waitForFunction(
    (old) => {
      const badge = document.querySelector("#status");
      return badge.classList.contains("live") && !badge.textContent.includes(old);
    },
    podBefore,
    { timeout: 90000 },
  );
  const podAfter = await podOf(screen);
  const badges = await screen.evaluate(() => window.__badges);
  const last = accepted[accepted.length - 1];
  await screen.waitForFunction((text) => document.querySelector("#questions .question .text")?.textContent === text, last, { timeout: 20000 }).catch(() => {});
  const newest = await screen.textContent("#questions .question .text");
  const snapshot = await (await fetch(`${BASE}/api/rooms/${code}`)).json();

  check(`no question was lost (${accepted.length} accepted, ${snapshot.questions.length} stored)`, snapshot.questions.length === accepted.length);
  check(`requests failed only transiently (${failedAttempts} retried attempts, none abandoned)`, accepted.length > 0);
  check(`the Deployment never dropped below ${replicas} available replicas (lowest seen: ${minAvailable})`, minAvailable >= replicas);
  check("the screen noticed the pod going away ('reconnecting' was shown)", badges.some((b) => b.includes("reconnecting")));
  check(`the screen reconnected on its own, to a new pod (${podBefore} -> ${podAfter})`, podAfter !== podBefore);
  check(`the screen caught up to the newest question ('${last}')`, newest === last);
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
