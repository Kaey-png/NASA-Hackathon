# Trend Detective: night-blueprint redesign critique

Reviewed: `templates/base.html`, `templates/dashboard.html`, `static/css/style.css`, `static/js/{chart,map,verdict,event_chance,controls,ui}.js`. I inspected the running app at http://localhost:5055 with Texas · Temperature at 1440×900 and 390×844, and measured layout and text with in-page JS. The browser pane's screenshots were unreliable at full scale, so some visual calls come from scaled captures combined with DOM measurements. Contrast figures are WCAG 2.x ratios computed from the actual tokens composited over the actual sheet fill.

**Verdict:** The surface vocabulary is right: the grid paper, double-outlined sheets, strip with ruler ticks, registration mark, Barlow and JetBrains Mono, square corners and the dashed select underline. The structure underneath is still a generic dashboard. The page never answers its own question ("is it really changing?") above the fold, the largest element on the page (the map) carries the least information, and the blueprint language is applied as skin rather than used to encode meaning: hatching, callouts, title-block metadata and dimension lines all go unused. Legibility of the small mono text also fails AA.

---

## P0: fix before anything else

### 1. The answer is below the fold. A first-time visitor gets a logo, not a finding
- **What:** At 1440×900 Sheet 01 takes 331 px for brand, kicker and lede. The verdict ("Significant warming, +0.41 °C/decade") starts around y≈1000 and the 81 % event chance around y≈1300. On mobile the verdict is at y=1872 and the 81 % at y=2397, roughly three screens down, behind a map.
- **Why:** The product has one question and one answer. In 5 seconds a visitor should read "Texas is warming: +1.8 °C since 1982, significant". Today they read "TREND DETECTIVE".
- **Fix:** Turn Sheet 01's title block into a **finding readout**. Keep the three selects, then add a row of `dl` cells that the existing fetches populate: `Finding` (badge plus a one-line verdict), `Change` (+1.8 °C since 1982, as a ticking counter), `Next month` (81 %, usually 20 %) and `Data` (MERRA-2 · 1982–2026). Add one small `static/js/summary.js` listener on `trend:select` (or have verdict.js and event_chance.js also write into these cells). Demote the brand to the strip (`TD · Trend Detective`) and make the question the display line: `<h1>Is Texas really getting warmer?</h1>`, rewritten from the state and variable labels.

### 2. The map is the largest object on the page and shows two overlapping dots
- **What:** `.board` stretches the map column to the right column's height. `#map-panel` is 1240 px tall and `.map-wrap` is 939 px. `/api/hotspots` returns drought (29 %) and flood (14 %) at the **same** lat/lon (31.2, −99.3), so one circle sits on top of the other. At pitch 55 and zoom 5 the frame is mostly Mexico and the Gulf.
- **Why:** The biggest canvas carries two numbers, one of them hidden. The chart, which is the evidence, is squeezed into a 573×290 box.
- **Fix:** Remove the equal-height stretch (`.board{align-items:start}` and drop `flex:1` on `.map-wrap`), then cap the map at `aspect-ratio: 4/3; max-height: 520px`. Reorder the board: the chart gets full width (Sheet 02, `grid-column:1/-1`, chart `height: clamp(320px, 42vh, 460px)`), with the map and event chance side by side below. In map.js, offset co-located hazards (for example ±0.35° lon) or draw them as two concentric rings: drought as the outer hatched ring, flood as the inner dotted ring. Set `pitch: 30`, default terrain exaggeration to 0 (offer a "3D" toggle), and use `fitBounds` on the state rather than `flyTo` the centroid.

### 3. Small mono text fails contrast
- **What:** `--ink-3` (`rgba(234,244,255,.42)`) composites to **3.78:1** on the sheet. It is used for every 10–12 px uppercase mono label: `.tb__label`, `.chart-source`, `.verdict-method`, `.verdict dt`, `.verdict-model`, `.meter-legend`, `.legend-hint`, `.colophon`, `.placeholder`. Sizes of 9–10.5 px (`.meter-tick::before` is 9 px, `.tb__label` is 10 px) make it worse.
- **Why:** These elements carry the method, the source and the "usual" reference, which are the trust layer of a science tool. WCAG AA needs 4.5:1 for this text.
- **Fix:** Split the tokens. `--ink-3: rgba(234,244,255,.62)` gives 7.0:1 and is the lowest alpha allowed for text. `--rule: rgba(234,244,255,.22)` and `--rule-faint: .10` are for lines only. Set a floor of 11 px for mono labels and 12 px for running mono text (`.chart-source`, `.verdict-method`). Raise `.meter-tick::before` to 10 px/800 with a `--sheet` backing plate.

### 4. Selects have almost no focus indicator
- **What:** Bootstrap's `.form-select:focus{outline:0}` has specificity (0,2,0) and beats the global `:focus-visible` outline at (0,1,0). The only focus cue is a 1 px amber bottom border.
- **Why:** These are the page's only inputs, and keyboard users lose their place.
- **Fix:** Use `.tb:focus-within{outline:2px solid var(--amber);outline-offset:-2px}` together with `.form-select:focus-visible{outline:none}`, so the whole title-block cell lights up like a selected CAD field. Better still, drop Bootstrap (finding 15) and the specificity fight goes away.

---

## P1: makes or breaks the blueprint idea

### 5. Colour carries value judgements it shouldn't, and teal is off-palette
- **What:** `.badge-up` and `.tag-lower` use teal `#6ee7c8`, while `.badge-down` and `.tag-higher` use red. "Significant **warming**" therefore renders in a reassuring green-teal. Teal is not in the reference palette, and map hazard colours come from the API (`#ffb86b`, `#60a5fa`) rather than tokens.
- **Why:** Direction is not the same thing as good or bad (drying soil is "down"). The palette drifts from the reference's four inks.
- **Fix:** Encode **significance** with ink and line style: a significant result gets a solid 1.5 px cyan border and solid fill, a non-significant one a dashed grey border and no fill, mirroring the dashed vs dotted trend line. Show **direction** with a glyph (`▲ ▼ —`) and words only. Keep red for risk above usual and amber for reference or "usual" marks. Remove `--teal`. Map hazards to `--hz-drought:#ffc163` and `--hz-flood:#a9b8ff` (10:1 on the sheet), and have map.js prefer the tokens, falling back to the API colour.

### 6. The chart hides the trend it is meant to show
- **What:** The monthly line swings about 10–30 °C. At 290 px tall the 12-month average and the dashed trend sit as a near-flat line in the middle, and the significant 1.8 °C change is invisible. The modebar is always on, and the legend shows one item.
- **Fix:** Make monthly traces `visible:'legendonly'` by default (or add a `Monthly` chip toggle) so the y-range fits the 12-month average and the trend. Annotate the trend's right end with a dimension-line callout (`annotations:[{text:'+0.41 °C / decade', showarrow:true, arrowcolor:amber, bordercolor:amber, borderpad:4, bgcolor:'#050f1d', font:{family:mono,size:11}}]`). Add a CAD crosshair with `xaxis.showspikes:true, spikemode:'across', spikedash:'dot', spikecolor:'#ffc163', spikethickness:1`, the same on `yaxis`, and `hovermode:'x'`. Use `displayModeBar:'hover'` and set legend `font.size:11` in uppercase mono.

### 7. Title-block metadata is missing, which is the reference's signature element
- **What:** `.titleblock` holds only selects and a definition. The reference's title block is a `dl` grid of drawing metadata.
- **Fix:** Add cells that carry information, not ornament: `Dataset` (MERRA-2), `Period` (1982–2026), `Units` (°C), `Valid for` (Nov 2026), `Method` (Seasonal Mann-Kendall), `Drawn` (today's date) and `Sheet` (01 / 04). Every value already exists in the `/api/timeseries`, `/api/trend` and `/api/event-chance` payloads. Lay it out with `display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:1px; background:var(--rule)`.

### 8. The sheets disagree about dates and nothing surfaces it
- **What:** The map reads "September 2027", the event card "November 2026", and the basis "through September 2026". The lede promises "next month's odds".
- **Why:** In a trust-sensitive tool, an inconsistent "valid for" reads as a bug. It may be a demo-data artefact, but the design gives no place to see it.
- **Fix:** Put a live `VALID · NOV 2026` in every strip's `.strip__ref` (for example `TD-03 · TX · T2M · 1982–2026`). When dates differ across sheets, show an amber dashed callout in Sheet 01: "Map estimates are for Sep 2027; event odds for Nov 2026." Raise the data mismatch with whoever owns the backend.

### 9. Hatching never means "affected"
- **What:** Hatching appears only on the placeholder (as decoration) and the meter fill (where it means "probability").
- **Fix:** Reserve 45° hatch for **risk above usual**. Hatch the meter segment between the usual tick and the value when the value is higher than usual (`.meter-excess{left:var(--usual);width:calc(var(--p) - var(--usual));background:repeating-linear-gradient(45deg,var(--red) 0 1.5px,transparent 1.5px 6px)}`), keep the base fill solid cyan, and use the same hatch on map hazard rings above the state's usual. Placeholders get a plain dashed frame instead.

### 10. Loading leaves blanks and the layout jumps; errors are swallowed
- **What:** verdict.js calls `clear()`, so the box collapses to `display:none` and reappears 360 px tall, pushing Sheet 04. `!res.ok` or `!d.available` returns silently. Nothing sets `aria-busy`.
- **Fix:** Reserve space with `#verdict{min-height:180px}` while loading, render a skeleton (two dashed outline bars plus a `PLOTTING…` mono label), and set `aria-busy="true"` on each `.sheet` during fetch. Show errors in a red dashed callout (`.callout--error`) instead of nothing. Each sheet should have exactly four documented states: loading, ready, empty (no data for this choice) and error.

### 11. The mobile order and gestures work against the reader
- **What:** At 390 px, Sheet 02 (the map, 340 px, drag-pan on) comes before the chart and verdict, so one-finger scrolling gets captured by MapLibre. Selects are 33 px tall, under the 44 px touch target. The panel title wraps to 2 lines and duplicates the strip.
- **Fix:** On ≤900 px, order the sheets Finding → Chart and verdict → Event chance → Map. Pass `cooperativeGestures: matchMedia('(pointer:coarse)').matches` to `new maplibregl.Map`. Set `.form-select{min-height:44px}` on coarse pointers, and set `.strip{font-size:10px;letter-spacing:.12em}` below 420 px.

### 12. The hero does not plot itself in, and there is no crosshair: the two signature motions are missing
- **What:** The only motion is a generic `gsap.from('.sheet',{y:18,opacity:0})` fade-up, plus the % counter.
- **Fix:** (a) On first chart draw, animate the 12-month line with an SVG `stroke-dashoffset` reveal on `.js-plotly-plot .scatterlayer .trace:nth-child(2) path` over 900 ms, followed by the trend dash. (b) Add a crosshair readout to the chart and map frames: a `position:absolute` mono badge in the lower-left corner showing `X 2014-07  Y 28.4 °C` from `plotly_hover`, and `LAT 31.20 N  LON 99.30 W` from `map.on('mousemove')`. (c) The meter and the "other events" bars grow when scrolled into view, using `IntersectionObserver` with `threshold:.4`. (d) Tick the headline counter (finding 1). Gate everything on `prefers-reduced-motion`.

### 13. There are no print styles. The reference turns into a whiteprint
- **Fix:** Add `@media print{:root{--sheet:#fff;--ink:#0b1f3a;--ink-2:#0b1f3acc;--ink-3:#0b1f3a99;--rule:#0b1f3a55;--cyan:#0a5ea8;--amber:#9a5b00;--red:#b3261e} body{background:#fff} .sheet{box-shadow:none;break-inside:avoid;page-break-after:always} .map-wrap{display:none} #map-list{display:block}}`. Also call `Plotly.relayout` on `beforeprint` with paper colours, and hide the skip link and controls chevrons.

---

## P2: polish

### 14. Strip titles and panel titles say the same thing twice
"Plan · statewide outlook" is followed by "Statewide phenomena outlook", and "Elevation · change over time" by "Change over time". The drafting words (Plan, Elevation, Detail) are cute but say nothing. Make the strip carry **metadata** (`02 | HAZARD PLAN | TD-02 · TX · VALID SEP 2027`) and the h2 carry the **claim** ("Drought risk is the bigger worry this season"), or keep the h2 as the label and drop the strip title.

### 15. Bootstrap and Font Awesome are dead weight that fights the style
The Bootstrap CSS and JS bundle (~80 KB plus 80 KB) is used only for `.form-select`. Font Awesome (~100 KB of CSS plus fonts) is used for 10 icons, and the rounded icon tiles (`.tile`) read like a SaaS dashboard, not a drawing. Remove both. Restyle the native `select` with `appearance:none` and an inline-SVG chevron. Replace the icons with mono glyphs (`▲ ▼ — ◎ ⌖`) or 1.5 px-stroke inline SVGs drawn in the ink colour.

### 16. Glows contradict flat ink
`.prob-value{text-shadow:0 0 24px…}`, `.legend-dot{box-shadow:0 0 8px}` and the map `glow` layer with `circle-blur:1` look like a neon HUD, not a blueprint. Remove them. Draw map hazards as 1.5 px ink rings with hatch or dot fills.

### 17. The grid is fixed while sheets scroll
`background-attachment:fixed` repaints on every scroll and is ignored on iOS Safari. The 120 px ruler ticks on strips also never line up with the page grid. Attach the grid to `body` (scroll with the content) and size sheet padding and strip heights in multiples of 24 px (strip 36 px becomes 48 px, sheet padding-top 72 px) so ticks register with the paper.

### 18. Semi-transparent sheets let the grid run behind body text
`--sheet: rgba(3,14,28,.72)`. Make sheets opaque (`#050f1d`) and draw the fine grid **inside** chart and map frames only, as the drawing area.

### 19. There is no sheet navigation
Four sheets and no index. Add a sheet index to the title block (`01 Finding · 02 Record · 03 Odds · 04 Map`) as anchor links, and make `.strip__no` a link to `#sheet-0n`. On wide screens, add an optional sticky 32 px rail on the left edge with sheet numbers and the current one in amber (via `IntersectionObserver`).

### 20. The verdict detail list hides the key numbers
"The numbers" `<details>` is closed by default, so slope, range and p-value sit behind a click while the prose repeats them. Render slope and p-value as two always-visible title-block cells inside each verdict card (`RATE +0.41 °C/dec · p 0.002`). Keep the `<details>` for "Likely range" and "Method".

### 21. Fonts are over-fetched
JetBrains Mono loads 5 weights (400–800) and Barlow Condensed 3. Use JetBrains Mono 400/600/700 and Barlow Condensed 600/700, and add `font-display:swap` (already set) plus `size-adjust` fallbacks to cut CLS on the h1.

### 22. The entrance animation hides content until GSAP runs
`gsap.from('.sheet',{opacity:0})` makes the first paint invisible on slow CDNs. Use a CSS-only `@keyframes` reveal with `animation-fill-mode:both` and a JS-free fallback, or drop it: the plot-in and counters are better motion.
