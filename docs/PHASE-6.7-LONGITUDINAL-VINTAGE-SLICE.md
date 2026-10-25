# Phase 6.7 — Longitudinal vintage slice: what is established about a wine

Gate: **SAFE — PHASE 6.7 LONGITUDINAL VINTAGE SLICE IMPLEMENTED**

This implements the first slice defined in `docs/NEXT-PHASE-LONGITUDINAL-VINTAGE-DESIGN.md`
(`aa75bf7`).

**Display only.** No model, canonical data, evidence, provenance, source, identity or historical
record changed. No date was added, no former name inferred, and no unresolved case resolved.

## What the user sees

**In the drawer**, above each wine's vintage list, a compact block titled *What is established about
this wine*. It shows the selected wine's facts as the model holds them now:

| Line | Shown | Missingness |
|---|---|---|
| Name | the current name, marked "current name" | "When it was adopted, and any earlier names, are not recorded." (every NameRecord is CURRENT, from UNKNOWN) |
| Rank | first or second wine, …, "current, as this dataset records it" | for a SECOND-tier wine of an estate whose second-wine status is *not established* or *conflict* (Phase 6.3), a note pointing to that fact; nothing is resolved |
| Classification | rank and scheme, "the current list (YEAR)" | "The list in force today; which list applied to each vintage is not recorded." Or "none recorded for this wine". |
| Appellation | the wine's appellation, "current" | "none recorded for this wine itself", with "The estate's appellation is shown above." where it is |
| Sheets on file | "13 vintages, 2011–2025" | "none" |
| Recorded as not made | only years with a NOT_PRODUCED statement | the line is absent otherwise |

Then: "A year without a sheet is not evidence that the wine was not made: only the years listed as not
made are recorded as such."

The vintage rows below are unchanged.

**In Compare**, in the vertical view only, one line: "Rank and appellation are the estate's current
values, the same under every vintage; they are not established for each vintage."

**Dutch** entries were added for every phrase. Four short labels (Rank, Classification, Appellation,
none) already had identical entries, which the block reuses.

## Data

`data/app/wine-established.js` (`BDX_WINE_ESTABLISHED`, 98 KB, **593 records**, one per wine the page
can show) is written by `tools/build-app-data.py` `wine_established()` from the model. Its keys are
`estate|slug`, `grand` for the grand vin, from the identity map's `grand-vin` and `wine-by-slug`.

| Key | From |
|---|---|
| `n` | the CURRENT NameRecord |
| `nf`, `fn` | a dated start, or FORMER names; **none exist**, so none are written |
| `r`, `rc` | distinct RankAssertion tiers and claimants |
| `c` | ClassificationMembership: rank, scheme, edition year, edition status |
| `a` | AppellationMembership |
| `s` | sheets on file: the fiche and cuvée records the wine's observations came from |
| `x` | NOT_PRODUCED VintageStatements |

The other 26 generated files are byte-identical. The file is deterministic, and
`build-app-data --check` passes.

**Sheet coverage is the model's**, every year with a sheet record. For a few wines that includes years
outside the reference's 1982–2025 list: earlier vintages, which the drawer shows in its own section,
and 2026.

## Cases

| Case | Shown |
|---|---|
| Lynch-Bages grand vin | first wine; Cinquièmes Crus, Classification of 1855, the current list (1855); Pauillac; 31 vintages, 1988–2025 |
| Echo de Lynch-Bages | current name only; second wine; no classification or appellation of its own; 13 vintages, 2011–2025. Haut-Bages Averous, 2008 and "renamed" appear nowhere, in the data or on the page. |
| Haut-Bailly II | current name; second wine, with "Which wine is the estate's second wine is not established"; La Parde is not mentioned in the block |
| Lions de Batailley | "The estate's records conflict about its second wine"; 4 vintages, 2014–2017 |
| Yquem, Climens | not made: 1992, 2012, 2018 / 1984, 1987, 1992, 1993, 2012, 2017 |
| Corbin | Grands Crus Classés, Saint-Émilion 2022, the current list (2022), with the per-vintage note; the 2022 "no second wine" statement (P6) is not shown, because it is not in the model |

## Tests

**`tools/test-phase67.py`**, 16 checks:

- the file is the model and deterministic;
- every fact is re-derived from the model's own tables;
- no history invented;
- not-made years only where recorded;
- each case above, rendered;
- every phrase has Dutch, and the block renders in Dutch;
- Compare's note appears in the vertical view only;
- it fits at 390 px;
- no focusable element in the block, and Tab passes from the wine selector to the first vintage row;
- the model and protected data are unchanged.

**The checks can fail.** The page checks fail against `aa75bf7`'s application. The data checks fail
when a former name or an unrecorded not-made year is injected.

**Comparison tooling, extended the established way:**

- `app-reference.py` names a fourth presentation, ESTABLISHED WINE FACTS: the drawer text without the
  block.
- The long-lived control was re-captured from `8b13cb0`.
- test-phase63's 137-drawer comparison leaves the block out on both sides.
- test-phase4, 5, 61, 63 and 65 name the new file and the observed classes.

No assertion was removed or loosened.

## Equivalence

**Against `aa75bf7`:**

| Class | Count |
|---|---:|
| IDENTICAL | 10,902 |
| ESTABLISHED WINE FACTS presentation (12 captured drawers) | 12 |
| the added global | 1 |
| unexplained | **0** |

L'Enclos, a list-only estate with no record, is identical.

**Against the long-lived control:** 0 unexplained. The block appears only together with the
presentations named by Phases 6.1, 6.3 and 6.5, and the 22 accepted order differences remain.

## Suite

**26 suites, 724 checks** (708 + 16), all pass with `tools/run-tests.py` at 2 workers.

## Not done

Deliberately:

- the drawer's vintage-list heading still reads "*Wine*, 1982–2025". The block above it qualifies it;
  rewording the heading was outside this slice.
- No dated history: D2 (Echo, Haut-Bailly II), Corbin 2022 and document dates remain the decisions
  listed in the design document (§7).
