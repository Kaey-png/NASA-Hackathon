/* Time series chart. Redraws whenever the dropdowns change.
   Each data source (e.g. FLDAS, NLDAS) gets its own colour. */
(function () {
  const box = document.getElementById("chart");
  const sourceNote = document.getElementById("chart-source");
  let requestId = 0;

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function message(text) {
    if (window.Plotly) Plotly.purge(box);
    box.innerHTML = "";
    const p = document.createElement("p");
    p.className = "placeholder";
    p.textContent = text;
    box.appendChild(p);
    sourceNote.textContent = "";
  }

  function draw(d) {
    box.innerHTML = "";
    const ink = css("--ink"), soft = css("--ink-soft"), line = css("--line");
    const colors = [css("--teal"), css("--accent"), css("--blue")];
    const multi = d.series.length > 1;
    const named = d.series.every((s) => s.name); // label lines by model when we know it

    const traces = [];
    d.series.forEach((s, i) => {
      const color = colors[i % colors.length];
      const label = named ? s.name + " model" : "Each month";
      // Faint month-by-month line (hidden from the legend, linked to the average)
      traces.push({
        x: s.dates, y: s.values, type: "scatter", mode: "lines",
        name: label + ", monthly", legendgroup: s.name, showlegend: false,
        line: { color: named ? color : soft, width: 1 }, opacity: 0.35,
        hovertemplate: "%{x|%b %Y}: %{y:.1f} " + d.unit + "<extra>" + label + "</extra>",
      });
      // Bold 12-month average
      traces.push({
        x: s.dates, y: s.rolling12, type: "scatter", mode: "lines",
        name: named ? s.name + " model (12-month average)" : "12-month average",
        legendgroup: s.name, connectgaps: false,
        line: { color: color, width: 3 },
        hovertemplate: "%{x|%b %Y}: %{y:.1f} " + d.unit + "<extra>" + (named ? s.name + " average" : "12-month average") + "</extra>",
      });
    });

    // Dashed trend line per source (solid-ish if significant, dotted if not)
    d.series.forEach((s, i) => {
      if (!s.trend) return;
      const color = colors[i % colors.length];
      traces.push({
        x: s.trend.line.x, y: s.trend.line.y, type: "scatter", mode: "lines",
        name: "Trend", legendgroup: s.name, showlegend: false,
        line: { color: color, width: 2, dash: s.trend.significant ? "dash" : "dot" },
        hovertemplate: "Trend: %{y:.1f} " + d.unit + "<extra></extra>",
      });
    });

    const layout = {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Rubik, system-ui, sans-serif", color: ink, size: 14 },
      margin: { l: 56, r: 12, t: 8, b: 40 },
      xaxis: { gridcolor: line, linecolor: line },
      yaxis: { title: { text: d.label + " (" + d.unit + ")" }, gridcolor: line, zeroline: false },
      legend: { orientation: "h", y: -0.2 },
      hovermode: "x unified",
      hoverlabel: { bgcolor: "#0b1220", bordercolor: "rgba(255,255,255,0.12)", font: { color: ink } },
    };
    Plotly.newPlot(box, traces, layout, { responsive: true, displaylogo: false });

    const parts = [];
    if (d.source) parts.push("Source: " + d.source + ".");
    if (d.note && multi) parts.push(d.note);
    parts.push("The dashed line is the overall trend (dotted if it is not statistically significant).");
    parts.push("Drag to zoom, double-click to reset.");
    sourceNote.textContent = parts.join(" ");
  }

  async function load({ state, variable, depth }) {
    const id = ++requestId;
    message("Loading…");
    try {
      const url = `/api/timeseries?state=${state}&variable=${variable}&depth=${depth || ""}`;
      const res = await fetch(url);
      const d = await res.json();
      if (id !== requestId) return; // a newer choice replaced this one
      if (!res.ok) return message(d.error || "Something went wrong loading this chart.");
      if (!d.available) return message(d.message);
      draw(d);
    } catch (err) {
      message("We couldn't load this chart. Check that the server is running, then try again.");
    }
  }

  document.addEventListener("trend:select", (e) => load(e.detail));
})();
