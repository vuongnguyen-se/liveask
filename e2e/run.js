"use strict";
// Three-view check through nginx: host, audience (phones) and projector screen update each
// other live, across two app containers. Needs `docker compose up --build -d` first.
//
// The selectors below (#status, #questions .question, ...) are the contract between these
// checks and the pages: keep those ids and classes when restyling.
const path = require("path");
const { BASE, launch, check, podOf } = require("./lib");

const SHOTS = process.env.SHOTS_DIR; // optional: save screenshots here

(async () => {
  const browser = await launch();
  const errors = [];
  // A separate context is a separate localStorage, so each one is a different device.
  async function newPage(viewport) {
    const page = await (await browser.newContext(viewport ? { viewport } : {})).newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    return page;
  }
  /** Open a page until it is connected to a container other than `avoid` (round robin). */
  async function openOn(url, avoid, viewport) {
    for (let i = 0; i < 6; i++) {
      // nginx rotates per request and a page load makes a fixed number of requests, so the
      // WebSocket would land on the same container every time: one extra request shifts it.
      if (i > 0) await fetch(BASE + "/healthz");
      const page = await newPage(viewport);
      await page.goto(url);
      const pod = await podOf(page);
      if (pod !== avoid) return { page, pod };
      await page.context().close();
    }
    throw new Error("could not reach a container other than " + avoid);
  }

  // 1. the presenter creates a room through the real form
  const host = await newPage();
  await host.goto(BASE + "/");
  await host.fill("#title", "E2E demo <b>room</b>");
  await host.click("#create button[type=submit]");
  await host.waitForURL(/\/host\/[A-Z0-9]{6}#t=/);
  const code = host.url().match(/\/host\/([A-Z0-9]{6})/)[1];
  check("host page opened with the token in the #fragment", host.url().includes("#t="));
  const hostPod = await podOf(host);
  await host.waitForFunction(() => document.querySelector("#title").textContent.includes("E2E demo"));
  check("room title is shown as text (no HTML injection)", (await host.textContent("#title")).includes("<b>room</b>"));

  // 2. the screen on the OTHER container, plus two phones
  const { page: screen, pod: screenPod } = await openOn(`${BASE}/screen/${code}`, hostPod);
  check(`host and screen are on different containers (${hostPod}, ${screenPod})`, hostPod !== screenPod);
  check("screen shows the room code", (await screen.textContent("#code")) === code);
  check("screen shows a QR image", ((await screen.getAttribute("#qr", "src")) || "").startsWith("data:image/"));

  const phone = await newPage({ width: 390, height: 800 });
  await phone.goto(`${BASE}/r/${code}`);
  await podOf(phone);
  const phone2 = await newPage({ width: 390, height: 800 });
  await phone2.goto(`${BASE}/r/${code}`);
  await podOf(phone2);

  // 3. a question, with an XSS attempt as text
  const evil = "<img src=x onerror=window.__pwned=1> Why Kubernetes?";
  await phone.fill("#text", evil);
  await phone.fill("#name", "Lan");
  await phone.click("#ask button[type=submit]");
  await screen.waitForSelector("#questions .question");
  check("a question appears on the screen", (await screen.textContent("#questions .question .text")) === evil);
  check("HTML in a question is not executed", !(await screen.evaluate(() => window.__pwned)));
  await host.waitForSelector("#questions .question");
  check("the question appears on the host page", (await host.textContent("#questions .question .text")) === evil);
  await phone2.waitForSelector("#questions .question");
  check("the question appears on the other phone", true);

  // 4. upvote, re-sort, unvote
  await phone.fill("#text", "Second question");
  await phone.click("#ask button[type=submit]");
  await screen.waitForFunction(() => document.querySelectorAll("#questions .question").length === 2);
  await phone2.waitForFunction(() => document.querySelectorAll("#questions .question").length === 2);
  const second = phone2.locator("#questions .question", { hasText: "Second question" });
  await second.locator("button.vote").click();
  await screen.waitForFunction(() => document.querySelector("#questions .question .text").textContent === "Second question");
  check("an upvote re-sorts the screen live", true);
  await phone2.waitForFunction(() => [...document.querySelectorAll("#questions .question")].find((q) => q.textContent.includes("Second question")).querySelector("button.vote").getAttribute("aria-pressed") === "true");
  check("the vote button shows the pressed state for the voter", true);
  await second.locator("button.vote").click();
  await screen.waitForFunction(() => document.querySelector("#questions .question .vote strong").textContent === "0");
  check("tapping again removes the vote", true);

  // 5. moderation
  await host.locator("#questions .question", { hasText: "Why Kubernetes" }).getByRole("button", { name: "Hide" }).click();
  await screen.waitForFunction(() => document.querySelectorAll("#questions .question").length === 1);
  await phone.waitForFunction(() => document.querySelectorAll("#questions .question").length === 1);
  check("a hidden question disappears from the screen and the audience", true);
  check("the host still sees the hidden question", (await host.locator("#questions .question.hidden").count()) === 1);

  // 6. a poll
  await host.fill("#poll-question", "Which service next?");
  await host.fill("#poll-options", "EKS\nECS\nLambda");
  await host.click("#poll-form button[type=submit]");
  await host.getByRole("button", { name: "Open for voting" }).click();
  await phone.waitForSelector("#polls .option");
  await screen.waitForSelector("#polls .option");
  await phone2.locator("#polls .option", { hasText: "EKS" }).click();
  await phone.locator("#polls .option", { hasText: "ECS" }).click();
  await screen.waitForFunction(() => document.querySelector("#polls .muted").textContent.startsWith("2 votes"));
  check("poll results update live on the screen", true);
  await phone.locator("#polls .option", { hasText: "Lambda" }).click();
  await screen.waitForFunction(() => [...document.querySelectorAll("#polls .option .label span:last-child")][2].textContent === "1");
  check("changing a vote moves the count", true);

  if (SHOTS) {
    await screen.screenshot({ path: path.join(SHOTS, "screen.png") });
    await phone.screenshot({ path: path.join(SHOTS, "phone.png") });
    await host.screenshot({ path: path.join(SHOTS, "host.png"), fullPage: true });
  }

  // 7. close the room
  host.once("dialog", (d) => d.accept());
  await host.click("#close-room");
  await phone.waitForSelector("#closed:not([hidden])");
  await screen.waitForSelector("#closed:not([hidden])");
  check("closing the room is shown to the audience and the screen", await phone.locator("#ask textarea").isDisabled());

  check("no JavaScript errors on any page", errors.length === 0);
  if (errors.length) console.log(errors);
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
