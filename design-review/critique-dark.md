# Trend Detective: the darker night blueprint, reviewed

**What I reviewed.** I read `templates/base.html`, `templates/dashboard.html`, `static/css/style.css` and `static/js/{summary,chart,map,controls,verdict,event_chance,ui}.js`. I also checked the live app at http://localhost:5055 (Texas · Temperature) at 1440×900 and 375×812. I looked at all four sheets on each, plus the first paint during loading, and measured with in-page JS. The browser pane returns scaled screenshots, so a few pixel-level calls (halation, hatch texture) are judgement made at 1× zoom.

**Scope.** I didn't repeat anything the first critique (`critique.md`) covered that has since been fixed, such as finding-first, contrast floors, the title block, hatch semantics and print. Two of its P2 items are still open and come up again below only where the dark change makes them worse.

All contrast figures are WCAG 2.x ratios, computed by compositing each token over the actual fill.

## Verdict

The darkening worked on text. Every text token now passes with room to spare. It failed on **surfaces**:

- The page, the sheet, the title-block cells and the chart and map wells are all within 1.7 % luminance of each other (1.01–1.02:1).
- The only blue left is in the accents.

As a result the page no longer reads as blueprint paper. It reads as generic near-black "dark mode" with cyan lines on it. Structure survives only because the 1.5 px `--line` borders do all the work.

The fix keeps the page as dark as it is now, or darker, and does three things:

1. Put **chroma**, not lightness, back into the ground.
2. Build a real **elevation ladder** with steps of ≥1.05:1.
3. Tint the **rules and grid blue** instead of neutral white-at-alpha.

---

## Contrast on the current tokens

Text is fine. UI boundaries are not.

| Token | on `--sheet #02070f` | on cell `--paper #030a14` | Requirement |
|---|---|---|---|
| `--ink #eaf4ff` | 18.16 | 17.86 | 4.5 ✔ (halation risk, see #6) |
| `--ink-2` .78 | 10.97 | 10.88 | 4.5 ✔ |
| `--ink-3` .62 | 7.10 | 7.06 | 4.5 ✔ |
| `--line` .82 | 12.07 | 11.96 | 3 ✔ |
| `--rule` .22 | **1.79** | **1.81** | 3 ✘ when it bounds a control |
| `--rule-faint` .10 | 1.22 | 1.23 | decorative only |
| `--grid` .05 (on page) | 1.06 | – | effectively invisible |
| `--grid-major` .09 | 1.12 | – | barely visible |
| cyan / amber / red / grey | 13.1 / 12.6 / 8.2 / 9.4 | similar | ✔ |

Surface separation:

| Pair | Ratio |
|---|---|
| sheet vs page | 1.017 |
| sheet vs title-block cell | 1.017 |
| sheet vs frame well | 1.016 |
| 6 px sheet "mat" ring `rgba(3,12,24,.95)` vs page | **1.012** |

The mat ring is invisible, so the outer outline is only the 1 px `--rule-faint` ring at 1.22:1.

---

## P0

### 1. The surfaces have collapsed into one black, and sheets now sit *below* the page
- **What:** `--sheet #02070f` is darker than `--paper #030a14`. The body gradient also runs from `#06162a` at the top through `--paper` at 40 %. So at the top of the page the gutters are *brighter* than the sheets, and the sheets read as holes cut into the paper rather than drawings laid on it.
  - Title-block cells (`.tb`, `.finding__cell` → `--paper`) are 1.7 % lighter than the sheet. That isn't perceivable.
  - The chart and map wells (`.frame` → `--paper-deep`) are 1.6 % darker. Also not perceivable.
- **Why:** A blueprint's depth comes from sheet on table and drawing area on sheet. With no elevation the eye has to parse structure from line weight alone. That is tiring at this density (title block, finding, verdict stats and the frames all look like the same box).
- **Fix:** Use a five-step ladder, each step ≥1.05:1 apart and all blue-hued (see the token table):
  - `--page-deep #010409`
  - `--page #020914`
  - `--sheet #04112a`
  - `--cell #061733`
  - `--well #010813`

  Measured: sheet vs page 1.064, cell vs sheet 1.053, well vs sheet 1.070.

  Apply them as follows:
  - `.tb, .finding__cell { background: var(--cell) }`
  - `.verdict-stats div, .verdict-item.is-sig { background: var(--cell) }`
  - `.frame { background-color: var(--well) }`
  - `.sheet { background: var(--sheet) }`

  The sheet is still about **8× darker in luminance than a classic blueprint** (`#0f3d6e`, L=0.046, versus L=0.006), so the darker-than-blueprint intent holds.

### 2. Neutral rules and lost chroma make it generic dark mode, not a blueprint
- **What:** Every line token is `rgba(234,244,255,α)`. Over near-black that composites to neutral grey: `--rule` becomes `#353b44` and `--rule-faint` becomes `#191f27`. The ground has almost no chroma either (`#02070f` is about 5 % saturation in practice).
  - In the screenshots the only blue on the page comes from the cyan accents and the top-left glow.
  - The title-block hairlines, strip dividers, ruler ticks, registration marks and the dashed select underline are all grey.
- **Why:** Blueprint identity is *blue ground with white or cyan linework*. You can drop the ground to near-black and keep the identity, but only if the **lines carry the blue**.
- **Fix:** Re-base the line family on a blueprint-line blue `#8cc4ff`:
  - `--rule: rgba(140,196,255,.26)`, decorative, 1.78:1
  - `--rule-faint: rgba(140,196,255,.12)`
  - `--rule-ui: rgba(140,196,255,.50)`, **3.37:1** on sheet, cell, well and page

  Keep `--line` (the sheet and title-block outline) as near-white `rgba(220,236,255,.82)`. The white outline on blue hairlines is the classic drawing look.

  Raise the grid as well, still hue-tinted:
  - `--grid: rgba(120,180,255,.07)`
  - `--grid-major: rgba(120,180,255,.14)`, 1.23:1 on page

### 3. Control boundaries fail 3:1 (WCAG 1.4.11)
- **What:** `--rule` (1.79:1) is the *only* visible edge of several controls:
  - `.form-select`: a dashed underline, and the only affordance that the State and Measurement values are editable
  - `.chip` (Show monthly values, 3D terrain)
  - `.sheet-index a`
  - the MapLibre control group (`box-shadow: 0 0 0 1px var(--rule)`)

  On the darker sheet these read as floating text.
- **Fix:**
  - `.form-select { border-bottom: 1px dashed var(--rule-ui) }`
  - `.chip, .sheet-index a { border-color: var(--rule-ui) }`
  - `.maplibregl-ctrl-group { box-shadow: 0 0 0 1px var(--rule-ui) !important; background: var(--cell) !important }`

  Give selects a resting fill so they read as fields: `.tb--select { background: var(--control, #0a1f40) }`, which is 1.147:1 against the sheet. Ink on that fill is still 14.7:1.

---

## P1

### 4. The double outline, ruler ticks and registration marks have nearly disappeared
- **What:**
  - **Sheet mat:** the 6 px `0 0 0 6px rgba(3,12,24,.95)` ring is 1.01:1 against the page, so the "double outline" is now one bright border plus a 1 px ring at 1.22:1 that only shows on good panels.
  - **Ruler ticks:** the 24 px minor ticks (`--rule-faint`) are invisible, and only the 120 px ticks show.
  - **Registration mark:** at `--rule` it shows as a smudge (visible in the screenshots, but only just).
- **Fix:**
  - **Mat:** `box-shadow: 0 0 0 6px var(--page-deep), 0 0 0 7px var(--rule), 0 24px 48px -24px #000`. The mat is now *darker* than the page, so the ring separates, and the ring itself is 1.78:1.
  - **Strip ticks:** major ticks `--rule-ui` 8 px tall, minor ticks `--rule` 4 px tall.
  - **Registration mark:** `--rule-ui`. Add a second mark top-left inside the strip area (`.sheet::before` at `left:12px; top:48px`) so the sheets register diagonally like a real set.

### 5. The radial top glow points the wrong way. Drop it, or move it onto the sheet
- **What:** `radial-gradient(… #06162a 0%, var(--paper) 40%, var(--paper-deep) 100%)` sits behind Sheet 01. At 1440 wide it only shows as a 22 px halo in the gutters above and beside the first sheet. Being brighter than the sheet, it makes Sheet 01 look sunken (#1). On mobile it is a 16 px sliver.
- **Why:** The glow is the only chroma on the ground, which is why it was kept, but it lights the table and not the drawing.
- **Fix:** Remove it from `body`. Instead:
  - Use flat `--page` with a soft edge vignette: `radial-gradient(ellipse 140% 90% at 50% 30%, var(--page) 55%, var(--page-deep) 100%)`.
  - Optionally add a lamp on the hero sheet only: `.sheet--hero { background: radial-gradient(ellipse 80% 60% at 20% 0%, #06173a 0%, var(--sheet) 60%) }`. That gives one deliberate pool of light on the finding, the thing you want read first.

### 6. Halation: big solid accent blocks and pure-white body text glare on near-black
- **What:** At 12–18:1, solid accent fills bloom on black, especially for astigmatic readers and on OLED. Examples:
  - the solid cyan `.finding__badge.is-sig` and `.badge-up/.badge-down`
  - the solid ink `.chip[aria-pressed=true]`
  - the amber `.callout::before` tag and `.map-demo`
  - the full-width cyan `.meter-fill`
  - 15–16 px body text in pure `#eaf4ff` (18:1)

  The thin mono labels are fine: `--ink-3` at 7:1 does not halate.
- **Fix:**
  - **Badges:** change to outline plus tint: `.finding__badge.is-sig, .badge-up, .badge-down { background: rgba(127,220,255,.14); color: var(--cyan); border: 1.5px solid var(--cyan) }`. That keeps 9.05:1.
  - **Pressed chip:** `background: rgba(234,244,255,.12); color: var(--ink); border-color: var(--ink)`.
  - **Body text:** add `--ink-body: rgba(234,244,255,.90)` (13.7:1) for running text (`body`, `.verdict-text`, `.prob-sentence`, `.callout`). Keep full `--ink` for headings, numbers and values.
  - **Meter:** `.meter-fill { background: rgba(127,220,255,.55) }` with a 2 px solid cyan right edge.
  - **Chart:** drop the 12-month line to `width: 2`.

### 7. Tinted callout fills turn muddy brown and maroon on near-black
- **What:**
  - `.callout` uses `rgba(255,193,99,.06)`, which composites to `#111214`, an olive-brown smear. It is very visible on mobile, where the 160 px "Dates differ" box is the second thing on screen.
  - `.callout--error` at `rgba(255,125,125,.07)` goes maroon.
  - `.tag-higher` does the same.
- **Why:** Low-alpha warm tints only work over a ground with some lightness. Over blue-black they desaturate into mud.
- **Fix:** Callouts get the cool `--cell` fill (amber .06 over `#061733` gives `#152136`, still blue). Carry the warning colour in the border and a 3 px left bar: `.callout { background: var(--cell); border: 1px dashed var(--amber); box-shadow: inset 3px 0 0 var(--amber) }`. Apply the same to `--error` with red. Remove the tint from `.tag-higher`, so it is a red outline plus red text only.

### 8. The basemap reads as dark Google Maps, not a plan drawing, and land and water merge
- **What:** The paint `raster-brightness-min .92 / max 0`, `saturation -.85`, `hue-rotate 200`, `contrast .15` makes OSM tiles near-black grey. In the screenshots:
  - the Gulf of Mexico and the land are almost the same value
  - state boundaries are faint
  - labels are grey sans-serif

  Nothing on the map is blueprint blue, so it is the most "generic dark" object on the page.
- **Fix (no new dependencies):** Put a blue `background` layer under the raster and let the inverted tiles multiply over it:
  - `{ id:'paper', type:'background', paint:{ 'background-color':'#05183a' } }` first
  - then the raster with `'raster-opacity': 0.78, 'raster-brightness-min': 0.9, 'raster-brightness-max': 0.04, 'raster-saturation': -1, 'raster-contrast': 0.3`

  Water comes out darker blue, land a lifted blue-grey, and lines and labels pale blue.
- **Better, if a vector source is acceptable:** OpenFreeMap or another keyless vector style lets the plan be pure linework:
  - water `#020c1e`
  - land `#05183a`
  - state lines `rgba(140,196,255,.5)` at 0.8 px
  - coast lines `rgba(127,220,255,.6)`
  - labels in JetBrains Mono at 10 px, `rgba(234,244,255,.7)`

  Also set `hillshade-highlight-color: #1a4a80` so the 3D view has some relief on dark.

### 9. The chart and map wells aren't legible as drawing areas
- **What:** `.frame` is `--paper-deep` on `--sheet`, 1.016:1. The fine grid inside it is `.05`, 1.05:1. In the screenshots the chart area is defined only by its `--ink-2` border and corner brackets, and Plotly's own gridlines (`--rule-faint`, 1.22:1) are almost invisible behind the series.
- **Fix:**
  - **Frame:** `.frame { background-color: var(--well) }` with the inner grid at `rgba(120,180,255,.08)` / 24 px and `.16` / 120 px. The well becomes recessed, gridded paper.
  - **chart.js grid:** `gridcolor: css('--rule')`, the blue .26 version.
  - **chart.js axes:** `linecolor/tickcolor: css('--rule-ui')`. Keep `--ink-2` for tick labels only.
  - **Annotation:** `bgcolor: css('--well')`.

### 10. Loading states: empty selects, an h1 that reflows, and cyan dashes
- **What:**
  - **Selects:** on first paint (screenshot at about 0.3 s, 375 px) they show as empty fields with chevrons. There is no "Loading states…" text, so they look broken.
  - **h1:** it starts as "Is this part of the Earth really changing?" (3 lines on mobile), then becomes "Is Texas really getting warmer?" (2 lines). The finding block jumps about 40 px.
  - **Placeholders:** the finding `–` placeholders render as 46 px cyan Barlow dashes at .45 opacity, which reads as a value of "minus".
- **Fix:**
  - **Selects:** server-render `<option>Loading…</option>` in each select, styled `--ink-3`.
  - **h1:** give it `min-height: 2lh` at ≤900 px (`3lh` is too much once resolved) and use `text-wrap: balance`, which already exists.
  - **Busy values:** `[aria-busy=true] .finding__num { color: var(--ink-3) }`. Replace the dash with a dashed outline bar: `.finding__num:empty::before { content:''; display:block; width:4ch; height:.6em; border:1px dashed var(--rule-ui) }`, and have summary.js write `''` instead of `–` while busy.

---

## P2

### 11. Mobile (375 px): the modebar, the 3D chip and lost "valid" dates
- **Modebar:** Plotly's modebar is permanently visible on touch, because hover becomes always-on. It sits over the top-right of the plot, where the trend annotation lands. Use `displayModeBar: matchMedia('(pointer:coarse)').matches ? false : 'hover'`.
- **3D chip:** it covers about 30 % of the map's bottom-right on a 343 px wide map. Move it into the MapLibre control column as a custom control, or below the map next to the legend.
- **Valid dates:** `.strip__ref` is `display:none` at ≤900 px, so the amber "VALID NOV 2026" dates, the very thing the "Dates differ" callout warns about, disappear on mobile. Wrap the strip to two rows instead: `.strip { grid-template-columns: auto 1fr; height:auto } .strip__ref { grid-column: 1/-1; border-left:0; border-top:1px solid var(--rule) }`. Bump `.sheet` padding-top to 84 px.
- **Callout order:** on mobile the "Dates differ" callout sits above the controls. Move it below the title block (`#date-callout { order: 4 }`). It is context, not the answer.

### 12. Strip titles truncate on the half-width sheets
At 1440 wide, Sheet 03's strip shows "ODDS · CHANCE OF AN EVE…" because the ref with its VALID date takes the room. The h2 directly below repeats the title. Shorten the strip titles to one word (`ODDS`, `MAP`, `RECORD`, `FINDING`) and let the ref carry the metadata.

### 13. The red hatch reads lilac at 1×
`.meter-excess` draws 1.5 px red lines over an 18 % red base on near-black, and at normal zoom it reads as pinkish-grey. Use 2 px lines on a 6 px pitch over `rgba(255,125,125,.24)`, with a 1 px solid red top and bottom edge. The hatch then reads as "red, affected" from arm's length.

### 14. Map popup and attribution are the flattest things on the page
`.maplibregl-popup-content` uses `--paper-deep` on a near-black map, so it barely separates. Use `background: var(--cell); border: 1px solid var(--cyan); box-shadow: 0 0 0 4px var(--page-deep)`. The attribution should be `--ink-3` on `rgba(2,9,20,.85)`.

### 15. Leftovers from the first critique that dark makes worse
- **Bootstrap:** it is still loaded (`data-bs-theme="dark"` plus about 160 KB). Its `.form-select` dark background image and the `--bs-body-bg` cascade fight the new `--cell` fill.
- **Font Awesome:** the icon tiles (`.tile`) are solid-stroke cyan boxes, more halation sources.

Replace the select with `appearance:none` and an inline SVG chevron stroked in `--ink-2`. Swap the FA icons for 1.5 px inline SVGs in `--ink-2`, keeping cyan for data only.

### 16. The odds sheet ends in a 200 px void beside the map
At 1440 wide, Sheet 03 is about 200 px shorter than Sheet 04, and the dark gutter under it is now indistinguishable from the sheet edge. Either `align-items: stretch` the board row and pin `#prob-basis` to the bottom (`margin-top:auto` in a flex column), or move "other events" into a small two-cell title-block table to fill it with data.

---

## Proposed dark token table

These tokens are darker than a classic blueprint, but blue-hued. All ratios are WCAG 2.x, measured on the token's own surface.

| Token | Value | Role | Key contrast |
|---|---|---|---|
| `--page-deep` | `#010409` | outer vignette, sheet mat ring, readout and popup backing | – |
| `--page` | `#020914` | page ground under the grid | – |
| `--sheet` | `#04112a` | sheet fill (L≈0.006, about 8× darker than `#0f3d6e`) | 1.064 vs page |
| `--cell` | `#061733` | title-block cells, finding cells, verdict stats, callouts, popups | 1.053 vs sheet |
| `--well` | `#010813` | chart and map frame background (recessed drawing area) | 1.070 vs sheet |
| `--control` | `#0a1f40` | resting fill of select cells, chip hover | 1.147 vs sheet |
| `--ink` | `#eaf4ff` | headings, numbers, values | 16.9 sheet |
| `--ink-body` | `rgba(234,244,255,.90)` | running text | 13.7 sheet |
| `--ink-2` | `rgba(234,244,255,.78)` | secondary text, tick labels | 10.4 sheet |
| `--ink-3` | `rgba(234,244,255,.64)` | mono labels; the text floor | 7.3 sheet / 7.1 cell |
| `--line` | `rgba(220,236,255,.82)` | sheet and title-block outline (white-on-blue) | 10.7 |
| `--rule-ui` | `rgba(140,196,255,.50)` | **any control boundary**, axis lines, registration marks, major ticks | **3.37** everywhere |
| `--rule` | `rgba(140,196,255,.26)` | decorative hairlines, cell gaps, chart gridlines | 1.78 |
| `--rule-faint` | `rgba(140,196,255,.12)` | list separators, minor ticks | 1.24 |
| `--grid` | `rgba(120,180,255,.07)` | 24 px paper grid | 1.09 |
| `--grid-major` | `rgba(120,180,255,.14)` | 120 px paper grid | 1.23 |
| `--well-grid` / `--well-grid-major` | `.08` / `.16` (same blue) | grid inside frames | – |
| `--cyan` | `#7fdcff` | record and significant results (lines, outline badges) | 12.1 sheet |
| `--cyan-tint` | `rgba(127,220,255,.14)` | significant badge or verdict fill | cyan on it 9.05 |
| `--amber` | `#ffc163` | usual, valid dates, focus, trend line | 11.7 sheet |
| `--red` | `#ff7d7d` | risk above usual (text, ring, hatch lines) | 7.6 sheet |
| `--red-hatch-base` | `rgba(255,125,125,.24)` | under the 2 px/6 px hatch | – |
| `--grey` | `#9fb3cc` | not significant (dashed) | 8.8 sheet |
| `--hz-drought` / `--hz-flood` | `#ffc163` / `#a9b8ff` | map hazards | ≥9 |
| map paper | `#05183a` background layer, raster opacity .78 | blue plan under inverted tiles | – |

Body: `background: radial-gradient(ellipse 140% 90% at 50% 30%, var(--page) 55%, var(--page-deep) 100%)` under the two grid layers. Remove `#06162a` from the body.
