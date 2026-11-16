/* "Chance of an event" sheet. Redraws whenever the dropdowns change.
   The meter grows in when scrolled into view; the part above "usual" is
   hatched red, because hatching on this page means "risk above usual". */
(function () {
  const $ = (id) => document.getElementById(id);
  const el = {
    value: $("prob-value"), label: $("prob-label"), tag: $("prob-tag"),
    meter: $("prob-meter"), fill: $("meter-fill"), excess: $("meter-excess"), tick: $("meter-tick"),
    legend: $("meter-legend"), sentence: $("prob-sentence"),
    others: $("prob-others"), basis: $("prob-basis"), note: $("prob-note"),
  };
  const TAGS = { higher: "Higher than usual", lower: "Lower than usual", usual: "About usual" };
  const GLYPH = { higher: "▲ ", lower: "▼ ", usual: "— " };
  const reduce = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let requestId = 0;
  let tween = null;
  let seen = !("IntersectionObserver" in window);
  let pendingMeter = null;

  function report(r) { if (window.TD) TD.report("odds", r); }

  function reset(message) {
    el.value.textContent = "–";
    el.value.classList.remove("is-high");
    el.label.textContent = message;
    [el.tag, el.meter, el.legend].forEach((n) => (n.hidden = true));
    el.fill.style.width = "0";
    el.excess.style.width = "0";
    el.sentence.textContent = "";
    el.others.innerHTML = "";
    el.basis.textContent = "";
    el.note.textContent = "";
  }

  function showNumber(target) {
    if (tween) tween.kill();
    if (!window.gsap || reduce()) { el.value.textContent = target + "%"; return; }
    const counter = { n: 0 };
    tween = gsap.to(counter, {
      n: target, duration: 0.8, ease: "power2.out",
      onUpdate: () => (el.value.textContent = Math.round(counter.n) + "%"),
      onComplete: () => (el.value.textContent = target + "%"),
    });
  }

  function setMeter(m) {
    if (!seen) { pendingMeter = m; return; }
    el.fill.style.width = m.p + "%";
    el.tick.style.left = m.usual + "%";
    el.excess.style.left = m.usual + "%";
    el.excess.style.width = Math.max(0, m.p - m.usual) + "%";
  }

  if (!seen) {
    const io = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting)) return;
      seen = true;
      io.disconnect();
      if (pendingMeter) { setMeter(pendingMeter); pendingMeter = null; }
    }, { threshold: 0.4 });
    io.observe(el.meter.parentElement);
  }

  function pctText(n) { return n < 1 ? "less than 1%" : n + "%"; }

  function draw(d) {
    const top = d.events[0];
    showNumber(top.probability_pct);
    el.value.classList.toggle("is-high", top.trend === "higher");
    el.label.textContent = top.label + " · " + top.hazard;

    el.tag.textContent = GLYPH[top.trend] + TAGS[top.trend];
    el.tag.className = "tag tag-" + top.trend;
    el.tag.hidden = false;

    el.meter.hidden = false;
    el.meter.setAttribute("aria-label",
      "Chance " + top.probability_pct + " percent; usually " + top.normal_pct + " percent");
    setMeter({ p: Math.min(top.probability_pct, 100), usual: Math.min(top.normal_pct, 100) });
    el.legend.textContent = "The amber marker shows how often this usually happens (" + top.normal_pct + "%)." +
      (top.probability_pct > top.normal_pct ? " Hatched red: the extra chance above usual." : "");
    el.legend.hidden = false;

    el.sentence.textContent = top.sentence + (top.skill_text ? " " + top.skill_text : "");

    el.others.innerHTML = "";
    d.events.slice(1).forEach((e) => {
      const li = document.createElement("li");
      li.textContent = e.label + " (" + e.hazard + "): " + pctText(e.probability_pct) +
        " – usually " + e.normal_pct + "%";
      el.others.appendChild(li);
    });

    el.basis.textContent = d.basis;
    el.note.textContent = d.note;
  }

  async function load({ state, variable, depth }) {
    const id = ++requestId;
    reset("Working it out…");
    try {
      const res = await fetch(`/api/event-chance?state=${state}&variable=${variable}&depth=${depth || ""}`);
      const d = await res.json();
      if (id !== requestId) return;
      if (!res.ok) { reset(d.error || "Something went wrong."); return report({ ok: false, message: d.error }); }
      if (!d.available) { reset(d.message); return report({ ok: false, message: d.message }); }
      draw(d);
      report({ ok: true, data: d });
    } catch (err) {
      if (id !== requestId) return;
      reset("We couldn't work this out. Check that the server is running, then try again.");
      report({ ok: false, message: "The estimate failed to load." });
    }
  }

  document.addEventListener("trend:select", (e) => load(e.detail));
})();
