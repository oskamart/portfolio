// osys-one-portfolio · maintained by the opencode agent session · do not edit from other sessions
/* ============================================================================
   osys.one — site behaviour

   Three jobs:
     1. Read assets/manifest.json and write the measured numbers into the page.
     2. Draw the hero field — an oscilloscope-style signal trace, not decoration.
     3. Wire the small interactions (mobile nav, scroll state, counters).
   ========================================================================= */

/* ── 1. measured metrics ────────────────────────────────────────────────── */

const fmt = new Intl.NumberFormat("en-GB");

/** Resolve a dotted path such as "systems.uvmstack.code_loc" against an object. */
function dig(obj, path) {
  return path.split(".").reduce((acc, key) => (acc == null ? acc : acc[key]), obj);
}

async function loadManifest() {
  try {
    const res = await fetch("assets/manifest.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(String(res.status));
    return await res.json();
  } catch {
    return null;
  }
}

function renderMetrics(manifest) {
  if (!manifest) return;

  for (const el of document.querySelectorAll("[data-metric]")) {
    const value = dig(manifest, el.dataset.metric);
    if (value === undefined || value === null) continue;

    if (typeof value === "number" && el.dataset.metric !== "generated") {
      el.textContent = fmt.format(value);
    } else if (el.dataset.metric === "generated") {
      const d = new Date(value);
      el.textContent = Number.isNaN(d.valueOf())
        ? value
        : d.toISOString().slice(0, 10);
    } else {
      el.textContent = String(value);
    }
  }

  // The shared temporal-AA core, measured across the four designs that use it.
  const taa = document.querySelector('[data-metric="taa.loc"]');
  if (taa && manifest.taa_core) taa.textContent = fmt.format(manifest.taa_core.loc);

  const stamp = document.getElementById("foot-stamp");
  if (stamp && manifest.generated) {
    stamp.textContent = `Manifest generated ${manifest.generated.replace("T", " ").slice(0, 19)} UTC`;
  }

  // Announce the loaded figures once, so a screen-reader user knows the
  // measured numbers are there rather than "—".
  const status = document.getElementById("metrics-status");
  if (status && manifest.totals) {
    status.textContent =
      `Figures loaded from source: ${fmt.format(manifest.totals.code_loc)} lines of code, ` +
      `${fmt.format(manifest.totals.files)} files, ${fmt.format(manifest.totals.commits)} commits.`;
  }
}

/* ── 2. hero field ──────────────────────────────────────────────────────── */

/**
 * A slow, wide dual-trace on a graticule — the visual language of a bench
 * oscilloscope. It reacts to the pointer: the traces lean toward it.
 * Falls back to nothing at all when the context is unavailable.
 */
function initHeroField() {
  const canvas = document.getElementById("hero-field");
  if (!canvas) return;

  const ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) return;

  let w = 0;
  let h = 0;
  let dpr = 1;
  let raf = 0;
  let t = 0;
  let px = 0.5;
  let py = 0.5;
  let targetX = 0.5;
  let targetY = 0.5;
  let paused = false;
  let reduceQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const reduced = reduceQuery.matches;

  function resize() {
    const rect = canvas.getBoundingClientRect();
    // Cap the backing store: this is a background field, not the content.
    dpr = Math.min(window.devicePixelRatio || 1, 1.75);
    w = Math.max(1, Math.round(rect.width));
    h = Math.max(1, Math.round(rect.height));
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  /** Deterministic value noise — no Math.random in the render loop. */
  function noise(x) {
    const s = Math.sin(x * 127.1 + 311.7) * 43758.5453;
    return s - Math.floor(s);
  }

  function smoothNoise(x) {
    const i = Math.floor(x);
    const f = x - i;
    const u = f * f * (3 - 2 * f);
    return noise(i) * (1 - u) + noise(i + 1) * u;
  }

  function drawGraticule() {
    ctx.save();
    ctx.strokeStyle = "rgba(124, 148, 172, 0.055)";
    ctx.lineWidth = 1;
    const step = Math.max(46, Math.round(w / 14));
    ctx.beginPath();
    for (let x = (w % step) / 2; x < w; x += step) {
      ctx.moveTo(Math.round(x) + 0.5, 0);
      ctx.lineTo(Math.round(x) + 0.5, h);
    }
    for (let y = (h % step) / 2; y < h; y += step) {
      ctx.moveTo(0, Math.round(y) + 0.5);
      ctx.lineTo(w, Math.round(y) + 0.5);
    }
    ctx.stroke();
    ctx.restore();
  }

  function trace(offset, amp, freq, phase, alpha, colour) {
    const mid = h * (0.42 + offset * 0.16);
    const span = h * amp;

    ctx.save();
    ctx.beginPath();
    for (let x = 0; x <= w; x += 2) {
      const u = x / w;
      const n =
        smoothNoise(u * freq + phase + t * 0.11) * 0.62 +
        smoothNoise(u * freq * 2.7 + phase * 1.9 + t * 0.19) * 0.26 +
        smoothNoise(u * freq * 6.1 + phase * 0.6 + t * 0.31) * 0.12;

      // Lean the trace toward the pointer, as a beam would follow a control.
      const lean = (px - 0.5) * (1 - Math.abs(u - 0.5) * 1.2);
      const y = mid - (n - 0.5) * 2 * span + lean * h * 0.05 * Math.sin(u * Math.PI);

      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = colour;
    ctx.globalAlpha = alpha;
    ctx.lineWidth = 1.25;
    ctx.lineJoin = "round";
    ctx.stroke();
    ctx.restore();
  }

  function render() {
    ctx.clearRect(0, 0, w, h);
    drawGraticule();

    px += (targetX - px) * 0.04;
    py += (targetY - py) * 0.04;

    trace(0, 0.3, 3.1, 0.0, 0.5, "rgba(114, 255, 217, 0.55)");
    trace(1.1, 0.19, 4.7, 21.3, 0.34, "rgba(120, 166, 255, 0.6)");
    trace(2.0, 0.1, 7.9, 47.1, 0.2, "rgba(255, 109, 122, 0.5)");

    // Cursor line — the instrument's read point.
    const cx = w * (0.18 + px * 0.64);
    ctx.save();
    ctx.strokeStyle = "rgba(114, 255, 217, 0.16)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(Math.round(cx) + 0.5, 0);
    ctx.lineTo(Math.round(cx) + 0.5, h);
    ctx.stroke();
    ctx.restore();
  }

  function loop() {
    t += 0.006;
    render();
    raf = requestAnimationFrame(loop);
  }

  function start() {
    if (reduced || paused) {
      render();
      return;
    }
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(loop);
  }

  resize();
  render();
  if (!reduced) start();

  window.addEventListener("resize", () => {
    resize();
    render();
  });

  window.addEventListener("pointermove", (e) => {
    const rect = canvas.getBoundingClientRect();
    targetX = (e.clientX - rect.left) / rect.width;
    targetY = (e.clientY - rect.top) / rect.height;
  }, { passive: true });

  // Stop drawing when the hero is off-screen — no wasted frames.
  if ("IntersectionObserver" in window) {
    new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) start();
        else cancelAnimationFrame(raf);
      }
    }, { threshold: 0 }).observe(canvas);
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) cancelAnimationFrame(raf);
    else start();
  });

  // A change to the motion preference takes effect without a reload.
  reduceQuery.addEventListener("change", (e) => {
    if (e.matches) {
      cancelAnimationFrame(raf);
      render();
    } else {
      start();
    }
  });

  // WCAG 2.2.2: the trace runs automatically next to other content, so offer a
  // visible, keyboard-operable way to stop it.
  const toggle = document.getElementById("motion-toggle");
  if (toggle) {
    const label = toggle.querySelector(".btn__label");
    const icon = toggle.querySelector(".btn__icon");

    const sync = () => {
      const stopped = paused || reduced;
      toggle.setAttribute("aria-pressed", String(stopped));
      toggle.hidden = false;
      if (label) label.textContent = stopped ? "Resume the trace" : "Pause the trace";
      if (icon) icon.textContent = stopped ? "▶" : "‖";
    };

    toggle.addEventListener("click", () => {
      if (reduced) return;
      paused = !paused;
      if (paused) {
        cancelAnimationFrame(raf);
        render();
      } else {
        start();
      }
      sync();
    });

    reduceQuery.addEventListener("change", sync);
    sync();
  }
}

/* ── contact field ──────────────────────────────────────────────────────── */

/** A single low-contrast horizontal sweep; nothing more. */
function initContactField() {
  const canvas = document.getElementById("contact-field");
  if (!canvas) return;
  const ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let w = 0, h = 0, raf = 0, t = 0;

  function resize() {
    const r = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    w = Math.max(1, Math.round(r.width));
    h = Math.max(1, Math.round(r.height));
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function render() {
    ctx.clearRect(0, 0, w, h);
    const y = h * 0.62;
    ctx.save();
    ctx.beginPath();
    for (let x = 0; x <= w; x += 3) {
      const u = x / w;
      const v =
        Math.sin(u * 26 + t * 1.1) * 0.5 +
        Math.sin(u * 61 - t * 0.7) * 0.28 +
        Math.sin(u * 13 + t * 0.4) * 0.22;
      const yy = y - v * h * 0.1;
      if (x === 0) ctx.moveTo(x, yy);
      else ctx.lineTo(x, yy);
    }
    ctx.strokeStyle = "rgba(114, 255, 217, 0.22)";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.restore();
  }

  function loop() {
    t += 0.012;
    render();
    raf = requestAnimationFrame(loop);
  }

  resize();
  render();
  if (!reduced) {
    raf = requestAnimationFrame(loop);
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) cancelAnimationFrame(raf);
      else raf = requestAnimationFrame(loop);
    });
  }
  window.addEventListener("resize", () => { resize(); render(); });
}

/* ── 3. interactions ────────────────────────────────────────────────────── */

function initMobileNav() {
  const btn = document.querySelector(".menu");
  const panel = document.getElementById("mobile-nav");
  if (!btn || !panel) return;

  function set(open) {
    btn.setAttribute("aria-expanded", String(open));
    panel.hidden = !open;
  }

  btn.addEventListener("click", () => {
    set(btn.getAttribute("aria-expanded") !== "true");
  });

  panel.addEventListener("click", (e) => {
    if (e.target.tagName === "A") set(false);
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && btn.getAttribute("aria-expanded") === "true") {
      set(false);
      btn.focus();
    }
  });

  // The CSS breakpoint is 46rem; match it with a media query rather than a
  // hard-coded pixel count, so the two cannot drift apart.
  const wide = window.matchMedia("(min-width: 46.0625rem)");
  wide.addEventListener("change", (e) => {
    if (e.matches) set(false);
  });
}

/** Add a hairline marker to the nav for the section in view. */
function initScrollSpy() {
  const links = [...document.querySelectorAll(".nav a")];
  if (!links.length || !("IntersectionObserver" in window)) return;

  const targets = links
    .map((a) => document.querySelector(a.getAttribute("href")))
    .filter(Boolean);

  const spy = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        for (const a of links) {
          const active = a.getAttribute("href") === `#${entry.target.id}`;
          a.style.color = active ? "var(--ink)" : "";
          a.style.borderBottomColor = active ? "var(--mint)" : "transparent";
        }
      }
    },
    { rootMargin: "-45% 0px -50% 0px" }
  );

  targets.forEach((t) => spy.observe(t));
}

/* ── boot ───────────────────────────────────────────────────────────────── */

async function boot() {
  initMobileNav();
  initScrollSpy();
  initHeroField();
  initContactField();

  const manifest = await loadManifest();
  renderMetrics(manifest);

  document.documentElement.dataset.metrics = manifest ? "loaded" : "missing";
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}
