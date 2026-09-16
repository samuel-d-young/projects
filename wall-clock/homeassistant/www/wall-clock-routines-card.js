/* wall-clock-routines-card.js — program a child's picture routine on a wall clock.
 *
 *   type: custom:wall-clock-routines-card
 *   clock: zac            # the routine slug (matches routine_slug in the clock's yaml)
 *   name: Zac             # optional, for the header
 *   copy_from: [jake, third]   # optional: offer "copy X's routine" / "copy X's face times" per clock listed
 *   img_px: 180           # optional: picture size; must equal routine_img_px in the firmware
 *
 * What it does, and nothing else:
 *   - lists the steps in sensor.wall_clock_routine_<clock>_steps (attribute `steps`)
 *   - adds / edits / deletes a step: name, start, finish, days, colour, picture
 *   - a picture is an emoji drawn onto a canvas OR a photo cropped to a circle,
 *     both uploaded as a img_px-square JPEG (q 0.92) to HA's image store
 *     (POST /api/image/upload), which the clock later fetches at
 *     /api/image/serve/<id>/original with no auth. JPEG and not PNG because the
 *     clock's PNG decoder needs 47 kB of contiguous heap it does not have; JPEG
 *     needs about 23 kB. HA's store takes jpeg/png/gif only.
 *   - saves through script.wall_clock_routine_save (one event, one sensor update)
 *   - "Try it" shows a step on the clock for two minutes via script.wall_clock_routine_preview
 *   - while a step is on: Done (ends it early), +5 min, Next now; all ride on the
 *     same preview event, so nothing here touches the saved schedule
 *
 * Plain custom element, no build step, no framework. Talks to HA only through the
 * `hass` object the frontend hands every card (callService, callWS, fetchWithAuth).
 */
(function () {
  const EMOJIS = [
    "👕", "🎒", "🪥", "🚿", "🛁", "🧼", "🚽", "🥣", "🍎", "🍽️", "🥪", "💧",
    "👟", "🧦", "🧥", "🧢", "📚", "✏️", "🎨", "🧩", "🧸", "🎮", "📺", "🎵",
    "🐕", "🧹", "🛏️", "😴", "🌙", "⭐", "☀️", "⏰", "🚗", "🏫", "⚽", "🚲",
  ];
  const COLOURS = [
    { hue: 173, name: "teal" }, { hue: 120, name: "green" }, { hue: 50, name: "yellow" },
    { hue: 25, name: "orange" }, { hue: 0, name: "red" }, { hue: 320, name: "pink" },
    { hue: 275, name: "purple" }, { hue: 215, name: "blue" },
  ];
  const DAYS = [["everyday", "Every day"], ["weekdays", "School days"], ["weekends", "Weekends"]];
  const FACES = [["grow", "Grow face"], ["clock", "Clock face"]];
  const FACE_ICON = { grow: "🙂", clock: "🕘" };

  const css = `
    :host { display: block; }
    ha-card { padding: 12px 16px 16px; }
    .hdr { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
    .hdr h2 { font-size: 1.25em; margin: 0; flex: 1 1 auto; font-weight: 500; }
    .now { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; padding: 8px 12px; border-radius: 10px; background: var(--secondary-background-color, rgba(127,127,127,.12)); font-size: .95em; margin-bottom: 10px; }
    .now b { color: var(--primary-color); }
    .now .txt { flex: 1 1 220px; }
    .now .acts { display: flex; flex-wrap: wrap; gap: 6px; }
    .steps { display: flex; flex-direction: column; gap: 6px; }
    .step { display: grid; grid-template-columns: 52px 1fr auto; gap: 10px; align-items: center; padding: 6px 8px; border-radius: 10px; border: 1px solid var(--divider-color, rgba(127,127,127,.3)); }
    .step.on { border-color: var(--primary-color); box-shadow: 0 0 0 1px var(--primary-color) inset; }
    .thumb { width: 52px; height: 52px; border-radius: 12px; background: #000; display: grid; place-items: center; font-size: 34px; line-height: 1; overflow: hidden; }
    .thumb img { width: 52px; height: 52px; object-fit: cover; display: block; }
    .meta .l { font-weight: 500; }
    .meta .t { color: var(--secondary-text-color); font-size: .9em; }
    .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
    .acts { display: flex; gap: 2px; }
    button { font: inherit; cursor: pointer; border-radius: 8px; border: 1px solid var(--divider-color, rgba(127,127,127,.35)); background: var(--card-background-color, transparent); color: var(--primary-text-color); padding: 6px 10px; }
    button.p { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    button.i { padding: 4px 7px; border: none; font-size: 1.05em; background: transparent; }
    button:disabled { opacity: .5; cursor: default; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 8px 0; }
    .row label { font-size: .85em; color: var(--secondary-text-color); display: block; margin-bottom: 2px; }
    input[type=text], input[type=time] { font: inherit; padding: 6px 8px; border-radius: 8px; border: 1px solid var(--divider-color, rgba(127,127,127,.35)); background: var(--card-background-color); color: var(--primary-text-color); }
    input[type=text] { width: 100%; box-sizing: border-box; }
    .seg button { border-radius: 0; }
    .seg button:first-child { border-radius: 8px 0 0 8px; } .seg button:last-child { border-radius: 0 8px 8px 0; }
    .seg button.on { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    .sw { display: flex; gap: 6px; flex-wrap: wrap; }
    .sw button { width: 30px; height: 30px; padding: 0; border-radius: 50%; border: 2px solid transparent; }
    .sw button.on { border-color: var(--primary-text-color); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(44px, 1fr)); gap: 4px; }
    .grid button { font-size: 26px; padding: 4px 0; line-height: 1.2; }
    .grid button.on { background: var(--primary-color); }
    .pv { display: flex; gap: 12px; align-items: center; }
    .pv canvas { width: 90px; height: 90px; border-radius: 12px; background: #000; }
    .err { color: var(--error-color, #d33); font-size: .9em; }
    .muted { color: var(--secondary-text-color); font-size: .9em; }
    .tabs button.on { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
    .tog { display: inline-flex; align-items: center; gap: 6px; font-size: .9em; cursor: pointer; }
    .tog input { width: 18px; height: 18px; }
    .fh { display: flex; align-items: baseline; gap: 10px; margin: 16px 0 6px; }
    .fh h3 { font-size: 1.05em; font-weight: 500; margin: 0; }
  `;

  const pad = (n) => String(n).padStart(2, "0");
  const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const hsl = (h) => `hsl(${h}, 90%, 55%)`;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const mins = (hhmm) => { const [h, m] = String(hhmm || "0:0").split(":").map((x) => parseInt(x, 10) || 0); return h * 60 + m; };

  async function emojiPng(emoji, px) {
    const c = document.createElement("canvas"); c.width = c.height = px;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, px, px);
    ctx.font = `${Math.round(px * 0.76)}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji","Twemoji Mozilla",sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(emoji, px / 2, px / 2 + px * 0.04);
    return new Promise((r) => c.toBlob(r, "image/jpeg", 0.92));
  }
  async function photoPng(file, px) {
    let bmp;
    try { bmp = await createImageBitmap(file, { imageOrientation: "from-image" }); }
    catch (e) { bmp = await createImageBitmap(file); }
    const s = Math.min(bmp.width, bmp.height), sx = (bmp.width - s) / 2, sy = (bmp.height - s) / 2;
    const c = document.createElement("canvas"); c.width = c.height = px;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, px, px);
    ctx.save(); ctx.beginPath(); ctx.arc(px / 2, px / 2, px / 2 - 1, 0, Math.PI * 2); ctx.clip();
    ctx.drawImage(bmp, sx, sy, s, s, 0, 0, px, px); ctx.restore();
    bmp.close && bmp.close();
    return new Promise((r) => c.toBlob(r, "image/jpeg", 0.92));
  }

  class WallClockRoutinesCard extends HTMLElement {
    static getStubConfig() { return { clock: "zac", name: "Zac" }; }
    setConfig(config) {
      if (!config || !config.clock) throw new Error("wall-clock-routines-card: `clock` is required (the routine slug, e.g. zac)");
      this._config = Object.assign({ name: "", img_px: 180 }, config);
      this._edit = null;      // the step being edited (a copy), or null
      this._fedit = null;     // the face window being edited, or null
      this._busy = "";
      this._err = "";
      this._pending = null;   // {blob, emoji} picture waiting for upload
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      this._lastKey = "";
      this._render();
    }
    getCardSize() { return 6; }
    set hass(hass) {
      this._hass = hass;
      const k = this._key();
      if (k !== this._lastKey) { this._lastKey = k; this._render(); }
    }
    // ---- state ------------------------------------------------------------
    get _ids() {
      const c = this._config.clock;
      return { steps: `sensor.wall_clock_routine_${c}_steps`, now: `sensor.wall_clock_routine_${c}_now`,
               on: `input_boolean.wall_clock_routine_${c}`, hol: "input_boolean.wall_clock_school_holidays",
               fwin: `sensor.wall_clock_face_${c}_windows`, fnow: `sensor.wall_clock_face_${c}_now`,
               pv: `sensor.wall_clock_routine_${c}_preview` };
    }
    _st(id) { return this._hass && this._hass.states[id]; }
    _steps() { const s = this._st(this._ids.steps); const l = (s && s.attributes.steps) || []; return Array.isArray(l) ? l.slice().sort((a, b) => mins(a.start) - mins(b.start)) : []; }
    _others() { const c = this._config.copy_from; return (Array.isArray(c) ? c : c ? [c] : []).filter((o) => o && o !== this._config.clock); }
    _label(slug) { return slug === "third" ? "the Third Clock" : slug.charAt(0).toUpperCase() + slug.slice(1); }
    _faces() { const s = this._st(this._ids.fwin); const l = (s && s.attributes.windows) || []; return Array.isArray(l) ? l.slice().sort((a, b) => mins(a.start) - mins(b.start)) : []; }
    _key() {
      const s = this._st(this._ids.steps), n = this._st(this._ids.now), o = this._st(this._ids.on), h = this._st(this._ids.hol);
      const fw = this._st(this._ids.fwin), fn = this._st(this._ids.fnow), pv = this._st(this._ids.pv);
      return [s && s.last_updated, n && n.state, n && n.attributes.step_id, n && n.attributes.end_s, o && o.state, h && h.state, fw && fw.last_updated, fn && fn.state, pv && pv.state, this._edit ? "e" : "", this._fedit ? "f" : "", this._busy, this._err].join("|");
    }
    // ---- HA calls ---------------------------------------------------------
    async _save(steps) {
      await this._hass.callService("script", "wall_clock_routine_save", { clock: this._config.clock, steps });
    }
    async _preview(step, seconds) {
      await this._hass.callService("script", "wall_clock_routine_preview", { clock: this._config.clock, step, seconds: seconds || 120 });
    }
    async _upload(blob) {
      const fd = new FormData(); fd.append("file", blob, "routine.jpg");
      const r = await this._hass.fetchWithAuth("/api/image/upload", { method: "POST", body: fd });
      if (!r.ok) throw new Error(`upload failed: HTTP ${r.status}`);
      const j = await r.json();
      return j.id;
    }
    // ---- render -----------------------------------------------------------
    _render() {
      if (!this.shadowRoot) return;
      const name = this._config.name || this._config.clock;
      const on = this._st(this._ids.on), hol = this._st(this._ids.hol), now = this._st(this._ids.now);
      const missing = !this._st(this._ids.steps) && !now;
      let body;
      if (missing) {
        body = `<div class="err">Entities for <code>${esc(this._config.clock)}</code> are not there yet: install packages/wall_clock_routines.yaml (tools/install_routines.py) and reload templates.</div>`;
      } else if (this._edit) {
        body = this._renderEditor();
      } else {
        body = this._renderList();
      }
      const nowLine = (() => {
        if (!now) return "";
        const btn = (d, t, cls) => `<button class="${cls || ""}" data-${d} ${this._busy ? "disabled" : ""}>${t}</button>`;
        if (now.state && now.state !== "none" && now.state !== "unknown") {
          const e = now.attributes.end_s || 0, pv = now.attributes.preview;
          const cur = this._steps().find((x) => x.id === now.attributes.step_id);
          const nx = this._next();
          // Parent controls: Done ends the step early (nothing shows until its
          // scheduled end), +5 min refills the ring for what is left plus five,
          // Next now jumps to the following step until ITS scheduled end.
          const acts = pv ? btn("back", "Back to schedule")
            : (cur ? btn("done", "Done ✓", "p") + btn("more", "+5 min") + (nx ? btn("nextnow", "Next now ▶") : "") : "");
          return `<div class="now"><span class="txt">Now on the clock: <b>${esc(now.state)}</b> until ${pad(Math.floor(e / 3600))}:${pad(Math.floor(e / 60) % 60)}${pv ? " <span class=muted>(preview)</span>" : ""}</span>
            <span class="acts">${acts}</span></div>`;
        }
        const pvs = this._st(this._ids.pv), skip = pvs && pvs.attributes.step && pvs.attributes.step.skip && (pvs.attributes.until || 0) > Date.now() / 1000;
        const nx = this._next();
        if (skip) return `<div class="now"><span class="txt">Marked <b>done</b> early. ${nx ? `Next: <b>${esc(nx.label)}</b> at ${esc(nx.start)}.` : ""}</span><span class="acts">${btn("back", "Undo")}</span></div>`;
        return `<div class="now"><span class="txt">Nothing on right now.${nx ? ` Next: <b>${esc(nx.label)}</b> at ${esc(nx.start)}.` : ""}</span></div>`;
      })();
      this.shadowRoot.innerHTML = `<style>${css}</style><ha-card>
        <div class="hdr"><h2>${esc(name)}'s routine</h2>
          <label class="tog"><input type="checkbox" data-tog="${this._ids.on}" ${on && on.state === "on" ? "checked" : ""}> On</label>
          <label class="tog"><input type="checkbox" data-tog="${this._ids.hol}" ${hol && hol.state === "on" ? "checked" : ""}> School holidays</label>
        </div>
        ${nowLine}
        ${this._err ? `<div class="err">${esc(this._err)}</div>` : ""}
        ${body}
      </ha-card>`;
      this._wire();
    }
    _next() {
      const t = new Date(), m = t.getHours() * 60 + t.getMinutes();
      const hol = this._st(this._ids.hol), weekend = (hol && hol.state === "on") || t.getDay() === 0 || t.getDay() === 6;
      return this._steps().find((s) => mins(s.start) > m && (s.days === "everyday" || !s.days || (s.days === "weekdays" && !weekend) || (s.days === "weekends" && weekend)));
    }
    _renderList() {
      const now = this._st(this._ids.now), curId = now && now.attributes.step_id;
      const rows = this._steps().map((s) => `
        <div class="step ${s.id === curId ? "on" : ""}" data-id="${esc(s.id)}">
          <div class="thumb">${s.image ? `<img src="/api/image/serve/${esc(s.image)}/256x256" alt="">` : esc(s.emoji || "🕒")}</div>
          <div class="meta"><div class="l"><span class="dot" style="background:${hsl(s.hue ?? 173)}"></span>${esc(s.label)}</div>
            <div class="t">${esc(s.start)} – ${esc(s.end)} · ${esc((DAYS.find((d) => d[0] === s.days) || DAYS[0])[1])}</div></div>
          <div class="acts"><button class="i" data-try="${esc(s.id)}" title="Try it on the clock for 2 minutes">▶</button><button class="i" data-edit="${esc(s.id)}" title="Edit">✎</button><button class="i" data-del="${esc(s.id)}" title="Delete">✕</button></div>
        </div>`).join("");
      const copyBtns = this._others().map((o) => { const st = ((this._st(`sensor.wall_clock_routine_${o}_steps`) || {}).attributes || {}).steps; return Array.isArray(st) && st.length ? `<button data-copy="${esc(o)}">Copy ${esc(this._label(o))}'s routine</button>` : ""; }).join(" ");
      return `<div class="steps">${rows || `<div class="muted">No steps yet. Add the first one: what should happen, and when.</div>`}</div>
        <div class="row" style="margin-top:12px">
          <button class="p" data-add>＋ Add a step</button>
          ${copyBtns}
          ${this._busy ? `<span class="muted">${esc(this._busy)}</span>` : ""}
        </div>
        ${this._renderFaces()}`;
    }
    // ---- faces through the day -------------------------------------------
    _renderFaces() {
      const fnow = this._st(this._ids.fnow);
      if (!this._st(this._ids.fwin) && !fnow) return "";
      const nowTxt = fnow ? (fnow.state === "grow" ? "Grow face" : fnow.state === "clock" ? "Clock face" : "the clock decides (auto)") : "";
      const wins = this._faces();
      const rows = wins.map((w) => `
        <div class="step ${fnow && fnow.attributes.window_id === w.id ? "on" : ""}">
          <div class="thumb" style="font-size:28px">${FACE_ICON[w.face] || FACE_ICON.clock}</div>
          <div class="meta"><div class="l">${esc((FACES.find((f) => f[0] === w.face) || FACES[1])[1])}</div>
            <div class="t">${esc(w.start)} \u2013 ${esc(w.end)}${mins(w.end) <= mins(w.start) ? " (over midnight)" : ""} \u00b7 ${esc((DAYS.find((d) => d[0] === w.days) || DAYS[0])[1])}</div></div>
          <div class="acts"><button class="i" data-fedit="${esc(w.id)}" title="Edit">\u270E</button><button class="i" data-fdel="${esc(w.id)}" title="Delete">\u2715</button></div>
        </div>`).join("");
      let editor = "";
      if (this._fedit) {
        const e = this._fedit;
        editor = `<div class="editor" style="margin-top:8px">
          <div class="row"><div><label>Face</label><span class="seg">${FACES.map((f) => `<button data-fface="${f[0]}" class="${e.face === f[0] ? "on" : ""}">${f[1]}</button>`).join("")}</span></div></div>
          <div class="row">
            <div><label>From</label><input type="time" data-ff="start" value="${esc(e.start)}"></div>
            <div><label>Until</label><input type="time" data-ff="end" value="${esc(e.end)}"></div>
            <div><label>Days</label><span class="seg">${DAYS.map((d) => `<button data-fdays="${d[0]}" class="${(e.days || "everyday") === d[0] ? "on" : ""}">${d[1]}</button>`).join("")}</span></div>
          </div>
          <div class="muted">"Until" earlier than "From" runs over midnight (for example Grow face 18:30 until 07:30).</div>
          <div class="row"><button class="p" data-fsave ${this._busy ? "disabled" : ""}>Save</button><button data-fcancel>Cancel</button></div>
        </div>`;
      }
      return `<div class="fh"><h3>Faces through the day</h3><span class="muted">Now: ${esc(nowTxt)}</span></div>
        <div class="steps">${rows || `<div class="muted">No times set: the clock decides by itself (grow face on the grow schedule, the ordinary clock by day). Add a time to say which face shows when. A routine step always takes over.</div>`}</div>
        ${editor || `<div class="row"><button data-fadd>\uFF0B Add a time</button>${this._others().map((o) => { const w = ((this._st(`sensor.wall_clock_face_${o}_windows`) || {}).attributes || {}).windows; return Array.isArray(w) && w.length ? ` <button data-fcopy="${esc(o)}">Copy ${esc(this._label(o))}'s face times</button>` : ""; }).join("")}</div>`}`;
    }
    async _commitFace() {
      const e = this._fedit; if (!e) return;
      if (!/^\d{1,2}:\d{2}$/.test(e.start) || !/^\d{1,2}:\d{2}$/.test(e.end)) { this._err = "From and until need a time."; this._render(); return; }
      if (mins(e.start) === mins(e.end)) { this._err = "From and until are the same time."; this._render(); return; }
      try {
        const w = { id: e.id, face: e.face || "grow", start: e.start, end: e.end, days: e.days || "everyday" };
        this._busy = "Saving\u2026"; this._render();
        await this._hass.callService("script", "wall_clock_face_save", { clock: this._config.clock, windows: this._faces().filter((x) => x.id !== w.id).concat([w]) });
        this._fedit = null; this._err = "";
      } catch (err) { this._err = String(err.message || err); }
      this._busy = ""; this._render();
    }
    _renderEditor() {
      const e = this._edit, pic = this._pending;
      const tab = e._tab || (e.image && !e.emoji ? "photo" : "emoji");
      return `<div class="editor">
        <div class="row"><div style="flex:1 1 220px"><label>What</label><input type="text" data-f="label" value="${esc(e.label)}" placeholder="Get dressed" maxlength="24"></div></div>
        <div class="row">
          <div><label>Start</label><input type="time" data-f="start" value="${esc(e.start)}"></div>
          <div><label>Finish</label><input type="time" data-f="end" value="${esc(e.end)}"></div>
          <div><label>Days</label><span class="seg">${DAYS.map((d) => `<button data-days="${d[0]}" class="${(e.days || "everyday") === d[0] ? "on" : ""}">${d[1]}</button>`).join("")}</span></div>
        </div>
        <div class="row"><div><label>Ring colour</label><span class="sw">${COLOURS.map((c) => `<button data-hue="${c.hue}" class="${(e.hue ?? 173) === c.hue ? "on" : ""}" style="background:${hsl(c.hue)}" title="${c.name}"></button>`).join("")}</span></div></div>
        <div class="row"><label>Picture</label><span class="tabs"><button data-tab="emoji" class="${tab === "emoji" ? "on" : ""}">Emoji</button><button data-tab="photo" class="${tab === "photo" ? "on" : ""}">Photo</button></span></div>
        ${tab === "emoji" ? `<div class="grid">${EMOJIS.map((x) => `<button data-emoji="${x}" class="${(pic ? pic.emoji : e.emoji) === x ? "on" : ""}">${x}</button>`).join("")}</div>
          <div class="row"><div style="flex:1 1 200px"><label>…or type any emoji</label><input type="text" data-f="anyemoji" value="" placeholder="🧃" maxlength="8"></div></div>`
        : `<div class="row"><input type="file" accept="image/*" data-file></div><div class="muted">Cropped to a circle, ${this._config.img_px}px, black background.</div>`}
        <div class="pv" style="margin-top:8px"><canvas width="${this._config.img_px}" height="${this._config.img_px}" data-pv></canvas>
          <div class="muted">${pic ? "New picture ready to upload." : e.image ? "Keeping the current picture." : "Pick an emoji or a photo."}</div></div>
        <div class="row" style="margin-top:12px">
          <button class="p" data-save ${this._busy ? "disabled" : ""}>Save</button>
          <button data-tryedit ${this._busy ? "disabled" : ""}>Try it on the clock</button>
          <button data-cancel>Cancel</button>
          ${this._busy ? `<span class="muted">${esc(this._busy)}</span>` : ""}
        </div>
      </div>`;
    }
    // ---- events -----------------------------------------------------------
    _wire() {
      const r = this.shadowRoot, q = (s) => r.querySelector(s), qa = (s) => Array.from(r.querySelectorAll(s));
      qa("[data-tog]").forEach((el) => el.addEventListener("change", (ev) => {
        const id = ev.target.dataset.tog;
        this._hass.callService("input_boolean", ev.target.checked ? "turn_on" : "turn_off", { entity_id: id });
      }));
      // parent controls on the Now line
      const secsNow = () => { const t = new Date(); return t.getHours() * 3600 + t.getMinutes() * 60 + t.getSeconds(); };
      const act = async (label, fn) => { try { this._busy = label; this._render(); await fn(); this._err = ""; } catch (e) { this._err = String(e.message || e); } this._busy = ""; this._render(); };
      const nowS = this._st(this._ids.now), curStep = nowS && this._steps().find((x) => x.id === nowS.attributes.step_id);
      const remaining = () => Math.max(5, (nowS && nowS.attributes.end_s || 0) - secsNow());
      const dn = q("[data-done]"); if (dn) dn.onclick = () => act("Marking done…", () => this._preview({ id: "done", skip: true, label: "done" }, remaining()));
      const mo = q("[data-more]"); if (mo) mo.onclick = () => act("Adding five minutes…", () => this._preview(curStep, remaining() + 300));
      const nn = q("[data-nextnow]"); if (nn) nn.onclick = () => { const nx = this._next(); if (!nx) return; act("Starting the next step…", () => this._preview(nx, Math.max(60, mins(nx.end) * 60 - secsNow()))); };
      const bk = q("[data-back]"); if (bk) bk.onclick = () => act("Back to the schedule…", () => this._hass.callService("script", "wall_clock_routine_preview_stop", { clock: this._config.clock }));
      const add = q("[data-add]"); if (add) add.onclick = () => { this._edit = { id: uid(), label: "", start: "08:00", end: "08:20", days: "weekdays", hue: 173, image: "", emoji: "" }; this._pending = null; this._err = ""; this._render(); };
      qa("[data-edit]").forEach((b) => b.onclick = () => { const s = this._steps().find((x) => x.id === b.dataset.edit); if (s) { this._edit = Object.assign({}, s); this._pending = null; this._err = ""; this._render(); this._drawPreview(); } });
      qa("[data-del]").forEach((b) => b.onclick = async () => {
        const s = this._steps().find((x) => x.id === b.dataset.del); if (!s) return;
        if (!confirm(`Delete "${s.label}"?`)) return;
        try { this._busy = "Deleting…"; this._render(); await this._save(this._steps().filter((x) => x.id !== s.id)); }
        catch (e) { this._err = String(e.message || e); }
        this._busy = ""; this._render();
      });
      qa("[data-try]").forEach((b) => b.onclick = async () => {
        const s = this._steps().find((x) => x.id === b.dataset.try); if (!s) return;
        try { this._busy = "Sending to the clock…"; this._render(); await this._preview(s, 120); this._err = ""; }
        catch (e) { this._err = String(e.message || e); }
        this._busy = ""; this._render();
      });
      qa("[data-copy]").forEach((cp) => cp.onclick = async () => {
        const other = cp.dataset.copy;
        const src = ((this._st(`sensor.wall_clock_routine_${other}_steps`) || {}).attributes || {}).steps || [];
        if (!confirm(`Replace ${this._config.name || this._config.clock}'s steps with ${this._label(other)}'s ${src.length}?`)) return;
        try { this._busy = "Copying…"; this._render(); await this._save(src.map((s) => Object.assign({}, s, { id: uid() }))); }
        catch (e) { this._err = String(e.message || e); }
        this._busy = ""; this._render();
      });
      qa("[data-fcopy]").forEach((cp) => cp.onclick = async () => {
        const other = cp.dataset.fcopy;
        const src = ((this._st(`sensor.wall_clock_face_${other}_windows`) || {}).attributes || {}).windows || [];
        if (!confirm(`Replace ${this._config.name || this._config.clock}'s face times with ${this._label(other)}'s ${src.length}?`)) return;
        try { this._busy = "Copying…"; this._render(); await this._hass.callService("script", "wall_clock_face_save", { clock: this._config.clock, windows: src.map((w) => Object.assign({}, w, { id: uid() })) }); }
        catch (e) { this._err = String(e.message || e); }
        this._busy = ""; this._render();
      });
      // faces through the day
      const fa = q("[data-fadd]"); if (fa) fa.onclick = () => { this._fedit = { id: uid(), face: "grow", start: "18:30", end: "07:30", days: "everyday" }; this._err = ""; this._render(); };
      qa("[data-fedit]").forEach((b) => b.onclick = () => { const w = this._faces().find((x) => x.id === b.dataset.fedit); if (w) { this._fedit = Object.assign({}, w); this._err = ""; this._render(); } });
      qa("[data-fdel]").forEach((b) => b.onclick = async () => {
        const w = this._faces().find((x) => x.id === b.dataset.fdel); if (!w || !confirm(`Delete this ${w.face} face time?`)) return;
        try { this._busy = "Deleting\u2026"; this._render(); await this._hass.callService("script", "wall_clock_face_save", { clock: this._config.clock, windows: this._faces().filter((x) => x.id !== w.id) }); }
        catch (err) { this._err = String(err.message || err); }
        this._busy = ""; this._render();
      });
      if (this._fedit) {
        const fe = this._fedit;
        qa("[data-ff]").forEach((el) => el.addEventListener("input", (ev) => { fe[ev.target.dataset.ff] = ev.target.value; }));
        qa("[data-fface]").forEach((b) => b.onclick = () => { fe.face = b.dataset.fface; this._render(); });
        qa("[data-fdays]").forEach((b) => b.onclick = () => { fe.days = b.dataset.fdays; this._render(); });
        const fs = q("[data-fsave]"); if (fs) fs.onclick = () => this._commitFace();
        const fc = q("[data-fcancel]"); if (fc) fc.onclick = () => { this._fedit = null; this._err = ""; this._render(); };
      }
      if (!this._edit) return;
      const e = this._edit;
      qa("[data-f]").forEach((el) => el.addEventListener("input", (ev) => {
        const f = ev.target.dataset.f;
        if (f === "anyemoji") { const v = ev.target.value.trim(); if (v) this._setEmoji(v); return; }
        e[f] = ev.target.value;
      }));
      qa("[data-days]").forEach((b) => b.onclick = () => { e.days = b.dataset.days; this._render(); this._drawPreview(); });
      qa("[data-hue]").forEach((b) => b.onclick = () => { e.hue = parseInt(b.dataset.hue, 10); this._render(); this._drawPreview(); });
      qa("[data-tab]").forEach((b) => b.onclick = () => { e._tab = b.dataset.tab; this._render(); this._drawPreview(); });
      qa("[data-emoji]").forEach((b) => b.onclick = () => this._setEmoji(b.dataset.emoji));
      const f = q("[data-file]"); if (f) f.onchange = async () => {
        const file = f.files && f.files[0]; if (!file) return;
        try { const blob = await photoPng(file, this._config.img_px); this._pending = { blob, emoji: "" }; this._err = ""; }
        catch (err) { this._err = "Could not read that photo: " + (err.message || err); }
        this._render(); this._drawPreview();
      };
      const sv = q("[data-save]"); if (sv) sv.onclick = () => this._commit(false);
      const te = q("[data-tryedit]"); if (te) te.onclick = () => this._commit(true);
      const cn = q("[data-cancel]"); if (cn) cn.onclick = () => { this._edit = null; this._pending = null; this._err = ""; this._render(); };
      this._drawPreview();
    }
    async _setEmoji(emoji) {
      try { const blob = await emojiPng(emoji, this._config.img_px); this._pending = { blob, emoji }; this._err = ""; }
      catch (err) { this._err = "Could not draw that emoji: " + (err.message || err); }
      this._render(); this._drawPreview();
    }
    _drawPreview() {
      const c = this.shadowRoot.querySelector("[data-pv]"); if (!c) return;
      const ctx = c.getContext("2d"); ctx.fillStyle = "#000"; ctx.fillRect(0, 0, c.width, c.height);
      const e = this._edit;
      const src = this._pending ? URL.createObjectURL(this._pending.blob) : e.image ? `/api/image/serve/${e.image}/original` : "";
      if (!src) return;
      const im = new Image();
      im.onload = () => { ctx.drawImage(im, 0, 0, c.width, c.height); if (this._pending) URL.revokeObjectURL(src); };
      im.src = src;
    }
    _validate(e) {
      if (!e.label || !e.label.trim()) return "Give the step a name.";
      if (!/^\d{1,2}:\d{2}$/.test(e.start) || !/^\d{1,2}:\d{2}$/.test(e.end)) return "Start and finish need a time.";
      if (mins(e.end) <= mins(e.start)) return "Finish has to be after start (same day).";
      if (!this._pending && !e.image) return "Pick an emoji or a photo.";
      return "";
    }
    async _commit(tryToo) {
      const e = this._edit; if (!e) return;
      const v = this._validate(e); if (v) { this._err = v; this._render(); this._drawPreview(); return; }
      try {
        if (this._pending) {
          this._busy = "Uploading the picture…"; this._render();
          e.image = await this._upload(this._pending.blob);
          e.emoji = this._pending.emoji || "";
          this._pending = null;
        }
        const step = { id: e.id, label: e.label.trim(), start: e.start, end: e.end, days: e.days || "everyday", hue: e.hue ?? 173, image: e.image, emoji: e.emoji || "" };
        const others = this._steps().filter((x) => x.id !== step.id);
        this._busy = "Saving…"; this._render();
        await this._save(others.concat([step]));
        if (tryToo) { this._busy = "Sending to the clock…"; this._render(); await this._preview(step, 120); }
        this._edit = null; this._err = "";
      } catch (err) {
        this._err = String(err.message || err);
      }
      this._busy = ""; this._render();
    }
  }
  customElements.define("wall-clock-routines-card", WallClockRoutinesCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: "wall-clock-routines-card", name: "Wall clock routines", description: "Program a child's picture routine (emoji or photo per step) on a wall clock." });
})();
