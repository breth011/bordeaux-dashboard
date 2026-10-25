# Phase 6.5 — Provenance display and accessibility

Gate: **SAFE — PHASE 6.5 PROVENANCE DISPLAY AND ACCESSIBILITY IMPLEMENTED**

This phase implements recommendation B of the Phase 6.4 audit (`docs/PHASE-6.4-PROVENANCE-EVIDENCE-AUDIT.md`,
`c15b421`, unchanged and authoritative). Provenance the model already holds is now:

- shown in the Compare tab;
- inspectable without a hover;
- reachable by touch and keyboard;
- worded no more strongly than the data allows.

**No model, canonical data, evidence decision, identity, or source artifact was changed.** No
provenance was repaired or added, no conflict was resolved, and Braude/Mongravey 1999 (audit F5) stays
as recorded.

## 1. Scope

| Changed | Not changed |
|---|---|
| display logic (`assets/app.js`) | the normalized model (`data/model/`, byte-identical) |
| one generated file, `data/app/source-facts.js` | the 25 existing generated files (byte-identical) |
| Compare-tab sources | canonical values, evidence, discovery, artifacts, URLs, identities |
| provenance wording, website and sparse-estate labels | extraction methods, confidence, dates, passages |
| source summaries, touch, keyboard, ARIA | the scraper; the Phase 6.4 audit |
| CSS, Dutch strings, `index.html`, service worker (cache v172) | |
| tests and comparison tooling | |

## 2. Files changed

| File | Change |
|---|---|
| `assets/app.js` | `figSrc` renders controls instead of title-only spans; `srcMore`, `srcSummary`, `toggleSrc`, `closeSrc`, a capture-phase Escape handler; `cmpSrc` and per-figure sources in Compare; the Sheet row renamed and allowed to wrap; `SITE_SOURCE` wording; the Wikidata fallback; the sparse-estate notice |
| `assets/styles.css` | `.src-btn`, `.src-more`, `.src-panel`, focus rings, `.cmp tbody th.cmp-wrap` |
| `assets/i18n.js` | Dutch for the summary, the Sheet row and the website titles |
| `index.html`, `service-worker.js` | load `data/app/source-facts.js`; cache `bordeaux-classified-v172` |
| `tools/build-app-data.py` | `source_facts()` and `pack()`; writes `source-facts.js` |
| `data/app/source-facts.js` | new, generated (28 KB) |
| `tools/test-phase65.py` | new, 20 checks |
| `tools/app-reference.py` | a third named presentation, provenance wording; the new controls dropped with the source marks; `BDX_SOURCE_FACTS` a named addition |
| `tools/fixtures/app-reference.json` | re-captured from `8b13cb0`'s application on the legacy source, as in Phase 6.3, with the extra text |
| `tools/test-phase4.py`, `test-phase5.py`, `test-phase61.py`, `test-phase63.py` | name the new generated file and the 6.5 classes where they list later additions; no check removed or loosened |

## 3. Provenance states displayed

Each state is shown exactly as the generated data records it:

| State | Model | Beside the figure | The summary says |
|---|---|---|---|
| Known web source | LEGACY_FIELD_SOURCE with a URL placement | the "source" link, as before, which opens the document in a new tab; beside it an "about this source" control | the document's file name; its type; "open the document" (the same address); "Also cited for N other estates" where it applies |
| File-only source | LEGACY_FIELD_SOURCE, no URL | "source on file", now a button | the file name; its type; "Kept on file: no web address was recorded, and this app does not publish the file." |
| Ambiguous source | LEGACY_AMBIGUOUS_SOURCE | "source unclear", now a button | "Which document this figure was recorded from is unclear"; the name in the record; "N documents carry this name; which of them this figure came from is not recorded" |
| No known source | record-level or none | nothing, as before | — |
| Several documents on one record | per field | each figure its own mark and summary (Cantemerle 2019: in barrel → FR sheet, new oak and blend → EN sheet) | its own document |
| Shared source | the same artifact cited for another estate | as above | "Also cited for N other estates" |

**Document type.** Where the model's assessment is specific, the summary uses it:

- "a web page; its text is kept on file" (WEB_PAGE);
- "a sheet covering several wines" (MULTI_WINE_SHEET);
- "a report covering several estates" (GROUP_REPORT).

Otherwise it says only what the file name says: "PDF document" or "text file". UNKNOWN and OTHER are
not shown.

**What the summary does not say.** The heading is "The document this figure was recorded from". It
does not claim the document was checked against the figure, and a test holds that no summary uses
"verified", "confirmed", "proven", "checked" or "authoritative". No placeholder advertises data the
model lacks (passages, dates, method, confidence).

**Braude/Mongravey 1999.** The summary shows the recorded file, *FT-Ch-Braude-Fellonneau-2015-GB.pdf*,
and "Also cited for 1 other estate". Nothing is corrected or flagged, and a test holds that.

## 4. Compare tab

**Sources beside each figure.** Each compared figure now carries the drawer's own mark, through the
same `figSrc`. The rows covered are:

- blend, picked, yield, alcohol, in barrel, new oak;
- pH, residual sugar, total acidity, serve at;
- serve it with, decant, the estate on the wine.

**No merging across differing sources.** A cell with a mark never merges with its neighbour. Two
vintages that read alike but come from two records are two cells. Cantemerle 2019 and 2020 "12
months" used to be one merged cell with no source.

**The sheet row stays, with its scope named.**

- It is now called "Sheet recorded for this vintage". It links what it linked before, and still shows
  "—" where no address is recorded.
- Its label wraps within the label column. The labels are sticky and do not wrap, so the longer name
  had doubled the column that covers the cells on a phone (106 → 213 px). A test holds that it stays
  at 106 px.

**Cantemerle 2019.** In barrel links the French sheet; new oak and blend link the English one. The
sheet row links the English sheet as the vintage's record, beside figures that show their own.

## 5. Wording corrections

| Where | Before | After |
|---|---|---|
| website, tag `dom` (81) | "from the estate's own site, confirmed by reading it" | "from the estate's own site" |
| website, tag `domr` (26) | "…, checked by hand" | "from the estate's own site, recorded by hand" |
| website, tag `hand` (6) | "from the estate, checked by hand" | "from the estate, recorded by hand" |
| website, an unmapped tag (`handx`: Suau) | "from Wikidata" (a fallback) | "where this address was found is not recorded"; a `wikidata` tag is still "from Wikidata" |
| sparse estates | "**A verified name and rank, and little else.**" | "**A name and rank, and little else.**" (the next sentence already says they come from the published list) |

The tag data is unchanged. The `dom`/`domr`/`hand` wording describes how the address was recorded, not
a check. What those tags meant originally is still the audit's open question 6.

## 6. Touch and keyboard

**The pattern.** It is the settings panel's own pattern: a real `<button type="button">` with
`aria-expanded`. A press opens a summary directly under the control, in the run of the text, so
nothing is covered and nothing needs a hover. Only one summary is open at a time.

**Closing.** Any of these closes the summary:

- a second press;
- a click elsewhere;
- **Escape**, which also returns focus to the control.

Escape is handled in the capture phase, so with a summary open it closes the summary, not the drawer.
With none open, Escape closes the drawer as before.

**Keyboard.** The controls are in the tab order. Enter and Space work natively, and both open the same
summary. Focus never sticks: Tab moves into the summary's link and on.

**Touch.** A tap opens and closes the summary, and the page never navigates. The "source" link still
opens the document in a new tab (`target="_blank"`, `rel="noopener noreferrer"`). The tap target of
the 16 px "about" control is enlarged by an invisible 10 px margin.

## 7. Accessibility semantics

- **Accessible names.** "Source on file" and "source unclear" are buttons whose visible words are
  their names. The icon-only control is named "About this source" by `aria-label`, translated into
  Dutch with the page.
- **States.** `aria-expanded` gives the state, and `aria-controls` points at the open summary, a
  `role="group"` named "Source details".
- **No title-only information.** The file name and the ambiguity count are no longer in `title`. The
  web link keeps its title as an extra and repeats the file name in its summary.
- **Visible focus.** `:focus-visible` rings use the app's existing outline colour.
- **Not by colour alone.** The status reads in words; colour only reinforces it.
- **No focus on information.** Elements that only inform (the record line, the hint) are not made
  focusable.

## 8. Generated data

**Why `source-facts.js` was needed.** `figure-sources.js` deduplicates documents by name and address,
not by the model's artifact identity, and does not carry the model's document type. Sharing could
only have been inferred from equal URLs, which the spec rules out. The new file adds exactly two
model facts per LEGACY_FIELD_SOURCE figure, and only where they say something:

| Key | Meaning | Source in the model |
|---|---|---|
| `t` | WEB_PAGE, MULTI_WINE_SHEET or GROUP_REPORT | `document/assessments` for the figure's artifact |
| `o` | how many other estates have a figure from the same artifact | provenance → artifact id across the fiche and cuvée observations |

**Contents and size.** 1,427 figure entries over 681 records: 1,419 web pages, 4 multi-wine sheets,
and 18 entries citing one of the four artifacts the audit found shared. It is packed like
`figure-sources.js` and is 28,054 bytes (+0.7 % on the 4.0 MB of generated data). Ambiguous sources
get no facts, because which artifact they are is what is unknown.

**Checks.** Generation is deterministic, and `build-app-data.py --check` passes. The other 25
generated files are byte-identical to `c15b421`.

## 9. Tests

**`tools/test-phase65.py`**, 20 checks:

| Area | Checks |
|---|---|
| generated data | the file is `source_facts()`; every `t` is the artifact's assessment; every `o` counts the other estates citing the same artifact exactly; no fact left out; four shared artifacts; none for ambiguous sources; the other generated files byte-identical and generation deterministic |
| figure provenance | known web source (link kept, details one press away, same address); several documents on one record; file-only, inspectable, no invented link; ambiguous, inspectable; no source: no mark, no link (drawer and Compare); shared, said only where the model has it, including Braude without judgment; no summary claims proof |
| Compare | each figure's own source (Cantemerle 2019 in barrel ≠ the sheet row); every mark equals the figure source for that wine, year and field, and no figure without one gets one; values and sheet-row links unchanged against `c15b421` but for the row's name; the label column not widened on a phone |
| wording | no "verified", "confirmed" or "checked" in website labels or titles, one estate per tag rendered; Suau not credited to Wikidata, a real Wikidata address still is; the sparse notice |
| keyboard and touch | Tab reaches the controls in a drawer (Cantemerle 2020) and in Compare (Cantemerle 2019 and 2020); the focus ring shows; Enter opens; Escape closes and returns focus without closing the drawer; Space opens the same summary; Tab moves on; with no summary open, Escape still closes the drawer; at 390 px with touch, a tap opens and closes the details, which fit the screen, long file names wrap, and nothing navigates |
| semantics | marks that are not links are buttons with names and no title-only content; focus styles exist |
| protected data | the model, the Phase 6.4 audit, the legacy data, sources, evidence and discovery unchanged since `c15b421`; the group digests match the baseline |

**The checks can fail.** The page checks were run against `c15b421`'s application, and every one
failed there for the reason it names: title-only spans, the Wikidata fallback, "confirmed by reading
it", Compare without marks.

**Suite totals:**

| | Before | After |
|---|---:|---:|
| Suites | 24 | 25 |
| Checks | 687 | 707 |
| Failures | 0 | 0 |

**Integrity checks.** `phase4-baseline --check` reports unchanged; `migrate --check` rebuilds the model
byte for byte; `build-app-data --check` passes; `app-source` reports the model source.

## 10. Equivalence

Method: `tools/app-reference.py`, as in Phases 6.1 and 6.3. It covers the globals, the producers list,
13 searches, the lookups, and 13 estate drawers with every wine and opened vintage rows.

**Against `c15b421`** (Phase 6.4's application, captured fresh):

| Class | Count |
|---|---:|
| IDENTICAL | 10,907 |
| EXPECTED: PROVENANCE WORDING PRESENTATION | 4 (the captured sparse estates: Badette, Beaumont, Lauga, L'Enclos) |
| EXPECTED: ADDED SOURCE FACTS (Phase 6.5) | 1 |
| UNEXPLAINED | **0** |

**What the closed drawers show.** No drawer text differs beyond the sparse notice. A closed source mark
reads as it did ("source", "source on file", "source unclear"); the "about" control has no text; the
summaries exist only when opened. Phase 6.3's 137-drawer comparison (`test-phase63`) passes unchanged.

**Against the long-lived control** (re-captured from `8b13cb0` on the legacy source):

| Class | Count |
|---|---:|
| IDENTICAL | 10,736 |
| presentation order (Phase 5) | 22 |
| provenance (6.1) | 6 |
| provenance and second-wine status | 2 |
| provenance wording (6.5) | 2 |
| provenance and provenance wording | 2 |
| three named additions | 3 |
| UNEXPLAINED | **0** |

**Compare tab** (`test-phase65`; five estates, 2 to 4 vintages each, against `c15b421`):

- every row's values, with the source marks removed, are identical;
- only the sheet row's name changed, and its links are identical.

## 11. Browser, mobile and keyboard verification

Screenshots in headless Chrome at 1400 px and at 390 px (touch, scale 2), and in Dutch. They were
checked by eye and not committed. Each case:

- **Web-linked:** Cantemerle 2019, in barrel → FR, new oak → EN.
- **File-only:** Cantemerle 2020.
- **Ambiguous:** Batailley 2020.
- **No source:** Batailley 2025 blend.
- **Shared:** Lafite 2025, the group's page, "Also cited for 3 other estates".
- **Braude 1999.**
- **Suau.**
- **A sparse estate:** Beaumont.
- **A `dom` website:** Marceline.
- **Compare:** Cantemerle 2019 against 2020.

**Desktop.** The summary sits under its figure, the source reads as quiet grey words as before, and
Compare's marks sit in their own cells.

**Phone.** The summary wraps long file names within the cell, and the page does not scroll sideways.

**Dutch.** The summary reads "Het document waaruit dit cijfer is overgenomen …".

Keyboard and touch were exercised by the tests in section 9: real key and touch events through the
DevTools protocol, not synthetic clicks.

## 12. Performance

Measured with `tools/benchmark-phase5.py --only startup` and `--only search`. The output was not kept:
the benchmark log was restored.

| | Phase 6.3 | Phase 6.5 |
|---|---|---|
| cold app ready | 688 / 608 ms | 546 ms |
| warm app ready | 139 / 148 ms | 143 ms |
| broadest search ("chateau", 446 matches) | 34.8 ms | 53.0 ms, then 35.6 and 33.9 ms on reruns |
| page JS heap after cold load | — | 11.4 MB used |
| generated data | 4.0 MB | +28 KB (one file) |

There is no material regression. The first search run was noisy: it ranged 37–94 ms within the run,
and the reruns match Phase 6.3. The search code was not touched.

## 13. Known limitations, deliberately left

- **Not recorded in the model:** passages, locations, retrieval and publication dates, extraction
  method, confidence, and evidence against value. These are the audit's model and evidence decisions,
  and nothing here suggests otherwise.
- **The 2,149 figures without a field source** still show nothing. The summary does not tell the
  section 9 categories apart (the record's sheet, ambiguous, unknown); that would need the blank
  category generated. It was left out to keep this phase to the controls and summaries.
- **Braude/Mongravey 1999** (F5) and the four shared group pages stay as recorded and unjudged.
- **Hand-entered scores** (F10) still show their citation as text. `scoreFor`'s unrendered
  `verified: true` and the `flag-verified` class name (F15, F16) are untouched code-level names.
- **The website source** remains in the link's `title` (now honestly worded). It is supplementary to
  the address and was not made a visible line, to keep the 137 Phase 6.3 drawers unchanged.
- **The drawer's picking dates** (in the season line) still carry no per-figure mark. Compare's Picked
  row now does, from the same data.
- **Compare on a phone:** the sticky label column covers part of a scrolled cell. That is the table's
  existing layout, and this phase only kept it from getting wider.
- **Second wines in Compare:** Compare reads the grand vin only, so second wines still have no sheet
  row or sources there (F14).
