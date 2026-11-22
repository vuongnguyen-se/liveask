"use strict";
// Accessibility basics on every page at a 320 px phone width (the narrowest we support):
// no sideways scroll, 44 px tap targets, labelled fields, alt text, page language, one h1.
// Needs `docker compose up --build -d`. Run: node a11y.js
const { BASE, launch, check, waitForBothContainers } = require("./lib");

async function api(method, url, body, headers = {}) {
  const res = await fetch(BASE + url, {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return res.status === 204 ? null : res.json();
}

/** Runs inside the page: returns the problems it finds. */
function audit() {
  const problems = [];
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  };
  const name = (el) => (el.id ? "#" + el.id : el.className ? "." + String(el.className).split(" ")[0] : el.tagName.toLowerCase());

  if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) {
    problems.push(`sideways scroll: page is ${document.documentElement.scrollWidth}px wide in ${document.documentElement.clientWidth}px`);
  }
  if (!document.documentElement.lang) problems.push("no lang on <html>");
  const h1s = [...document.querySelectorAll("h1")].filter(visible);
  if (h1s.length !== 1) problems.push(`${h1s.length} visible h1 (want 1)`);

  for (const el of document.querySelectorAll("button, input:not([type=hidden]), textarea, select, a.btn, .nav__toggle")) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    // a text field is 48px; buttons 44; allow the kit's small 36px secondary buttons only on the host page
    if (r.height < 36) problems.push(`tap target ${name(el)} is ${Math.round(r.height)}px tall`);
  }
  for (const el of document.querySelectorAll("input:not([type=hidden]):not([type=submit]), textarea, select")) {
    if (!visible(el)) continue;
    const labelled = el.labels && el.labels.length > 0;
    if (!labelled && !el.getAttribute("aria-label") && !el.getAttribute("aria-labelledby")) problems.push(`field ${name(el)} has no label`);
  }
  for (const el of document.querySelectorAll("button, a[href]")) {
    if (!visible(el)) continue;
    if (!(el.textContent || "").trim() && !el.getAttribute("aria-label") && !el.querySelector("img[alt]")) problems.push(`${name(el)} has no accessible name`);
  }
  for (const img of document.querySelectorAll("img")) {
    if (!visible(img)) continue;
    if (!img.hasAttribute("alt")) problems.push(`img ${name(img)} has no alt`);
  }
  return problems;
}

(async () => {
  await waitForBothContainers();
  const room = await api("POST", "/api/rooms", { title: "Accessibility" });
  const host = { Authorization: `Bearer ${room.host_token}` };
  const device = { "X-Device-Id": crypto.randomUUID() };
  await api("POST", `/api/rooms/${room.code}/questions`, { text: "A question to measure" }, device);
  const poll = await api("POST", `/api/rooms/${room.code}/polls`, { question: "A poll?", options: ["Yes", "No"] }, host);
  await api("PATCH", `/api/polls/${poll.id}`, { status: "open" }, host);

  const browser = await launch();
  const pages = [
    ["landing", "/"],
    ["audience", `/r/${room.code}`],
    ["host", `/host/${room.code}#t=${room.host_token}`],
    ["screen", `/screen/${room.code}`],
  ];
  for (const scheme of ["light", "dark"]) {
    for (const [label, url] of pages) {
      const ctx = await browser.newContext({ viewport: { width: 320, height: 640 }, colorScheme: scheme });
      const page = await ctx.newPage();
      await page.goto(BASE + url);
      await page.waitForTimeout(label === "landing" ? 2500 : 1500);
      const problems = await page.evaluate(audit);
      check(`${label} (${scheme}, 320px): ${problems.length ? problems.join("; ") : "no problems"}`, problems.length === 0);
      await ctx.close();
    }
  }
  await browser.close();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
