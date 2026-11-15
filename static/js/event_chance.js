/* "Chance of an event" card. Redraws whenever the dropdowns change. */
(function () {
  const $ = (id) => document.getElementById(id);
  const el = {
    value: $("prob-value"), label: $("prob-label"), tag: $("prob-tag"),
    meter: $("prob-meter"), fill: $("meter-fill"), tick: $("meter-tick"),
    legend: $("meter-legend"), sentence: $("prob-sentence"),
    others: $("prob-others"), basis: $("prob-basis"), note: $("prob-note"),
  };
  const TAGS = { higher: "Higher than usual", lower: "Lower than usual", usual: "About usual" };
  let requestId = 0;
  let tween = null;

  function reset(message) {
    el.value.textContent = "\u2013";
    el.label.textContent = message;
    [el.tag, el.meter, el.legend].forEach((n) => (n.hidden = true));
    el.sentence.textContent = "";
    el.others.innerHTML = "";
    el.basis.textContent = "";
    el.note.textContent = "";
  }

  function showNumber(target) {
    if (tween) tween.kill();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!window.gsap || reduce) { el.value.textContent = target + "%"; return; }
    const counter = { n: 0 };
    tween = gsap.to(counter, {
      n: target, duration: 0.6, ease: "power2.out",
      onUpdate: () => (el.value.textContent = Math.round(counter.n) + "%"),
      onComplete: () => (el.value.textContent = target + "%"),
    });
  }

  function pctText(n) { return n < 1 ? "less than 1%" : n + "%"; }

  function draw(d) {
    const top = d.events[0];
    showNumber(top.probability_pct);
    el.label.textContent = top.label + " \u00b7 " + top.hazard;

    el.tag.textContent = TAGS[top.trend];
    el.tag.className = "tag tag-" + top.trend;
    el.tag.hidden = false;

    el.fill.style.width = Math.min(top.probability_pct, 100) + "%";
    el.tick.style.left = Math.min(top.normal_pct, 100) + "%";
    el.meter.setAttribute("aria-label",
      "Chance " + top.probability_pct + " percent; usually " + top.normal_pct + " percent");
    el.meter.hidden = false;
    el.legend.textContent = "The marker shows how often this usually happens (" + top.normal_pct + "%).";
    el.legend.hidden = false;

    el.sentence.textContent = top.sentence + (top.skill_text ? " " + top.skill_text : "");

    el.others.innerHTML = "";
    d.events.slice(1).forEach((e) => {
      const li = document.createElement("li");
      li.textContent = e.label + " (" + e.hazard + "): " + pctText(e.probability_pct) +
        " \u2013 usually " + e.normal_pct + "%";
      el.others.appendChild(li);
    });

    el.basis.textContent = d.basis;
    el.note.textContent = d.note;
  }

  async function load({ state, variable, depth }) {
    const id = ++requestId;
    reset("Working it out\u2026");
    try {
      const res = await fetch(`/api/event-chance?state=${state}&variable=${variable}&depth=${depth || ""}`);
      const d = await res.json();
      if (id !== requestId) return;
      if (!res.ok) return reset(d.error || "Something went wrong.");
      if (!d.available) return reset(d.message);
      draw(d);
    } catch (err) {
      reset("We couldn't work this out. Check that the server is running, then try again.");
    }
  }

  document.addEventListener("trend:select", (e) => load(e.detail));
})();
