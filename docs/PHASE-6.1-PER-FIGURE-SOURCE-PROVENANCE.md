# Phase 6.1 — Per-figure source provenance

Gate: **SAFE — PHASE 6.1 PER-FIGURE SOURCE PROVENANCE IMPLEMENTED**

The vintage view now shows each figure's own source, as the normalized model records it. No value,
model record, canonical data, evidence or discovery data changed. The application still reads
`data/app/`.

## 1. The defect

The Phase 6.0 audit (finding F1) found this. Every expanded vintage ended with one "Read the
estate's own sheet" link, which read as the source of all the figures above it. Of the 4,691
canonical figures on records that carried such a link:

- the linked sheet was the figure's own source for 1,833 (39 %);
- it was a **different document** for 612 (13 %);
- for 2,245 (48 %) no source was established either way.

## 2. Where the provenance was lost

The path is: model figure → provenance → generated application data → UI.

- **Model:** every figure is an observation with its own provenance (Phase 4 M6/M7). A field
  source points at its document through a legacy reference and that document's artifact; the
  artifact's URL placements give its addresses. The record's sheet is separate (`document_url`).
- **Generated data (`tools/build-app-data.py`):** the files were the legacy-shaped projection. They
  kept one `src` filename and one `url` per vintage record and **dropped the per-field
  provenance**. This is where the source identity was lost.
- **UI:** `fichesBlock` printed one record link (`ficheUrl`). The prose sourcing lines (`srcLine`)
  linked the same record sheet.

## 3. The implementation

**Generated data.** `tools/build-app-data.py` writes one more file,
`data/app/figure-sources.js`, holding `window.BDX_FIGURE_SRC` (537 KB). It is derived from the
model's provenance per figure, and the other 23 generated files are byte-identical. For each fiche
and cuvée record, by field:

| The model's provenance | Generated | Shown |
|---|---|---|
| field source, one document with a recorded address | `{n: file, u: url}` | a **source** link to that document |
| field source, one document, no address recorded | `{n: file}` | **source on file**, with the file name on hover |
| field source names a file several documents share | `{a: file, c: n}` | **source unclear** (no link) |
| only the record's source, or none | no entry | **no source**; the record's sheet is not substituted |

Each distinct source is stored once, and each figure holds an index into that list.

Where one document sits at several addresses (the same bytes), the record's own address is used if
it is one of them, otherwise the first in sorted order. That is not a choice between documents: all
those addresses hold the same bytes.

**UI** (`assets/app.js`):

- The new `figSrc` mark sits beside the blend, yield, alcohol, months in barrel, new oak, pH,
  residual sugar, total acidity, serving temperature, the food suggestion and the reprinted scores.
- The prose sourcing lines (note and tasting) link only to their own field's document (`srcLine`
  with the field).
- The record link is renamed **"The sheet recorded for this vintage"**, with "each figure above
  cites its own source, where one is known".
- The new labels have Dutch entries in `assets/i18n.js`.
- `index.html` and the service worker load the new file, and the cache name is bumped to
  `bordeaux-classified-v170`.

Not changed: the values, the layout, the Compare tab's "Sheet" row (a record-level row in another
view, §6), and every other Phase 6.0 finding (out of scope).

## 4. Tests

**`tools/test-phase61.py`**, 10 checks on real cases from the audit:

| Check | Case |
|---|---|
| a figure from the estate's sheet | Cantemerle 2019 blend and new oak, from `FT-Cantemerle-2019-EN.pdf`, the linked sheet |
| a figure from a different document | Cantemerle 2019 months in barrel, from `FT-Cantemerle-2019-FR.pdf` |
| two documents on one page | Cantemerle 2019 new oak against months in barrel |
| no established source | Batailley 2025 blend: no source shown, although the record links a sheet. Batailley 2020 blend: a name two documents share, shown as "source unclear" |
| metadata is the model's | the months' provenance, legacy reference and URL placement, traced in the model |
| generated equals the model | every fiche and cuvée figure's generated source against its provenance; none invented |
| no misattribution | the audit's 4,691-figure measure: 0 linked to another document, 0 shown without a known source |
| the page | headless Chrome on the real page: each fact's link equals its own source; Batailley's blend has none; the record link carries its new name |
| values unchanged | the control comparison (below): 0 unexplained |
| generated and protected data | the 23 generated files unchanged since `8b13cb0`; canonical, evidence, discovery, scope and proposals unchanged; the model unchanged |

**The control comparison** (`tools/app-reference.py`) was made able to see the change:

- **It opens the vintage blocks it claims to.** The expanded vintage block had never been in the
  captured text: rows open from their head button, and the capture clicked the row. Phase 5's page
  comparison therefore did not cover the fiche figures. It does now.
- **It splits presentation from values.** It records each drawer's text with the source marks and
  the record link removed (the *value text*). A page whose value text is unchanged is classified
  "EXPECTED: PROVENANCE PRESENTATION"; any other difference stays UNEXPLAINED.
- **It names the one new global.** `BDX_FIGURE_SRC` is reported as an addition, and no other global
  is.
- **It was re-captured.** The control comes from the application as committed at `8b13cb0`, on the
  legacy source, in a copy of the site.

Result:

| Class | Count |
|---|---:|
| IDENTICAL | 10,738 |
| EXPECTED: PRESENTATION ORDER | 22 (unchanged since the switch) |
| EXPECTED: PROVENANCE PRESENTATION | 10 pages |
| EXPECTED: ADDED FIGURE PROVENANCE | 1 |
| **UNEXPLAINED** | **0** |

The three pages left identical hold no field-sourced figure.

**Rescoped, not weakened.** Three Phase 5 checks and one Phase 4 check assumed the application never
changes after Phase 5. They now hold their own phase:

- no Phase 5 commit touched `assets/`;
- `index.html` and the service worker differ from Phase 4 by the switch, plus the one named
  `figure-sources.js` line;
- the control comparison may contain only the named Phase 6.1 classes;
- M12's load list allows `data/app/figure-sources.js` as the one generated extra.

## 5. Before and after

Measured over the same 4,691 canonical figures on records that link a sheet:

| | Before | After |
|---|---:|---:|
| shown with the record sheet, which is their own source | 1,833 | — |
| linked to their **own** source | — | **2,142** |
| their own source named, no address recorded | — | 304 |
| shown with the record sheet, which is **another** document | **612** | **0** |
| ambiguous source (one name, several documents) | under the record sheet | 96, marked "source unclear" |
| no established source | under the record sheet | 2,149, shown without a source |

No figure with known provenance is presented as though the record sheet were its source. The 612
now link their own documents, and the 2,245 unestablished ones are no longer given the record's
sheet. Coverage is not 100 %, and was not the aim: 2,149 figures have no field-level source in the
model, and inventing one would be the defect again.

**Performance**, as a regression check:

| | Before (M0 / after the switch) | After this phase |
|---|---|---|
| cold app ready | 655 / 674, 462, 724 ms | 497, 654, 631 ms |
| warm app ready | 148 / 134, 135, 143 ms | 134, 136, 122 ms |
| broadest search | 39.6 / 37.7–45.5 ms | 34.3 ms |

Startup data grew by the 537 KB file, about 14 %. No material regression was measured. These runs
went to a temporary file, not the benchmark log, because they were taken before this commit existed.

## 6. Remaining limitations

- **2,149 figures have no established source**, so they show none. Establishing them is data work
  (audit F12, Q0).
- **96 figures cite a file name that several documents share** (multi-version paths, audit Q0).
  They stay "source unclear"; choosing one would be the first-match resolution I22 forbids.
- **304 figures have their own source document but no recorded web address.** The file name shows
  on hover, and no URL is fabricated.
- **The Compare tab's "Sheet" row** still links each column's record sheet. It is a row of its own,
  not attached to a figure, but it sits under the compared figures. Out of scope here; it is the
  same pattern in another view.
- **Estate-level figures** (hectares, owner, typical blend) cite nothing, as before. The model holds
  them as LEGACY_UNSOURCED.

## 7. Verification

| | |
|---|---|
| test-phase61 | 10/10 |
| test-phase5 | 25/25 |
| test-phase4 | 66/66 |
| all suites | 23 pass |
| protected hashes | unchanged (`tools/phase4-baseline.py --check`) |
| model | rebuilds byte for byte |
| `data/app/` | the model, byte for byte (`tools/build-app-data.py --check`) |
| application source | `data/app/` |
