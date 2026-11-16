/* Plain-English trend verdict beside the chart.
   Significance is shown by line style (solid = significant, dashed = not);
   direction by a glyph and words, never by colour alone. */
(function () {
  const box = document.getElementById("verdict");
  let requestId = 0;
  const GLYPH = { up: "▲", down: "▼", none: "—" };

  function text(tag, cls, str) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    n.textContent = str;
    return n;
  }

  function report(r) { if (window.TD) TD.report("trend", r); }

  function stat(label, value) {
    const div = document.createElement("div");
    div.append(text("dt", "", label), text("dd", "", value));
    return div;
  }

  function block(r) {
    const wrap = document.createElement("div");
    wrap.className = "verdict-item" + (r.kind !== "none" ? " is-sig" : "");

    const head = document.createElement("div");
    head.className = "verdict-head";
    const badge = document.createElement("span");
    badge.className = "badge-trend badge-" + r.kind;
    const glyph = text("span", "", GLYPH[r.kind]);
    glyph.setAttribute("aria-hidden", "true");
    badge.append(glyph, " " + r.badge);
    head.appendChild(badge);
    if (r.label) head.appendChild(text("span", "verdict-model", r.label));
    wrap.appendChild(head);

    wrap.appendChild(text("p", "verdict-text", r.sentence));
    if (r.note) wrap.appendChild(text("p", "verdict-warn", r.note));

    // The key numbers stay visible, as title-block cells.
    const stats = document.createElement("dl");
    stats.className = "verdict-stats";
    stats.append(stat("Rate", r.details.slope), stat("p-value", r.details.p_value));
    wrap.appendChild(stats);

    const det = document.createElement("details");
    det.appendChild(text("summary", "", "More detail"));
    const dl = document.createElement("dl");
    [["Likely range", r.details.range], ["Period", r.details.years]].forEach(([k, v]) => {
      dl.appendChild(text("dt", "", k));
      dl.appendChild(text("dd", "", v));
    });
    det.appendChild(dl);
    wrap.appendChild(det);
    return wrap;
  }

  function skeleton() {
    const s = document.createElement("div");
    s.className = "verdict-skeleton";
    s.append(text("b", "", "Testing for a trend…"), document.createElement("span"), document.createElement("span"));
    box.replaceChildren(s);
  }

  function fail(message, isError) {
    const p = text("p", "callout" + (isError ? " callout--error" : ""), message);
    if (!isError) p.dataset.tag = "No verdict";
    box.replaceChildren(p);
  }

  async function load({ state, variable, depth }) {
    const id = ++requestId;
    skeleton();
    try {
      const res = await fetch(`/api/trend?state=${state}&variable=${variable}&depth=${depth || ""}`);
      const d = await res.json();
      if (id !== requestId) return;
      if (!res.ok) {
        fail(d.error || "Something went wrong testing for a trend.", true);
        return report({ ok: false, message: d.error });
      }
      if (!d.available) {
        fail(d.message, false);
        return report({ ok: false, message: d.message });
      }
      box.replaceChildren();
      d.results.forEach((r) => box.appendChild(block(r)));
      if (d.agreement) box.appendChild(text("p", "verdict-agree", d.agreement));
      box.appendChild(text("p", "verdict-method", d.method));
      report({ ok: true, data: d });
    } catch (err) {
      if (id !== requestId) return;
      fail("We couldn't test for a trend. Check that the server is running, then try again.", true);
      report({ ok: false, message: "The trend test failed to load." });
    }
  }

  document.addEventListener("trend:select", (e) => load(e.detail));
})();
