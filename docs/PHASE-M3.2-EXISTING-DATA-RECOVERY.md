# Phase M3.2: existing-data recovery and mapping

*Started 2026-10-25 from `eb3772e`, after M3.1 (`6880c16`). The order is: existing evidence →
deterministic mapping → provenance → reconciliation → model. Nothing is scraped, OCR'd or
guessed, and no model value is corrected because a sheet disagrees.*

## Baseline

| | |
|---|---|
| HEAD | `eb3772e`, clean tree |
| Suite | 32 suites, 836 checks, all pass (404.6 s with 2 workers: the performance reference) |
| Model | 333,180 rows; hashes captured per file; `migrate --check` byte for byte |
| Protected groups | canonical, evidence, discovery, scope, review, phase records, phase34 model: unchanged |
| Generated app data | byte-identical to the model |
| M3.1 register | 580 gaps; 458 live (R1 102, R2 189, R3 23, R4 95, R5 49) and 122 deferred |

The first full run of the baseline tripped the new performance check (more than 10 % slower).
The suites that grew were the ones running while the recovery dry run competed for the processor.
A clean rerun passed and became the reference. The check works, and the recovery dry runs are
kept off the machine while the suite runs.

## How a figure reaches its source (what exists, reused)

- A fiche or cuvée figure is a legacy **Observation** plus a **CanonicalValue**, both pointing at
  one **Provenance**. `tools/mig_m6_provenance.value_prov` chooses that provenance:
  - **LEGACY_FIELD_SOURCE:** field-src names the field and one artifact;
  - **LEGACY_AMBIGUOUS_SOURCE:** field-src names a file that several artifacts could be;
  - **LEGACY_RECORD_SOURCE:** only the record names a sheet. Phase 4's invariant I13 says this is
    *never* taken as the field's source.
- `tools/build-app-data.figure_sources` turns the first two into the page's per-figure source.
  The third gives none: these are the 2,149 figures shown without a source.

M3.2 adds no new layer. A figure is recovered when the record's own held sheet is shown, from its
text, to state that figure. The figure then gets a **DOCUMENT** provenance with:

- the exact artifact (proven sha256);
- the quoted passage and its locus;
- `derived_from` pointing at the old record-level provenance, so its history is kept;
- `code_state` naming the stream, the audit candidate, the record, the field and the file name.

The canonical value's status becomes **SOURCED**, which is already in the contract. **Its value
is never touched.** `figure_sources` gives the figure that file, with an address only where those
exact bytes have one; otherwise the source is on file.

## M3.2A: own-sheet recovery

**Candidates:** the 1,247 figures M3.1 found "printed in the record's own held sheet".

That M3.1 check was a token check: the number with its unit, anywhere in the document. M3.2A
reads each sheet again with **field-anchored** rules (`tools/m32_recovery.py`). A value counts as
explicitly present only where it stands with its own field's label:

| Field | Counts when |
|---|---|
| alcohol | after *alcool / alcohol / degré / TAV*, or as *N % vol* (not "100% Alcohol", not "14 % Cabernet Franc") |
| pH | after *pH* |
| yield | after *rendement / yield*, with hl |
| new oak | *N % neuves / new*, or *neuves / new oak N %* adjacent |
| months | *N mois / months* after an élevage, barrel or oak word |
| blend | every share beside its own grape, all in one contiguous run, in a passage naming the blend, and not straight after a planting or soil heading |

Never a match, whatever the value:

- a number that is the bound of a range ("50-80 % neuves suivant millésime", "16 to 18 months");
- a labelled number outside the field's plausible range;
- a sheet stating the field twice with different values.

Each rule came from reading the samples. The first draft took "100% Alcohol" as an alcohol of 100,
and the top of "50-80 % neuves" as Dauzac's new oak. It also built a blend out of a vineyard
table's planting percentages (Sarget de Gruaud-Larose 2000), which is decision D1's territory. All
three are refused now, and each is a test.

**Classification of the 1,247:**

| Classification | Count | Disposition |
|---|---:|---|
| MODEL_MATCHES | **716** | APPLY_PROVENANCE: the figure gains its own sheet as source |
| AMBIGUOUS | 380 | review: the value is printed, but not as that field (115 months, 86 oak, 80 blend, 70 alcohol, 29 yield) |
| NOT_FOUND | 108 | review: no labelled statement in the held text (88 blend, 20 months) |
| DUPLICATE_VALUE | 17 | review: the sheet states the field with two values (two wines on one sheet) |
| FIELD_NOT_CHECKABLE | 16 | review: a blend with a grape code no rule reads |
| MODEL_CONFLICT | **10** | reconciliation: the sheet states another value; the model keeps its own |
| MODEL_MISSING | 0 | (stream A only covers figures the model holds) |

**The 716 recovered:**

- **By field:** blend 254, alcohol 201, new oak 104, yield 80, months 50, pH 27.
- **Where they come from:** 390 records of 58 estates.
- **Source type:** 715 have a web source (those exact bytes have an address); 1 is on file only.
- **Shared sources:** 1 sheet is shared by several estates; the source names the file, never
  another estate.

**The 10 conflicts, kept for reconciliation and not corrected:**

| Record | Field | Model | Sheet |
|---|---|---|---|
| beychevelle 2013 | yield | 28.8 | 28,5 hl/ha |
| stem-chateau-de-ferrand 2024 | yield | 40 | "a final yield of 30 hl/ha" |
| dauzac 2008 | new oak | 80 | 70 % |
| stem-chateau-grand-mayne 2022 | new oak | 40 | "60% fût neuf, 40% fûts d'un an": the model's 40 looks like the one-year barrels |
| la-mission-haut-brion 2024 | blend | CS 51, ME 46.5, CF 2.5 | "Cabernet Franc: 51%; Merlot: 46.5%; Cabernet Sauvignon: 2.5%": CS and CF look swapped |
| batailley 2025, gruaud-larose 2012 and 2013, margaux 2021, stem-chateau-destieux 2020 | blend | the model's shares | the same grapes with other shares |

### Application

The migration reads the audit's APPLY_PROVENANCE rows and nothing else. The model changed exactly
as expected:

| File | Change |
|---|---|
| `canonical/values.jsonl` | 716 rows: provenance and status only (LEGACY_RECORD_SOURCE_ONLY → SOURCED); every value identical |
| `observation/observations.jsonl` | 716 rows: provenance only; every value, unit and qualifier identical |
| `cross/provenance.jsonl` | +716 DOCUMENT rows; none changed or removed |
| `manifest.json` | those three files; the M7 status counts move by exactly 716 (fiches 651, cuvées 65); totals unchanged |
| `data/app/figure-sources.js` | exactly the 716 figures gain their source; nothing else added, removed or changed |

Everything else is unchanged:

- the 30 other model files, byte for byte;
- the evidence store and the discovery data;
- canonical data, scope and review data;
- every other generated file.

`migrate --check` and `build-app-data --check` pass. The recovery audit and the M3.1 register both
reproduce byte for byte. The analysis reads a recovered figure through `derived_from` as it stood
before, so M3.1's measurements stay its own.

### The earlier suites

Ten earlier checks asserted that the model or the generated data never changed after their own
phase. Each now names M3.2's change exactly, through `tools/historical_m2_scope.py`:

- the model may differ only as above;
- `figure-sources.js` may differ only by the recovered figures, verified entry by entry against the
  pre-M3.2 file;
- `app-reference` names `BDX_FIGURE_SRC` as an expected M3.2 change.

Two checks needed more than a scope:

- **test-phase4's I13 rule** (an artifact on a value's provenance only through a resolved field
  source) now also admits an M3.2 source. It must be SOURCED, quoted, and derived from the record
  source: evidence, not the record's assumption. Badette 2020's own assertion is unchanged.
- **test-phase61** names the recovered source as the figure's own, by the same rules.

Nothing was removed or skipped.

### Gate

**SAFE — M3.2A EXISTING DATA RECOVERY COMPLETE**
