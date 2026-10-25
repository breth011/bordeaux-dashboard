# Phase 6.9 — The vintage-list heading, and sheets outside the listed years

Gate: **SAFE — PHASE 6.9 HEADING AND COVERAGE SEMANTICS IMPLEMENTED**

This implements the change recommended by the Phase 6.8 audit
(`docs/PHASE-6.8-HEADING-SEMANTICS-AUDIT.md`, `8bedf42`). It is presentation only.

No model, canonical data, evidence, provenance, source document, vintage value, identity or
second-wine decision changed. No historical date was added and no name resolved.

## 1. Why the old heading misled

The vintage list's span is the **reference's** years: the keys of the regional vintage file
(`BDX_VINTAGES`), 1982–2025, the same for every wine. The heading put something else before it:

- **"All vintages, 1982–2025"** for a grand vin;
- **the wine's current name** for any other wine.

"Echo de Lynch-Bages, 1982–2025" reads as that name across those 44 years. Three things contradict
that reading:

- Echo's sheets start in 2011;
- the unreconciled evidence names it Haut-Bages Averous until 2007;
- the Phase 6.7 block directly below says the name's adoption is not recorded.

## 2. The new heading

The heading is **"Vintages 1982–2025 in this reference"** for every wine, grand vin included. In
Dutch it is **"Jaargangen 1982–2025 in deze gids"**.

- **The span** is still computed from `BDX_VINTAGES`, so it follows the data.
- **No wine or estate name**, and no "All vintages". The "Which wine" selector above names the wine;
  the block below says what is established about it.
- **It claims nothing about the wine:** not that it existed under this name, not that it has a sheet
  for every year, not that it was made every year.
- **The hints keep their meaning:** "N of 44 rated · M ready to drink now" (grand vin) and "N of 44
  with a sheet on file" (other wines). The latter now has its Dutch, "N van 44 met een fiche in het
  archief", which it lacked (Phase 6.8).
- **Dutch terminology.** `gids` was chosen over `naslagwerk`: neither occurred in `assets/i18n.js`,
  and `gids` is the plainer word, as the brief preferred. "Fiche in het archief" reuses the wording
  Phases 6.5 and 6.7 established for "on file".

## 3. Reference range against sheet coverage

| | Meaning | Where |
|---|---|---|
| **Reference range** | the 44 years the list shows, the same for every wine | the heading |
| **Sheets within it** | the wine's sheets among those years | the hint ("13 of 44 with a sheet on file") and the rows |
| **Sheets on file** | **every** sheet the model holds for the wine, with its first and last year | the Phase 6.7 block |
| **Sheets outside it** | how many of those lie before or after the listed years | the block's sheets line, since this phase |

**Wording.** For a wine whose sheets all lie within the range, the line reads as before: "13 vintages,
2011–2025". Otherwise it adds what lies outside:

- "48 vintages, 1978–2025; **4 before the years listed below**"
- "28 vintages, 1998–2026; **1 after the years listed below**"

In Dutch: "4 vóór de jaren hieronder" and "1 na de jaren hieronder". When there are no sheets, the
line still reads "none". Not-made years are unchanged.

## 4. Sheets outside the listed years

19 wines have them. None is dropped, and no row is created for them.

| Group | Wines | What the page does |
|---|---|---|
| grand vins with sheets before 1982 | 12 (for example Braude, Lafite) | the block says "N before the years listed below"; the existing "Earlier vintages" section lists them, as before |
| **grand vins with a 2026 sheet** | 5: Haut-Bailly, La Tour Blanche, Langoa-Barton, Léoville-Barton, Lynch-Moussas | the block says "1 after the years listed below"; **no 2026 row is created**, and the list still ends at 2025 |
| **the Pavillons du Château Margaux**, rouge and blanc | 2 | "48 vintages, 1978–2025; 4 before the years listed below". The 1978–1981 sheets are kept; other wines have no "Earlier vintages" section. The hint still reads "44 of 44 with a sheet on file", the years listed. |

## 5. A Phase 6.7 counting defect, corrected

Auditing the sheet count found that Phase 6.7 counted only the sheet records **figures were extracted
from**. The page itself, in its rows and hint, treats every sheet record as a sheet on file, including
the three that only name their document:

| Record | Holds |
|---|---|
| Latour-Martillac 2020 | `src` only |
| Malescot 1995 | `src` only (the Phase 2 refused note) |
| Prieuré-Lichine 2021 | `src` and a drink window |

So the block undercounted by one for those three wines.

**The correction.** `wine_established()` now counts every fiche or cuvée record that has
observations or a record-level legacy reference. That reproduces the page's records exactly: 2,725
fiche and 1,174 cuvée records, with nothing extra on either side.

## 6. Generated data

`data/app/wine-established.js`, regenerated (98 → 120 KB, still 593 records):

- **`y` added:** each wine's sorted sheet years, so the page can count those outside its range. This
  applies to the 340 wines with any sheet.
- **`s` corrected for exactly three wines:**

  | Wine | Before | After |
  |---|---|---|
  | Latour-Martillac | 10 | 11 |
  | Malescot | 25 | 26 |
  | Prieuré-Lichine | 25 | 26 |

- **Nothing else changed,** in that file or in any other generated file. Generation is
  deterministic, and `build-app-data --check` passes.

## 7. Representative cases

English, at the committed state:

| Case | Heading | Hint | Sheets on file |
|---|---|---|---|
| Lynch-Bages | Vintages 1982–2025 in this reference | 21 of 44 rated · 18 ready to drink now | 31 vintages, 1988–2025 |
| Echo de Lynch-Bages | the same | 13 of 44 with a sheet on file | 13 vintages, 2011–2025 |
| Haut-Bailly | the same | 21 of 44 rated · 23 ready to drink now | 28 vintages, 1998–2026; 1 after the years listed below |
| Haut-Bailly II | the same | 7 of 44 with a sheet on file | 7 vintages, 2018–2025 |
| Lions de Batailley | the same | 4 of 44 with a sheet on file | 4 vintages, 2014–2017 |
| Yquem | the same | 10 of 44 rated · 20 ready to drink now | 2 vintages, 2021–2023 (not made 1992, 2012, 2018, unchanged) |
| Climens | the same | 8 of 44 rated · 18 ready to drink now | 15 vintages, 2005–2023 (six not-made years, unchanged) |
| Pavillon Rouge / Blanc | the same | 44 of 44 with a sheet on file | 48 vintages, 1978–2025; 4 before the years listed below |
| Lynch-Moussas | the same | 22 of 44 rated · 19 ready to drink now | 8 vintages, 2019–2026; 1 after the years listed below |
| Malescot | the same | 0 of 44 rated · 23 ready to drink now | 26 vintages, 1990–2018 (was 25) |

**The unresolved cases stay unresolved:**

- **Echo:** "When it was adopted, and any earlier names, are not recorded"; no Haut-Bages Averous,
  no "renamed".
- **Haut-Bailly II:** the estate fact still reads "Not established", and the block still says which
  wine is the second is not established.
- **Lions de Batailley:** "Conflicting records", with no winner.

## 8. Tests

**`tools/test-phase69.py`**, 16 checks. The page checks sweep **all 593 wines** in the page.

| Area | Checks |
|---|---|
| the heading | every wine uses the reference heading; it names no wine and no estate; no "All vintages" remains; it holds no control; the list is still the reference's 44 years, and a grand vin's earlier section still holds exactly its pre-span sheets |
| language | the English and Dutch heading, the Dutch hint and the two coverage phrases exist, and render in Dutch |
| coverage | every wine's sheets line equals the generated record with its outside counts; wines within the range read exactly as in Phase 6.7 (over 300 of them); the 19 out-of-range wines say their counts; the five 2026 sheets get no row and are kept in the data; the Pavillons' 1978–1981 sheets are kept and said |
| unchanged | not-made years identical to `aaa90c6`; Echo, Haut-Bailly II and Lions de Batailley as before |
| page | clean at 390 px; Tab from the wine selector still reaches the first vintage row in one step |
| data | the generated change is exactly the sheet years plus the three counts, each explained by a record-level reference in the model; all other generated files byte-identical; deterministic; the model and protected data unchanged |

**The checks can fail.** Run against `aaa90c6`'s application, the page checks fail for the intended
reasons: the "All vintages" heading, the old Dutch heading, and coverage without the outside counts.

**Earlier suites, updated the established way, with no assertion removed or loosened:**

- **test-phase67** re-derives sheet coverage with the corrected definition, checks the new `y`, and
  expects the outside counts.
- **test-phase63's** 137-drawer comparison leaves the heading out on both sides.
- **test-phase5, 61 and 63** name the observed heading classes.

**Comparison tooling.** `app-reference.py` names a fifth presentation, VINTAGE LIST HEADING, and one
intended global change, `CHANGED_GLOBALS`. The precise content of that change is held by
test-phase69, because the capture keeps only hashes. The long-lived control was re-captured from
`8b13cb0`.

## 9. Equivalence

**Against `aaa90c6`** (Phase 6.7):

| Class | Count |
|---|---:|
| IDENTICAL | 10,901 |
| VINTAGE LIST HEADING presentation | 11 |
| ESTABLISHED WINE FACTS and VINTAGE LIST HEADING (Lafite and Margaux, whose coverage gained an outside count) | 2 |
| CHANGED: the wine-established data (sheet years) | 1 |
| unexplained | **0** |

Every vintage row and value is identical.

**Against the long-lived control (`8b13cb0`):** 0 unexplained. The heading appears only together
with the presentations Phases 6.1–6.7 named, and the 22 accepted order differences remain.

## 10. Suite

**27 suites, 740 checks** (724 + 16), all pass with `tools/run-tests.py` at 2 workers.
