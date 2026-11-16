# Remake prompt: Trend Detective as a night-blueprint drawing set

You are remaking the front end of **Trend Detective**, a small Flask app that answers one question for a non-expert: **"Is this part of the Earth really changing?"** The user picks a US state and a measurement (air temperature, precipitation, or soil moisture with a depth). The page then shows:

- whether the long-term record has a statistically significant trend
- how big the change is
- the odds that next month is unusual
- a statewide hazard map

Build it as a **night-blueprint drawing set**: four bordered drawing sheets on a gridded ground, darker than a classic blueprint, but unmistakably blueprint. The blue lives in the ground's hue, in the hairlines and in the grid, and not in lightness. Work only in `templates/base.html`, `templates/dashboard.html`, `static/css/style.css` and `static/js/*.js`.

---

## 1. Hard constraints (do not break)

- **Stack:** Flask and Jinja. `dashboard.html` extends `base.html` with the blocks `title`, `head`, `content` and `scripts`. Use plain JS (IIFE modules) and plain CSS. **No build step, no npm, no framework.**
- **CDN libraries:** only these, each pinned to an exact version.
  - Plotly `https://cdn.plot.ly/plotly-2.35.2.min.js`
  - MapLibre GL `maplibre-gl@4.7.1` (CSS and JS from jsdelivr)
  - GSAP `3.12.2` from cdnjs (optional, motion only; the page must work without it)
  - Google Fonts: **Barlow Condensed** 600/700/800 and **JetBrains Mono** 400/600/700, with `display=swap`

  Do **not** load Bootstrap or Font Awesome. Use native `<select>` with `appearance:none` and an inline SVG chevron, and 1.5 px-stroke inline SVG icons.
- **Existing JSON endpoints.** Do not change the server.
  - `GET /api/options` returns `{ states:[{code,name,has_data}], parameters:[{key,label,definition,has_data,depths:[{key,label}]}] }`
  - `GET /api/timeseries?state&variable&depth` returns `{ available, message, label, unit, source, note, series:[{ name, dates[], values[], rolling12[], trend:{ significant, line:{x[],y[]} } }] }`
  - `GET /api/trend?state&variable&depth` returns `{ results:[{ name, kind:'up'|'down'|'none', badge, sentence, details:{ slope, years, … } }], agreement }`
  - `GET /api/event-chance?state&variable&depth` returns `{ for_month, events:[{ label, probability_pct, normal_pct, trend:'higher'|'lower'|… }], … }`
  - `GET /api/hotspots?state` returns `{ available, message, demo, for_month, bbox:[s,w,n,e], view:{lat,lon,zoom}, legend:[{key,label,color}], hotspots:[{lat,lon,phenomenon,label,probability_pct,color}], skipped }`

  Treat every non-OK response, `available:false` or network error as a state to render (see §8), never as silence.
- **Element IDs that must exist** (other code and tests rely on them):
  - Controls: `state-select`, `variable-select`, `depth-select`, `depth-field`, `variable-definition`, `controls-status`
  - Sheet 01: `question`, `date-callout`
  - Chart: `chart`, `chart-panel`, `chart-source`, `chart-readout`, `toggle-monthly`, `verdict`
  - Odds: `probability-panel`, `prob-value`, `prob-label`, `prob-tag`, `prob-meter`, `meter-fill`, `meter-excess`, `meter-tick`, `meter-legend`, `prob-sentence`, `prob-others`, `prob-basis`, `prob-note`
  - Map: `map-panel`, `map`, `map-message`, `map-demo`, `map-readout`, `toggle-3d`, `map-legend`, `map-note`, `map-list`
  - Page: `main`, `top`
- **Event contract.** `controls.js` fills the selects from `/api/options` and dispatches `document.dispatchEvent(new CustomEvent('trend:select', { detail:{ state, variable, depth } }))` on load and on every change. `depth` is `""` when not applicable. Every other module listens for `trend:select` and fetches its own endpoint. Guard against stale responses with a request counter.
- **Report contract.** `summary.js` exposes `window.TD = { report(kind, { ok, data, message }) }` with `kind ∈ 'series'|'trend'|'odds'|'map'`. Every module calls `TD.report` once per load, on success and on failure. `summary.js` uses these reports to fill Sheet 01 (question, finding, title-block metadata, strip refs, the date-mismatch callout) and to clear `aria-busy` on each sheet.

---

## 2. Page structure: four sheets

The page is `.doc`, max-width 1440 px, centred, holding four `.sheet`s. The DOM order is also the mobile order.

### Sheet 01, Finding (`<header class="sheet sheet--hero" id="top">`)
- **h1 `#question`:** built from the selection, for example "Is <span class=q-accent>Texas</span> really getting warmer?". Use "Is rainfall in X really changing?" and "Is soil moisture in X really changing?" for the other measurements. Put a mono kicker above it. Add a one-line lede and a sheet index (`01 Finding · 02 Record · 03 Odds · 04 Map` anchor links), but hide the lede and index at ≤900 px.
- **Title block:** a `section.titleblock`, a 6-column grid of cells separated by 1 px hairlines. It holds:
  - the State and Measurement selects (span 3 each, span 2 when the Soil depth cell is shown)
  - a full-width Definition cell
  - six metadata cells: Dataset, Period, Units, Odds valid for, Method, Drawn (today's date)
  - `#controls-status` as an error callout spanning the full width
- **Finding readout:** a `dl.finding` with three cells.
  - `Finding`: a significance badge with a direction glyph ▲ ▼ —, plus the first sentence of the verdict
  - `Change`: a big number such as "+0.41", with "°C / decade · 1.8 °C since 1982" under it
  - `Next month`: the top event's % (red when higher than usual), with "label · usually N%" under it
- **`#date-callout`:** an amber callout shown only when the map's `for_month` and the odds' `for_month` differ. Example: "The map's estimates are for September 2027; the event odds are for November 2026. Read them as separate forecasts."
- **Layout:** desktop is two columns, copy 0.9fr and block 1.25fr. At ≤900 px use one column ordered h1 → finding → title block → date callout.

### Sheet 02, Record (`#chart-panel`, full width)
- **Grid:** the chart frame takes 1.65fr and a side column takes `minmax(280px,1fr)`. Below 1180 px, stack them.
- **Chart:** `#chart` is `clamp(320px, 42vh, 460px)` tall, inside a `.frame` with CAD corner brackets (top-left and bottom-right) and an amber `#chart-readout` crosshair badge ("X 2014-07  Y 28.40 °C").
- **Side column:**
  - the `#toggle-monthly` chip (`aria-pressed`)
  - `#verdict` cards, one per data source. Each has a badge, the model name, the sentence, a 2-cell stats table (RATE and P-VALUE), and a `<details>` element for the likely range and method.
- **Source line:** `#chart-source`, below the grid.

### Sheet 03, Odds (`#probability-panel`)
- **Headline:** a big `#prob-value` % (cyan, or red when higher than usual), with `#prob-label` and a `#prob-tag` outline tag.
- **Meter (`#prob-meter`):**
  - It is drawn like a scale bar, with ticks every 10 %.
  - `#meter-fill` is the probability.
  - `#meter-tick` is the amber "USUAL" mark at `normal_pct`, with its label on a backing plate.
  - `#meter-excess` is a red 45° hatch from usual to value, shown only when the value is above usual.
- **Text below the meter:** `#meter-legend`, the plain sentence `#prob-sentence`, the other events in `#prob-others` (a mono list), `#prob-basis` and `#prob-note`.

### Sheet 04, Map (`#map-panel`)
- **Frame:** a MapLibre map in a `.frame` with `aspect-ratio: 4/3`, `max-height: 520px` (1/1 at ≤600 px) and corner brackets.
- **Overlays:**
  - `#map-message` (status), top-left
  - `#map-demo` (an amber "Demo data – not real predictions" tag when `demo`)
  - `#map-readout` ("LAT 31.20 N  LON 99.30 W"), bottom-left
  - the `#toggle-3d` chip, inside the control column or under the map on mobile, never covering more than 15 % of the map
- **Below the map:** the legend `#map-legend` (outline rings plus "Bigger ring = higher model-estimated risk"), `#map-note`, and `#map-list`, a text list of the top five hotspots that also serves as the no-WebGL and print fallback.

On desktop, Sheet 02 spans the full width, with Sheets 03 and 04 side by side below it (1fr and 1.15fr). Either stretch the row and pin Sheet 03's footnotes to the bottom, or let the shorter sheet end cleanly. Never leave a 200 px dead void.

Add a footer colophon after the sheets: "Trend Detective · drawn from NASA Earth observation data · estimates are experimental, not official alerts", plus "Back to the top ↑".

---

## 3. Visual system: dark tokens

Define every colour once on `:root`. Use them only through `var()`, and have JS read them with `getComputedStyle`. The page is **darker than a classic blueprint** (the sheet is about 8× darker in luminance than `#0f3d6e`), but every surface keeps a blue hue. The **lines carry the blueprint blue** (`#8cc4ff`), not neutral white-at-alpha.

```css
:root {
  /* ground → sheet → cell elevation ladder (each step ≥1.05:1, all blue-hued) */
  --page-deep:  #010409;  /* vignette edge, sheet mat ring, overlay backings */
  --page:       #020914;  /* page ground */
  --sheet:      #04112a;  /* drawing sheet (opaque) */
  --cell:       #061733;  /* title-block / finding / stats cells, callouts, popups */
  --well:       #010813;  /* recessed chart + map drawing area */
  --control:    #0a1f40;  /* resting fill of select cells, chip hover */

  /* ink */
  --ink:       #eaf4ff;                   /* headings, numbers, values      16.9:1 on sheet */
  --ink-body:  rgba(234,244,255,.90);     /* running text                   13.7:1 */
  --ink-2:     rgba(234,244,255,.78);     /* secondary, tick labels         10.4:1 */
  --ink-3:     rgba(234,244,255,.64);     /* mono labels, the text floor    7.3:1 (7.1 on --cell) */
  --line:      rgba(220,236,255,.82);     /* sheet + title-block outlines   10.7:1 */

  /* blueprint linework */
  --rule-ui:    rgba(140,196,255,.50);    /* ANY control boundary, axes, reg marks, major ticks  3.37:1 */
  --rule:       rgba(140,196,255,.26);    /* decorative hairlines, cell gaps, chart gridlines */
  --rule-faint: rgba(140,196,255,.12);    /* list separators, minor ticks */
  --grid:       rgba(120,180,255,.07);    /* 24px paper grid */
  --grid-major: rgba(120,180,255,.14);    /* 120px paper grid */
  --well-grid:  rgba(120,180,255,.08);
  --well-grid-major: rgba(120,180,255,.16);

  /* accents: one meaning each */
  --cyan:  #7fdcff;   /* the measured record; significant result      12.1:1 */
  --cyan-tint: rgba(127,220,255,.14);
  --amber: #ffc163;   /* "usual", valid dates, focus, trend line       11.7:1 */
  --red:   #ff7d7d;   /* risk above usual (+ 45° hatch)                7.6:1 */
  --red-hatch-base: rgba(255,125,125,.24);
  --grey:  #9fb3cc;   /* not significant (always dashed)               8.8:1 */
  --hz-drought: #ffc163;
  --hz-flood:   #a9b8ff;

  --hatch-red: repeating-linear-gradient(45deg, var(--red) 0 2px, transparent 2px 6px);
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --cond: "Barlow Condensed", "Arial Narrow", Arial, sans-serif;
  --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
}
```

**Colour rules:**
- **Significance** is encoded with line style plus ink:
  - Significant: a solid 1.5 px cyan border with `--cyan-tint` fill and cyan text.
  - Not significant: a dashed grey border, no fill, grey text.
- **Direction** is shown with a glyph and words only (▲ warming, ▼ drying, — no clear trend). Never use green or red for "good" or "bad".
- **No large solid accent fills**, because solid cyan, amber or ink blocks halate on near-black. Badges, the pressed chip and tags use outline plus a ≤.14 tint. The only solid accent fills allowed are the tiny callout tag label, the 2 px usual tick and the skip link.
- **No warm low-alpha tints on the dark ground**, because they go muddy. Callouts use the `--cell` fill with a dashed accent border and a 3 px inset accent bar (`box-shadow: inset 3px 0 0 var(--amber)`).
- **No glows, text-shadows or blurred circles.** This is flat ink on paper.

**Ground:**
```css
body {
  background:
    linear-gradient(var(--grid-major) 1px, transparent 1px) 0 0/120px 120px,
    linear-gradient(90deg, var(--grid-major) 1px, transparent 1px) 0 0/120px 120px,
    linear-gradient(var(--grid) 1px, transparent 1px) 0 0/24px 24px,
    linear-gradient(90deg, var(--grid) 1px, transparent 1px) 0 0/24px 24px,
    radial-gradient(ellipse 140% 90% at 50% 30%, var(--page) 55%, var(--page-deep) 100%);
}
```
- The grid scrolls with the page; do not use `background-attachment: fixed`.
- Sheets are opaque, so there is no grid behind text.
- The only extra light is an optional "lamp" on Sheet 01: `radial-gradient(ellipse 80% 60% at 20% 0%, #06173a 0%, var(--sheet) 60%)`.

---

## 4. Type scale

| Role | Font | Size / line-height | Weight | Other |
|---|---|---|---|---|
| h1 question | Barlow Condensed | `clamp(40px,5vw,68px)` / .95 (mobile `clamp(34px,10vw,44px)`) | 700 | uppercase, `text-wrap:balance`; reserve `min-height:2lh` at ≤900 px |
| h2 sheet title | Barlow Condensed | `clamp(24px,2.4vw,32px)` / 1 | 700 | uppercase, .03em |
| Big numbers (finding, %) | Barlow Condensed | finding `clamp(34px,3.4vw,46px)`; odds `clamp(56px,6vw,76px)` | 800 | `tabular-nums` |
| Body | system sans | 16 px / 1.6 (lede 16–18 px) | 400 | `--ink-body` |
| Values (title block, stats) | JetBrains Mono | 13–15 px / 1.4 | 600–700 | `--ink` |
| Labels, strips, chips | JetBrains Mono | **11 px minimum** | 600–800 | uppercase, .12–.18em tracking, `--ink-3` or `--ink-2` |
| Running mono (source, method) | JetBrains Mono | **12 px minimum** / 1.7 | 400 | `--ink-3` |

No text is under 11 px, and no text uses an ink alpha below .64.

## 5. Spacing and sheet anatomy

Use a 24 px base unit with sub-steps of 4, 8, 12 and 16.

- **`.sheet`:**
  - `position:relative`, `background: var(--sheet)`, `border: 1.5px solid var(--line)`, square corners
  - padding `72px clamp(16px,2.4vw,32px) 28px`, with 56–84 px on top on mobile
  - `scroll-margin-top: 20px`
  - **Double outline (mat):** `box-shadow: 0 0 0 6px var(--page-deep), 0 0 0 7px var(--rule), 0 24px 48px -24px #000`. The mat is darker than the page, so the outer ring separates.
- **Strip** (`.strip`, top of every sheet, 48 px tall):
  - three cells: sheet number (link to the sheet, `--ink` weight 800), title (one word: FINDING, RECORD, ODDS, MAP) and ref (`TD-03 · TX · T2M · <span class=valid>VALID NOV 2026</span>`, with the valid date in amber)
  - mono 11 px, uppercase, .18em, `--ink-2`, with `--rule` dividers
  - **Ruler ticks** under the strip: major every 120 px in `--rule-ui` (8 px tall), minor every 24 px in `--rule` (4 px tall), so they register with the page grid
  - **At ≤900 px**, wrap the ref onto a second row; do not hide it.
- **Registration marks:** a crosshair circle, 18 px, in `--rule-ui`, bottom-right (`::after`) and top-left just below the strip (`::before`).
- **Title-block grid:** `gap:1px; background: var(--rule); border: 1.5px solid var(--line)`. Cells are `--cell` with 9–12 px padding, label above value. A select cell has a `--control` fill and its select has a `1px dashed var(--rule-ui)` underline. On `:focus-within` the whole cell gets `outline: 2px solid var(--amber); outline-offset:-2px` and its label turns amber.
- **`.frame` (drawing area):** a `1px solid var(--ink-2)` border, `--well` background, and an internal 24/120 px grid in `--well-grid`/`--well-grid-major`. Cyan corner brackets are 18 px long, 2 px thick and 6 px inset. The readout badge has a 1 px amber border, `--page-deep` at .9 behind it, amber mono 11 px/700, and is hidden until hover.
- **Chips:** 11 px mono uppercase, `1px solid var(--rule-ui)`, transparent background. Hover: cyan border and text. Pressed: `rgba(234,244,255,.12)` fill, ink border, with a "✓ " prefix.
- **Gaps:** 40 px between sheets on desktop, 28 px on mobile. `.doc` padding is `40px 22px`, or `24px 16px` on mobile (16 px gutters, no horizontal scroll at 375 px).

## 6. Plotly theming (`chart.js`)

- **Layout background:** `paper_bgcolor` and `plot_bgcolor` are `'rgba(0,0,0,0)'`, so the well grid shows through.
- **Font:** mono, 12 px, `--ink-2`.
- **Axes:** `gridcolor: --rule`, `griddash:'dot'` on y, `linecolor`/`tickcolor: --rule-ui`, `ticks:'outside'`, `zeroline:false`. The y title is "Label (unit)" in `--ink`.
- **Traces per source:**
  - Monthly values: 1 px at .35 opacity, **hidden by default** (`visible:false`), toggled by `#toggle-monthly` so the y-range fits the signal.
  - 12-month average: **2 px** in cyan; additional sources use amber, then grey.
  - Trend line: amber 2 px, `dash` when significant, `dot` when not.
- **Trend annotation:** a dimension-line callout at the right end of the trend, "+1.8 °C since 1982", or "… · not significant". Use `arrowcolor/bordercolor: amber`, `bgcolor: --well`, mono 11 px amber, `borderpad 4`.
- **Crosshair:**
  - `showspikes:true, spikemode:'across', spikedash:'dot', spikecolor: amber, spikethickness:1, spikesnap:'cursor'`
  - `hovermode:'x'`, with `hoverdistance` and `spikedistance` set to -1
  - `plotly_hover` and `plotly_unhover` drive `#chart-readout`
- **Hover label:** `bgcolor: --cell`, `bordercolor: --cyan`, ink mono 12 px.
- **Legend:** horizontal, below the plot, 11 px.
- **Config:** `displaylogo:false`, `responsive:true`, and `displayModeBar: matchMedia('(pointer:coarse)').matches ? false : 'hover'`. Style the modebar icons in `--ink-3`, turning cyan on hover.
- **`#chart-source`:** "Source: … The amber line is the overall trend: dashed if statistically significant, dotted if not. Drag to zoom, double-click to reset."

## 7. MapLibre theming (`map.js`)

- **Style:** an inline style object, no API key. Sources:
  - OSM raster `https://tile.openstreetmap.org/{z}/{x}/{y}.png` with attribution
  - Terrarium DEM `https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png`
  - a `hotspots` GeoJSON source
- **Layers, in order:**
  1. `{ id:'paper', type:'background', paint:{ 'background-color':'#05183a' } }`. This is the blueprint plan colour.
  2. `base` raster: `raster-opacity .78, raster-brightness-min .9, raster-brightness-max .04, raster-saturation -1, raster-contrast .3`. The tiles invert and multiply over the blue, so water is darker blue, land a lifted blue-grey, and roads, borders and labels pale blue.
  3. `shade` hillshade: `exaggeration .5`, shadow `#000`, highlight `#1a4a80`, accent `#061c33`.
  4. `core` circles: `circle-color` from a token (`--hz-drought`, `--hz-flood`, falling back to the API colour), `circle-opacity .14`, 2 px stroke in the same colour, and radius interpolated by probability and zoom (zoom 4: 10–34 px; zoom 8: 18–56 px). Use `circle-pitch-alignment:'map'`.
  5. `centre` dots, 3 px.
- **Hazards that share a lat/lon** are offset ±0.45° in longitude so both rings show.
- **Map options:** `center [-98,39]`, `zoom 3.2`, `pitch 0`, `attributionControl:false`, plus a compact `AttributionControl`, a `NavigationControl` (top-right, `visualizePitch`), and `cooperativeGestures: matchMedia('(pointer:coarse)').matches`.
- **On select:** `fitBounds(bbox, { padding:36, duration: reduced ? 0 : 1400 })`, or `easeTo(view)` when there is no bbox.
- **3D toggle:** `setTerrain({source:'dem', exaggeration:1.6})` with pitch 50 and bearing -10. Toggle it back to flat.
- **Interactions:**
  - Click a ring for a popup: `--cell` background, 1 px cyan border, square corners, mono 12.5 px, and a `0 0 0 4px var(--page-deep)` mat.
  - `mousemove` drives `#map-readout`.
- **Control group:** square corners, `--cell` background, `--rule-ui` ring, icons inverted to light.
- **No WebGL:** catch the constructor error, show a message in `#map-message`, hide `#toggle-3d` and keep `#map-list`.

## 8. States: every sheet has four

Every sheet has exactly four documented states:

- **Loading:** set `aria-busy="true"` on the sheet and the finding cells.
  - Selects are server-rendered with `<option>Loading…</option>` (`--ink-3`) and are disabled until options arrive.
  - The chart shows a centred mono `PLOTTING…` in `--ink-3` inside the well.
  - The verdict reserves `min-height:180px` and shows a skeleton of dashed `--rule-ui` bars.
  - Finding numbers show a dashed outline bar, not a dash character and not a cyan glyph.
  - Layout must not shift by more than 8 px when data lands.
- **Ready:** the content as specified.
- **Empty** (`available:false`): a plain-language message from the API in the same place as the content. Use a mono message in the well, and for the finding, "No verdict" plus the reason.
- **Error:** a `.callout--error` with a dashed red border, a 3 px red inset bar, a `--cell` fill and a red "ERROR" tag, saying in words what to try ("Check that the server is running, then try again"). `TD.report` is still called with `ok:false`.

## 9. Motion

All motion is gated on `prefers-reduced-motion: no-preference`. With reduced motion, everything is instant (`animation:none; transition:none`, Plotly and MapLibre durations 0, counters set directly).

- **Plot-in:** on the first draw for a selection, each 12-month line path draws in with a `stroke-dashoffset` animation (900 ms, `cubic-bezier(.55,0,.3,1)`, staggered 60 ms). The trend line fades in after 900 ms.
- **Counters:** the Change and Next month numbers tick up over 800 ms (GSAP if present, otherwise set directly).
- **Meter:** the fill and the excess hatch grow (800 ms, the excess delayed 200 ms) when Sheet 03 is ≥40 % in view, via `IntersectionObserver`. The usual tick slides to place.
- **Map:** `fitBounds` is animated over 1400 ms.
- **Entrance:** no JS-gated fade that hides content before scripts run. If you add an entrance, use CSS `@keyframes` with `animation-fill-mode: both`.
- **Hover:** border and colour transitions only, 150–200 ms. Nothing bounces.

## 10. Accessibility

- **Contrast:** every text token passes AA, and most pass AAA (see the token comments). Every control boundary uses `--rule-ui` (≥3:1). Focus is a 2 px amber outline everywhere, and selects light up their whole title-block cell.
- **Skip link:** "Skip to results" points to `#main`; it is amber with dark text and visible on focus.
- **Landmarks and labels:**
  - `header` (Sheet 01), `main.board`, and `section[aria-labelledby]` per sheet
  - visible `<label for>` on every select
  - the sheet index in a `nav[aria-label]`
- **Live regions:** `.finding` and `#verdict` are `aria-live="polite"`. `#controls-status` is `role=alert`. `#map-message`, `#prob-note` and `#date-callout` are `role=status`.
- **Non-visual equivalents:** the meter has `role="img"` with an `aria-label` such as "81% chance, usually 20%". The map has `role=region` and an `aria-label`, and `#map-list` is the text alternative. Decorative readouts, corners and registration marks are `aria-hidden`.
- **Touch targets:** at least 44 px on coarse pointers (selects, chips, index links).
- **Colour is never the only signal:** significance is also line style (solid or dashed), direction is a glyph plus a word, and risk above usual is hatch plus red plus the "Higher than usual" text.

## 11. Responsive

- **≤1180 px:** the hero and record stack to one column.
- **≤900 px:** one column throughout, in DOM order Finding → Record → Odds → Map.
  - The title block becomes 2 columns, with the selects at full width.
  - The finding becomes 2 columns, with Finding at full width.
  - Hide the lede and sheet index.
  - The strip ref wraps to a second row.
  - `#date-callout` sits after the title block.
- **≤600 px:** the map is 1/1, and sheet padding-top matches the two-row strip.
- **≤420 px:** strip text 10 px with .12em tracking (the only place 10 px is allowed, and only for the uppercase strip).
- **Throughout:** no horizontal scroll at 375 px, and the map never captures one-finger scroll.

## 12. Print: whiteprint

```css
@media print {
  :root { --page:#fff; --page-deep:#fff; --sheet:#fff; --cell:#fff; --well:#fff; --control:#fff;
          --ink:#0b1f3a; --ink-body:#0b1f3a; --ink-2:#0b1f3acc; --ink-3:#0b1f3aa6; --line:#0b1f3a;
          --rule-ui:#0b1f3a99; --rule:#0b1f3a55; --rule-faint:#0b1f3a2a;
          --grid:transparent; --grid-major:transparent; --well-grid:transparent; --well-grid-major:transparent;
          --cyan:#0a5ea8; --cyan-tint:transparent; --amber:#9a5b00; --red:#b3261e; --grey:#4d5f78; }
  html, body { background:#fff !important; }
  .sheet { box-shadow:none; break-inside:avoid; }
  .skip-link, .sheet-index, .chip, .readout, .map-wrap, .modebar-container { display:none !important; }
  .map-list { display:block !important; }
}
```

On `beforeprint`, call `Plotly.relayout` with the print colours, and restore them on `afterprint`.

---

## 13. Acceptance checklist

**Identity and surfaces**
- [ ] At a glance, the page reads as a **blueprint drawing set**, not generic dark mode: the blue is visible in the ground hue, the hairlines, the grid and the map plan.
- [ ] The surfaces form a visible ladder: page < sheet < cell, with the well recessed below the sheet. Every step is ≥1.05:1 and blue-hued, and no sheet looks darker than the ground behind it.
- [ ] The double outline, ruler ticks (major and minor), both registration marks and the 24/120 px grid are visible on a typical laptop panel at 100 % brightness.
- [ ] The sheet fill is darker than `#0a2140` and well below a classic blueprint (`#0f3d6e`).

**Contrast and colour**
- [ ] Every text token is ≥4.5:1 on its actual surface, and every control boundary is ≥3:1. Verify with a script that composites alpha over the surface.
- [ ] There is no solid cyan, amber or ink block larger than a 20 px-tall tag. There are no glows, text-shadows or warm low-alpha fills on the dark ground.

**Content and states**
- [ ] On load at 1440×900, the h1 question, significance badge, change number and next-month odds are all above the fold. At 375×812 the finding is visible without scrolling past any control.
- [ ] Loading shows labelled skeletons, with no empty selects and no layout jump over 8 px. Empty and error states render in place with plain-language messages, and `TD.report` fires for every outcome.
- [ ] Mismatched valid dates show the amber callout, and each strip shows its own VALID date on desktop and mobile.

**Chart and map**
- [ ] The chart opens with monthly values hidden and the trend callout visible. The crosshair readout tracks the cursor. There is no modebar on touch.
- [ ] On the map, land and water are distinguishable. Co-located hazards are both visible. The 3D toggle tilts and flattens. With no WebGL, the hotspot list still works.

**Contracts and constraints**
- [ ] All listed IDs exist. `trend:select` and `TD.report` behave as specified. No endpoint or Python file was changed.
- [ ] No Bootstrap, no Font Awesome, no build step. CDN versions are pinned exactly.

**Accessibility, motion and print**
- [ ] Keyboard-only: the skip link works, the focus ring is visible on every control, and the select cell lights up amber.
- [ ] With reduced motion on, nothing animates, and every value is correct immediately.
- [ ] Print preview gives a white whiteprint with the map replaced by the hotspot list, and each sheet stays on one page where possible.
