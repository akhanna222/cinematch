import { CATALOGUE } from "./catalogue.js";

// --- tiny state + api helper ------------------------------------------------
const state = {
  token: localStorage.getItem("cm_token") || null,
  user: null,
  ratings: {}, // content_id -> signal
};

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(data?.detail || res.statusText);
  return data;
}

function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1800);
}

const titleOf = (id) => CATALOGUE.find((c) => c.id === id)?.title || id;

// --- views ------------------------------------------------------------------
const app = () => document.getElementById("app");

function renderAuth() {
  document.getElementById("nav").classList.add("hidden");
  app().innerHTML = `
    <div class="panel" style="max-width:420px;margin:40px auto;">
      <h2>Welcome to CineMatch</h2>
      <p class="sub">Social discovery through shared taste.</p>
      <div id="authForms"></div>
      <p class="muted" id="authToggle" style="cursor:pointer;margin-top:16px;"></p>
    </div>`;
  let mode = "signup";
  const renderForm = () => {
    document.getElementById("authForms").innerHTML =
      mode === "signup"
        ? `<label>Display name</label><input id="name" value="Demo User"/>
           <label>Email</label><input id="email" value="demo${Math.floor(Math.random()*9999)}@cinematch.dev"/>
           <label>Password</label><input id="pw" type="password" value="password123"/>
           <label>Looking for</label>
           <select id="intent"><option value="both">Friends & dating</option>
             <option value="friends">Friends</option><option value="dating">Dating</option></select>
           <button class="btn" style="margin-top:18px;width:100%" id="go">Create profile</button>`
        : `<label>Email</label><input id="email"/>
           <label>Password</label><input id="pw" type="password"/>
           <button class="btn" style="margin-top:18px;width:100%" id="go">Log in</button>`;
    document.getElementById("authToggle").textContent =
      mode === "signup" ? "Already have an account? Log in" : "Need an account? Sign up";
    document.getElementById("go").onclick = mode === "signup" ? doSignup : doLogin;
  };
  document.getElementById("authToggle").onclick = () => {
    mode = mode === "signup" ? "login" : "signup";
    renderForm();
  };
  renderForm();
}

async function doSignup() {
  try {
    await api("/auth/signup", {
      method: "POST", auth: false,
      body: {
        display_name: document.getElementById("name").value,
        email: document.getElementById("email").value,
        password: document.getElementById("pw").value,
        social_intent: document.getElementById("intent").value,
      },
    });
    await doLogin();
  } catch (e) { toast(e.message); }
}

async function doLogin() {
  try {
    const r = await api("/auth/login", {
      method: "POST", auth: false,
      body: {
        email: document.getElementById("email").value,
        password: document.getElementById("pw").value,
      },
    });
    state.token = r.access_token;
    localStorage.setItem("cm_token", state.token);
    await boot();
  } catch (e) { toast(e.message); }
}

async function loadRatings() {
  const rows = await api("/ratings");
  state.ratings = {};
  rows.forEach((r) => (state.ratings[r.content_id] = r.signal));
}

function renderRate() {
  setTab("rate");
  const count = Object.keys(state.ratings).length;
  app().innerHTML = `
    <h2>Build your Movie DNA</h2>
    <p class="sub">Rate titles to power recommendations and compatibility.
      <strong>${count}</strong> rated — ${count >= 20 ? "✅ social matching unlocked" : `${20 - count} more to unlock social matching`}.</p>
    <div class="card-grid">
      ${CATALOGUE.map((c) => {
        const sel = state.ratings[c.id];
        const b = (sig, lbl) =>
          `<button class="${sig} ${sel === sig ? "sel" : ""}" data-id="${c.id}" data-sig="${sig}">${lbl}</button>`;
        return `<div class="card">
          <div class="title">${c.title}</div>
          <div class="meta">${c.year}</div>
          <div class="tags">${c.genres.map((g) => `<span class="tag">${g}</span>`).join("")}</div>
          <div class="rate-row">${b("love","Love")}${b("like","Like")}${b("dislike","Nah")}${b("want","Watchlist")}</div>
        </div>`;
      }).join("")}
    </div>`;
  app().querySelectorAll(".rate-row button").forEach((btn) => {
    btn.onclick = async () => {
      const id = btn.dataset.id, sig = btn.dataset.sig;
      const c = CATALOGUE.find((x) => x.id === id);
      try {
        await api("/ratings", { method: "POST", body: { content_id: id, signal: sig, genres: c.genres } });
        state.ratings[id] = sig;
        renderRate();
      } catch (e) { toast(e.message); }
    };
  });
}

async function renderDNA() {
  setTab("dna");
  const dna = await api(`/users/${state.user.user_id}/dna`);
  const entries = Object.entries(dna.genre_weights).sort((a, b) => b[1] - a[1]);
  app().innerHTML = `
    <h2>Your Movie DNA</h2>
    <p class="sub">${dna.rating_count} ratings · genre weights derived from your signals.</p>
    <div class="panel">
      ${entries.length ? entries.map(([g, w]) => `
        <div class="dna-row">
          <span style="text-transform:capitalize">${g}</span>
          <div class="bar"><div style="width:${Math.round(w*100)}%"></div></div>
          <span class="muted">${w.toFixed(2)}</span>
        </div>`).join("") : `<div class="empty">Rate some titles first.</div>`}
    </div>`;
}

async function renderDiscover() {
  setTab("discover");
  app().innerHTML = `<h2>Discover</h2><p class="sub">People ranked by taste compatibility.</p><div id="feed">Loading…</div>`;
  try {
    const feed = await api("/social/discover");
    document.getElementById("feed").innerHTML = feed.length
      ? feed.map((p) => `
        <div class="panel" style="margin-bottom:12px">
          <div class="row" style="justify-content:space-between">
            <div><strong>${p.user.display_name}</strong>
              <div class="muted">${p.user.social_intent}</div></div>
            <span class="score-pill">${Math.round(p.score*100)}% match</span>
          </div>
          ${p.shared_favourites.length ? `<div class="muted" style="margin-top:8px">Shared faves: ${p.shared_favourites.map(titleOf).join(", ")}</div>` : ""}
        </div>`).join("")
      : `<div class="empty">No matches yet. You need 20+ ratings <em>and</em> another eligible user.
           Open a second browser/incognito, sign up, and rate 20 titles to see a match.</div>`;
  } catch (e) {
    document.getElementById("feed").innerHTML = `<div class="empty">${e.message}</div>`;
  }
}

// --- Watch Night (solo demo; multiplayer via join code) ---------------------
let wn = null;
async function renderWatchNight() {
  setTab("wn");
  if (!wn) {
    app().innerHTML = `
      <h2>Watch Night</h2>
      <p class="sub">Swipe a deck; the engine returns consensus picks. (Solo demo — share the join code for multiplayer.)</p>
      <button class="btn" id="start">Start a session</button>`;
    document.getElementById("start").onclick = startWatchNight;
    return;
  }
  drawSwipe();
}

async function startWatchNight() {
  const deck = CATALOGUE.slice(0, 10).map((c) => c.id);
  const s = await api("/sessions", { method: "POST", auth: false, body: { services: [], deck } });
  const j = await api(`/sessions/join/${s.join_code}`, {
    method: "POST", auth: false,
    body: { display_name: state.user.display_name, user_id: state.user.user_id },
  });
  await api(`/sessions/${s.session_id}/start`, { method: "POST", auth: false });
  wn = { sessionId: s.session_id, code: s.join_code, participantId: j.participant_id, deck, idx: 0 };
  drawSwipe();
}

function drawSwipe() {
  if (wn.idx >= wn.deck.length) return finishWatchNight();
  const c = CATALOGUE.find((x) => x.id === wn.deck[wn.idx]);
  app().innerHTML = `
    <h2>Watch Night</h2>
    <p class="sub">Join code <strong>${wn.code}</strong> · card ${wn.idx + 1} of ${wn.deck.length}</p>
    <div class="swipe-stage">
      <div class="swipe-card">
        <div class="big">${c.title}</div>
        <div class="muted">${c.year}</div>
        <div class="tags">${c.genres.map((g) => `<span class="tag">${g}</span>`).join("")}</div>
      </div>
      <div class="swipe-actions">
        <button class="pass" data-sig="pass">✗ Pass</button>
        <button class="interested" data-sig="interested">✓ Interested</button>
        <button class="strong" data-sig="strong_yes">★ Strong Yes</button>
      </div>
    </div>`;
  app().querySelectorAll(".swipe-actions button").forEach((b) => {
    b.onclick = async () => {
      await api(`/sessions/${wn.sessionId}/swipe`, {
        method: "POST", auth: false,
        body: { participant_id: wn.participantId, content_id: c.id, signal: b.dataset.sig },
      });
      wn.idx++;
      drawSwipe();
    };
  });
}

async function finishWatchNight() {
  const r = await api(`/sessions/${wn.sessionId}/complete/${wn.participantId}`, { method: "POST", auth: false });
  const picks = r.picks || [];
  app().innerHTML = `
    <h2>It's a match 🍿</h2>
    <p class="sub">Top consensus picks from your swipes.</p>
    ${picks.length ? picks.map((p, i) => `
      <div class="panel" style="margin-bottom:12px">
        <div class="row" style="justify-content:space-between">
          <div><strong>${i+1}. ${titleOf(p.content_id)}</strong>
            <div class="muted">${p.full_consensus ? "Full consensus" : "Partial match"} · score ${p.aggregate_score}</div></div>
          <span class="score-pill">${p.positive_count}/${p.total_participants}</span>
        </div>
        ${p.dissenters.length ? `<div class="muted" style="margin-top:6px">Not keen: ${p.dissenters.length} participant(s)</div>` : ""}
      </div>`).join("") : `<div class="empty">No positive swipes — try again.</div>`}
    <button class="btn secondary" id="again">New session</button>`;
  document.getElementById("again").onclick = () => { wn = null; renderWatchNight(); };
}

// --- nav / boot -------------------------------------------------------------
function setTab(name) {
  document.querySelectorAll("#nav button[data-tab]").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === name));
}

function buildNav() {
  const nav = document.getElementById("nav");
  nav.classList.remove("hidden");
  nav.innerHTML = `
    <button data-tab="rate">Rate</button>
    <button data-tab="dna">Movie DNA</button>
    <button data-tab="discover">Discover</button>
    <button data-tab="wn">Watch Night</button>
    <button data-tab="logout">Log out (${state.user.display_name})</button>`;
  nav.querySelector('[data-tab="rate"]').onclick = renderRate;
  nav.querySelector('[data-tab="dna"]').onclick = renderDNA;
  nav.querySelector('[data-tab="discover"]').onclick = renderDiscover;
  nav.querySelector('[data-tab="wn"]').onclick = () => { wn = null; renderWatchNight(); };
  nav.querySelector('[data-tab="logout"]').onclick = () => {
    localStorage.removeItem("cm_token");
    state.token = null; state.user = null;
    renderAuth();
  };
}

async function boot() {
  try {
    state.user = await api("/me");
    await loadRatings();
    buildNav();
    renderRate();
  } catch {
    state.token = null;
    localStorage.removeItem("cm_token");
    renderAuth();
  }
}

if (state.token) boot(); else renderAuth();
