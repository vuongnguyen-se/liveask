"use strict";
// Seeds one realistic room and screenshots every view at its real size.
//   node shots.js                      -> ../shots/ (git-ignored)
//   SHOTS_DIR=../docs/images node shots.js
// Needs `docker compose up --build -d` (same as run.js).
const fs = require("fs");
const path = require("path");
const { BASE, launch, waitForBothContainers } = require("./lib");

const OUT = path.resolve(__dirname, process.env.SHOTS_DIR || "../shots");
const QUESTIONS = [
  ["What is a pod?", "Lan", 9],
  ["EKS or ECS for a small app?", "", 7],
  ["Do pods share one database?", "", 5],
  ["When is Lambda the better fit?", "", 3],
  ["Can I try this at home for free?", "", 2],
  ["What does a Service do?", "", 1],
];

async function api(method, url, body, headers = {}) {
  const res = await fetch(BASE + url, {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return res.status === 204 ? null : res.json();
}

async function seed() {
  const room = await api("POST", "/api/rooms", { title: "Cloud 101, week 5" });
  const host = { Authorization: `Bearer ${room.host_token}` };
  const devices = Array.from({ length: 10 }, () => ({ "X-Device-Id": crypto.randomUUID() }));
  const made = [];
  for (const [i, [text, name]] of QUESTIONS.entries()) {
    made.push(await api("POST", `/api/rooms/${room.code}/questions`, { text, author_name: name || null }, devices[i]));
  }
  for (const [i, [, , votes]] of QUESTIONS.entries()) {
    for (let d = 0; d < votes; d++) await api("POST", `/api/questions/${made[i].id}/vote`, undefined, devices[d]);
  }
  await api("PATCH", `/api/questions/${made[4].id}`, { status: "answered" }, host);
  const hidden = await api("POST", `/api/rooms/${room.code}/questions`, { text: "Which region should we use?" }, devices[7]);
  await api("PATCH", `/api/questions/${hidden.id}`, { status: "hidden" }, host);
  const poll = await api("POST", `/api/rooms/${room.code}/polls`, { question: "Which service next?", options: ["EKS", "ECS", "Lambda"] }, host);
  await api("PATCH", `/api/polls/${poll.id}`, { status: "open" }, host);
  const picks = [0, 0, 0, 0, 0, 1, 1, 2];
  for (const [d, pick] of picks.entries()) await api("POST", `/api/polls/${poll.id}/vote`, { option_index: pick }, devices[d]);
  return room;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  await waitForBothContainers();
  const room = await seed();
  const browser = await launch();
  const shot = async (name, url, viewport, { scheme = "light", full = false, before } = {}) => {
    const ctx = await browser.newContext({ viewport, colorScheme: scheme });
    const page = await ctx.newPage();
    await page.goto(BASE + url);
    if (url.startsWith("/r/") || url.startsWith("/host/") || url.startsWith("/screen/")) {
      await page.waitForSelector("#status.live", { timeout: 15000 });
      await page.waitForTimeout(600);
    } else {
      await page.waitForTimeout(2500);
    }
    if (before) await before(page);
    await page.screenshot({ path: path.join(OUT, name), fullPage: full });
    await ctx.close();
    console.log("saved", name);
  };
  const phone = { width: 390, height: 844 };
  const voteAndPick = async (page) => {
    await page.locator("#questions .vote").first().click();
    await page.locator("#polls .option").first().click();
    await page.waitForTimeout(500);
  };
  await shot("audience-390.png", `/r/${room.code}`, phone, { before: voteAndPick });
  await shot("audience-390-dark.png", `/r/${room.code}`, phone, { scheme: "dark", before: voteAndPick });
  await shot("host-1280.png", `/host/${room.code}#t=${room.host_token}`, { width: 1280, height: 900 }, { full: true });
  await shot("screen-1920.png", `/screen/${room.code}`, { width: 1920, height: 1080 });
  await shot("screen-1280.png", `/screen/${room.code}`, { width: 1280, height: 720 });
  await shot("landing-1440.png", "/", { width: 1440, height: 900 });
  await shot("landing-390.png", "/", phone);
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
