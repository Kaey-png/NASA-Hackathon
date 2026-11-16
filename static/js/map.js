/* State-level risk map (MapLibre GL JS), using rows from /api/hotspots.
   Flat by default; the "3D terrain" chip tilts it and turns terrain on.
   Hazards are drawn as ink rings, not glows. Hazards that share a location
   are nudged apart so neither hides the other. */
(function () {
  const msg = document.getElementById("map-message");
  const legend = document.getElementById("map-legend");
  const note = document.getElementById("map-note");
  const list = document.getElementById("map-list");
  const demoTag = document.getElementById("map-demo");
  const readout = document.getElementById("map-readout");
  const toggle3d = document.getElementById("toggle-3d");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const coarse = window.matchMedia("(pointer: coarse)").matches;

  const EMPTY = { type: "FeatureCollection", features: [] };
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  // Theme tokens win over the API's colours; the API colour is the fallback.
  const TOKEN = { drought: css("--hz-drought"), flood: css("--hz-flood") };
  const colorFor = (h) => TOKEN[h.phenomenon] || h.color;

  // Size grows with probability; zoomed-out view uses smaller rings.
  const sizeAt = (lo, hi) => ["interpolate", ["linear"], ["get", "p"], 0, lo, 100, hi];
  const radius = ["interpolate", ["linear"], ["zoom"], 4, sizeAt(10, 34), 8, sizeAt(18, 56)];

  const style = {
    version: 8,
    sources: {
      base: {
        type: "raster", tileSize: 256, maxzoom: 19,
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        attribution: "© OpenStreetMap contributors",
      },
      dem: {
        type: "raster-dem", encoding: "terrarium", tileSize: 256, maxzoom: 15,
        tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
        attribution: "Terrain: Mapzen / AWS Terrain Tiles",
      },
      hotspots: { type: "geojson", data: EMPTY },
    },
    layers: [
      // Blue plan paper under inverted, desaturated OSM tiles: water reads darker,
      // land lifts to blue-grey, lines and labels go pale blue.
      { id: "paper", type: "background", paint: { "background-color": "#05183a" } },
      { id: "base", type: "raster", source: "base", paint: {
          "raster-opacity": 0.78,
          "raster-brightness-min": 0.9, "raster-brightness-max": 0.04,
          "raster-saturation": -1, "raster-contrast": 0.3 } },
      { id: "shade", type: "hillshade", source: "dem", paint: {
          "hillshade-exaggeration": 0.5, "hillshade-shadow-color": "#000000",
          "hillshade-highlight-color": "#1a4a80", "hillshade-accent-color": "#061c33" } },
      { id: "core", type: "circle", source: "hotspots", paint: {
          "circle-color": ["get", "color"], "circle-opacity": 0.18,
          "circle-radius": radius,
          "circle-stroke-color": ["get", "color"], "circle-stroke-width": 2,
          "circle-pitch-alignment": "map" } },
      { id: "centre", type: "circle", source: "hotspots", paint: {
          "circle-color": ["get", "color"], "circle-radius": 3, "circle-pitch-alignment": "map" } },
    ],
  };

  let map = null;
  try {
    map = new maplibregl.Map({
      container: "map", style: style, center: [-98, 39], zoom: 3.2, pitch: 0, bearing: 0,
      maxPitch: 75, attributionControl: false,
      cooperativeGestures: coarse,
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }));
  } catch (err) {
    msg.textContent = "The map needs WebGL, which this browser isn't providing. The hotspot list below still works.";
    toggle3d.hidden = true;
  }

  let ready = false, pending = null, requestId = 0, last = null, is3d = false;
  if (map) map.on("load", () => { ready = true; msg.textContent = ""; if (pending) { apply(pending); pending = null; } });

  const popup = map && new maplibregl.Popup({ closeButton: false, offset: 12 });
  if (map) {
    map.on("click", "core", (e) => {
      const f = e.features[0];
      const div = document.createElement("div");
      const strong = document.createElement("strong");
      strong.textContent = f.properties.label + ": " + f.properties.p + "%";
      div.appendChild(strong);
      popup.setLngLat(e.lngLat).setDOMContent(div).addTo(map);
    });
    map.on("mouseenter", "core", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "core", () => (map.getCanvas().style.cursor = ""));

    // CAD readout of the cursor position.
    map.on("mousemove", (e) => {
      const { lat, lng } = e.lngLat;
      readout.textContent = "LAT " + Math.abs(lat).toFixed(2) + (lat >= 0 ? " N" : " S") +
        "  LON " + Math.abs(lng).toFixed(2) + (lng >= 0 ? " E" : " W");
      readout.classList.add("is-on");
    });
    map.getCanvas().addEventListener("mouseleave", () => readout.classList.remove("is-on"));
  }

  function setView(d) {
    if (!map || !last) return;
    const pitch = is3d ? 50 : 0, bearing = is3d ? -10 : 0;
    const bb = d.bbox; // [south, west, north, east]
    const opts = { pitch, bearing, padding: 36, duration: reduceMotion ? 0 : 1400 };
    if (bb) map.fitBounds([[bb[1], bb[0]], [bb[3], bb[2]]], opts);
    else map.easeTo({ center: [d.view.lon, d.view.lat], zoom: d.view.zoom, ...opts });
  }

  toggle3d.addEventListener("click", () => {
    if (!map || !ready) return;
    is3d = !is3d;
    toggle3d.setAttribute("aria-pressed", String(is3d));
    map.setTerrain(is3d ? { source: "dem", exaggeration: 1.6 } : null);
    setView(last);
  });

  function renderLegend(items) {
    legend.replaceChildren();
    items.forEach((it) => {
      const li = document.createElement("li");
      const dot = document.createElement("span");
      dot.className = "legend-dot";
      dot.style.color = TOKEN[it.key] || it.color;
      li.append(dot, it.label);
      legend.appendChild(li);
    });
    if (items.length) {
      const li = document.createElement("li");
      li.className = "legend-hint";
      li.textContent = "Bigger ring = higher model-estimated risk";
      legend.appendChild(li);
    }
  }

  function renderList(hotspots) {
    list.replaceChildren();
    hotspots.slice(0, 5).forEach((h) => {
      const li = document.createElement("li");
      li.textContent = h.label + " · " + h.probability_pct + "% · statewide estimate";
      list.appendChild(li);
    });
  }

  // Nudge hazards that share a point apart, east-west, so both rings show.
  function spread(hotspots) {
    const groups = new Map();
    hotspots.forEach((h) => {
      const k = h.lat.toFixed(3) + "," + h.lon.toFixed(3);
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(h);
    });
    const out = [];
    groups.forEach((g) => g.forEach((h, i) => {
      const off = g.length > 1 ? (i - (g.length - 1) / 2) * 0.9 : 0;
      out.push({ ...h, lon: h.lon + off });
    }));
    return out;
  }

  function apply(d) {
    popup.remove();
    map.getSource("hotspots").setData({
      type: "FeatureCollection",
      features: spread(d.hotspots).map((h) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [h.lon, h.lat] },
        properties: {
          p: h.probability_pct, color: colorFor(h), label: h.label,
        },
      })),
    });
    setView(d);
    msg.textContent = d.available ? "" : d.message;
  }

  async function load({ state }) {
    const id = ++requestId;
    try {
      const res = await fetch("/api/hotspots?state=" + state);
      const d = await res.json();
      if (id !== requestId) return;
      if (!res.ok) {
        msg.textContent = d.error || "Something went wrong loading the map.";
        if (window.TD) TD.report("map", { ok: false, message: d.error });
        return;
      }
      last = d;
      if (window.TD) TD.report("map", { ok: d.available, data: d, message: d.message });

      demoTag.hidden = !(d.demo && d.available);
      renderLegend(d.available ? d.legend : []);
      renderList(d.hotspots);
      note.textContent = d.available
        ? (d.demo ? "Demo data: made-up hotspots for testing, not real predictions. " : "") +
          "State-level estimates for " + d.for_month +
          ". Markers sit near the state's centre, not at localized hotspots; where two hazards share a point they are drawn side by side. " +
          "Estimates are experimental, not official alerts. Click a ring for details." +
          (d.skipped ? " " + d.skipped + " row(s) in the hotspot file were skipped (see the server log)." : "")
        : (d.skipped ? d.skipped + " row(s) in the hotspot file were skipped (see the server log)." : "");
      if (!map) { if (!d.available) msg.textContent = d.message; return; }
      if (ready) apply(d); else pending = d;
    } catch (err) {
      if (id !== requestId) return;
      msg.textContent = "We couldn't load the hotspots. Check that the server is running, then try again.";
      if (window.TD) TD.report("map", { ok: false, message: "Map failed to load." });
    }
  }

  document.addEventListener("trend:select", (e) => load(e.detail));
})();
