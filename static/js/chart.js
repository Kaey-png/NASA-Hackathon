/* Time series chart. Redraws whenever the dropdowns change.
   Each data source (e.g. FLDAS, NLDAS) gets its own colour.
   Monthly values are hidden by default so the y-axis fits the 12-month
   average and the trend; the "Show monthly values" chip brings them back. */
(function () {
  const box = document.getElementById("chart");
  const sourceNote = document.getElementById("chart-source");
  const readout = document.getElementById("chart-readout");
  const toggle = document.getElementById("toggle-monthly");
  const reduce = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const MONO = "JetBrains Mono, ui-monospace, monospace";
  let requestId = 0;
  let showMonthly = false;
  let last = null;

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function report(r) { if (window.TD) TD.report("series", r); }

  function message(text, isError) {
    if (window.Plotly) Plotly.purge(box);
    box.innerHTML = "";
    const p = document.createElement("p");
    p.className = "placeholder" + (isError ? " is-error" : "");
    p.textContent = text;
    box.appendChild(p);
    sourceNote.textContent = "";
    readout.classList.remove("is-on");
  }

  function fmt(n) { return (n > 0 ? "+" : n < 0 ? "−" : "") + Math.abs(n).toFixed(1); }

  function draw(d, animate) {
    box.innerHTML = "";
    const ink = css("--ink"), soft = css("--ink-2"), rule = css("--rule"), ui = css("--rule-ui");
    const amber = css("--amber");
    const colors = [css("--cyan"), amber, css("--grey")];
    const multi = d.series.length > 1;
    const named = d.series.every((s) => s.name);

    const traces = [];
    const annotations = [];
    d.series.forEach((s, i) => {
      const color = colors[i % colors.length];
      const label = named ? s.name + " model" : "Each month";
      traces.push({
        x: s.dates, y: s.values, type: "scatter", mode: "lines",
        name: label + ", monthly", legendgroup: s.name, showlegend: false,
        visible: showMonthly ? true : false,
        line: { color: named ? color : soft, width: 1 }, opacity: 0.35,
        hovertemplate: "%{y:.1f} " + d.unit + "<extra>" + label + ", monthly</extra>",
      });
      traces.push({
        x: s.dates, y: s.rolling12, type: "scatter", mode: "lines",
        name: named ? s.name + " · 12-month average" : "12-month average",
        legendgroup: s.name, connectgaps: false,
        line: { color: color, width: 2 },
        hovertemplate: "%{y:.2f} " + d.unit + "<extra>" + (named ? s.name + " average" : "12-month average") + "</extra>",
      });
    });

    // Trend line per source: dashed if significant, dotted if not.
    d.series.forEach((s, i) => {
      if (!s.trend) return;
      const { x, y } = s.trend.line;
      traces.push({
        x, y, type: "scatter", mode: "lines",
        name: "Trend", legendgroup: s.name, showlegend: false, hoverinfo: "skip",
        line: { color: amber, width: 2, dash: s.trend.significant ? "dash" : "dot" },
      });
      // Dimension-line callout at the right end of the trend.
      const change = y[y.length - 1] - y[0];
      annotations.push({
        x: x[x.length - 1], y: y[y.length - 1], xref: "x", yref: "y",
        text: (named && multi ? s.name + " · " : "") + fmt(change) + " " + d.unit + " since " + x[0].slice(0, 4) +
          (s.trend.significant ? "" : " · not significant"),
        showarrow: true, arrowhead: 0, arrowcolor: amber, arrowwidth: 1,
        ax: -40, ay: -34 - i * 28,
        bgcolor: css("--well"), bordercolor: amber, borderpad: 4, borderwidth: 1,
        font: { family: MONO, size: 11, color: amber },
      });
    });

    const axis = {
      gridcolor: rule, linecolor: ui, tickcolor: ui, ticks: "outside",
      showspikes: true, spikemode: "across", spikedash: "dot", spikecolor: amber, spikethickness: 1, spikesnap: "cursor",
    };
    const layout = {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: MONO, color: soft, size: 12 },
      margin: { l: 60, r: 16, t: 16, b: 40 },
      xaxis: { ...axis },
      yaxis: { ...axis, title: { text: d.label + " (" + d.unit + ")", font: { color: ink, size: 12 } }, zeroline: false, griddash: "dot" },
      legend: { orientation: "h", y: -0.16, font: { size: 11 } },
      showlegend: true,
      hovermode: "x",
      hoverdistance: -1, spikedistance: -1,
      hoverlabel: { bgcolor: css("--paper-deep"), bordercolor: css("--cyan"), font: { color: ink, family: MONO, size: 12 } },
      annotations,
    };
    Plotly.newPlot(box, traces, layout, { responsive: true, displaylogo: false,
        // Touch makes "hover" always-on, so the toolbar would sit over the annotation.
        displayModeBar: window.matchMedia("(pointer: coarse)").matches ? false : "hover" })
      .then(() => { if (animate) plotIn(); });

    // CAD readout: date and value under the cursor.
    box.on("plotly_hover", (ev) => {
      const pt = ev.points.find((p) => p.y != null);
      if (!pt) return;
      readout.textContent = "X " + String(pt.x).slice(0, 7) + "  Y " + Number(pt.y).toFixed(2) + " " + d.unit;
      readout.classList.add("is-on");
    });
    box.on("plotly_unhover", () => readout.classList.remove("is-on"));

    const parts = [];
    if (d.source) parts.push("Source: " + d.source + ".");
    if (d.note && multi) parts.push(d.note);
    parts.push("The amber line is the overall trend: dashed if statistically significant, dotted if not.");
    parts.push("Drag to zoom, double-click to reset.");
    sourceNote.textContent = parts.join(" ");
  }

  // The lines draw themselves in, then the trend follows.
  function plotIn() {
    if (reduce()) return;
    const paths = box.querySelectorAll(".scatterlayer .trace path.js-line");
    paths.forEach((p, i) => {
      const len = p.getTotalLength ? p.getTotalLength() : 0;
      if (!len) return;
      const isTrend = p.style.strokeDasharray && p.style.strokeDasharray !== "none";
      if (isTrend) {
        p.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500, delay: 900, fill: "backwards" });
        return;
      }
      p.animate(
        [{ strokeDasharray: len + "px " + len + "px", strokeDashoffset: len + "px" },
         { strokeDasharray: len + "px " + len + "px", strokeDashoffset: "0px" }],
        { duration: 900, delay: i * 60, easing: "cubic-bezier(0.55, 0, 0.3, 1)", fill: "backwards" }
      );
    });
  }

  toggle.addEventListener("click", () => {
    showMonthly = !showMonthly;
    toggle.setAttribute("aria-pressed", String(showMonthly));
    if (last) draw(last, false);
  });

  async function load({ state, variable, depth }) {
    const id = ++requestId;
    message("Plotting…");
    try {
      const url = `/api/timeseries?state=${state}&variable=${variable}&depth=${depth || ""}`;
      const res = await fetch(url);
      const d = await res.json();
      if (id !== requestId) return;
      if (!res.ok) {
        message(d.error || "Something went wrong loading this chart.", true);
        return report({ ok: false, message: d.error });
      }
      if (!d.available) {
        message(d.message);
        return report({ ok: false, message: d.message });
      }
      last = d;
      draw(d, true);
      report({ ok: true, data: d });
    } catch (err) {
      if (id !== requestId) return;
      message("We couldn't load this chart. Check that the server is running, then try again.", true);
      report({ ok: false, message: "Chart failed to load." });
    }
  }

  document.addEventListener("trend:select", (e) => load(e.detail));
})();
