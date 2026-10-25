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

## M3.2B: online-source recovery

**Candidates:** the 71 figures whose own sheet is held and named but carries no address, while the
crawl fetched the same bytes from a URL.

For each figure the audit records:

- the exact artifact (sha256) and its file name;
- every address that served exactly those bytes, by the crawl's own sha256;
- whether that address is on the estate's own site (websites.js via `targets.json`, and the
  crawled domain);
- how the crawl found the address, and when;
- how many files of the same name with *other* bytes exist online (other versions).

Nothing was fetched: the crawl's record of each address is the evidence.

| Classification | Figures | Disposition |
|---|---:|---|
| EXACT_FIRST_PARTY (the estate's own site served exactly these bytes) | **71** | APPLY_PLACEMENT |
| EXACT_THIRD_PARTY (same bytes, another host) | 0 | review |
| AMBIGUOUS_SOURCE (no address with these bytes) | 0 | review |
| Different versions found under the same name | 0 | (would be recorded, never attached) |

The 71 figures sit on 47 artifacts at 48 addresses: one artifact is served at two. All are on the
estates' own sites, for example lafon-rochet.com, mission-haut-brion.com, chateau-kirwan.com and
chateau-climens.com.

### Application

The migration (M6 `recovered_placements`) reads the APPLY_PLACEMENT rows. For each address it adds:

- a **URL Placement** of the exact artifact, status PRESENT, observed on the crawl's fetch date
  (a point on the calendar axis);
- its **Locator**;
- a **DOCUMENT provenance** naming the stream, the audit row, the address, how it was discovered
  and when, and "identical bytes (sha256)".

| File | Change |
|---|---|
| `document/placements.jsonl` | +48 URL placements; none changed |
| `document/locators.jsonl` | +48 URL locators |
| `cross/provenance.jsonl` | +48 DOCUMENT rows |
| `derived/source-documents.json` | 14 sources gain the artifacts placed on their host; nothing removed |
| `manifest.json` | those files; one M6 statistic |
| `data/app/figure-sources.js` | 88 figures gain an address: the 71, and 17 other fields (picking dates, notes) that cite the same 47 files. Each keeps its file name; each new address is one M3.2B placed. |

An address belongs to bytes, not to a field, so every figure citing those bytes gains it. That is
why the count is 88 and not 71. No URL was made up: each one is an address the estate's own site
answered with exactly the held file.

The scope helper, the derived-index rebuild and the M3.2 suite hold the change to exactly this.
The helper checks that the index only gains placed artifacts, and that each changed figure only
went from {file} to {file, address} with an address from this stream.

### Gate

**SAFE — M3.2B EXISTING DATA RECOVERY COMPLETE**

## M3.2C: held-sheet extraction

**Candidates:** the 411 figures whose record's own sheet is a held PDF with no stored text. The
sheet reader (`tools/sheetreader.py`, pymupdf) reads such PDFs while it runs, but nothing kept the
text.

M3.2C reads each sheet the same way: flat, then by columns for two-column layouts. It then checks
the figure with stream A's rules. Only the passage that states the figure is kept (at most 200
characters, with the reader's version). No document is copied into the model. Nothing is OCR'd.

**Document classes, 195 PDFs:**

| Class | PDFs | Figures |
|---|---:|---:|
| TEXT_EXTRACTABLE | 195 | 408 |
| LAYOUT_EXTRACTABLE | 0 (no figure needed the column reading) | 0 |
| IMAGE_ONLY | **0**: every one has a text layer | 0 |
| CORRUPT_OR_UNREADABLE | 0 | 0 |
| IRRELEVANT_AFTER_REVIEW (text held, the figure not stated) | 3 | 3 |

M3.1 had called these "text not stored". They needed no OCR at all.

**Figures:**

| Classification | Count | Disposition |
|---|---:|---|
| MODEL_MATCHES | **284** | APPLY_PROVENANCE |
| AMBIGUOUS | 88 | review |
| FIELD_NOT_CHECKABLE | 19 | review |
| MODEL_CONFLICT | **13** | reconciliation, uncorrected |
| DUPLICATE_VALUE | 4 | review |
| NOT_FOUND | 3 | review |

**The conflicts show consistent entry errors.** Each is kept for reconciliation, never corrected:

- **pomerol-chateau-taillefer 2013–2018 new oak:** the model holds the *one-year* barrel share
  each time, e.g. 35 where the sheet says "50 % de barriques neuves, 35 % de barriques d'un an".
- **stem-chateau-fombrauge 2020 new oak:** 65 in the model; "35% new oak barrels, 65% one
  year-old" on the sheet.
- **stem-chateau-ripeau 2020–2024 yield:** 75 / 70 / 20 / 65 in the model, against
  30,75 / 31,70 / 41,20 / 32,65 hl/ha on the sheets.
- **lagrange 2024 and 2025 blend; belgrave 2005 months:** the latter labelled on another wine's
  passage.

### A stricter blend rule, and four of stream A withdrawn

Reading the compilations exposed a gap in the blend rule. It returned the first passage matching
the model's shares, without looking for another blend in the same document. A sheet covering
several vintages could therefore cite another vintage's section whose shares happen to coincide.
The Yon-Figeac merged PDF covers 2013 to 2022.

The rule now reads every labelled blend run in the document, in order. Each share is paired with
its own grape, by whichever orientation keeps the pairs closest, and a run counts only when its
shares make a whole (97 to 101). If another whole blend stands in the document, the figure is
DUPLICATE_VALUE. A first draft of this check paired each share with both neighbouring grapes and
invented blends that were not on the page (Beychevelle, Dauzac and others); reading the samples
caught it before anything was applied.

Four of stream A's 716 were applied in `ba5aaa4` and are refused now. Each sheet holds a second
blend:

- dauzac 2010 (another version, 66/34);
- malartic-lagraviere 2021 and 2022 (primeur and final);
- stem-chateau-yon-figeac 2013 (the compilation).

They are withdrawn openly. On the rebuild they go back to their record-level provenance, and the
four DOCUMENT rows M3.2 wrote for them go. No legacy row is touched, and the register's M3.2A count
reads 712.

### Application

| File | Change |
|---|---|
| `canonical/values.jsonl`, `observation/observations.jsonl` | 288 rows each: +284 gain their own sheet (C), 4 return to record-only (A withdrawn); provenance and status only, every value identical |
| `cross/provenance.jsonl` | +284 DOCUMENT rows, −4 (M3.2's own, withdrawn) |
| `data/app/figure-sources.js` | 284 figures gain their sheet; 4 lose the source A gave them |

SOURCED canonical values now total **996** (712 from A, 284 from C). `migrate --check`,
`build-app-data --check` and the index rebuild pass.

### Gate

**SAFE — M3.2C EXISTING DATA RECOVERY COMPLETE**
