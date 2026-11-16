/* Sheet 01: the headline question, the finding readout, title-block metadata,
   strip references and the "dates disagree" callout.

   The other modules report what they loaded with:
     TD.report(kind, { ok, data, message })
   where kind is "series" (chart), "trend" (verdict), "odds" (event chance) or "map". */
(function () {
  const reduce = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (sel) => document.querySelector(sel);
  const SHEETS = { series: "#chart-panel", trend: "#chart-panel", odds: "#probability-panel", map: "#map-panel" };
  const GLYPH = { up: "▲", down: "▼", none: "—" };
  const SHORT = { temperature: "T2M", precipitation: "PRECIP", soil_moisture: "SOIL" };

  let sel = { state: "", variable: "", depth: "" };
  let loaded = {};

  function optionText(id) {
    const s = document.getElementById(id);
    const o = s && s.selectedOptions[0];
    return o ? o.textContent.replace(/\s*\(no data yet\)$/, "") : "";
  }

  function meta(key, value) {
    const el = document.querySelector(`[data-meta="${key}"]`);
    if (el) el.textContent = value || "–";
  }

  function f(key) { return document.querySelector(`[data-f="${key}"]`); }
  function cell(key) { return document.querySelector(`[data-finding="${key}"]`); }

  function setBusy(el, busy) { if (el) el.setAttribute("aria-busy", busy ? "true" : "false"); }

  function question() {
    const state = optionText("state-select");
    const v = sel.variable;
    const h1 = $("#question");
    if (!state || !h1) return;
    const span = `<span class="q-accent">${state.replace(/</g, "&lt;")}</span>`;
    const q = v === "temperature" ? `Is ${span} really getting warmer?`
      : v === "precipitation" ? `Is rainfall in ${span} really changing?`
      : v === "soil_moisture" ? `Is soil moisture in ${span} really changing?`
      : `Is ${span} really changing?`;
    h1.innerHTML = q;
  }

  function strips() {
    const code = sel.state || "–";
    const v = SHORT[sel.variable] || (sel.variable || "").toUpperCase();
    const ref = (n, extra) => {
      const el = document.querySelector(`[data-ref="${n}"]`);
      if (!el) return;
      el.innerHTML = `TD-${n} · ${code} · ${v}` + (extra ? ` · <span class="valid">${extra}</span>` : "");
    };
    const t = loaded.trend && loaded.trend.ok && loaded.trend.data.results[0];
    ref("01", "DRAWN " + today().toUpperCase());
    ref("02", t ? t.details.years.replace(/\s*\(.*\)/, "") : "");
    ref("03", loaded.odds && loaded.odds.ok ? "VALID " + loaded.odds.data.for_month.toUpperCase() : "");
    ref("04", loaded.map && loaded.map.ok && loaded.map.data.for_month ? "VALID " + loaded.map.data.for_month.toUpperCase() : "");
  }

  function today() {
    return new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  }

  // Counters tick to their value instead of jumping.
  function tick(el, text) {
    const m = /^([+−-]?)(\d+(?:\.\d+)?)(.*)$/.exec(text);
    if (!m || reduce() || !window.gsap) { el.textContent = text; return; }
    const target = parseFloat(m[2]);
    const dp = (m[2].split(".")[1] || "").length;
    const c = { n: 0 };
    gsap.to(c, {
      n: target, duration: 0.8, ease: "power2.out",
      onUpdate: () => (el.textContent = m[1] + c.n.toFixed(dp) + m[3]),
      onComplete: () => (el.textContent = text),
    });
  }

  function showTrend(r) {
    const badge = f("badge"), line = f("line");
    const c = cell("verdict"), ch = cell("change");
    setBusy(c, false); setBusy(ch, false);
    if (!r.ok) {
      badge.className = "finding__badge";
      badge.textContent = "No verdict";
      line.textContent = r.message || "There isn't enough data to test for a trend.";
      f("change").textContent = "";
      f("change-sub").textContent = "";
      return;
    }
    const d = r.data, first = d.results[0];
    const sig = first.kind !== "none";
    badge.className = "finding__badge" + (sig ? " is-sig" : "");
    badge.textContent = GLYPH[first.kind] + " " + first.badge;
    const sentence = first.sentence.split(/(?<=\.)\s/)[0];
    line.textContent = sentence + (d.agreement ? " " + d.agreement : "");

    // "+0.41 °C per decade" → "+0.41" and "°C / decade"
    const m = /^([+−-]?[\d.]+)\s*(.*?)\s*per decade/.exec(first.details.slope);
    const total = /\(([^)]*?) in total since (\d{4})\)/.exec(first.sentence);
    if (m) {
      tick(f("change"), m[1]);
      f("change-sub").textContent = m[2] + " / decade" + (total ? " · " + total[1] + " since " + total[2] : "");
    } else {
      f("change").textContent = first.details.slope;
      f("change-sub").textContent = "";
    }
    meta("dataset", d.results.map((x) => x.name).join(" · "));
    meta("period", first.details.years);
    meta("method", "Seasonal Mann-Kendall · Sen's slope");
  }

  function showOdds(r) {
    const c = cell("odds");
    setBusy(c, false);
    c.classList.remove("is-high");
    if (!r.ok) {
      f("odds").textContent = "";
      f("odds-sub").textContent = r.message || "No estimate for this measurement.";
      meta("valid", "");
      return;
    }
    const top = r.data.events[0];
    tick(f("odds"), top.probability_pct + "%");
    f("odds-sub").textContent = top.label + " · usually " + top.normal_pct + "%";
    c.classList.toggle("is-high", top.trend === "higher");
    meta("valid", r.data.for_month);
  }

  function dateCallout() {
    const box = $("#date-callout");
    const odds = loaded.odds && loaded.odds.ok && loaded.odds.data.for_month;
    const map = loaded.map && loaded.map.ok && loaded.map.data.for_month;
    if (odds && map && odds !== map) {
      box.dataset.tag = "Dates differ";
      box.textContent = `The map's estimates are for ${map}; the event odds are for ${odds}. Read them as separate forecasts.`;
      box.hidden = false;
    } else {
      box.hidden = true;
    }
  }

  function report(kind, r) {
    loaded[kind] = r;
    const sheet = SHEETS[kind] && $(SHEETS[kind]);
    if (kind === "series") {
      if (r.ok) meta("units", r.data.unit);
      else meta("units", "");
    }
    if (kind === "trend") showTrend(r);
    if (kind === "odds") showOdds(r);
    // The record sheet is busy until both its chart and its verdict are in.
    if (kind === "series" || kind === "trend") {
      setBusy(sheet, !(loaded.series && loaded.trend));
    } else {
      setBusy(sheet, false);
    }
    strips();
    dateCallout();
  }

  document.addEventListener("trend:select", (e) => {
    sel = e.detail;
    loaded = {};
    document.querySelectorAll(".finding__cell, #chart-panel, #probability-panel, #map-panel")
      .forEach((el) => setBusy(el, true));
    f("badge").className = "finding__badge";
    f("badge").textContent = "Plotting…";
    f("line").textContent = "";
    ["change", "odds"].forEach((k) => (f(k).textContent = ""));
    ["change-sub", "odds-sub"].forEach((k) => (f(k).textContent = ""));
    ["dataset", "period", "units", "valid", "method"].forEach((k) => meta(k, ""));
    meta("drawn", today());
    question();
    strips();
    $("#date-callout").hidden = true;
  });

  window.TD = { report };
})();
