/* Plain-English trend verdict under the chart. */
(function () {
  const box = document.getElementById("verdict");
  let requestId = 0;
  const ICONS = { up: "fa-arrow-trend-up", down: "fa-arrow-trend-down", none: "fa-minus" };

  function text(tag, cls, str) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    n.textContent = str;
    return n;
  }

  function block(r) {
    const wrap = document.createElement("div");
    wrap.className = "verdict-item";

    const head = document.createElement("div");
    head.className = "verdict-head";
    const badge = document.createElement("span");
    badge.className = "badge-trend badge-" + r.kind;
    const icon = document.createElement("i");
    icon.className = "fa-solid " + ICONS[r.kind];
    icon.setAttribute("aria-hidden", "true");
    badge.append(icon, " " + r.badge);
    head.appendChild(badge);
    if (r.label) head.appendChild(text("span", "verdict-model", r.label));
    wrap.appendChild(head);

    wrap.appendChild(text("p", "verdict-text", r.sentence));
    if (r.note) wrap.appendChild(text("p", "verdict-warn", r.note));

    const det = document.createElement("details");
    det.appendChild(text("summary", "", "The numbers"));
    const dl = document.createElement("dl");
    [["Rate of change", r.details.slope], ["Likely range", r.details.range],
     ["p-value", r.details.p_value], ["Period", r.details.years]].forEach(([k, v]) => {
      dl.appendChild(text("dt", "", k));
      dl.appendChild(text("dd", "", v));
    });
    det.appendChild(dl);
    wrap.appendChild(det);
    return wrap;
  }

  function clear() { box.replaceChildren(); }

  async function load({ state, variable, depth }) {
    const id = ++requestId;
    clear();
    try {
      const res = await fetch(`/api/trend?state=${state}&variable=${variable}&depth=${depth || ""}`);
      const d = await res.json();
      if (id !== requestId || !res.ok || !d.available) return; // the chart already explains missing data
      d.results.forEach((r) => box.appendChild(block(r)));
      if (d.agreement) box.appendChild(text("p", "verdict-agree", d.agreement));
      box.appendChild(text("p", "verdict-method", d.method));
    } catch (err) {
      box.appendChild(text("p", "verdict-warn", "We couldn't test for a trend. Please try again."));
    }
  }

  document.addEventListener("trend:select", (e) => load(e.detail));
})();
