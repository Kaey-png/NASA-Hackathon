# Prompt: Remake the Trend Detective UI as a night-blueprint drawing set

You are a senior designer-engineer. Rebuild the front end of **Trend Detective**, a small Flask app, so it reads like a set of engineering drawings printed on very dark blueprint paper. It should be a precise, legible, honest scientific instrument, not a neon dashboard. Work only in `templates/`, `static/css/` and `static/js/`. Do not touch the Python back end.

---

## 1. The product

Trend Detective answers one question for a US state and a measurement: **"Is this part of the Earth really changing?"** Measurements are temperature, precipitation and soil moisture at several depths. The page has four parts, each drawn as a numbered **sheet**:

1. **Sheet 01, Title and finding.** Choose a state, a measurement and (for soil moisture) a depth. The variable's plain-English definition appears here. A **finding readout** gives the answer at a glance: verdict badge, total change since the start of the record, and the chance of an unusual month next.
2. **Sheet 02, The record (time series).** A Plotly chart shows a faint monthly line, a bold 12-month average per data source, and a trend line per source: dashed if significant, dotted if not. Under it sit plain-English **verdict cards**, one per data source. Each card has a badge (up, down or none), a sentence, optional warnings, a `<details>` block with rate of change, likely range, p-value and period, an optional agreement line across sources, and a method note.
3. **Sheet 03, Chance of an event.** A big probability (for example 81 %), the event label and hazard, a tag (higher than usual, lower than usual or about usual), a meter with a "usual" tick, an explanatory sentence, a list of other events with their chance and usual rate, the basis and a note.
4. **Sheet 04, Statewide hazard plan (map).** A MapLibre map shows statewide drought and flood risk estimates (state-level, placed at the state centre), with a legend, an accessible list of the same hotspots and notes. Demo data is flagged.

On desktop, the reading order is the question, then the answer, then the evidence, then the odds, then the map. The map is supporting context, not the hero.

---

## 2. Hard constraints (do not break these)

- **Stack:** Flask and Jinja (`templates/base.html` and `templates/dashboard.html`, where dashboard extends base). There is no build step: plain CSS in `static/css/style.css` and plain ES2019+ scripts in `static/js/`, loaded with `<script>` tags. No npm and no bundler.
- **Libraries come from a CDN only.** Keep Plotly (`https://cdn.plot.ly/plotly-2.35.2.min.js`) and MapLibre GL (`maplibre-gl@4.7.1` from jsDelivr). GSAP 3.12.2 from cdnjs is optional. Bootstrap and Font Awesome may be removed, and removing them is recommended. Fonts come from Google Fonts: Barlow Condensed (600, 700) and JetBrains Mono (400, 600, 700).
- **Data comes only from the existing endpoints**, with unchanged request shapes:
  - `GET /api/options` returns `{states:[{code,name,has_data}], parameters:[{key,label,definition,source,has_data,depths?:[{key,label}]}]}`.
  - `GET /api/timeseries?state=&variable=&depth=` returns `{available, message?, label, unit, source, note?, series:[{name?, dates, values, rolling12, trend?:{significant, line:{x,y}}}]}`.
  - `GET /api/trend?state=&variable=&depth=` returns `{available, results:[{kind:'up'|'down'|'none', badge, label?, sentence, note?, details:{slope, range, p_value, years}}], agreement?, method}`.
  - `GET /api/event-chance?state=&variable=&depth=` returns `{available, message?, events:[{label, hazard, probability_pct, normal_pct, trend:'higher'|'lower'|'usual', sentence, skill_text?}], basis, note}`.
  - `GET /api/hotspots?state=` returns `{available, demo, message, for_month, state, skipped, view:{lat,lon,zoom}, legend:[{key,label,color}], hotspots:[{phenomenon,label,lat,lon,probability_pct,color}]}`. Drought and flood can share **identical** coordinates.
- **Keep every element ID** below. JS may be rewritten, but these IDs must exist and keep their meaning:
  `top`, `main`, `state-select`, `variable-select`, `depth-select`, `depth-field` (toggled with `hidden`), `variable-definition`, `controls-status`, `map-panel`, `map-h`, `map`, `map-message`, `map-demo`, `map-legend`, `map-note`, `map-list`, `chart-panel`, `chart-h`, `chart`, `chart-source`, `verdict`, `probability-panel`, `prob-h`, `prob-value`, `prob-label`, `prob-tag`, `prob-meter`, `meter-fill`, `meter-tick`, `meter-legend`, `prob-sentence`, `prob-others`, `prob-basis`, `prob-note`.
- **Event contract:** `controls.js` fills the selects from `/api/options` and dispatches `document.dispatchEvent(new CustomEvent('trend:select', {detail:{state, variable, depth}}))` on load and on every change. `depth` is `""` when the depth field is hidden. Every other module listens only to this event. Each module guards against stale responses with an incrementing request id. New modules (for example `summary.js` or `sheetnav.js`) must follow the same pattern.
- All user-facing text is set with `textContent`, never `innerHTML` with API strings.
- The page must work, with the map list as a fallback, when WebGL is unavailable.

---

## 3. Visual system

### 3.1 Colour tokens (night blueprint, darker than a classic blueprint)

Define these on `:root` and use only tokens in components. Contrast figures are measured on `--sheet`.

| Token | Value | Use |
|---|---|---|
| `--night-0` | `#01060d` | page edge, outer vignette |
| `--night-1` | `#030b16` | page base |
| `--night-2` | `#071a30` | radial glow centre (top of page) |
| `--sheet` | `#050f1d` | **opaque** sheet fill |
| `--cell` | `#081a2f` | title-block cells, inputs, callout fill |
| `--ink` | `#eaf4ff` | primary text, sheet border (15.9:1) |
| `--ink-2` | `rgba(234,244,255,.78)` | body text (10.6:1) |
| `--ink-3` | `rgba(234,244,255,.62)` | labels, captions. **Minimum for any text** (7.0:1) |
| `--rule` | `rgba(234,244,255,.22)` | hairlines, cell gaps (lines only, never text) |
| `--rule-faint` | `rgba(234,244,255,.10)` | row dividers, chart grid |
| `--grid` | `rgba(127,220,255,.05)` | 24 px paper grid |
| `--grid-major` | `rgba(127,220,255,.10)` | 120 px paper grid |
| `--cyan` | `#7fdcff` | primary drawing ink, links, data series 1, significant results (12.4:1) |
| `--amber` | `#ffc163` | focus, reference marks ("usual" tick, dimension lines, crosshair), warnings, data series 2 (12.0:1) |
| `--red` | `#ff7d7d` | risk above usual, errors (7.8:1) |
| `--grey` | `#8fa6c2` | neutral, no trend, not significant (7.7:1) |
| `--violet` | `#a9b8ff` | data series 3 and the flood hazard (10.1:1) |
| `--hz-drought` | `var(--amber)` | drought hazard |
| `--hz-flood` | `var(--violet)` | flood hazard |
| `--hz-heat` / `--hz-cold` | `var(--red)` / `var(--cyan)` | temperature hazards |

The page background stacks four layers: a 24 px grid, a 120 px major grid (both drawn with 1 px `linear-gradient` lines), a `radial-gradient(ellipse 120% 70% at 50% 0%, var(--night-2), var(--night-1) 50%, var(--night-0))`, and `background-color: var(--night-1)`. Use **no** `background-attachment: fixed`. There is no teal, no glow, no text-shadow and no gradient fill on data.

**Colour semantics (strict):**
- Direction (up or down) is never encoded by colour. Use a glyph (`▲`, `▼`, `—`) and words.
- Significance is encoded by **line style and fill**. A significant result gets a solid 1.5 px `--cyan` border with a 6 % cyan fill and a dashed trend line. A non-significant result gets a 1 px dashed `--grey` border, no fill and a dotted trend line.
- Risk above usual is `--red` plus a 45° hatch. Never use colour alone.
- Amber always means "reference or attention": the usual mark, focus, warnings and annotations.

### 3.2 Type

- `--cond`: "Barlow Condensed", "Arial Narrow", sans-serif. Headings and big numerals, uppercase, weight 700, line-height 0.95.
- `--mono`: "JetBrains Mono", ui-monospace, Consolas, monospace. Labels, kickers, strips, captions, numbers in tables. Uppercase labels use letter-spacing `.14em–.2em`.
- `--sans`: system-ui stack. Body copy and sentences.
- Scale (use `clamp`):
  - Display (finding question): `clamp(40px, 5.2vw, 76px)`
  - Big number (counter, probability): `clamp(56px, 6vw, 88px)`, Barlow 700, `tabular-nums`
  - h2 (sheet heading): `clamp(26px, 2.6vw, 36px)`
  - h3 (card heading): 18 px Barlow 700
  - Body: 16 px/1.6 sans. Lede: `clamp(17px, 1.5vw, 20px)`/1.5
  - Mono running text (captions, method): **12 px minimum**, 1.7
  - Mono labels (uppercase): **11 px minimum**, weight 600
  - Strip: 11 px mono 600, `.18em` tracking (10 px and `.12em` below 420 px)
- `text-wrap: balance` on headings and `text-wrap: pretty` on paragraphs. Body measure is no more than 68ch.

### 3.3 Spacing, grid and borders

- Base unit 8 px. Paper module 24 px. Sheet paddings and strip heights are multiples of 24 so ruler ticks register with the paper.
- Container: `max-width: 1440px`, side gutter `clamp(16px, 3vw, 40px)`, 48 px gap between sheets (32 px on mobile).
- Borders: sheet `1.5px solid var(--ink)`. Inner frames (chart, map) `1px solid var(--ink-2)`. Cell gaps `1px` showing `--rule`. Callouts `1px dashed`. Every corner is square: `border-radius: 0` everywhere, including MapLibre controls, popups and Plotly hover labels.

### 3.4 Sheet anatomy (every sheet)

```
┌──────────────────────────────────────────────────────────┐  1.5px ink border
│ 02 │ THE RECORD                   │ TD-02 · TX · T2M · 1982–2026 │  strip, 48px
├┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┴┤  ruler ticks: 1px every 24px (5px tall), every 120px (10px tall)
│  h2 claim / label                                         │
│  content…                                                 │
│                                                       ⊕   │  registration crosshair, 18px, bottom-right
└──────────────────────────────────────────────────────────┘
  box-shadow: 0 0 0 6px var(--night-1), 0 0 0 7px var(--rule), 0 30px 60px -30px #000c
```

- `<section class="sheet" id="sheet-0N" aria-labelledby="…">`, with an opaque `--sheet` background.
- The strip is a 3-column grid: `no | title | ref`. `.strip__no` is an anchor to its own sheet and acts as a permalink. `.strip__ref` is **live metadata** updated by JS (state code, variable code, period or valid-for month). Below 600 px the ref collapses to the state and variable codes only. It is never hidden entirely.
- The h2 inside the sheet states the **claim** when data exists (for example "Warming, and it is significant") and falls back to the label ("The record") when it does not. Do not repeat the strip title.
- Corner brackets (2 px cyan L-shapes, 16 px) mark the drawing area of the chart and map frames only.
- Inside chart and map frames only, draw the fine 24 px grid as the "drawing area". Sheets themselves are plain.

### 3.5 Components

- **Title block** (`dl` grid): `display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:1px; background:var(--rule); border:1.5px solid var(--ink)`. Each cell has a `--cell` background and 10 px 14 px padding. `dt` is an 11 px mono uppercase `--ink-3` label. `dd` is 15 px mono 600 `--ink`.
- **Select** (native, restyled): `appearance:none`, transparent background, `border:0; border-bottom:1px dashed var(--ink-3)`, an inline-SVG chevron in `--ink-2` as `background-image`, 15 px mono 600, `min-height:44px` on `(pointer:coarse)`. Hover: underline turns `--cyan`. Focus: the **whole cell** gets `outline:2px solid var(--amber); outline-offset:-2px` via `.tb:focus-within`, and the select's own outline is suppressed only inside `.tb`. Disabled: `--ink-3` with an "Loading options…" mono label.
- **Badge / tag:** 11 px mono 700 uppercase, `padding:2px 8px`, 1 px border. Variants: `--sig` (solid cyan), `--nonsig` (dashed grey), `--risk` (red border plus hatched fill `repeating-linear-gradient(45deg, rgba(255,125,125,.22) 0 1.5px, transparent 1.5px 6px)`), `--usual` (grey). Prefix with the glyph `▲`, `▼` or `—`.
- **Callout:** `border:1px dashed var(--cyan); background:var(--cell); padding:12px 16px`, with a mono label ("NOTE", "AGREEMENT", "DEMO DATA", "ERROR") as a 0-margin tab on the top border (`position:absolute; top:-0.8em; background:var(--sheet); padding:0 6px`). Variants are `--amber` (warning or demo) and `--red` (error).
- **Hatch** (`.hatch-risk`) is reserved for "risk above usual". Use it nowhere else.
- **Dimension line:** a 1 px amber line with 45° end ticks and a mono label centred on a `--sheet` plate. Use it for the "usual" mark on the meter and for the trend annotation on the chart.

### 3.6 States (each sheet must implement all four)

- **Loading:** set `aria-busy="true"` on the sheet. The content area keeps its final min-height: chart 360 px, verdict 180 px, odds 220 px, map 420 px. Show a dashed frame with a blinking-cursor mono label `PLOTTING…` (static under reduced motion). There must be no layout shift when data arrives.
- **Ready:** the content as specified.
- **Empty** (`available:false`): a dashed grey callout with the API `message` and a suggested next action ("Try Precipitation, which has data for this state").
- **Error** (network or non-2xx): a red dashed callout, "We couldn't load this sheet. Check the server is running, then try again.", plus a **Retry** button that re-dispatches the last `trend:select` detail. Never fail silently (the current verdict module does).

---

## 4. Layout and sections

### Desktop (≥1100 px)

```
[ Sheet 01  Title + finding ............................. full width ]
[ Sheet 02  The record: chart (full width) + verdict cards in 2 cols ]
[ Sheet 03  Chance of an event  (5/12) ][ Sheet 04  Hazard plan (7/12) ]
[ colophon ]
```
Use `align-items:start` with no equal-height stretching. The map frame uses `aspect-ratio:4/3; max-height:520px`.

### Tablet (600–1099 px)
Single column in the order 01, 02, 03, 04. The verdict cards are a single column.

### Mobile (<600 px)
Single column, same order. Sheet padding is 16 px. The strip height stays 48 px. The big number is 56 px. The map uses `aspect-ratio:1/1` with cooperative gestures. Tap targets are at least 44 px. There is no horizontal scroll at 360 px.

### Sheet 01: title and finding
- Strip: `01 | TREND DETECTIVE | TD-01 · SHEET 01 / 04`.
- Kicker (mono cyan): `FIELD INSTRUMENT · NASA EARTH OBSERVATION`.
- `<h1>` is the **question**, rewritten live from the selection: "Is Texas really getting warmer?", "…wetter?" for precipitation, "Is Texas's surface soil drying out?" for soil moisture. Default: "Is this part of the Earth really changing?". The brand name appears only in the strip and `<title>`.
- Lede (one sentence): "Pick a place and a measurement. The sheets below plot the record, test the trend and estimate next month's odds."
- **Title block, row 1 (inputs):** `State`, `Measurement`, `Soil depth` (`#depth-field`, hidden when not applicable) and `Definition` (`#variable-definition`, spanning 2 columns). `#controls-status` is a full-width red callout with `role="alert"`, hidden by default.
- **Title block, row 2 (finding readout, `aria-live="polite"`):**
  - `Finding`: verdict badge plus a short phrase ("Significant warming").
  - `Change`: a big ticking counter in Barlow, for example `+1.8 °C`, with "since 1982" in mono. It is derived from the trend's slope and period, or from the first and last points of the trend line if no total is given.
  - `Next month`: `81 %`, with "usually 20 %" in mono and a red hatched tag if higher than usual.
  - `Data`: dataset · period · units.
  - `Valid for`: the event-chance month. If the hotspot `for_month` differs, add an amber dashed callout under the block: "Map estimates are for Sep 2027; event odds are for Nov 2026."
- **Sheet index:** a row of four anchor links (`01 Finding`, `02 Record`, `03 Odds`, `04 Map`) in mono, with the current sheet in amber.

### Sheet 02: the record (`#chart-panel`)
- Strip ref: `TD-02 · {STATE} · {VAR} · {first year}–{last year}`.
- h2 `#chart-h` states the claim from the first verdict ("Warming · significant"), with the fallback "The record".
- `#chart` is a full-width frame, `height: clamp(340px, 44vh, 480px)`, with the inner drawing-area grid and corner brackets.
- A chip row above the chart (mono 11 px buttons with `aria-pressed`): `12-mo average` (on), `Monthly` (off by default), `Trend` (on). Toggling calls `Plotly.restyle` on the matching traces.
- `#chart-source` is a 12 px mono caption: source, line legend explanation ("dashed = significant trend · dotted = not significant") and the interaction hint.
- `#verdict` holds a 2-column grid of cards on desktop. Each card is a mini title block:
  - Header: badge (significance style) and the source label (`MERRA-2`).
  - Sentence in 16 px sans `--ink`.
  - An always-visible 2-cell strip: `RATE +0.41 °C / decade` and `P 0.002`.
  - `note` as an amber dashed callout.
  - `<details>` "More numbers" with a `dl` of likely range and period. The summary is a mono cyan uppercase label with a `+`/`−` glyph and keyboard focus.
  - The agreement text goes in a full-width cyan dashed callout labelled "AGREEMENT". The method goes in a 12 px mono `--ink-3` paragraph labelled "METHOD".

### Sheet 03: chance of an event (`#probability-panel`)
- Strip ref: `TD-03 · VALID {MONTH YEAR}`.
- Head: `#prob-value` is the big Barlow numeral in `--ink` (not cyan, and no glow) and ticks from its previous value. Next to it are `#prob-label` ("Unusually hot month · heat risk", 12 px mono uppercase) and `#prob-tag`.
- `#prob-meter` is a scale bar 16 px tall with a 1 px `--ink-2` border, ticks every 10 % (major every 50 % with `0 / 50 / 100` labels below), and `role="img"` with an `aria-label`.
  - `#meter-fill` is solid `--cyan` from 0 up to `min(value, usual)`. The **excess** above usual is a separate hatched red segment (add a child or pseudo-element driven by CSS custom properties `--p` and `--u`). If the value is below usual, the gap between the value and the usual mark is drawn as a dashed outline.
  - `#meter-tick` is an amber 2 px dimension mark extending 8 px above and below, with a "USUAL {n}%" label on a `--sheet` plate (10 px mono 700 minimum).
- `#meter-legend` is a 12 px mono caption.
- `#prob-sentence` is 16 px sans.
- `#prob-others` renders each other event as a row: label · hazard, a 6 px mini meter with its own usual tick, and `1 % · usually 20 %` in mono. The bars grow when scrolled into view.
- `#prob-basis` is a mono caption. `#prob-note` is an amber dashed callout, hidden when empty.

### Sheet 04: statewide hazard plan (`#map-panel`)
- Strip ref: `TD-04 · {STATE} · VALID {for_month}`.
- h2 `#map-h` gives the leading hazard ("Drought is the bigger risk: 29 %"), with the fallback "Statewide hazard plan".
- The map frame contains `#map` (MapLibre container), `#map-message` (cyan dashed callout overlaid top-left, `role="status"`), `#map-demo` (amber solid tag "DEMO DATA, NOT REAL PREDICTIONS", bottom-left) and corner brackets.
- A crosshair readout badge sits bottom-right inside the frame: `LAT 31.20 N · LON 99.30 W`, updated on `mousemove` and `aria-hidden`.
- `#map-legend` is a row of swatches showing both colour **and pattern**: drought is an amber ring with hatch, flood a violet ring with dots. It ends with "ring size = estimated chance".
- `#map-note` is a 12 px mono caption that says the estimates are state-level, plotted at the state centre, not localised hotspots and experimental.
- `#map-list` is always visible and is the accessible equivalent. It is a mono `dl`-style list: `Drought risk · 29 % · statewide estimate`, each with a mini meter.

### Colophon
A mono 11 px line: `TREND DETECTIVE · DRAWN FROM NASA EARTH OBSERVATION DATA · ESTIMATES ARE EXPERIMENTAL, NOT OFFICIAL ALERTS`, followed by a "Back to sheet 01 ↑" link to `#top`, a drawn date and the sheet count.

---

## 5. Plotly theming (`chart.js`)

- Read the colours from CSS custom properties at draw time. The series colours are `[--cyan, --amber, --violet]`.
- Traces per source:
  - Monthly: width 1, `opacity:.35`, `visible:'legendonly'` by default, `showlegend:false` (controlled by the chip).
  - 12-month average: width 2.5, solid, `connectgaps:false`.
  - Trend: width 1.5, `dash:'dash'` if significant, otherwise `'dot'`.
- Layout:
  ```js
  {
    paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
    font:{family:'JetBrains Mono, ui-monospace, monospace', size:11, color:ink2},
    margin:{l:60, r:96, t:12, b:44},
    xaxis:{gridcolor:ruleFaint, linecolor:ink2, tickcolor:ink2, ticks:'outside', ticklen:5,
           showspikes:true, spikemode:'across', spikedash:'dot', spikecolor:amber, spikethickness:1, spikesnap:'cursor'},
    yaxis:{title:{text:`${label} (${unit})`, font:{size:11, color:ink2}}, gridcolor:ruleFaint, griddash:'dot',
           zeroline:false, linecolor:ink2, showspikes:true, spikemode:'across', spikedash:'dot', spikecolor:amber, spikethickness:1},
    hovermode:'x', hoverlabel:{bgcolor:'#050f1d', bordercolor:cyan, font:{family:'JetBrains Mono', size:12, color:ink}},
    showlegend: series.length > 1, legend:{orientation:'h', y:-0.18, font:{size:11}},
    annotations:[/* per significant trend: text '+0.41 °C / decade' at the trend's last point,
                   showarrow:true, arrowcolor:amber, ax:48, ay:-24, bordercolor:amber, borderwidth:1,
                   borderpad:4, bgcolor:'#050f1d', font:{color:amber, size:11} */]
  }
  ```
- Config: `{responsive:true, displaylogo:false, displayModeBar:'hover', modeBarButtonsToRemove:['lasso2d','select2d','autoScale2d']}`. Style the modebar icons with `--ink-3`, `--cyan` on hover, square corners and a transparent background.
- **Plot-in:** on the first draw for a selection (and not under reduced motion), reveal the 12-month path with `stroke-dasharray`/`stroke-dashoffset` over 900 ms (`cubic-bezier(.2,.7,.2,1)`), then fade in the trend and the annotation after 200 ms.
- **Crosshair readout:** on `plotly_hover`, update a frame badge with `X 2014-07 · Y 28.4 °C`. On `plotly_unhover`, show the latest value.
- Call `Plotly.purge` before re-rendering and when showing a state message.

## 6. MapLibre theming (`map.js`)

- Basemap: drop the inverted OSM raster. Use `https://basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png` (attribution "© OpenStreetMap contributors © CARTO") with `raster-saturation:-1`, `raster-brightness-max:.55` and `raster-hue-rotate:200`. Even better, use no raster at all and draw linework from a static US-states GeoJSON in `static/data/` (a file asset, not an API change): state outlines as a 0.75 px `--rule` line, the selected state as a 1.5 px `--ink` line with an 8 % cyan fill, and a graticule every 5° as a `--rule-faint` dashed line.
- Terrain is off by default, with a small "3D" toggle button in the control group (exaggeration 1.2, pitch 45). The default is `pitch:20, bearing:0`. Fit to the selected state's bounds with 40 px padding (`fitBounds`), and use `jumpTo` under reduced motion.
- Hazards: draw a ring per hazard (`circle-color:transparent`, `circle-stroke-width:1.5`, `circle-stroke-color` from the token by phenomenon, falling back to the API colour), with radius scaled by `probability_pct`. Use a hatched fill via `fill-pattern` (an `addImage` with a canvas-drawn 8×8 45° hatch) or a symbol layer. Co-located hazards must not hide each other: either offset them ±0.4° in longitude, or render them as concentric rings with the larger probability outermost. Add a text label layer (`{label} {p}%`, JetBrains Mono through glyphs is not required; a DOM marker is acceptable) so meaning never depends on colour.
- Controls: `NavigationControl` (square, `--cell` background, `--rule` borders, icons inverted to `--ink-2`) and a compact `AttributionControl`.
- Use `cooperativeGestures: matchMedia('(pointer:coarse)').matches`.
- Popups: square, 1 px cyan border, `--sheet` background, 12 px mono. They open on click **and** on keyboard focus of the matching `#map-list` item.
- On WebGL failure, hide the frame and show an amber callout in `#map-message`. The list remains.

---

## 7. Motion

- Use one easing everywhere: `cubic-bezier(.2,.7,.2,1)`, with durations of 600–900 ms.
- **Counters** (`#prob-value`, the "Change" finding cell and other-event percentages) tick from the previous value to the new one with `requestAnimationFrame` (or GSAP if loaded), using `tabular-nums`.
- **Bars and meters** grow from 0 when they enter the viewport (`IntersectionObserver`, `threshold:.4`), and only once per selection.
- **Chart** plots itself in (see §5).
- **Sheet reveal:** CSS-only, `@keyframes` translateY(12px)→0 with opacity, `animation-fill-mode:both` and 60 ms stagger. Content must remain visible if JS or the CDN fails, so do not gate first paint on GSAP.
- **Crosshair readouts** on the chart and the map.
- `@media (prefers-reduced-motion: reduce)`: no transitions or animations, counters jump to the final value, the map uses `jumpTo`, there is no plot-in, `scroll-behavior:auto`. Check this in JS with `matchMedia` as well.

## 8. Accessibility

- Every text colour is at least 4.5:1 on its background (the token table guarantees this when `--ink-3` is the floor). Lines may use `--rule`.
- There is a visible focus on every interactive element: a 2 px amber outline, plus the `.tb:focus-within` treatment for selects. Nothing removes the outline without a replacement.
- The skip link "Skip to results" goes to `#main` and is visible on focus.
- Landmarks: `header` (Sheet 01), `main`, one `section` per sheet with `aria-labelledby`. The heading order is h1 → h2 → h3.
- Live regions: the finding readout `aria-live="polite"`, `#verdict` `aria-live="polite"`, `#map-message` and `#prob-note` `role="status"`, `#controls-status` `role="alert"`. Set `aria-busy` during loads.
- `#prob-meter` has `role="img"` with an `aria-label` ("Chance 81 percent; usually 20 percent"). The chart frame has `role="img"` and `aria-describedby` pointing at the verdict sentence. `#map` has `aria-label` and is backed by `#map-list`.
- Meaning is never carried by colour alone: badges carry glyph and words, hazards carry pattern, label and list, and significance carries line style and word.
- Touch targets are at least 44×44 px on coarse pointers. Zooming to 200 % causes no loss of content.
- Chip toggles are `<button aria-pressed>`. `<details>` summaries are keyboard reachable.

## 9. Print (whiteprint)

`@media print`:
- Swap the tokens to whiteprint: `--sheet:#ffffff; --cell:#f3f6fa; --ink:#0b1f3a; --ink-2:rgba(11,31,58,.85); --ink-3:rgba(11,31,58,.7); --rule:rgba(11,31,58,.35); --cyan:#0a5ea8; --amber:#9a5b00; --red:#b3261e; --violet:#4b4fb3`. Set `body{background:#fff}` with no grid.
- Sheets have no box-shadow, `break-inside:avoid`, and one sheet per page where possible. The strip and ruler ticks remain.
- Hide the map canvas, the chip row, the modebar and the skip link. Show `#map-list` and expand all `<details>`.
- On `beforeprint`, call `Plotly.relayout` with the print ink colours (and `font.color:'#0b1f3a'`). On `afterprint`, restore them.
- The colophon prints the drawn date and source.

## 10. Housekeeping

- Remove Bootstrap and Font Awesome. Replace icons with mono glyphs or inline 1.5 px-stroke SVGs in `currentColor`.
- Load the trimmed font weights only, with `display=swap`.
- No inline styles from JS except CSS custom properties (`--p`, `--u`) and map and chart internals.
- Keep JS modules small and independent. They share only `trend:select`, plus an optional `trend:loaded` event (`detail:{kind, data}`) that summary and strip-ref modules may consume.

---

## 11. Acceptance checklist

- [ ] All IDs listed in §2 exist. `trend:select` is dispatched on load and on change, with `{state, variable, depth}` and `depth===""` when hidden.
- [ ] No build step. All third-party assets come from CDNs. Bootstrap and Font Awesome are not loaded.
- [ ] At 1440×900, the h1 question, the selects, the verdict badge, the total change and the next-month chance are all visible without scrolling.
- [ ] At 390×844, the finding readout is visible within the first 1.5 screens, there is no horizontal scroll, and the map does not trap one-finger scroll.
- [ ] The chart is full width and at least 340 px tall, with monthly lines off by default. The trend is visibly sloped, a significant trend carries a dimension annotation, and the crosshair spikes are amber dotted.
- [ ] Co-located drought and flood markers are both visible and distinguishable without colour.
- [ ] No text is below 11 px. Every text colour reaches at least 4.5:1 (checked with a contrast tool on `--sheet`).
- [ ] Keyboard: Tab reaches the skip link, three selects, sheet index links, chart chips, verdict `<details>`, the map list and Retry buttons, each with a visible amber focus.
- [ ] Every sheet shows distinct loading, empty, error (with Retry) and ready states, with no layout shift when data lands.
- [ ] No teal, no glows, no rounded corners. Hatch appears only where risk exceeds usual.
- [ ] Strip refs update live with state, variable, period or valid-for month. A date mismatch between sheets shows an amber callout.
- [ ] Reduced motion produces no animation, counters jump, and the map jumps.
- [ ] Print preview shows a white, legible whiteprint with the map list instead of the canvas and the details expanded.
- [ ] With WebGL disabled, the map shows a callout and the hotspot list still works. With the network blocked for `/api/*`, each sheet shows its error state and Retry works.
- [ ] No console errors on load or on switching to soil moisture (depth field appears) and back.
