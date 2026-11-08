/* Retrieval cloud: the document's passages as points in 3D (PCA of their embeddings),
   the question as a point in the same space, and lines to the passages it retrieved.
   Plain canvas 2D with a hand-rolled perspective projection, no dependencies. */
(function () {
  "use strict";

  var canvas = document.getElementById("cloud-canvas");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  var CAMERA = 3.4;        // camera distance from the origin, in cloud units (cloud radius is 1)
  var FRAME_MS = 1000 / 30;
  var IDLE_MS = 25000;     // auto-rotation stops after this long without input
  var SPIN = 0.16;         // rad/s
  var ENTER_MS = 900;
  var STAGGER_MS = 14;

  var s = {
    key: null, demo: true, points: [], variance: 0,
    query: null, queryKey: null, queryAt: 0, links: [], ringRadius: 0,
    searching: false,
    yaw: 0.7, pitch: -0.32,
    lastInput: performance.now(), drag: null, hover: -1, projected: [],
    width: 0, height: 0, focal: 1, base: 3,
    visible: true, raf: 0, last: 0, colors: null, font: "sans-serif"
  };

  /* ---------- helpers ---------- */

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
  function progress(start, duration, now) {
    if (reduce.matches || duration <= 0) return now >= start ? 1 : 0;
    return clamp((now - start) / duration, 0, 1);
  }

  function hexToRgb(hex) {
    var h = hex.replace("#", "").trim();
    if (h.length === 3) h = h.replace(/./g, "$&$&");
    var n = parseInt(h, 16);
    return isNaN(n) ? [128, 128, 128] : [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function rgba(rgb, a) { return "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + "," + a.toFixed(3) + ")"; }
  function mix(a, b, t) { return [Math.round(a[0] + (b[0] - a[0]) * t), Math.round(a[1] + (b[1] - a[1]) * t), Math.round(a[2] + (b[2] - a[2]) * t)]; }

  function readColors() {
    var css = getComputedStyle(document.documentElement);
    var get = function (name) { return hexToRgb(css.getPropertyValue(name)); };
    s.colors = { a: get("--cloud-a"), b: get("--cloud-b"), query: get("--cloud-query"), line: get("--cloud-line"), ink: get("--cloud-ink") };
    s.light = document.documentElement.dataset.theme === "light";
    s.font = getComputedStyle(document.body).fontFamily;
  }

  // Seeded RNG so the example cloud looks the same on every load.
  function rng(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function demoPoints() {
    var rand = rng(42);
    var centers = [[0.55, 0.3, -0.2], [-0.5, 0.15, 0.45], [0.05, -0.55, -0.35], [-0.2, 0.6, -0.5]];
    var out = [];
    for (var i = 0; i < 44; i++) {
      var c = centers[i % centers.length];
      var g = function () { return (rand() + rand() + rand() - 1.5) * 0.32; };
      out.push([c[0] + g(), c[1] + g(), c[2] + g()]);
    }
    return out;
  }

  /* ---------- state changes ---------- */

  function setPoints(list, demo, now) {
    var previous = s.points;
    s.demo = demo;
    s.points = list.map(function (p, i) {
      var from = previous[i] ? current(previous[i], now) : [0, 0, 0];
      return { to: p, from: from, born: now + i * STAGGER_MS, t: list.length > 1 ? i / (list.length - 1) : 0.5, n: i + 1 };
    });
    s.hover = -1;
  }

  function current(point, now) {
    var k = easeOut(progress(point.born, ENTER_MS, now));
    return [
      point.from[0] + (point.to[0] - point.from[0]) * k,
      point.from[1] + (point.to[1] - point.from[1]) * k,
      point.from[2] + (point.to[2] - point.from[2]) * k
    ];
  }

  function setQuery(position, numbers, similarities, now) {
    var sims = similarities.map(Number);
    var top = Math.max.apply(null, sims), low = Math.min.apply(null, sims);
    s.query = position;
    s.queryAt = now;
    s.links = numbers.map(function (n, rank) {
      return { index: n - 1, rank: rank, weight: top > low ? (sims[rank] - low) / (top - low) : 1 };
    }).filter(function (link) { return link.index >= 0 && link.index < s.points.length; });
    s.ringRadius = s.links.reduce(function (r, link) {
      var p = s.points[link.index].to;
      return Math.max(r, Math.hypot(p[0] - position[0], p[1] - position[1], p[2] - position[2]));
    }, 0.2);
  }

  function clearQuery() { s.query = null; s.links = []; }

  /* ---------- projection and drawing ---------- */

  function project(x, y, z) {
    var cy = Math.cos(s.yaw), sy = Math.sin(s.yaw), cp = Math.cos(s.pitch), sp = Math.sin(s.pitch);
    var x1 = x * cy + z * sy;
    var z1 = -x * sy + z * cy;
    var y1 = y * cp - z1 * sp;
    var z2 = y * sp + z1 * cp;
    var k = s.focal / (CAMERA - z2);
    return { x: s.width / 2 + x1 * k, y: s.height / 2 - y1 * k, k: k, z: z2 };
  }

  function ring(axis, alpha) {
    ctx.beginPath();
    for (var i = 0; i <= 64; i++) {
      var a = (i / 64) * Math.PI * 2;
      var c = Math.cos(a), d = Math.sin(a);
      var p = axis === "y" ? project(c, 0, d) : project(c, d, 0);
      if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
    }
    ctx.strokeStyle = rgba(s.colors.line, alpha);
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  function dot(x, y, r, color, alpha) {
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = rgba(color, alpha);
    ctx.fill();
  }

  function draw(now) {
    var c = s.colors;
    var unit = s.focal / CAMERA;
    ctx.clearRect(0, 0, s.width, s.height);
    ctx.globalCompositeOperation = "source-over";

    ring("y", 0.55);
    ring("z", 0.3);

    var linkAt = s.queryAt + (reduce.matches ? 0 : 650);
    var focus = s.query ? progress(linkAt, 400, now) : 0;
    var retrieved = {};
    s.links.forEach(function (link) { retrieved[link.index] = link; });

    // Far points first so near ones overlap them.
    s.projected = s.points.map(function (point, i) {
      var pos = current(point, now);
      var p = project(pos[0], pos[1], pos[2]);
      p.i = i;
      return p;
    });
    var order = s.projected.slice().sort(function (l, r) { return l.z - r.z; });

    // Query position (flies out from the center).
    var q = null;
    if (s.query) {
      var k = easeOut(progress(s.queryAt, 700, now));
      q = project(s.query[0] * k, s.query[1] * k, s.query[2] * k);
    } else if (s.searching) {
      q = project(0, 0, 0);
    }

    // Search radius: a sphere around the question that grows until it holds the top passages.
    if (s.query) {
      var grow = progress(s.queryAt + 250, 800, now);
      if (grow > 0 && grow < 1) {
        ctx.beginPath();
        ctx.arc(q.x, q.y, s.ringRadius * q.k * easeOut(grow), 0, Math.PI * 2);
        ctx.strokeStyle = rgba(c.query, 0.6 * (1 - grow));
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }

    // Links, drawn in rank order.
    if (q && s.links.length) {
      s.links.forEach(function (link) {
        var t = easeOut(progress(linkAt + link.rank * 140, 420, now));
        if (!t) return;
        var p = s.projected[link.index];
        ctx.beginPath();
        ctx.moveTo(q.x, q.y);
        ctx.lineTo(q.x + (p.x - q.x) * t, q.y + (p.y - q.y) * t);
        ctx.strokeStyle = rgba(c.query, 0.3 + 0.5 * link.weight);
        ctx.lineWidth = 0.8 + 2 * link.weight;
        ctx.stroke();
      });
    }

    if (!s.light) ctx.globalCompositeOperation = "lighter";
    order.forEach(function (p) {
      var point = s.points[p.i];
      var depth = clamp((p.z + 1) / 2, 0, 1);
      var color = mix(c.a, c.b, point.t);
      var link = retrieved[p.i];
      var alpha = (0.35 + 0.65 * depth) * (link ? 1 : 1 - 0.7 * focus);
      var r = s.base * (p.k / unit) * (link ? 1 + 0.6 * focus : 1);
      var born = progress(point.born, ENTER_MS * 0.4, now);
      alpha *= born;
      if (!s.light) dot(p.x, p.y, r * 2.6, color, alpha * 0.12);
      dot(p.x, p.y, r, color, alpha);
    });
    ctx.globalCompositeOperation = "source-over";

    // Retrieved rings and rank labels.
    ctx.font = "700 11px " + s.font;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    var placed = [];
    s.links.forEach(function (link) {
      var shown = progress(linkAt + link.rank * 140 + 300, 250, now);
      if (!shown) return;
      var p = s.projected[link.index];
      var r = s.base * (p.k / unit) * 1.6 + 3;
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.strokeStyle = rgba(c.query, 0.9 * shown);
      ctx.lineWidth = 1.5;
      ctx.stroke();
      // Labels go in rank order; one that would cover a better-ranked label is skipped.
      var lx = p.x + r + 6, ly = p.y - r;
      var free = placed.every(function (l) { return Math.abs(l[0] - lx) > 14 || Math.abs(l[1] - ly) > 13; });
      if (!free) return;
      placed.push([lx, ly]);
      ctx.fillStyle = rgba(c.ink, shown);
      ctx.fillText(String(link.rank + 1), lx, ly);
    });

    // The question.
    if (q) {
      var pulse = reduce.matches ? 0.5 : (Math.sin(now / (s.searching ? 140 : 420)) + 1) / 2;
      var qr = s.base * (q.k / unit) * 1.7;
      dot(q.x, q.y, qr * (2.2 + pulse * 1.4), c.query, s.searching ? 0.22 : 0.14);
      dot(q.x, q.y, qr, c.query, 1);
    }

    // Hover label.
    if (s.hover >= 0 && !s.demo && s.projected[s.hover]) {
      var h = s.projected[s.hover];
      var label = "Passage #" + (s.hover + 1);
      ctx.font = "700 12px " + s.font;
      var w = ctx.measureText(label).width + 14;
      var x = clamp(h.x - w / 2, 4, s.width - w - 4);
      var y = h.y - 30 < 4 ? h.y + 12 : h.y - 30;
      ctx.fillStyle = rgba(s.light ? [255, 255, 255] : [20, 24, 28], 0.94);
      ctx.strokeStyle = rgba(c.line, 1);
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(x, y, w, 20, 6); else ctx.rect(x, y, w, 20);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = rgba(c.ink, 1);
      ctx.textAlign = "left";
      ctx.fillText(label, x + 7, y + 10.5);
    }
  }

  /* ---------- loop ---------- */

  function spinning(now) { return !reduce.matches && !s.drag && now - s.lastInput < IDLE_MS; }

  function animating(now) {
    var last = s.points.length ? s.points[s.points.length - 1].born + ENTER_MS : 0;
    return now < last || (s.query && now < s.queryAt + 2200) || s.searching;
  }

  function tick(now) {
    s.raf = 0;
    if (!s.visible || document.hidden) return;
    if (now - s.last < FRAME_MS - 2) { s.raf = requestAnimationFrame(tick); return; }
    var dt = Math.min(0.1, (now - s.last) / 1000);
    s.last = now;
    if (spinning(now)) s.yaw += SPIN * dt;
    draw(now);
    if (spinning(now) || animating(now) || s.drag) s.raf = requestAnimationFrame(tick);
  }

  function wake() {
    if (s.raf || !s.visible || document.hidden || !s.width) return;
    s.last = performance.now() - FRAME_MS;
    s.raf = requestAnimationFrame(tick);
  }

  function resize() {
    var rect = canvas.getBoundingClientRect();
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    s.width = rect.width;
    s.height = rect.height;
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    s.focal = Math.min(s.width, s.height) * 0.4 * CAMERA;
    s.base = clamp(Math.min(s.width, s.height) / 85, 2.2, 4.5);
    if (s.width) draw(performance.now());
    wake();
  }

  /* ---------- input ---------- */

  function nearest(x, y) {
    var best = -1, bestDist = 14 * 14;
    s.projected.forEach(function (p) {
      var d = (p.x - x) * (p.x - x) + (p.y - y) * (p.y - y);
      if (d < bestDist) { bestDist = d; best = p.i; }
    });
    return best;
  }

  function local(event) {
    var rect = canvas.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  canvas.addEventListener("pointerdown", function (event) {
    var p = local(event);
    s.drag = { x: p.x, y: p.y, yaw: s.yaw, pitch: s.pitch, moved: false };
    s.lastInput = performance.now();
    canvas.setPointerCapture(event.pointerId);
    wake();
  });

  canvas.addEventListener("pointermove", function (event) {
    var p = local(event);
    s.lastInput = performance.now();
    if (s.drag) {
      var dx = p.x - s.drag.x, dy = p.y - s.drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) s.drag.moved = true;
      s.yaw = s.drag.yaw + dx * 0.01;
      s.pitch = clamp(s.drag.pitch + dy * 0.01, -1.3, 1.3);
    } else {
      var hit = s.demo ? -1 : nearest(p.x, p.y);
      if (hit !== s.hover) { s.hover = hit; canvas.style.cursor = hit >= 0 ? "pointer" : ""; draw(performance.now()); }
    }
    wake();
  });

  function endDrag(event) {
    if (!s.drag) return;
    var clicked = !s.drag.moved;
    s.drag = null;
    if (clicked && event.type === "pointerup" && !s.demo) {
      var p = local(event);
      var hit = nearest(p.x, p.y);
      if (hit >= 0) document.dispatchEvent(new CustomEvent("cloud:open", { detail: hit + 1 }));
    }
    wake();
  }

  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);
  canvas.addEventListener("pointerleave", function () {
    if (s.hover !== -1) { s.hover = -1; canvas.style.cursor = ""; draw(performance.now()); }
  });

  /* ---------- sync with the page ---------- */

  function caption(text, badge, title) {
    var cap = document.getElementById("cloud-caption");
    var tag = document.getElementById("cloud-badge");
    if (cap) cap.textContent = text;
    if (tag) { tag.textContent = badge; tag.title = title || ""; tag.classList.toggle("is-live", !s.demo); }
  }

  function sync() {
    var now = performance.now();
    var data = document.getElementById("cloud-data");
    var raw = data && data.dataset.points ? data.dataset.points : "";
    if (raw !== s.key) {
      s.key = raw;
      var list = null;
      try { list = raw ? JSON.parse(raw) : null; } catch (e) { list = null; }
      setPoints(list && list.length ? list : demoPoints(), !(list && list.length), now);
      s.variance = data ? Number(data.dataset.variance || 0) : 0;
      clearQuery();
      s.queryKey = null;
      s.lastInput = now;
    }

    var answer = document.querySelector(".answer");
    var qraw = answer && !s.demo ? answer.dataset.query : "";
    var qkey = qraw ? qraw + "|" + answer.dataset.retrieved : null;
    if (qkey !== s.queryKey) {
      s.queryKey = qkey;
      s.searching = false;
      if (qkey) {
        try {
          setQuery(JSON.parse(qraw), answer.dataset.retrieved.split(",").map(Number), (answer.dataset.similarities || "").split(","), now);
          s.lastInput = now;
        } catch (e) { clearQuery(); }
      } else {
        clearQuery();
      }
    }

    var count = s.points.length;
    var pca = "3D projection (PCA) keeps " + s.variance + "% of the variance";
    if (s.demo) caption("Each dot is a passage, placed by meaning. Upload a document to see yours.", "Example");
    else if (s.query) caption("Lines link your question to the " + s.links.length + " closest passages, ranked by meaning in the full embedding space.", count + " passages", pca);
    else caption("Your " + count + " passages: similar ones sit close together. Drag to rotate, click a dot to read it.", count + " passages", pca);
    wake();
  }

  document.addEventListener("htmx:beforeRequest", function (event) {
    if (event.detail.elt.id !== "ask-form") return;
    clearQuery();
    s.queryKey = null;
    s.searching = true;
    s.lastInput = performance.now();
    wake();
  });

  document.addEventListener("htmx:afterRequest", function (event) {
    if (event.detail.elt.id !== "ask-form") return;
    s.searching = false;
    wake();
  });

  new MutationObserver(function () { readColors(); draw(performance.now()); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      s.visible = entries[0].isIntersecting;
      if (s.visible) { s.lastInput = performance.now(); resize(); }
    }).observe(canvas);
  }

  document.addEventListener("visibilitychange", wake);
  if ("ResizeObserver" in window) new ResizeObserver(resize).observe(canvas);
  else window.addEventListener("resize", resize);

  readColors();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { readColors(); draw(performance.now()); });

  window.RagCloud = { sync: sync };
})();
