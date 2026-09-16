/* wall-clock-layout-card.js — drag what is on a clock's screen, live.
 *
 *   type: custom:wall-clock-layout-card
 *   slug: mini_round_clock_3     # the clock's entity prefix
 *   name: Zac                    # optional
 *   routine: zac                 # optional: the routine slug, for "try the routine face"
 *
 * A 360 x 360 mock of the round panel. Every movable element on the real clock
 * is a pair (or triple) of number entities in the firmware -- "Layout weather
 * X/Y/size" and friends -- and dragging here calls number.set_value on them as
 * you go, throttled to five updates a second. The clock repaints within a
 * second, so the mock and the wall agree while you drag. Nothing is stored in
 * the browser: the numbers ARE the layout, and they survive a reboot.
 *
 * Faces you can arrange:
 *   grow     the child's face (eyes are fixed by the firmware), the time, the weather
 *   routine  the picture face: time, step name, picture, minutes left, weather
 *   clock    the ordinary clock: only the weather symbol is movable
 */
(function () {
  const SLOTS = {
    weather:          { label: "Weather",         faces: ["grow", "clock"], size: true },
    routine_weather:  { label: "Weather (routine)", faces: ["routine"], size: true, sw: "weather_symbol_on_the_routine_face" },
    grow_time:        { label: "Time",            faces: ["grow"],    size: true },
    routine_time:     { label: "Time",            faces: ["routine"], size: true },
    routine_name:     { label: "Step name",       faces: ["routine"], size: true },
    routine_picture:  { label: "Picture",         faces: ["routine"], size: true },
    routine_minutes:  { label: "Minutes left",    faces: ["routine"], size: true },
    routine_next:     { label: "What's next",     faces: ["routine"], size: true },
    next_other_faces: { label: "What's next (before a step)", faces: ["grow", "clock"], size: true },
  };
  const FACES = [["grow", "Grow face"], ["routine", "Routine face"], ["clock", "Clock face"]];
  const css = `
    :host { display:block }
    ha-card { padding: 12px 16px 16px; }
    .hdr { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:8px }
    .hdr h2 { margin:0; font-size:1.25em; font-weight:500; flex:1 1 auto }
    .seg button { font:inherit; cursor:pointer; padding:6px 10px; border:1px solid var(--divider-color, rgba(127,127,127,.35)); background:var(--card-background-color); color:var(--primary-text-color); border-radius:0 }
    .seg button:first-child { border-radius:8px 0 0 8px } .seg button:last-child { border-radius:0 8px 8px 0 }
    .seg button.on { background:var(--primary-color); color:var(--text-primary-color,#fff); border-color:var(--primary-color) }
    .wrap { display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start }
    svg { width: min(100%, 360px); height:auto; touch-action:none; border-radius:50%; background:#000; display:block }
    .el { cursor:grab } .el.sel .box { stroke: var(--primary-color, #4c8); stroke-dasharray: 4 3 }
    .box { fill: rgba(255,255,255,0.02); stroke: rgba(255,255,255,0.25); stroke-width:1 }
    .side { flex:1 1 200px; min-width:180px }
    .side label { display:block; font-size:.85em; color:var(--secondary-text-color); margin:8px 0 2px }
    .side input[type=range] { width:100% }
    .muted { color:var(--secondary-text-color); font-size:.9em }
    .err { color: var(--error-color,#d33); font-size:.9em }
    button.p { font:inherit; cursor:pointer; padding:6px 10px; border-radius:8px; background:var(--primary-color); color:var(--text-primary-color,#fff); border:1px solid var(--primary-color) }
    button.g { font:inherit; cursor:pointer; padding:6px 10px; border-radius:8px; background:var(--card-background-color); color:var(--primary-text-color); border:1px solid var(--divider-color, rgba(127,127,127,.35)) }
    .tog { display:inline-flex; align-items:center; gap:6px; font-size:.9em; cursor:pointer; margin-right:10px }
    .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:8px }
  `;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  // ---- the weather symbol, mirroring the firmware's primitives ------------
  function wxSvg(cond, hi, lo, showLow, sc) {
    const R = 26 * sc, haveHi = hi !== null && hi !== undefined && hi !== "unknown" && hi !== "unavailable";
    const ix = haveHi ? -34 * sc : 0, iy = 0;
    const SUN = "#ffcc28", CLOUD = "#d2d8e4", RAIN = "#50a0ff", BOLT = "#ffe13c", SNOW = "#ebf0ff", FOG = "#969caa", WIND = "#aac8e6";
    const sun = (cx, cy, r, c) => { let s = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${c}"/>`; for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4; s += `<line x1="${cx + Math.cos(a) * r * 1.35}" y1="${cy + Math.sin(a) * r * 1.35}" x2="${cx + Math.cos(a) * r * 1.85}" y2="${cy + Math.sin(a) * r * 1.85}" stroke="${c}" stroke-width="2.5"/>`; } return s; };
    const cloud = (cx, cy, r, c) => `<circle cx="${cx - r * .45}" cy="${cy + r * .12}" r="${r * .42}" fill="${c}"/><circle cx="${cx + r * .05}" cy="${cy - r * .18}" r="${r * .56}" fill="${c}"/><circle cx="${cx + r * .52}" cy="${cy + r * .18}" r="${r * .38}" fill="${c}"/><rect x="${cx - r * .45}" y="${cy + r * .14}" width="${r * .97}" height="${r * .4}" fill="${c}"/>`;
    const drops = (cx, cy, r, n) => { let s = ""; for (let k = 0; k < n; k++) { const dx = cx - r * .55 + k * (r * 1.1) / (n - 1); s += `<line x1="${dx}" y1="${cy + r * .62}" x2="${dx - r * .14}" y2="${cy + r * 1.05}" stroke="${RAIN}" stroke-width="2.5"/>`; } return s; };
    const flakes = (cx, cy, r) => [0, 1, 2].map((k) => `<circle cx="${cx - r * .5 + k * r * .5}" cy="${cy + r * .85}" r="${Math.max(2, r * .1)}" fill="${SNOW}"/>`).join("");
    const bolt = (cx, cy, r) => { const x0 = cx + r * .1, y0 = cy + r * .45, w = Math.max(3, r * .22), h = r * .7; return `<polygon points="${x0},${y0} ${x0 + w},${y0} ${x0 - w / 2},${y0 + h / 2 + 2}" fill="${BOLT}"/><polygon points="${x0 + w / 2},${y0 + h / 2 - 2} ${x0 - w / 2},${y0 + h / 2 + 2} ${x0 - w / 4},${y0 + h}" fill="${BOLT}"/>`; };
    const moon = (cx, cy, r) => `<circle cx="${cx}" cy="${cy}" r="${r}" fill="#ebe6c8"/><circle cx="${cx + r * .45}" cy="${cy - r * .3}" r="${r * .85}" fill="#000"/>`;
    let g = "";
    switch (cond) {
      case "sunny": g = sun(ix, iy, R * .62, SUN); break;
      case "clear-night": g = moon(ix, iy, R * .75); break;
      case "partlycloudy": g = sun(ix + R * .35, iy - R * .35, R * .42, SUN) + cloud(ix - R * .05, iy + R * .15, R * .9, CLOUD); break;
      case "rainy": g = cloud(ix, iy - R * .2, R, CLOUD) + drops(ix, iy - R * .2, R, 3); break;
      case "pouring": g = cloud(ix, iy - R * .2, R, "#a0aabe") + drops(ix, iy - R * .2, R, 5); break;
      case "lightning": g = cloud(ix, iy - R * .2, R, "#9696af") + bolt(ix, iy - R * .2, R); break;
      case "lightning-rainy": g = cloud(ix, iy - R * .2, R, "#9696af") + drops(ix - R * .35, iy - R * .2, R * .7, 2) + bolt(ix + R * .2, iy - R * .2, R); break;
      case "snowy": case "snowy-rainy": case "hail": g = cloud(ix, iy - R * .2, R, CLOUD) + flakes(ix, iy - R * .2, R); break;
      case "fog": g = cloud(ix, iy - R * .25, R * .9, FOG) + [0, 1].map((k) => `<rect x="${ix - R * .8}" y="${iy + R * (.45 + .25 * k)}" width="${R * 1.6}" height="${Math.max(2, R * .08)}" fill="${FOG}"/>`).join(""); break;
      case "windy": case "windy-variant": g = cloud(ix - R * .25, iy - R * .1, R * .75, CLOUD) + [0, 1, 2].map((k) => `<rect x="${ix - R * .2}" y="${iy + R * (.35 + .28 * k)}" width="${R * (1.2 - .25 * k)}" height="${Math.max(2, R * .09)}" fill="${WIND}"/>`).join(""); break;
      default: g = cloud(ix, iy, R, CLOUD);
    }
    if (haveHi) {
      const fs = sc < .8 ? 32 : sc < 1.3 ? 48 : sc < 1.9 ? 72 : 96;
      const tx = -4 * sc, showL = showLow && lo !== null && lo !== undefined && lo !== "unknown";
      const ty = showL ? -8 * sc : 0;
      g += `<text x="${tx}" y="${ty}" font-size="${fs}" font-family="Roboto, sans-serif" fill="#f0f0f0" dominant-baseline="central">${Math.round(hi)}°</text>`;
      if (showL) g += `<text x="${tx + 2 * sc}" y="${24 * sc}" font-size="${sc < 1.3 ? 22 : 32}" font-family="Roboto, sans-serif" fill="#969eaf" dominant-baseline="central">${Math.round(lo)}°</text>`;
    }
    return g;
  }

  class WallClockLayoutCard extends HTMLElement {
    static getStubConfig() { return { slug: "mini_round_clock_3", name: "Zac", routine: "zac" }; }
    setConfig(config) {
      if (!config || !config.slug) throw new Error("wall-clock-layout-card: `slug` is required (e.g. mini_round_clock_3)");
      this._config = Object.assign({ name: "", img_px: 180 }, config);
      this._face = "grow"; this._sel = "weather"; this._drag = null; this._local = {}; this._err = ""; this._pendingSend = {};
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      this._lastKey = ""; this._render();
    }
    getCardSize() { return 8; }
    set hass(hass) { this._hass = hass; const k = this._key(); if (k !== this._lastKey && !this._drag) { this._lastKey = k; this._render(); } }
    _id(kind, key) { return `${kind}.${this._config.slug}_${key}`; }
    _st(id) { return this._hass && this._hass.states[id]; }
    _numRaw(key, dflt) { const s = this._st(this._id("number", key)); const v = s ? parseFloat(s.state) : NaN; return isNaN(v) ? dflt : v; }
    _num(key, dflt) { const l = this._local[key]; if (l !== undefined) return l; const s = this._st(this._id("number", `layout_${key}`)); const v = s ? parseFloat(s.state) : NaN; return isNaN(v) ? dflt : v; }
    _key() {
      const parts = [this._face, this._sel, this._err];
      for (const k of Object.keys(SLOTS)) parts.push(this._num(k + "_x", 0), this._num(k + "_y", 0), this._num(k + "_size", 100));
      const w = this._st("sensor.wall_clock_weather_today"), h = this._st("sensor.wall_clock_weather_high"), l = this._st("sensor.wall_clock_weather_low");
      parts.push(w && w.state, h && h.state, l && l.state);
      for (const sw of ["weather_symbol", "weather_symbol_shows_the_low", "weather_symbol_on_the_routine_face", "grow_clock_show_time"]) { const s = this._st(this._id("switch", sw)); parts.push(s && s.state); }
      const n = this._st(`sensor.wall_clock_routine_${this._config.routine || "x"}_now`); parts.push(n && n.state);
      const st = this._st(`sensor.wall_clock_routine_${this._config.routine || "x"}_steps`); parts.push(st && st.last_updated);
      return parts.join("|");
    }
    _sw(key) { const s = this._st(this._id("switch", key)); return !s || s.state === "on"; }
    async _set(key, val) {
      // A tap without a drag has no position to send; never call the service
      // without a value (HA answers "required key not provided at 'value'").
      if (val === undefined || val === null || Number.isNaN(Number(val))) return;
      const id = this._id("number", `layout_${key}`);
      if (!this._st(id)) { this._err = `${id} is not there: flash the firmware with the layout slots first.`; return; }
      try { await this._hass.callService("number", "set_value", { entity_id: id, value: val }); this._err = ""; }
      catch (e) { this._err = String(e.message || e); }
    }
    _send(key, val, final) {
      // Throttle to ~5/s while dragging; the final position always goes.
      const now = Date.now(), last = this._pendingSend[key] || 0;
      if (!final && now - last < 200) return;
      this._pendingSend[key] = now; this._set(key, val);
    }
    // ---- render -----------------------------------------------------------
    _els() {
      const wx = this._st("sensor.wall_clock_weather_today"), hi = this._st("sensor.wall_clock_weather_high"), lo = this._st("sensor.wall_clock_weather_low");
      const cond = wx ? wx.state : "partlycloudy", H = hi ? hi.state : 24, L = lo ? lo.state : 12;
      const showLow = this._sw("weather_symbol_shows_the_low");
      const t = new Date(), h12 = (t.getHours() % 12) || 12, tstr = `${h12}:${String(t.getMinutes()).padStart(2, "0")}`;
      const stepsS = this._st(`sensor.wall_clock_routine_${this._config.routine}_steps`);
      const nowS = this._st(`sensor.wall_clock_routine_${this._config.routine}_now`);
      const steps = (stepsS && stepsS.attributes.steps) || [];
      const cur = (nowS && nowS.attributes.step_id && steps.find((s) => s.id === nowS.attributes.step_id)) || steps[0] || { label: "Get dressed", emoji: "👕", hue: 173 };
      const hue = cur.hue ?? 173, col = `hsl(${hue}, 60%, 70%)`;
      const fontNum = (sc) => sc < .8 ? 32 : sc < 1.3 ? 48 : sc < 1.9 ? 72 : 96;
      const fontTxt = (sc) => sc < .85 ? 22 : sc < 1.3 ? 32 : 48;
      const out = [];
      const add = (key, x, y, w, h, inner) => out.push({ key, x, y, w, h, inner });
      const nextBlock = (key, dx, dy, dsz) => {
        const nsc = this._num(key + "_size", dsz) / 100, npx = Math.round(64 * nsc);
        const nxt = steps.filter((x) => x.id !== cur.id)[0] || { label: "Brush teeth", emoji: "🪥", start: "08:20" };
        const nimg = nxt.image ? `<image href="/api/image/serve/${esc(nxt.image)}/original" x="${-npx / 2}" y="${-npx / 2}" width="${npx}" height="${npx}"/>` : `<text font-size="${npx * .7}" text-anchor="middle" dominant-baseline="central">${esc(nxt.emoji || "🕒")}</text>`;
        add(key, this._num(key + "_x", dx), this._num(key + "_y", dy), npx + 16, npx + 64 * nsc, `<text y="${-(npx / 2 + 14)}" font-size="${nsc < 1.4 ? 22 : 32}" fill="#788296" text-anchor="middle" dominant-baseline="central" font-family="Roboto,sans-serif">next</text>${nimg}<text y="${npx / 2 + 14}" font-size="${nsc < 1.4 ? 22 : 32}" fill="#788296" text-anchor="middle" dominant-baseline="central" font-family="Roboto,sans-serif">${esc(String(nxt.start || "").replace(/^0/, ""))}</text>`);
      };
      if (this._face === "grow") {
        // fixed: the eyes, roughly where the firmware's animation box puts them
        out.push({ key: "", x: 180, y: 150, w: 0, h: 0, fixed: true, inner: `<rect x="-88" y="-40" width="64" height="86" rx="18" fill="#3c78ff"/><rect x="24" y="-40" width="64" height="86" rx="18" fill="#3c78ff"/>` });
        if (this._sw("grow_clock_show_time")) { const sc = this._num("grow_time_size", 100) / 100, fs = fontNum(sc); add("grow_time", this._num("grow_time_x", 180), this._num("grow_time_y", 300), fs * 2.4 + 34, fs * 1.1, `<text font-size="${fs}" fill="#3c78ff" text-anchor="middle" dominant-baseline="central" font-family="Roboto,sans-serif">${tstr}</text><text x="${fs * 1.35}" y="${fs * .2}" font-size="${fs < 48 ? 22 : 32}" fill="#3c78ff" font-family="Roboto,sans-serif">${t.getHours() < 12 ? "am" : "pm"}</text>`); }
        if (this._sw("weather_symbol")) { const sc = this._num("weather_size", 100) / 100; add("weather", this._num("weather_x", 180), this._num("weather_y", 50), 150 * sc, 70 * sc, wxSvg(cond, H, L, showLow, sc)); }
        nextBlock("next_other_faces", 292, 262, 100);
      } else if (this._face === "routine") {
        { const sc = this._num("routine_time_size", 100) / 100, fs = sc < .6 ? 22 : sc < .8 ? 32 : fontNum(sc); add("routine_time", this._num("routine_time_x", 180), this._num("routine_time_y", 30), fs * 2.4, fs * 1.1, `<text font-size="${fs}" fill="#788296" text-anchor="middle" dominant-baseline="central" font-family="Roboto,sans-serif">${tstr}</text>`); }
        { const sc = this._num("routine_name_size", 100) / 100, fs = fontTxt(sc); add("routine_name", this._num("routine_name_x", 180), this._num("routine_name_y", 68), Math.max(80, fs * .55 * (cur.label || "").length + 10), fs * 1.1, `<text font-size="${fs}" fill="${col}" text-anchor="middle" dominant-baseline="central" font-family="Roboto,sans-serif">${esc(cur.label)}</text>`); }
        { const pk = Math.min(2, Math.max(.4, this._num("routine_picture_size", 100) / 100)), px = Math.round(this._config.img_px * pk); const img = cur.image ? `<image href="/api/image/serve/${esc(cur.image)}/original" x="${-px / 2}" y="${-px / 2}" width="${px}" height="${px}"/>` : `<text font-size="${px * .7}" text-anchor="middle" dominant-baseline="central">${esc(cur.emoji || "👕")}</text>`; add("routine_picture", this._num("routine_picture_x", 180), this._num("routine_picture_y", 188), px, px, img); }
        { const sc = this._num("routine_minutes_size", 100) / 100, fs = fontTxt(sc); add("routine_minutes", this._num("routine_minutes_x", 180), this._num("routine_minutes_y", 318), fs * 3.2, fs * 1.1, `<text font-size="${fs}" fill="${col}" text-anchor="middle" dominant-baseline="central" font-family="Roboto,sans-serif">12 min</text>`); }
        { const nsc = this._num("routine_next_size", 100) / 100, npx = Math.round(64 * nsc); const nxt = steps.filter((x) => x.id !== cur.id)[0] || { label: "Brush teeth", emoji: "🪥", start: "08:20" };
          const nimg = nxt.image ? `<image href="/api/image/serve/${esc(nxt.image)}/original" x="${-npx / 2}" y="${-npx / 2}" width="${npx}" height="${npx}"/>` : `<text font-size="${npx * .7}" text-anchor="middle" dominant-baseline="central">${esc(nxt.emoji || "🕒")}</text>`;
          add("routine_next", this._num("routine_next_x", 306), this._num("routine_next_y", 188), npx + 16, npx + 64 * nsc, `<text y="${-(npx / 2 + 14)}" font-size="${nsc < 1.4 ? 22 : 32}" fill="#788296" text-anchor="middle" dominant-baseline="central" font-family="Roboto,sans-serif">next</text>${nimg}<text y="${npx / 2 + 14}" font-size="${nsc < 1.4 ? 22 : 32}" fill="#788296" text-anchor="middle" dominant-baseline="central" font-family="Roboto,sans-serif">${esc(String(nxt.start || "").replace(/^0/, ""))}</text>`); }
        if (this._sw("weather_symbol") && this._sw("weather_symbol_on_the_routine_face")) { const sc = this._num("routine_weather_size", 70) / 100; add("routine_weather", this._num("routine_weather_x", 96), this._num("routine_weather_y", 300), 150 * sc, 70 * sc, wxSvg(cond, H, L, showLow, sc)); }
      } else {
        out.push({ key: "", x: 180, y: 180, w: 0, h: 0, fixed: true, inner: `<text font-size="118" fill="#eb9069" text-anchor="middle" dominant-baseline="central" font-family="Roboto,sans-serif">${tstr}</text><text y="78" font-size="22" fill="#9e9e9e" text-anchor="middle" font-family="Roboto,sans-serif">Wed 16/9</text>` });
        if (this._sw("weather_symbol")) { const sc = this._num("weather_size", 100) / 100; add("weather", this._num("weather_x", 180), this._num("weather_y", 50), 150 * sc, 70 * sc, wxSvg(cond, H, L, showLow, sc)); }
        nextBlock("next_other_faces", 292, 262, 100);
      }
      return out;
    }
    _render() {
      if (!this.shadowRoot) return;
      const name = this._config.name || this._config.slug;
      const present = !!this._st(this._id("number", "layout_weather_x"));
      const els = this._els();
      const svgEls = els.map((e) => `<g class="el ${e.key === this._sel ? "sel" : ""} ${e.fixed ? "fixed" : ""}" data-key="${e.key}" transform="translate(${e.x},${e.y})">${e.fixed ? "" : `<rect class="box" x="${-e.w / 2}" y="${-e.h / 2}" width="${e.w}" height="${e.h}" rx="6"/>`}${e.inner}</g>`).join("");
      const slot = SLOTS[this._sel], hasSize = slot && slot.size && slot.faces.includes(this._face);
      const sizeVal = this._num(this._sel + "_size", 100);
      this.shadowRoot.innerHTML = `<style>${css}</style><ha-card>
        <div class="hdr"><h2>${esc(name)}'s screen</h2>
          <span class="seg">${FACES.map((f) => `<button data-face="${f[0]}" class="${this._face === f[0] ? "on" : ""}">${f[1]}</button>`).join("")}</span></div>
        ${present ? "" : `<div class="err">This clock has no layout numbers yet (number.${esc(this._config.slug)}_layout_weather_x). Flash the firmware with the layout slots, then come back.</div>`}
        ${this._err ? `<div class="err">${esc(this._err)}</div>` : ""}
        <div class="wrap">
          <svg viewBox="0 0 360 360" data-svg><circle cx="180" cy="180" r="179" fill="#0a0c12"/><circle cx="180" cy="180" r="179" fill="none" stroke="#333" stroke-width="1"/>${svgEls}</svg>
          <div class="side">
            <div class="muted">Drag a thing on the mock; the clock follows within a second. Tap one to size it. On the grow and clock faces the "next" area only shows from <b>${esc(String(this._numRaw("next_step_shows_from", 60)))} min</b> before the next step (the clock's "Next step shows from" number).</div>
            <label>Selected</label><div>${slot ? esc(slot.label) : "—"}</div>
            ${hasSize ? `<label>Size ${Math.round(sizeVal)}%</label><input type="range" min="40" max="250" step="10" value="${sizeVal}" data-size>` : ""}
            <label>Weather symbol</label>
            <label class="tog"><input type="checkbox" data-sw="weather_symbol" ${this._sw("weather_symbol") ? "checked" : ""}> show</label>
            <label class="tog"><input type="checkbox" data-sw="weather_symbol_shows_the_low" ${this._sw("weather_symbol_shows_the_low") ? "checked" : ""}> with the low</label>
            <label class="tog"><input type="checkbox" data-sw="weather_symbol_on_the_routine_face" ${this._sw("weather_symbol_on_the_routine_face") ? "checked" : ""}> on the routine face</label>
            ${this._config.routine ? `<div class="row"><button class="g" data-try>Show the routine face on the clock (3 min)</button><button class="g" data-stop>Back to normal</button></div>` : ""}
            <div class="row"><button class="g" data-reset>Reset this face to the design</button></div>
          </div>
        </div></ha-card>`;
      this._wire();
    }
    _wire() {
      const r = this.shadowRoot, q = (s) => r.querySelector(s), qa = (s) => Array.from(r.querySelectorAll(s));
      qa("[data-face]").forEach((b) => b.onclick = () => { this._face = b.dataset.face; const first = Object.keys(SLOTS).find((k) => SLOTS[k].faces.includes(this._face)); this._sel = first; this._lastKey = ""; this._render(); });
      qa("[data-sw]").forEach((el) => el.onchange = () => this._hass.callService("switch", el.checked ? "turn_on" : "turn_off", { entity_id: this._id("switch", el.dataset.sw) }));
      const sz = q("[data-size]"); if (sz) { sz.oninput = () => { const v = parseInt(sz.value, 10); this._local[this._sel + "_size"] = v; this._send(this._sel + "_size", v, false); }; sz.onchange = () => { const v = parseInt(sz.value, 10); this._send(this._sel + "_size", v, true); setTimeout(() => { delete this._local[this._sel + "_size"]; this._lastKey = ""; this._render(); }, 800); }; }
      const tr = q("[data-try]"); if (tr) tr.onclick = async () => {
        const st = this._st(`sensor.wall_clock_routine_${this._config.routine}_steps`), steps = (st && st.attributes.steps) || [];
        const step = steps[0] || { id: "layout-demo", label: "Get dressed", start: "08:00", end: "08:20", days: "everyday", hue: 173, image: "", emoji: "👕" };
        try { await this._hass.callService("script", "wall_clock_routine_preview", { clock: this._config.routine, step, seconds: 180 }); this._face = "routine"; this._sel = "routine_picture"; this._lastKey = ""; this._render(); }
        catch (e) { this._err = String(e.message || e); this._render(); }
      };
      const sp = q("[data-stop]"); if (sp) sp.onclick = () => this._hass.callService("script", "wall_clock_routine_preview_stop", { clock: this._config.routine });
      const rs = q("[data-reset]"); if (rs) rs.onclick = async () => {
        const D = { weather: [180, 50, 100], routine_weather: [96, 300, 70], grow_time: [180, 300, 100], routine_time: [180, 30, 100], routine_name: [180, 68, 100], routine_picture: [180, 188, 100], routine_minutes: [180, 318, 100], routine_next: [306, 188, 100], next_other_faces: [292, 262, 100] };
        for (const k of Object.keys(SLOTS)) if (SLOTS[k].faces.includes(this._face)) { const d = D[k]; await this._set(k + "_x", d[0]); await this._set(k + "_y", d[1]); if (d[2] !== undefined) await this._set(k + "_size", d[2]); }
      };
      const svg = q("[data-svg]"); if (!svg) return;
      const pt = (ev) => { const b = svg.getBoundingClientRect(); return { x: (ev.clientX - b.left) * 360 / b.width, y: (ev.clientY - b.top) * 360 / b.height }; };
      qa("g.el:not(.fixed)").forEach((g) => {
        g.addEventListener("pointerdown", (ev) => {
          const key = g.dataset.key; this._sel = key;
          const p = pt(ev); const tf = g.getAttribute("transform").match(/translate\(([-\d.]+),([-\d.]+)\)/);
          this._drag = { key, g, ox: parseFloat(tf[1]) - p.x, oy: parseFloat(tf[2]) - p.y };
          g.setPointerCapture(ev.pointerId); ev.preventDefault();
          qa("g.el").forEach((x) => x.classList.toggle("sel", x === g));
        });
        g.addEventListener("pointermove", (ev) => {
          if (!this._drag || this._drag.g !== g) return;
          const p = pt(ev); let x = clamp(Math.round((p.x + this._drag.ox) / 2) * 2, 0, 360), y = clamp(Math.round((p.y + this._drag.oy) / 2) * 2, 0, 360);
          g.setAttribute("transform", `translate(${x},${y})`);
          this._local[this._drag.key + "_x"] = x; this._local[this._drag.key + "_y"] = y;
          this._send(this._drag.key + "_x", x, false); this._send(this._drag.key + "_y", y, false);
        });
        const up = (ev) => {
          if (!this._drag || this._drag.g !== g) return;
          const k = this._drag.key; this._drag = null;
          const x = this._local[k + "_x"], y = this._local[k + "_y"];
          if (x !== undefined && y !== undefined) {   // it moved; a plain tap only selects
            this._send(k + "_x", x, true); this._send(k + "_y", y, true);
            setTimeout(() => { delete this._local[k + "_x"]; delete this._local[k + "_y"]; this._lastKey = ""; this._render(); }, 900);
          } else {
            this._lastKey = ""; this._render();
          }
        };
        g.addEventListener("pointerup", up); g.addEventListener("pointercancel", up);
      });
    }
  }
  customElements.define("wall-clock-layout-card", WallClockLayoutCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "wall-clock-layout-card", name: "Wall clock layout", description: "Drag the time, the weather symbol and the routine picture around a mock of the clock; the real clock follows live." });
})();
