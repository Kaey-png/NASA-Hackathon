/* 3D state-level risk map (MapLibre GL JS), using rows from /api/hotspots. */
(function () {
  const msg = document.getElementById("map-message");
  const legend = document.getElementById("map-legend");
  const note = document.getElementById("map-note");
  const list = document.getElementById("map-list");
  const demoTag = document.getElementById("map-demo");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const EMPTY = { type: "FeatureCollection", features: [] };

  // Size grows with probability; zoomed-out view uses smaller dots.
  const sizeAt = (lo, hi) => ["interpolate", ["linear"], ["get", "p"], 0, lo, 100, hi];
  const radius = (k) => [
    "interpolate", ["linear"], ["zoom"],
    4, sizeAt(4 * k, 16 * k), 8, sizeAt(8 * k, 30 * k),
  ];

  const style = {
    version: 8,
    sources: {
      base: {
        type: "raster", tileSize: 256, maxzoom: 19,
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        attribution: "\u00a9 OpenStreetMap contributors",
      },
      dem: {
        type: "raster-dem", encoding: "terrarium", tileSize: 256, maxzoom: 15,
        tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
        attribution: "Terrain: Mapzen / AWS Terrain Tiles",
      },
      hotspots: { type: "geojson", data: EMPTY },
    },
    layers: [
      { id: "base", type: "raster", source: "base" },
      { id: "shade", type: "hillshade", source: "dem", paint: { "hillshade-exaggeration": 0.45 } },
      { id: "glow", type: "circle", source: "hotspots", paint: {
          "circle-color": ["get", "color"], "circle-radius": radius(2.2),
          "circle-blur": 1, "circle-opacity": 0.4, "circle-pitch-alignment": "map" } },
      { id: "core", type: "circle", source: "hotspots", paint: {
          "circle-color": ["get", "color"], "circle-radius": radius(1),
          "circle-opacity": 0.85, "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5,
          "circle-pitch-alignment": "map" } },
    ],
    terrain: { source: "dem", exaggeration: 1.6 },
  };

  let map = null;
  try {
    map = new maplibregl.Map({
      container: "map", style: style, center: [-98, 39], zoom: 3.2, pitch: 55, bearing: -10,
      maxPitch: 75, attributionControl: false,
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }));
  } catch (err) {
    msg.textContent = "The 3D map needs WebGL, which this browser isn't providing. The hotspot list below still works.";
  }

  let ready = false, pending = null, requestId = 0;
  if (map) map.on("load", () => { ready = true; msg.textContent = ""; if (pending) { apply(pending); pending = null; } });

  const popup = map && new maplibregl.Popup({ closeButton: false, offset: 12 });
  if (map) {
    map.on("click", "core", (e) => {
      const f = e.features[0];
      const div = document.createElement("div");
      const strong = document.createElement("strong");
      strong.textContent = f.properties.label + ": " + f.properties.p + "%";
      div.appendChild(strong);
      popup.setLngLat(f.geometry.coordinates).setDOMContent(div).addTo(map);
    });
    map.on("mouseenter", "core", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "core", () => (map.getCanvas().style.cursor = ""));
  }

  function renderLegend(items) {
    legend.replaceChildren();
    items.forEach((it) => {
      const li = document.createElement("li");
      const dot = document.createElement("span");
      dot.className = "legend-dot";
      dot.style.background = it.color;
      li.append(dot, it.label);
      legend.appendChild(li);
    });
    if (items.length) {
      const li = document.createElement("li");
      li.className = "legend-hint";
      li.textContent = "Bigger glow = higher model-estimated risk";
      legend.appendChild(li);
    }
  }

  function renderList(hotspots) {
    list.replaceChildren();
    hotspots.slice(0, 5).forEach((h) => {
      const li = document.createElement("li");
      li.textContent = h.label + " \u00b7 " + h.probability_pct + "% \u00b7 statewide estimate";
      list.appendChild(li);
    });
  }

  function apply(d) {
    popup.remove();
    map.getSource("hotspots").setData({
      type: "FeatureCollection",
      features: d.hotspots.map((h) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [h.lon, h.lat] },
        properties: { p: h.probability_pct, color: h.color, label: h.label },
      })),
    });
    const opts = { center: [d.view.lon, d.view.lat], zoom: d.view.zoom, pitch: 55, bearing: -10 };
    if (reduceMotion) map.jumpTo(opts); else map.flyTo({ ...opts, duration: 1800 });
    msg.textContent = d.available ? "" : d.message;
  }

  async function load({ state }) {
    const id = ++requestId;
    try {
      const res = await fetch("/api/hotspots?state=" + state);
      const d = await res.json();
      if (id !== requestId) return;
      if (!res.ok) { msg.textContent = d.error || "Something went wrong loading the map."; return; }

      demoTag.hidden = !(d.demo && d.available);
      renderLegend(d.available ? d.legend : []);
      renderList(d.hotspots);
      note.textContent = d.available
        ? (d.demo ? "Demo data: made-up hotspots for testing, not real predictions. " : "") +
          "State-level estimates for " + d.for_month +
          ". Markers are at state centers, not localized hotspots; estimates are experimental, not official alerts. " +
          "Click a marker for details." +
          (d.skipped ? " " + d.skipped + " row(s) in the hotspot file were skipped (see the server log)." : "")
        : (d.skipped ? d.skipped + " row(s) in the hotspot file were skipped (see the server log)." : "");
      if (!map) { if (!d.available) msg.textContent = d.message; return; }
      if (ready) apply(d); else pending = d;
    } catch (err) {
      msg.textContent = "We couldn't load the hotspots. Check that the server is running, then try again.";
    }
  }

  document.addEventListener("trend:select", (e) => load(e.detail));
})();
