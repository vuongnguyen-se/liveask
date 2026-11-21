"use strict";
/*
 * LiveAsk front end: plain JavaScript, no build step.
 * Rule: user text is only ever put into the page with textContent / createTextNode,
 * never parsed as HTML, so a question like "<img onerror=...>" is shown as plain text.
 */
(function () {
  const LA = {};
  const CODE_RE = /^[A-Za-z0-9]{6}$/;

  // ---------- small helpers ----------------------------------------------------------

  const store = {
    get(key) { try { return localStorage.getItem(key); } catch (e) { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } },
  };

  const $ = (id) => document.getElementById(id);

  /** el("button", {className: "x", onclick: fn, "aria-pressed": "true"}, "text", childNode) */
  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
      if (value === undefined || value === null || value === false) continue;
      if (key === "className") node.className = value;
      else if (key.startsWith("on")) node[key] = value;
      else node.setAttribute(key, value === true ? "" : String(value));
    }
    for (const child of children) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function uuid4() {
    // crypto.randomUUID only exists on HTTPS/localhost; the demo runs on plain HTTP.
    if (window.crypto && crypto.randomUUID) {
      try { return crypto.randomUUID(); } catch (e) { /* fall through */ }
    }
    const b = crypto.getRandomValues(new Uint8Array(16));
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
    return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
  }

  let deviceId = null;
  function getDeviceId() {
    if (deviceId) return deviceId;
    const saved = store.get("liveask.device");
    deviceId = saved && /^[0-9a-f-]{36}$/i.test(saved) ? saved : uuid4();
    store.set("liveask.device", deviceId);
    return deviceId;
  }

  async function api(method, path, body, token) {
    const headers = { "X-Device-Id": getDeviceId() };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers["Authorization"] = "Bearer " + token;
    let res;
    try {
      res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch (e) {
      throw Object.assign(new Error("Network error. Check your connection."), { status: 0 });
    }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) {
      const info = data && data.error;
      throw Object.assign(new Error(info ? info.message : `Request failed (${res.status})`), {
        status: res.status,
        code: info && info.code,
      });
    }
    return data;
  }

  function showError(node, err) { node.textContent = err ? err.message || String(err) : ""; }
  function pathCode() { return (location.pathname.split("/")[2] || "").toUpperCase(); }

  // ---------- room state + WebSocket with automatic reconnect ------------------------

  function sortQuestions(list) {
    // most votes first, then newest first (ISO timestamps compare correctly as strings)
    list.sort((a, b) => {
      if (b.votes !== a.votes) return b.votes - a.votes;
      if (a.created_at !== b.created_at) return a.created_at < b.created_at ? 1 : -1;
      return b.id - a.id;
    });
  }
  function upsert(list, item) {
    const i = list.findIndex((x) => x.id === item.id);
    if (i >= 0) list[i] = item; else list.push(item);
  }

  /**
   * Keeps `state` in sync with the server: loads a snapshot, then applies live messages.
   * On every (re)connect it reloads the snapshot, so nothing is missed while offline.
   */
  function joinRoom({ code, role, token, onChange, onStatus }) {
    const state = {
      room: { code, title: "", closed: false },
      questions: [],
      polls: [],
      myQuestions: new Set(),
      myPolls: {},
    };
    let ws = null;
    let attempt = 0;
    let pingTimer = null;
    let stopped = false;
    let retryTimer = null;

    function missing() {
      stopped = true;
      if (ws) ws.close();
      onStatus("missing");
    }

    async function resync() {
      let snap;
      try {
        snap = await api("GET", `/api/rooms/${code}`, undefined, token);
      } catch (err) {
        if (err.status === 404) missing();
        throw err;
      }
      state.room = { code: snap.code, title: snap.title, closed: snap.closed };
      state.questions = snap.questions;
      state.polls = snap.polls;
      state.myQuestions = new Set(snap.my_votes.questions);
      state.myPolls = snap.my_votes.polls;
      sortQuestions(state.questions);
      onChange();
    }

    function handle(msg) {
      const data = msg.data;
      switch (msg.type) {
        case "hello": onStatus("connected", data.pod); return;
        case "resync": resync().catch(() => {}); return;
        case "question.created":
        case "question.updated":
          if (data.status === "hidden" && data.text === undefined) {
            // The server never pushes the text of a hidden question.
            const known = state.questions.find((q) => q.id === data.id);
            if (role === "host") {
              if (known) known.status = "hidden"; else { resync().catch(() => {}); return; }
            } else {
              state.questions = state.questions.filter((q) => q.id !== data.id);
            }
          } else {
            upsert(state.questions, data);
          }
          sortQuestions(state.questions);
          break;
        case "poll.created":
        case "poll.updated":
          upsert(state.polls, data);
          break;
        case "room.closed":
          state.room.closed = true;
          break;
        default: return; // pong and anything unknown
      }
      onChange();
    }

    function connect() {
      if (stopped) return;
      onStatus("connecting");
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${scheme}://${location.host}/ws/rooms/${code}?role=${role}`);
      ws.onopen = () => {
        attempt = 0;
        resync().catch(() => {});
        pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('{"type":"ping"}');
        }, 25000); // keeps the load balancer from closing an idle connection
      };
      ws.onmessage = (event) => {
        try { handle(JSON.parse(event.data)); } catch (e) { /* ignore bad message */ }
      };
      ws.onclose = (event) => {
        clearInterval(pingTimer);
        if (stopped) return;
        if (event.code === 4404) { missing(); return; }
        onStatus("reconnecting");
        // 0.5 s, 1 s, 2 s ... up to 10 s, plus jitter so clients do not all return at once.
        const delay = Math.min(500 * 2 ** attempt, 10000) + Math.random() * 300;
        attempt += 1;
        retryTimer = setTimeout(connect, delay);
      };
      ws.onerror = () => { /* onclose follows */ };
    }

    window.addEventListener("online", () => {
      if (!stopped && ws && ws.readyState > 1) { // closed and waiting: retry now, once
        clearTimeout(retryTimer);
        attempt = 0;
        connect();
      }
    });
    connect();
    return { state, resync };
  }

  function bindStatus(node) {
    return (status, pod) => {
      node.classList.toggle("live", status === "connected");
      node.textContent = {
        connected: `live · pod ${pod}`,
        connecting: "connecting…",
        reconnecting: "reconnecting…",
        missing: "not found",
      }[status];
      if (status === "missing") {
        const banner = $("missing");
        if (banner) banner.hidden = false;
      }
    };
  }

  // ---------- shared rendering -------------------------------------------------------

  function pollCard(poll, { myChoice, onVote }) {
    const canVote = poll.status === "open" && onVote;
    const options = poll.options.map((label, i) => {
      const share = poll.total ? (poll.counts[i] / poll.total) * 100 : 0;
      const mine = myChoice === i;
      // Only an open poll with a voting handler gets real buttons; results are plain boxes.
      return el(
        canVote ? "button" : "div",
        { type: canVote ? "button" : null, className: "option" + (mine ? " mine" : ""), onclick: canVote ? () => onVote(i) : null },
        el("span", { className: "fill", style: `width:${share}%` }),
        el("span", { className: "label" }, el("span", {}, (mine ? "✓ " : "") + label), el("span", {}, `${poll.counts[i]}`)),
      );
    });
    return el(
      "div",
      { className: "card" },
      el("strong", {}, poll.question),
      " ",
      el("span", { className: "badge" }, poll.status),
      ...options,
      el("div", { className: "muted" }, `${poll.total} vote${poll.total === 1 ? "" : "s"}`),
    );
  }

  function questionItem(q, { voted, canVote, onVote, extra }) {
    // A button when this view can upvote; otherwise a plain counter (host, screen).
    const interactive = Boolean(onVote);
    const counter = el(
      interactive ? "button" : "div",
      {
        type: interactive ? "button" : null,
        className: "vote" + (interactive ? "" : " static"),
        "aria-pressed": interactive ? (voted ? "true" : "false") : null,
        "aria-label": interactive ? `Upvote, ${q.votes} votes` : `${q.votes} votes`,
        disabled: interactive && !canVote,
        onclick: interactive ? onVote : null,
      },
      el("span", {}, "▲"),
      el("strong", {}, q.votes),
    );
    return el(
      "li",
      { className: `card question ${q.status}` },
      counter,
      el(
        "div",
        { className: "body" },
        el("div", { className: "text" }, q.text),
        el(
          "div",
          { className: "muted" },
          q.author_name || "Anonymous",
          q.status !== "open" ? " " : "",
          q.status !== "open" ? el("span", { className: "badge" }, q.status) : null,
        ),
        extra || null,
      ),
    );
  }

  function applyRoomFlags(state) {
    if ($("title") && state.room.title) {
      $("title").textContent = state.room.title;
      document.title = `${state.room.title} · LiveAsk`;
    }
    if ($("closed")) $("closed").hidden = !state.room.closed;
  }

  // ---------- views ------------------------------------------------------------------

  const views = {};

  views.audience = function () {
    const code = pathCode();
    if (!CODE_RE.test(code)) { $("missing").hidden = false; return; }
    $("name").value = store.get("liveask.name") || "";
    let room;

    function render() {
      const s = room.state;
      applyRoomFlags(s);
      const open = !s.room.closed;
      $("ask").querySelectorAll("textarea, button, input").forEach((n) => { n.disabled = !open; });
      $("questions").replaceChildren(
        ...s.questions.map((q) =>
          questionItem(q, {
            voted: s.myQuestions.has(q.id),
            canVote: open,
            onVote: async () => {
              try {
                const res = await api("POST", `/api/questions/${q.id}/vote`);
                // a live message may have replaced this object meanwhile: update the list's copy
                const current = s.questions.find((x) => x.id === q.id);
                if (current) current.votes = res.votes;
                if (res.voted) s.myQuestions.add(q.id); else s.myQuestions.delete(q.id);
                sortQuestions(s.questions);
                render();
              } catch (err) { showError($("ask-error"), err); }
            },
          }),
        ),
      );
      $("empty").hidden = s.questions.length > 0;
      $("polls").replaceChildren(
        ...s.polls.map((p) =>
          pollCard(p, {
            myChoice: s.myPolls[p.id],
            onVote: open ? async (i) => {
              try {
                const updated = await api("POST", `/api/polls/${p.id}/vote`, { option_index: i });
                upsert(s.polls, updated);
                s.myPolls[p.id] = i;
                render();
              } catch (err) { showError($("ask-error"), err); }
            } : null,
          }),
        ),
      );
    }

    room = joinRoom({ code, role: "audience", onChange: render, onStatus: bindStatus($("status")) });

    $("text").addEventListener("input", () => { $("count").textContent = `${$("text").value.length}/280`; });
    $("ask").addEventListener("submit", async (event) => {
      event.preventDefault();
      showError($("ask-error"), null);
      const name = $("name").value.trim();
      store.set("liveask.name", name);
      try {
        const q = await api("POST", `/api/rooms/${code}/questions`, { text: $("text").value, author_name: name || null });
        upsert(room.state.questions, q); // the live message for the same id is harmless
        sortQuestions(room.state.questions);
        $("text").value = "";
        $("count").textContent = "0/280";
        render();
      } catch (err) { showError($("ask-error"), err); }
    });
  };

  views.host = function () {
    const code = pathCode();
    if (!CODE_RE.test(code)) { $("missing").hidden = false; return; }
    const fromUrl = new URLSearchParams(location.hash.slice(1)).get("t");
    if (fromUrl) store.set("liveask.host." + code, fromUrl);
    const token = fromUrl || store.get("liveask.host." + code);
    if (!token) { $("notoken").hidden = false; return; }

    const audienceUrl = `${location.origin}/r/${code}`;
    const screenUrl = `${location.origin}/screen/${code}`;
    $("audience-link").textContent = audienceUrl;
    $("audience-link").href = audienceUrl;
    $("screen-link").textContent = screenUrl;
    $("screen-link").href = screenUrl;
    $("copy-audience").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(audienceUrl); $("copy-audience").textContent = "Copied"; }
      catch (e) { $("copy-audience").textContent = "Select the link and copy"; }
    });

    let room;
    const call = async (method, path, body) => {
      try { return await api(method, path, body, token); }
      catch (err) { showError($("poll-error"), err); return null; }
    };

    function render() {
      const s = room.state;
      applyRoomFlags(s);
      $("close-room").disabled = s.room.closed;
      const setStatus = (q, status) => async () => {
        const updated = await call("PATCH", `/api/questions/${q.id}`, { status });
        if (updated) { upsert(s.questions, updated); sortQuestions(s.questions); render(); }
      };
      $("questions").replaceChildren(
        ...s.questions.map((q) =>
          questionItem(q, {
            voted: false,
            canVote: false,
            onVote: null,
            extra: el(
              "div",
              { className: "row" },
              q.status !== "answered" ? el("button", { type: "button", onclick: setStatus(q, "answered") }, "Mark answered") : null,
              q.status !== "hidden" ? el("button", { type: "button", onclick: setStatus(q, "hidden") }, "Hide") : null,
              q.status !== "open" ? el("button", { type: "button", onclick: setStatus(q, "open") }, "Reopen") : null,
            ),
          }),
        ),
      );
      $("empty").hidden = s.questions.length > 0;

      const setPoll = (p, status) => async () => {
        const updated = await call("PATCH", `/api/polls/${p.id}`, { status });
        if (updated) { upsert(s.polls, updated); render(); }
      };
      $("polls").replaceChildren(
        ...s.polls.map((p) => {
          const card = pollCard(p, { myChoice: undefined, onVote: null });
          const controls = el(
            "div",
            { className: "row" },
            p.status === "draft" ? el("button", { type: "button", className: "primary", onclick: setPoll(p, "open") }, "Open for voting") : null,
            p.status === "open" ? el("button", { type: "button", onclick: setPoll(p, "closed") }, "Close poll") : null,
          );
          card.append(controls);
          return card;
        }),
      );
    }

    room = joinRoom({ code, role: "host", token, onChange: render, onStatus: bindStatus($("status")) });

    $("poll-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      showError($("poll-error"), null);
      const options = $("poll-options").value.split("\n").map((l) => l.trim()).filter(Boolean);
      const poll = await call("POST", `/api/rooms/${code}/polls`, { question: $("poll-question").value, options });
      if (poll) {
        upsert(room.state.polls, poll);
        $("poll-question").value = "";
        $("poll-options").value = "";
        render();
      }
    });
    $("close-room").addEventListener("click", async () => {
      if (!confirm("Close this room? Nobody can ask or vote any more.")) return;
      try {
        await api("POST", `/api/rooms/${code}/close`, undefined, token);
        room.state.room.closed = true;
        render();
      } catch (err) { showError($("poll-error"), err); }
    });
  };

  views.screen = function () {
    const code = pathCode();
    if (!CODE_RE.test(code)) { $("missing").hidden = false; return; }
    const joinUrl = `${location.origin}/r/${code}`;
    $("code").textContent = code;
    $("join-url").textContent = joinUrl;
    try {
      const qr = qrcode(0, "M"); // type 0 = pick the smallest size that fits
      qr.addData(joinUrl);
      qr.make();
      $("qr").src = qr.createDataURL(8, 2);
      $("qr").hidden = false;
    } catch (e) { /* the code and URL are still shown */ }

    function render() {
      const s = (room && room.state) || { room: { title: "" }, questions: [], polls: [] };
      applyRoomFlags(s);
      const top = s.questions.filter((q) => q.status === "open").slice(0, 6);
      $("questions").replaceChildren(...top.map((q) => questionItem(q, { voted: false, canVote: false, onVote: null })));
      $("empty").hidden = top.length > 0;
      // Show the newest open poll, else the newest closed one.
      const shown = [...s.polls].reverse().find((p) => p.status === "open") || [...s.polls].reverse().find((p) => p.status === "closed");
      $("polls").replaceChildren(shown ? pollCard(shown, { myChoice: undefined, onVote: null }) : "");
    }
    let room = joinRoom({ code, role: "screen", onChange: render, onStatus: bindStatus($("status")) });
  };

  const view = document.body.dataset.view;
  if (views[view]) views[view]();
  window.LiveAsk = LA;
})();
