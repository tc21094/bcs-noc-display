// BCS NOC gesture agent: drawn into the dashboard page by kiosk-launch (Chrome DevTools pipe),
// fed ~30 times a second with the camera gesture state from bcs-gesture.
//   window.__bcsGesture(state) -> [viewport width, height]
// Draws the cursor, hold rings, short messages, a camera dot and (on request) a small camera
// preview, all in its own top-layer layer that ignores the mouse. Zoom is a CSS transform on the
// page, anchored at the cursor; Chrome's hit testing follows it, so hover lands on what you see.
(function () {
  "use strict";
  if (window.__bcsGesture) return;
  var host = document.createElement("div");
  host.setAttribute("style", "all:initial;position:fixed;inset:0;z-index:2147483647;pointer-events:none;" +
    "border:0;margin:0;padding:0;width:100vw;height:100vh;max-width:none;max-height:none;background:transparent;overflow:visible");
  try { host.popover = "manual"; } catch (e) {}
  var root = host.attachShadow({ mode: "closed" });
  var cv = document.createElement("canvas");
  cv.setAttribute("style", "position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none");
  var pv = document.createElement("img");
  pv.setAttribute("style", "position:fixed;right:18px;bottom:18px;width:min(30vw,640px);height:auto;aspect-ratio:16/9;border-radius:10px;" +
    "box-shadow:0 0 0 2px rgba(120,180,255,.7),0 8px 30px rgba(0,0,0,.6);display:none;pointer-events:none");
  root.appendChild(cv); root.appendChild(pv);
  var c = cv.getContext("2d");
  function mount() {
    if (!host.isConnected) document.documentElement.appendChild(host);
    try { if (host.hidePopover) host.hidePopover(); } catch (e) {}
    try { if (host.showPopover) host.showPopover(); } catch (e) {}   // last in = on top of the interlude / blanket
  }
  mount();

  var S = { on: false, x: 0.5, y: 0.5, hold: null, pinch: false, cam: true, t: 0, draw: false, pen: false, spot: false, help: false };
  var spotA = 0, helpA = 0, anim = null, dimT = 0, dimA = 0;   // dim: room-aware dimming (nobody in the room)   // spotlight / help card fade; throw animation {k: out|in, dir, t0}
  var HELP = [["Open palm, held still", "Wake it up: a cursor appears"], ["Move your hand", "Move the cursor (sweep fast to cross TVs)"],
    ["Quick pinch", "Click"], ["Pinch, then raise / lower", "Zoom (maps zoom themselves)"],
    ["Flick an open hand \u2190 \u2192", "Next / previous dashboard"], ["Flick a fist \u2190 \u2192", "Throw this dashboard to the next TV"],
    ["Fist, held", "Pause / resume rotation"], ["Thumbs up, held", "Spotlight on / off"], ["V (two fingers), held", "Play the interlude"],
    ["Point, held still", "Draw (a held fist clears it)"], ["Both open palms", "Blanket on / off"], ["Both fists, 3 seconds", "Reboot every TV (an open hand cancels)"]];
  var ink = [], stroke = null, ripple = 0;  // drawing: strokes of screen points; click ripple start
  var cur = { x: 0, y: 0, a: 0 };           // drawn cursor (eased), alpha
  var toast = { text: "", t: 0, ms: 1800 };
  var seen = 0, lastRaise = 0;
  // zoom: page point P shows at P * Z + T
  var Z = 1, T = [0, 0], zTarget = 1, zid = -1, z0 = 1, offSince = 0, saved = null;
  var NAMES = { next: "Next dashboard", prev: "Previous dashboard", pause: "", interlude: "Interlude",
                blanket: "Blanket", wake: "", sleep: "" };

  function W() { return window.innerWidth; }
  function H() { return window.innerHeight; }

  function applyZoom() {
    var el = document.documentElement;
    if (Z <= 1.001 && Math.abs(T[0]) < 0.5 && Math.abs(T[1]) < 0.5) {
      if (saved) { el.style.transform = saved[0]; el.style.transformOrigin = saved[1]; el.style.overflow = saved[2]; saved = null; }
      return;
    }
    if (!saved) saved = [el.style.transform, el.style.transformOrigin, el.style.overflow];
    el.style.overflow = "hidden";                                      // no scrollbars from the enlarged page
    el.style.transformOrigin = "0 0";
    el.style.transform = "translate(" + T[0].toFixed(1) + "px," + T[1].toFixed(1) + "px) scale(" + Z.toFixed(4) + ")";
  }
  function clampT() {
    T[0] = Math.min(0, Math.max(W() - W() * Z, T[0]));
    T[1] = Math.min(0, Math.max(H() - H() * Z, T[1]));
  }
  function zoomAt(nz, px, py) {
    nz = Math.max(1, Math.min(4, nz));
    T[0] = px - (px - T[0]) * nz / Z;
    T[1] = py - (py - T[1]) * nz / Z;
    Z = nz; clampT();
  }

  function ring(x, y, r, p, col, lw) {
    c.lineWidth = lw; c.strokeStyle = "rgba(255,255,255,.18)";
    c.beginPath(); c.arc(x, y, r, 0, 6.2832); c.stroke();
    c.strokeStyle = col; c.beginPath(); c.arc(x, y, r, -Math.PI / 2, -Math.PI / 2 + 6.2832 * p); c.stroke();
  }
  function pill(text, x, y, size) {
    c.font = "600 " + size + "px system-ui, sans-serif";
    var w = c.measureText(text).width + size * 1.4, h = size * 1.9;
    c.fillStyle = "rgba(8,14,28,.82)"; c.beginPath();
    if (c.roundRect) c.roundRect(x - w / 2, y - h / 2, w, h, h / 2); else c.rect(x - w / 2, y - h / 2, w, h);
    c.fill();
    c.strokeStyle = "rgba(120,180,255,.55)"; c.lineWidth = 1.5; c.stroke();
    c.fillStyle = "#fff"; c.textAlign = "center"; c.textBaseline = "middle"; c.fillText(text, x, y + 1);
  }
  function palm(x, y, s, col) {          // a small open-hand icon
    c.fillStyle = col;
    c.beginPath(); if (c.roundRect) c.roundRect(x - s * 0.42, y - s * 0.1, s * 0.84, s * 0.7, s * 0.2); else c.rect(x - s * 0.42, y - s * 0.1, s * 0.84, s * 0.7); c.fill();
    [[-0.32, 0.55], [-0.11, 0.7], [0.1, 0.68], [0.3, 0.52]].forEach(function (f) {
      c.beginPath(); if (c.roundRect) c.roundRect(x + f[0] * s - s * 0.09, y - f[1] * s, s * 0.18, f[1] * s + s * 0.1, s * 0.09); c.fill();
    });
    c.save(); c.translate(x - s * 0.42, y + s * 0.2); c.rotate(-0.7);
    c.beginPath(); if (c.roundRect) c.roundRect(-s * 0.09, -s * 0.45, s * 0.18, s * 0.5, s * 0.09); c.fill(); c.restore();
  }

  var last = performance.now();
  function frame(now) {
    var dt = Math.min(0.1, (now - last) / 1000); last = now;
    var dpr = window.devicePixelRatio || 1, w = W(), h = H();
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, w, h);
    var alive = Date.now() - S.t < 4000;
    // room-aware dimming: fades down slowly (~4 s), comes back quickly
    dimA += (dimT - dimA) * Math.min(1, dt * (dimT > dimA ? 0.7 : 6));
    if (dimA > 0.005) {
      c.fillStyle = "rgba(0,0,0," + (0.9 * dimA).toFixed(3) + ")"; c.fillRect(0, 0, w, h);
      c.globalAlpha = 0.3 * dimA; c.fillStyle = "#c8d2e0"; c.font = "400 " + Math.round(18 * Math.max(1, h / 1080)) + "px system-ui, sans-serif";
      c.textAlign = "center"; c.textBaseline = "middle"; c.fillText("Nobody's here - the wall wakes up when someone comes in", w / 2, h - 40 * Math.max(1, h / 1080));
      c.globalAlpha = 1;
    }
    var u = Math.max(1, h / 1080);                                     // drawing size follows the screen                     // no word from the camera for a while: draw nothing

    // zoom: ease toward the target; pan when the cursor rests near an edge
    if (Math.abs(zTarget - Z) > 0.001) zoomAt(Z + (zTarget - Z) * Math.min(1, dt * 10), cur.x, cur.y);
    if (S.on && !S.pinch && Z > 1.01) {
      var e = 0.07, sp = 900 * dt;
      if (S.x < e) T[0] += sp * (1 - S.x / e); if (S.x > 1 - e) T[0] -= sp * (1 - (1 - S.x) / e);
      if (S.y < e) T[1] += sp * (1 - S.y / e); if (S.y > 1 - e) T[1] -= sp * (1 - (1 - S.y) / e);
      clampT();
    }
    if (!S.on && Z > 1 && Date.now() - offSince > 20000) { zTarget = 1; }   // walked away: zoom back out after 20 s
    applyZoom();

    // the drawing: stays up (also when the camera goes quiet), fades 30 s after the hand leaves
    var inkA = S.on || !ink.length ? 1 : Math.max(0, 1 - (Date.now() - offSince - 30000) / 2000);
    if (!S.on && ink.length && inkA <= 0) { ink = []; stroke = null; }
    if (ink.length) {
      c.lineCap = "round"; c.lineJoin = "round";
      ink.forEach(function (st) {
        if (st.length < 2) return;
        for (var pass = 0; pass < 2; pass++) {               // dark edge, then the red line: shows on any page
          c.globalAlpha = inkA * (pass ? 1 : 0.5);
          c.strokeStyle = pass ? "#ff3b3b" : "rgba(10,10,20,.9)"; c.lineWidth = (pass ? 6 : 10) * u;
          c.beginPath(); c.moveTo(st[0][0], st[0][1]);
          for (var i = 1; i < st.length; i++) c.lineTo(st[i][0], st[i][1]);
          c.stroke();
        }
      });
      c.globalAlpha = 1;
    }

    // spotlight: everything dims except a circle round the cursor (no cursor here: this whole screen dims)
    spotA += ((alive && S.spot ? 1 : 0) - spotA) * Math.min(1, dt * 5);
    if (spotA > 0.01) {
      var SR = 0.21 * h;
      if (S.on && cur.a > 0.05) {
        var sg = c.createRadialGradient(cur.x, cur.y, SR * 0.82, cur.x, cur.y, SR * 1.28);
        sg.addColorStop(0, "rgba(3,5,12,0)"); sg.addColorStop(1, "rgba(3,5,12," + (0.8 * spotA).toFixed(3) + ")");
        c.fillStyle = sg; c.fillRect(0, 0, w, h);
        c.lineWidth = 2 * u; c.strokeStyle = "rgba(255,216,74," + (0.4 * spotA).toFixed(3) + ")";
        c.beginPath(); c.arc(cur.x, cur.y, SR * 0.98, 0, 6.2832); c.stroke();
      } else { c.fillStyle = "rgba(3,5,12," + (0.72 * spotA).toFixed(3) + ")"; c.fillRect(0, 0, w, h); }
    }

    if (alive) {
      // cursor
      var tx = S.x * w, ty = S.y * h, k = Math.min(1, dt * (S.draw ? 30 : 22));
      cur.x += (tx - cur.x) * k; cur.y += (ty - cur.y) * k;
      cur.a += ((S.on ? 1 : 0) - cur.a) * Math.min(1, dt * 8);
      // drawing: pen down adds to the current stroke
      if (S.on && S.draw && S.pen) {
        if (!stroke) { stroke = []; ink.push(stroke); }
        var lp = stroke[stroke.length - 1];
        if (!lp || Math.abs(lp[0] - cur.x) + Math.abs(lp[1] - cur.y) > 2) stroke.push([cur.x, cur.y]);
      } else stroke = null;
      if (ripple && now - ripple < 450) {                  // click
        var rp = (now - ripple) / 450;
        c.globalAlpha = 1 - rp; c.lineWidth = 4 * u; c.strokeStyle = "#5fafff";
        c.beginPath(); c.arc(cur.x, cur.y, (14 + 40 * rp) * u, 0, 6.2832); c.stroke(); c.globalAlpha = 1;
      }
      if (cur.a > 0.02 && S.draw) {                        // drawing mode: a pen tip instead of the ring
        c.globalAlpha = cur.a;
        c.fillStyle = "rgba(10,10,20,.6)"; c.beginPath(); c.arc(cur.x, cur.y, 11 * u, 0, 6.2832); c.fill();
        c.fillStyle = "#ff3b3b"; c.beginPath(); c.arc(cur.x, cur.y, (S.pen ? 8 : 5) * u, 0, 6.2832); c.fill();
        if (!S.pen) { c.lineWidth = 2.5 * u; c.strokeStyle = "#ff3b3b"; c.beginPath(); c.arc(cur.x, cur.y, 16 * u, 0, 6.2832); c.stroke(); }
        c.globalAlpha = 1;
      } else if (cur.a > 0.02) {
        c.globalAlpha = cur.a;
        var g = c.createRadialGradient(cur.x, cur.y, 0, cur.x, cur.y, 40 * u);
        g.addColorStop(0, "rgba(95,175,255,.4)"); g.addColorStop(1, "rgba(95,175,255,0)");
        c.fillStyle = g; c.beginPath(); c.arc(cur.x, cur.y, 40 * u, 0, 6.2832); c.fill();
        c.lineWidth = 3.5 * u; c.strokeStyle = "rgba(10,20,40,.55)";
        c.beginPath(); c.arc(cur.x, cur.y, (S.pinch ? 12 : 18) * u + 2 * u, 0, 6.2832); c.stroke();      // dark edge: visible on light pages too
        c.lineWidth = 3.5 * u; c.strokeStyle = "#ffffff";
        c.beginPath(); c.arc(cur.x, cur.y, (S.pinch ? 12 : 18) * u, 0, 6.2832); c.stroke();
        c.fillStyle = S.pinch ? "#5fafff" : "#ffffff"; c.beginPath(); c.arc(cur.x, cur.y, (S.pinch ? 7 : 4) * u, 0, 6.2832); c.fill();
        if (S.pinch && S.wheel) pill("zoom map  \u2195", cur.x, cur.y + 46 * u, 16 * u);
        else if (S.pinch || Z > 1.01) pill(Z.toFixed(1) + "×", cur.x, cur.y + 46 * u, 16 * u);
        c.globalAlpha = 1;
      }
      // holds
      var hd = S.hold;
      if (hd) {
        if (hd.k === "wake") {
          var wx = w / 2, wy = h * 0.12;
          c.fillStyle = "rgba(8,14,28,.7)"; c.beginPath(); c.arc(wx, wy, 44 * u, 0, 6.2832); c.fill();
          ring(wx, wy, 38 * u, hd.p, "#5fafff", 7 * u); palm(wx, wy + 4 * u, 36 * u, "rgba(255,255,255,.92)");
          pill("Hold still", wx, wy + 72 * u, 17 * u);
        } else if (hd.k === "blanket") {
          ring(w / 2, h / 2, 90 * u, hd.p, "#e82c44", 12 * u);
          pill("Blanket", w / 2, h / 2, 24 * u);
        } else if (hd.k === "reboot" || hd.k === "rebootwait") {    // both fists: reboot every display
          var wait = hd.k === "rebootwait", rx = w / 2, ry = h * 0.45, R = 120 * u;
          c.fillStyle = "rgba(4,6,14," + (wait ? 0.62 : 0.35 * Math.min(1, hd.p * 3)) + ")"; c.fillRect(0, 0, w, h);
          c.fillStyle = "rgba(8,14,28,.85)"; c.beginPath(); c.arc(rx, ry, R + 18 * u, 0, 6.2832); c.fill();
          if (wait) ring(rx, ry, R, 1 - hd.p, "#e82c44", 14 * u);
          else ring(rx, ry, R, hd.p, "#e82c44", 14 * u);
          c.fillStyle = "#fff"; c.textAlign = "center"; c.textBaseline = "middle";
          if (wait) { c.font = "700 " + Math.round(110 * u) + "px system-ui, sans-serif"; c.fillText(String(hd.s), rx, ry + 6 * u); }
          else {                                                       // restart symbol
            c.lineWidth = 12 * u; c.strokeStyle = "#fff"; c.lineCap = "round";
            c.beginPath(); c.arc(rx, ry, 52 * u, -Math.PI / 2 + 0.55, -Math.PI / 2 + 6.2832 - 0.55); c.stroke();
            c.beginPath(); c.moveTo(rx, ry - 74 * u); c.lineTo(rx, ry - 26 * u); c.stroke();
          }
          pill(wait ? "Rebooting all displays in " + hd.s + " s" : "Reboot all displays", rx, ry + R + 62 * u, 30 * u);
          pill(wait ? "Show an open hand to cancel" : "Keep both fists up", rx, ry + R + 128 * u, 20 * u);
        } else {
          var lab = { pause: ["Pause rotation", "#ffc84a"], interlude: ["Interlude", "#46cd78"],
                      draw: ["Draw", "#ff3b3b"], drawoff: ["Clear drawing", "#ff3b3b"], spot: ["Spotlight", "#ffd84a"],
                      help: ["Keep still for help", "#5fafff"] }[hd.k] || [hd.k, "#5fafff"];
          ring(cur.x, cur.y, 32 * u, hd.p, lab[1], 7 * u);
          pill(lab[0], cur.x, cur.y - 58 * u, 16 * u);
        }
      }
      // help card: every gesture, on the screen the cursor is on
      helpA += ((S.help ? 1 : 0) - helpA) * Math.min(1, dt * 7);
      if (helpA > 0.01) {
        var cw = Math.min(w * 0.7, 1120 * u), rh = 40 * u, ch = rh * HELP.length + 132 * u, hx0 = (w - cw) / 2, hy0 = (h - ch) / 2 + (1 - helpA) * 30 * u;
        c.globalAlpha = helpA;
        c.fillStyle = "rgba(8,14,28,.93)"; c.beginPath(); if (c.roundRect) c.roundRect(hx0, hy0, cw, ch, 18 * u); else c.rect(hx0, hy0, cw, ch); c.fill();
        c.strokeStyle = "rgba(120,180,255,.55)"; c.lineWidth = 2 * u; c.stroke();
        c.textBaseline = "middle"; c.textAlign = "left";
        c.fillStyle = "#fff"; c.font = "700 " + Math.round(30 * u) + "px system-ui, sans-serif"; c.fillText("Hand gestures", hx0 + 36 * u, hy0 + 44 * u);
        palm(hx0 + cw - 52 * u, hy0 + 48 * u, 30 * u, "rgba(95,175,255,.9)");
        for (var hi = 0; hi < HELP.length; hi++) {
          var ry = hy0 + 92 * u + hi * rh;
          if (hi % 2 === 0) { c.fillStyle = "rgba(255,255,255,.04)"; c.fillRect(hx0 + 20 * u, ry - rh / 2, cw - 40 * u, rh); }
          c.fillStyle = "#ffd27a"; c.font = "600 " + Math.round(21 * u) + "px system-ui, sans-serif"; c.fillText(HELP[hi][0], hx0 + 36 * u, ry);
          c.fillStyle = "#e8eef8"; c.font = "400 " + Math.round(21 * u) + "px system-ui, sans-serif"; c.fillText(HELP[hi][1], hx0 + cw * 0.43, ry);
        }
        c.fillStyle = "rgba(200,210,225,.7)"; c.font = "400 " + Math.round(17 * u) + "px system-ui, sans-serif"; c.textAlign = "center";
        c.fillText("Move your hand to close this", w / 2, hy0 + ch - 24 * u);
        c.globalAlpha = 1;
      }
      // message
      // camera dot, top right: grey watching, blue in use, red no camera
      c.fillStyle = !S.cam ? "rgba(232,44,68,.9)" : S.on ? "rgba(95,175,255,.95)" : "rgba(200,205,215,.45)";
      c.beginPath(); c.arc(w - 16 * u, 16 * u, (S.on ? 6 : 4.5) * u, 0, 6.2832); c.fill();
      if (!S.cam) { c.font = Math.round(13 * u) + "px system-ui, sans-serif"; c.textAlign = "right"; c.textBaseline = "middle"; c.fillStyle = "rgba(255,255,255,.7)"; c.fillText("no camera", w - 28 * u, 16 * u); }
    } else {
      cur.a = 0;
    }
    // message (also used without the camera, e.g. the AirPlay code)
    if (toast.text && now - toast.t < toast.ms) {
      c.globalAlpha = Math.min(1, (toast.ms - (now - toast.t)) / 300);
      pill(toast.text, w / 2, h - 80 * u, (toast.ms > 5000 ? 34 : 24) * u); c.globalAlpha = 1;
    }
    // a dashboard flying off to the next TV, or arriving from one
    if (anim) {
      var ae = (now - anim.t0) / (anim.k === "out" ? 600 : 750);
      if (ae >= 1 || ae < 0) anim = null;
      else {
        var aw = w * 0.42, ah = h * 0.42, ax, asc, aa = 1;
        if (anim.k === "out") { var uo = ae * ae; ax = w / 2 + anim.dir * (w / 2 + aw) * uo; asc = 1 - 0.3 * uo; }
        else { var ui = 1 - Math.pow(1 - ae, 3); ax = w / 2 - anim.dir * (w / 2 + aw) * (1 - ui); asc = 0.7 + (w / aw - 0.7) * ui; aa = 1 - Math.max(0, (ae - 0.55) / 0.45); }
        var bw = aw * asc, bh = ah * asc;
        c.globalAlpha = aa;
        c.fillStyle = "rgba(95,175,255,.13)"; c.strokeStyle = "rgba(95,175,255,.95)"; c.lineWidth = 4 * u;
        c.beginPath(); if (c.roundRect) c.roundRect(ax - bw / 2, h / 2 - bh / 2, bw, bh, 16 * u); else c.rect(ax - bw / 2, h / 2 - bh / 2, bw, bh); c.fill(); c.stroke();
        c.strokeStyle = "rgba(95,175,255,.5)"; c.lineWidth = 3 * u;
        for (var sl = -2; sl <= 2; sl++) { var sy = h / 2 + sl * bh * 0.18, sx = ax - anim.dir * (bw / 2 + 20 * u);
          c.beginPath(); c.moveTo(sx, sy); c.lineTo(sx - anim.dir * (90 + 40 * Math.abs(sl)) * u, sy); c.stroke(); }
        c.globalAlpha = 1;
      }
    }
    pv.style.display = alive && S.pv ? "block" : "none";
    if ((S.on || S.hold || S.spot || anim || dimA > 0.005 || (toast.text && now - toast.t < toast.ms)) && now - lastRaise > 1000) { lastRaise = now; if (!host.matches(":popover-open") || host !== document.documentElement.lastElementChild) mount(); }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  window.__bcsGesture = function (m) {
    if (!host.isConnected) mount();
    if (m.reset) { Z = 1; zTarget = 1; T = [0, 0]; applyZoom(); return [W(), H()]; }
    if (m.ink === "clear") { ink = []; stroke = null; return [W(), H()]; }
    if (m.ripple) { ripple = performance.now(); return [W(), H()]; }
    if ("dim" in m) { dimT = m.dim ? 1 : 0; if (m.only) return [W(), H()]; }
    if (m.toast) { toast.text = m.toast; toast.t = performance.now(); toast.ms = m.toast_ms || 1800; }
    if (m.throw || m.arrive) { anim = { k: m.throw ? "out" : "in", dir: m.throw || m.arrive, t0: performance.now() }; return [W(), H()]; }
    if (S.on && !m.on) offSince = Date.now();
    S.on = !!m.on; S.x = m.x == null ? S.x : m.x; S.y = m.y == null ? S.y : m.y;
    S.draw = !!m.draw; S.pen = !!m.pen;
    S.hold = m.hold || null; S.pinch = !!m.pinch; S.cam = m.cam !== false; S.t = Date.now();
    S.spot = !!m.spot; S.help = !!m.help;
    if (m.on && cur.a < 0.05) { cur.x = S.x * W(); cur.y = S.y * H(); }
    S.wheel = !!m.wheel;                                   // pinching over a map: the map zooms, the page doesn't
    if (m.pinch && !m.wheel) {
      if (m.zid !== zid) { zid = m.zid; z0 = zTarget; }
      zTarget = Math.max(1, Math.min(4, z0 * m.zf));
    } else if (m.pinch) { zid = m.zid; }
    if (m.pv) { S.pv = true; pv.src = "data:image/jpeg;base64," + m.pv; } else if (m.pv === null) { S.pv = false; }
    (m.ev || []).forEach(function (e) {
      if (e[0] <= seen) return;
      seen = e[0];
      if (NAMES[e[1]]) { toast.text = NAMES[e[1]]; toast.t = performance.now(); toast.ms = 1800; }
    });
    return [W(), H()];
  };
  window.__bcsGestureReset = function () { Z = 1; zTarget = 1; T = [0, 0]; applyZoom(); };
})();
