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
  pv.setAttribute("style", "position:fixed;right:18px;bottom:18px;width:384px;height:216px;border-radius:10px;" +
    "box-shadow:0 0 0 2px rgba(120,180,255,.7),0 8px 30px rgba(0,0,0,.6);display:none;pointer-events:none");
  root.appendChild(cv); root.appendChild(pv);
  var c = cv.getContext("2d");
  function mount() {
    if (!host.isConnected) document.documentElement.appendChild(host);
    try { if (host.hidePopover) host.hidePopover(); } catch (e) {}
    try { if (host.showPopover) host.showPopover(); } catch (e) {}   // last in = on top of the interlude / blanket
  }
  mount();

  var S = { on: false, x: 0.5, y: 0.5, hold: null, pinch: false, cam: true, t: 0 };
  var cur = { x: 0, y: 0, a: 0 };           // drawn cursor (eased), alpha
  var toast = { text: "", t: 0 };
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

    if (alive) {
      // cursor
      var tx = S.x * w, ty = S.y * h, k = Math.min(1, dt * 22);
      cur.x += (tx - cur.x) * k; cur.y += (ty - cur.y) * k;
      cur.a += ((S.on ? 1 : 0) - cur.a) * Math.min(1, dt * 8);
      if (cur.a > 0.02) {
        c.globalAlpha = cur.a;
        var g = c.createRadialGradient(cur.x, cur.y, 0, cur.x, cur.y, 40 * u);
        g.addColorStop(0, "rgba(95,175,255,.4)"); g.addColorStop(1, "rgba(95,175,255,0)");
        c.fillStyle = g; c.beginPath(); c.arc(cur.x, cur.y, 40 * u, 0, 6.2832); c.fill();
        c.lineWidth = 3.5 * u; c.strokeStyle = "rgba(10,20,40,.55)";
        c.beginPath(); c.arc(cur.x, cur.y, (S.pinch ? 12 : 18) * u + 2 * u, 0, 6.2832); c.stroke();      // dark edge: visible on light pages too
        c.lineWidth = 3.5 * u; c.strokeStyle = "#ffffff";
        c.beginPath(); c.arc(cur.x, cur.y, (S.pinch ? 12 : 18) * u, 0, 6.2832); c.stroke();
        c.fillStyle = S.pinch ? "#5fafff" : "#ffffff"; c.beginPath(); c.arc(cur.x, cur.y, (S.pinch ? 7 : 4) * u, 0, 6.2832); c.fill();
        if (S.pinch || Z > 1.01) pill(Z.toFixed(1) + "×", cur.x, cur.y + 46 * u, 16 * u);
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
        } else {
          ring(cur.x, cur.y, 32 * u, hd.p, hd.k === "pause" ? "#ffc84a" : "#46cd78", 7 * u);
          pill(hd.k === "pause" ? "Pause rotation" : "Interlude", cur.x, cur.y - 58 * u, 16 * u);
        }
      }
      // message
      if (toast.text && now - toast.t < 1800) {
        c.globalAlpha = Math.min(1, (1800 - (now - toast.t)) / 300);
        pill(toast.text, w / 2, h - 80 * u, 24 * u); c.globalAlpha = 1;
      }
      // camera dot, top right: grey watching, blue in use, red no camera
      c.fillStyle = !S.cam ? "rgba(232,44,68,.9)" : S.on ? "rgba(95,175,255,.95)" : "rgba(200,205,215,.45)";
      c.beginPath(); c.arc(w - 16 * u, 16 * u, (S.on ? 6 : 4.5) * u, 0, 6.2832); c.fill();
      if (!S.cam) { c.font = Math.round(13 * u) + "px system-ui, sans-serif"; c.textAlign = "right"; c.textBaseline = "middle"; c.fillStyle = "rgba(255,255,255,.7)"; c.fillText("no camera", w - 28 * u, 16 * u); }
    } else {
      cur.a = 0;
    }
    pv.style.display = alive && S.pv ? "block" : "none";
    if ((S.on || S.hold || toast.text) && now - lastRaise > 1000) { lastRaise = now; if (!host.matches(":popover-open") || host !== document.documentElement.lastElementChild) mount(); }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  window.__bcsGesture = function (m) {
    if (!host.isConnected) mount();
    if (m.reset) { Z = 1; zTarget = 1; T = [0, 0]; applyZoom(); return [W(), H()]; }
    if (m.toast) { toast.text = m.toast; toast.t = performance.now(); }
    if (S.on && !m.on) offSince = Date.now();
    S.on = !!m.on; S.x = m.x == null ? S.x : m.x; S.y = m.y == null ? S.y : m.y;
    S.hold = m.hold || null; S.pinch = !!m.pinch; S.cam = m.cam !== false; S.t = Date.now();
    if (m.on && cur.a < 0.05) { cur.x = S.x * W(); cur.y = S.y * H(); }
    if (m.pinch) {
      if (m.zid !== zid) { zid = m.zid; z0 = zTarget; }
      zTarget = Math.max(1, Math.min(4, z0 * m.zf));
    }
    if (m.pv) { S.pv = true; pv.src = "data:image/jpeg;base64," + m.pv; } else if (m.pv === null) { S.pv = false; }
    (m.ev || []).forEach(function (e) {
      if (e[0] <= seen) return;
      seen = e[0];
      if (NAMES[e[1]]) { toast.text = NAMES[e[1]]; toast.t = performance.now(); }
    });
    return [W(), H()];
  };
  window.__bcsGestureReset = function () { Z = 1; zTarget = 1; T = [0, 0]; applyZoom(); };
})();
