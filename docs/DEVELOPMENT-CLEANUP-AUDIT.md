# Development cleanup audit

A read-only audit of the repository's development machinery after M3.11 (`a343337`), to find what the
value-application runner (`tools/apply-value-manifest.py`, `data/audit/value-application-manifest.jsonl`) has made
obsolete. **Nothing was deleted or changed while writing this audit.**

**Result.** I found nothing that meets all eight deletion rules, so this audit proposes **no deletions**. It
proposes **two documentation updates**: the README's "Extending it" and `docs/ADDING-A-VINTAGE.md`. Both
still tell future work to edit legacy files that have been frozen since Phase 4. It also lists **twelve legacy
tools and one design document to investigate** in a separate decision. Whether they can go depends on retiring
the legacy-file workflow, a product decision this audit cannot make.

## 1. Method

- **Inventory.** Every tracked file under `tools/` (188), `data/audit/` (28), `docs/` (72) and `reports/` (62), and
  the nine root files: 359 in all. There are no git hooks, no CI configuration, and no shell, batch, PowerShell,
  package or Makefile files.
- **Reference graph.** I searched every tracked text file (1,082) for each candidate's file name, and for `.py`
  files also for `import`, `from`, `import_module` and quoted module-name loads, which cover
  `spec_from_file_location`. Each reference is counted separately for code and for documents and data.
- **Dependency mechanisms traced by hand:**
  - test discovery: `tools/run-tests.py` globs `tools/test-*.py`;
  - the migration chain: `migrate.py` STAGES M2–M7, and the M7 hooks;
  - the frozen validations listed in §6;
  - `historical_m2_scope.py` actor and manifest names;
  - generated reports and their `--check`;
  - the Phase 3.1 structural audit;
  - `.gitignore`;
  - every non-phase document that gives forward-looking instructions.
- **Classes and actions** are as the brief defines them. Where any deletion rule was uncertain, I kept the file.

## 2. Classification summary

| Class | Files | Action |
|---|---:|---|
| ACTIVE | 123 | KEEP; `README.md`: UPDATE_REFERENCE |
| HISTORICAL-BUT-RETAIN | 200 | KEEP |
| LIKELY-LEGACY | 27 | 14 KEEP (a code caller exists); 12 INVESTIGATE; `docs/ADDING-A-VINTAGE.md`: UPDATE_REFERENCE |
| ONE-OFF/EXPERIMENT | 8 | KEEP |
| DUPLICATE/SUPERSEDED | 0 | — (the superseded *code paths* sit inside retained files: §3.4) |
| UNKNOWN | 1 | INVESTIGATE (`docs/INGESTION-ARCHITECTURE.md`) |
| **Total** | **359** | 344 KEEP, 2 UPDATE_REFERENCE, 13 INVESTIGATE, **0 DELETE** |

Appendix A has every file with its class, action and reference counts.

## 3. The M3.11 supersession check

M3.11 is now the only path for applying new, already-approved values. Before it, three phases each applied a
small fixed set of canonical values through their own machinery. None of that machinery is dead.

### 3.1 M3.2D: recovered values

| | |
|---|---|
| Paths | `tools/m32-recovery.py` (CLI), `tools/m32_recovery.py` (rules), `tools/m32-ocr.py` (M3.2E OCR), `data/audit/m32-recovery-candidates.jsonl`; `mig_m7_observations.recovered_values` |
| Class / action | HISTORICAL-BUT-RETAIN / KEEP |
| What it does | The audit of held documents' figures; its APPLY_VALUE rows are read by the migration's `recovered_values`, which adds 25 values (M7 stat "M3.2D recovered values"). |
| Superseded by | M3.11 for **new** batches only. |
| Callers | `mig_m7_observations` and `mig_m6_provenance` read the audit; `historical_m2_scope` (`M32_AUDIT`, `m32d_applied`, `is_m32d_*`); `m34a-mapping-audit.py` (fingerprinted); `test-m32`, `test-m33`, `test-m34a`, `test-phase4`, `test-historical-m1`; `data/audit/data-gap-register.jsonl` records M3.2's resolutions. |
| Frozen validation | Yes: `test-m32` (22 checks), `test-phase4` (`m7_reconciliations…`, `t20…`), `test-historical-m1` (row counts). |
| Historical reproducibility | Yes: the migration rebuilds these 25 values, with their ids and provenance, from this audit on every run. |
| Reason | Replacing them with runner rows would change their observation, reconciliation and provenance ids, which is a model change. Deleting the audit would break `migrate.py --check`. |

### 3.2 M3.6F: Cuvée Mongravey vintages

| | |
|---|---|
| Paths | `tools/m36f-vintages.py`, `data/audit/m3.6f-cuvee-vintages.jsonl`, `docs/PHASE-M3.6F-…` (generated); `mig_m7_observations.m36f_values`, and `mig_m5_vintages` for the vintages |
| Class / action | HISTORICAL-BUT-RETAIN / KEEP |
| What it does | The audited input from which the migration creates Cuvée Mongravey's vintages (M5) and 11 values (M7). |
| Superseded by | M3.11 for **new values**. M3.11 does not create vintages, so M5's use of this audit has no replacement at all. |
| Callers | `mig_m5_vintages`, `mig_m7_observations`, `historical_m2_scope` (`M36F_*`, `is_m36f_*`, `m36f_applied`), `data_gap_analysis` (`M36F_ACTOR`, the as-of set-aside), `m36g-acquisition.py`; `test-m36f` (runs `m36f-vintages.py --check`), `test-m36d`, `test-m36e`, `test-m36g`, `test-m36h`, `test-m36a-r1`, `test-m32`, `test-phase4`. |
| Frozen validation | Yes. |
| Historical reproducibility | Yes: a migration input. Its provenance rows name `tools/m36f-vintages.py` as actor. |
| Reason | It is in the migration chain, and the model's provenance names the tool. |

### 3.3 M3.10C: Durfort-Vivens values

| | |
|---|---|
| Paths | `tools/m310c-values.py`, `data/audit/m3.10c-value-application.jsonl`, `docs/PHASE-M3.10C-VALUE-APPLICATION.md` (generated); `mig_m7_observations.m310c_values` |
| Class / action | HISTORICAL-BUT-RETAIN / KEEP |
| What it does | The audited input from which the migration applies Durfort-Vivens' nine values (M7 stat "M3.10C Durfort-Vivens values"). |
| Superseded by | M3.11. The production manifest re-authorizes the same nine as `vam_000001`–`009`, and in production each is NOOP_EXISTING_IDENTICAL. |
| Callers | `mig_m7_observations`, `historical_m2_scope` (`M310C_*`, `is_m310c*`, `m310c_applied`), `data_gap_analysis` and `m39-evidence-review.py` (set-asides); `test-m310c` (runs `m310c-values.py --check`), `test-value-application-manifest` (golden reference and expected scope), `test-m310a`, `test-m310b`, `test-m32`, `test-m34b`, `test-historical-m1`, `test-phase4`. |
| Frozen validation | Yes, including the M3.11 golden test, which reads this audit as its expected scope. |
| Historical reproducibility | Yes. **The M3.11 runner's rows are not interchangeable with these rows.** The golden test pins their differences: ids, extraction, actor, `code_state`, resolver and reason. Routing the nine through the runner would rewrite 51 model rows. |
| Reason | It is the M3.11 golden reference and a migration input. The runner's NOOP depends on these rows existing. |

### 3.4 Duplicated construction code (superseded inside retained files)

`mig_m7_observations.recovered_values`, `m36f_values`, `m310c_values` and `apply-value-manifest.materialize` each
build observations, a reconciliation and a canonical value in nearly the same way.

**Authoritative for new work:** `apply-value-manifest.materialize`, through the migration's single
`value_application` hook.

**The three older hooks** are each one phase's frozen output. They must keep their own id tags and actor names
(`m32d`, `m36f`, `m310c`), or the model changes. Merging them is a refactor of the migration, which this phase
rules out.

**Action:** KEEP, with no new per-phase hook. The M3.11 report already records that new batches use the runner.

## 4. Other cleanup targets

### 4.1 Temporary manifests

There are none. All 28 files in `data/audit/` are read by code:
- 22 are phase audits: each is a migration input (M2, M4, M5, M6, M7) or is re-checked by its phase's frozen suite;
- `phase31-structure.json` is the Phase 3.1 frozen report;
- `historical-m3-candidates.jsonl` is read by `data_gap_analysis`;
- the gap register, its resolutions file and the runner manifest are live.

None was an intermediate application mechanism that something replaced.

### 4.2 Generated diagnostics

There are none to delete:
- **Generated reports in `docs/`** (`PHASE-M3.3`, `M3.4A`, `M3.4B`, `M3.5`, `M3.6A`/B/F, `M3.9`, `M3.10C` and others) are each re-checked by their generator's `--check` in a frozen suite.
- **`docs/DATA-GAP-REGISTER.md`** and **`data/audit/data-gap-register.jsonl`** are live outputs.
- **`PROGRESS.md`** and **`progress-history.tsv`** are deliberately tracked history (README §Files).
- **`reports/estates/*.md`** are hand-written deliverables. `.gitignore` keeps them tracked because a regeneration once destroyed findings.

There are no stray scratch, backup or debug files: no tracked `*.bak`, `tmp`, `scratch`, `draft` or `wip` names.

### 4.3 Duplicate helpers

| Function | Implementations | Authoritative | Action |
|---|---|---|---|
| Model loading | `migration_lib.read_table`; `data_gap_analysis.table` (the as-of read that sets later phases aside); `apply-value-manifest.View` (indexed, per run); `migrate.Model` (in memory); small `table()` helpers in some suites | `read_table` for raw rows; `data_gap_analysis.table` for the audits' as-of view; `View` for the runner | KEEP: they differ in meaning (as-of versus live, memoised), not only in form |
| Value validation | `apply-value-manifest.FIELDS`; `m310c-values.py` and `m36f-vintages.py` parse their own documents; `m32_recovery.classify` | the runner, for approved values | KEEP: the per-phase ones *extract* from text in frozen phases; the runner *validates* approved values |
| Observation, reconciliation and provenance construction | see §3.4 | the runner | KEEP (§3.4) |
| Deterministic checking | each phase tool's `--check`; `migrate.py --check`; `build-indexes.py --check`; `build-app-data.py --check`; runner `--check-all` | each for its own output | KEEP |
| Manifest validation | the runner's `validate_manifest`; each historical phase tool's fail-closed build | the runner | KEEP |

No helper is a byte-for-byte or behavioural duplicate whose removal would leave the same behaviour in place.

### 4.4 Stale documentation

Two forward-looking documents still tell future work to edit the legacy files, which are now frozen.

**`README.md`, section "Extending it"** (ACTIVE; **UPDATE_REFERENCE**)

- **What it says:** fill a sparse estate by editing its compact-list record; add scores in `data/overrides.js`; add a collection in `data/classifications.js` and a new data file; add earlier vintages in `data/vintages.js` and `data/rightbank.js`.
- **Why it is stale:**
  - Since Phase 4 (2026-10-25), every `data/*.js` file belongs to the protected `canonical` group (`migration_lib.GROUPS`).
  - `test-phase4` and `test-historical-m1` compare the group's digest with the baseline, so any of these edits fails frozen validation.
  - Phase 5 calls these files "the protected canonical data and the rollback source".
- **When it was last edited:** 2026-10-24, before Phase 4.
- **Proposed update:** add one dated note at the head of the section and leave the original recipes as they are, as the historical record. The note says:
  - the legacy files have been frozen since Phase 4;
  - already-approved values for an **existing** vintage go through the value-application manifest;
  - there is no supported path yet for the other extensions listed;
  - a value applied through the manifest is not yet shown by the app.

**`docs/ADDING-A-VINTAGE.md`** (LIKELY-LEGACY; **UPDATE_REFERENCE**)

- **What it says:** seven commands, among them `read-sheets.py --apply`, which writes new vintage records into `data/fiches.js`.
- **Why it is stale:** the same frozen group. Running it now breaks frozen validation.
- **When it was last edited:** 2026-10-21.
- **No replacement exists yet:**
  - M3.11 never creates a vintage (§5.2 of its brief), so adding a vintage has no supported path today;
  - an applied value for an existing vintage does not show in the app, which projects only legacy records.
- **Proposed update:** one dated note at the head saying exactly that, with the procedure kept below it as the historical record. Callers: `docs/IMPLEMENTATION-AUDIT.md` and `docs/INGESTION-ARCHITECTURE.md` (historical) name it; nothing executes it.

Proposed note text, for approval (README version; the ADDING-A-VINTAGE version differs only in its first clause):

> **Since Phase 4 (2026-10-25) the legacy files in `data/` are frozen.** They are the protected canonical data and
> the application's rollback source, and `test-phase4` and the historical suites fail if their bytes change, so
> the recipes below no longer apply as written. An already-approved value for an existing vintage goes through
> the value-application manifest (`data/audit/value-application-manifest.jsonl`; `python
> tools/apply-value-manifest.py --plan`, then `--apply`; see `docs/PHASE-M3.11-VALUE-APPLICATION-RUNNER.md`). There
> is no supported path yet for a new vintage, scores, collections or sparse-estate records, and a value applied
> through the manifest is not yet shown by the application.

**Not stale:**
- the phase reports, which are kept historically accurate as the brief requires;
- `docs/BACKLOG.md`, which gives no value-application instruction;
- `docs/TEST-SUITE-COST-AUDIT.md`, a dated measurement whose tiers are still used. It predates the M3.11 suite, and updating it is optional and outside the brief.

## 5. Items to investigate (not proposed for deletion)

**Twelve legacy tools** have no code caller. They belong to the pre-model legacy-file workflow: translation,
adding a wine, finding URLs, curation reports. Five write files that are now frozen (`fiches-nl.js`,
`cuvees.js`, `sources.json`, `sheet-expectations.json`); seven are read-only inspectors.

They fail deletion rule 7 ("genuinely superseded"). M3.11 does not replace them, and whether the legacy-file
workflow is retired for good is a product decision. Two of them, `add-wine.py` and `find-doc-urls.py`, are also
named as recipe steps in `data/site-recipes.json`, a protected record (rule 5).

| Path | Writes | References (none in code) |
|---|---|---|
| `tools/add-dutch.py` | `data/fiches-nl.js` | `data/audit/phase31-structure.json` |
| `tools/add-wine.py` | `data/cuvees.js` | phase31 report; **`data/site-recipes.json` (protected)**; `docs/PHASE-3.1-…`; `reports/estates/ducru-beaucaillou.md` |
| `tools/ask-site.py` | — | phase31 report |
| `tools/audit-consistency.py` | `data/sheet-expectations.json` | phase31 report; `docs/IMPLEMENTATION-AUDIT.md`; `docs/INGESTION-ARCHITECTURE.md` |
| `tools/audit-multiwine.py` | `data/sources.json` | phase31 report; `docs/INGESTION-ARCHITECTURE.md` |
| `tools/census-conflicts.py` | — | phase31 report; `docs/EVIDENCE-CENSUS.md` |
| `tools/find-doc-urls.py` | `data/sources.json` | phase31 report; **`data/site-recipes.json` (protected)**; `docs/PHASE-3.1-…`; 13 estate reports |
| `tools/find-vintages.py` | — | phase31 report; `reports/estates/LEDGER.md` |
| `tools/missing-fiches.py` | — | phase31 report; `reports/estates/croizet-bages.md` |
| `tools/reconcile.py` | — | phase31 report; `docs/EVIDENCE-CENSUS.md`; `docs/IMPLEMENTATION-AUDIT.md` |
| `tools/to-translate.py` | — | phase31 report |
| `tools/whose-site.py` | — | phase31 report |

None is depended on by frozen validation. Phase 3.1's findings read the tree **as audited at `e100b25`** through
`git show`, and its live boundary checks only filter the tools that remain, so deleting any of these would not
fail `test-phase31`. They are kept on rule 7, plus rule 5 for the two that `site-recipes.json` names.

**`docs/INGESTION-ARCHITECTURE.md`** (UNKNOWN; INVESTIGATE) is a forward design from 2026-10-24: an
`ingest.py` runner wrapping the `ADDING-A-VINTAGE` sequence. Its write path is now frozen, and its acquisition
parts were partly overtaken by the M3.3–M3.10 phases. Whether it is still the intended direction is a roadmap
question.

## 6. Retained for frozen validation

What depends on what, so that any later cleanup knows which files it must not touch:

- **Protected groups** (`migration_lib.GROUPS`, checked by `phase4-baseline.py`, `test-phase4` and
  `test-historical-m1`):
  - every top-level `data/*` file (legacy `.js`, `sources.json`, phase records such as `site-recipes.json`, `provenance-audit.jsonl` and `v3-v4-comparison.jsonl`);
  - `data/evidence/`, `data/discovery/`, `data/scope/` and `data/review/`;
  - the four Phase 3.4 contract documents.

  Removing or changing any of them fails a digest.
- **The six fingerprinted rule files** (`m35_rubric.py`, `web_evidence.py`, `sheetreader.py`,
  `read-fiches.py`, `m34a-mapping-audit.py`, `model_schema.py`) are hashed into the evidence and the reports.
- **The migration chain:** `migrate.py`; `mig_m2_identity` through `mig_m7_observations`; and every audit they
  read: M3.2's candidates, M3.4B, M3.5, M3.6B, M3.6D, M3.6F, M3.10A, M3.10B, M3.10C, and the runner manifest.
- **`historical_m2_scope.py`** names actors and manifests of M3.2, M3.4B, M3.5, M3.6B/D/E/F/H and M3.10A/B/C.
  The tools behind those names are the provenance actors of committed model rows.
- **Generated reports** re-checked by `--check` in their phase's suite, and the generators that produce them.
- **The Phase 3.1 frozen report** (`data/audit/phase31-structure.json`), its generator and its suite.
- **The M3.11 golden test,** which reads `data/audit/m3.10c-value-application.jsonl` and the model at `128263f`
  and `88f8c8d`.

## 7. Proposed scope

| | |
|---|---|
| Deletions | **none** |
| Documentation updates | 2: one dated note each at the head of README "Extending it" and of `docs/ADDING-A-VINTAGE.md`; about 7 lines each; original text kept |
| Code changes | none |
| Model, evidence, app, migration | unchanged |
| Tests after the update | none of the protected groups include `README.md` or `docs/ADDING-A-VINTAGE.md`. I would first grep for any byte check on either file, then run `test-phase31` and `test-phase4` (they read the tree's structure and protected groups), each twice. |
| Deferred | the 12 legacy tools and the ingestion design, pending a decision on retiring the legacy-file workflow |

## Appendix A: every inspected file

Code refs are tracked `.py` files that name the file (by name, import or module load). Other refs are documents
and data. Counts come from the reference graph built over the tree at `a343337`.

| Path | Class | Action | Code refs | Other refs | Basis |
|---|---|---|---:|---:|---|
| `.gitattributes` | ACTIVE | KEEP | 0 | 0 | site or repository configuration |
| `.gitignore` | ACTIVE | KEEP | 0 | 0 | site or repository configuration |
| `.nojekyll` | ACTIVE | KEEP | 0 | 0 | site or repository configuration |
| `PROGRESS.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | generated by tools/progress.py from the frozen legacy files |
| `README.md` | ACTIVE | UPDATE_REFERENCE | 0 | 0 | "Extending it" instructs editing the frozen legacy files |
| `data/audit/data-gap-register.jsonl` | ACTIVE | KEEP | 13 | 2 | a live input or output (runner manifest; gap register and its resolutions) |
| `data/audit/historical-m3-candidates.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 4 | 1 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.10a-external-artifact-registration.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 7 | 3 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.10b-evidence-decisions.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 6 | 4 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.10c-value-application.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 4 | 5 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.3-source-acquisition-plan.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 8 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.4a-mapping-proposals.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 9 | 4 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.4b-mapping-application.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 8 | 3 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.5-held-document-review.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 7 | 4 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6a-blocked-run-summary.json` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6a-rerun-evidence-corrections.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 5 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6a-rerun-held-document-proposals.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 5 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6b-correction-application.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 7 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6b-historical-flags.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 6 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6b-mapping-application.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 5 | 4 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6c-cuvee-mongravey-identity.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 7 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6d-cuvee-mongravey.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 8 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6e-cuvee-historical-corrections.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 5 | 1 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6f-cuvee-vintages.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 11 | 3 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6g-cuvee-acquisition.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 6 | 1 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.6h-cuvee-2015-correction.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 1 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.7-source-confirmation.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 8 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.8-acquisition-pilot.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 7 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m3.9-evidence-review.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 8 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m32-recovery-candidates.jsonl` | HISTORICAL-BUT-RETAIN | KEEP | 6 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/m32-resolutions.json` | ACTIVE | KEEP | 3 | 1 | a live input or output (runner manifest; gap register and its resolutions) |
| `data/audit/phase31-structure.json` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 2 | a phase audit: a migration input or a frozen, re-checked record |
| `data/audit/value-application-manifest.jsonl` | ACTIVE | KEEP | 2 | 2 | a live input or output (runner manifest; gap register and its resolutions) |
| `docs/ADDING-A-VINTAGE.md` | LIKELY-LEGACY | UPDATE_REFERENCE | 0 | 2 | instructs writing the frozen legacy files |
| `docs/BACKLOG.md` | ACTIVE | KEEP | 0 | 3 | the backlog, a generated register, or a contract model_schema reads |
| `docs/DATA-GAP-REGISTER.md` | ACTIVE | KEEP | 3 | 0 | the backlog, a generated register, or a contract model_schema reads |
| `docs/EVIDENCE-CENSUS.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/HISTORICAL-EVENT-MODEL-DESIGN.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 2 | a phase report, audit or design record (historically accurate) |
| `docs/IMPLEMENTATION-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/INGESTION-ARCHITECTURE.md` | UNKNOWN | INVESTIGATE | 0 | 1 | a forward design built on the legacy update path |
| `docs/NEXT-PHASE-LONGITUDINAL-VINTAGE-DESIGN.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2-EVIDENCE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.1-VINTAGE-DECISIONS.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.10-V5-EVIDENCE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.11-TERRASSES-ATTRIBUTION-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.12-EVIDENCE-RECONCILIATION.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.2-ECHO-CORRECTION.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.3-READER-V3.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.4-EVIDENCE-STORE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.5-PROVENANCE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.6-SECOND-WINE-IDENTITY.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.7-V4-EVIDENCE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.8-GRAND-VIN-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-2.9-GRAND-VIN-FIX.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-3.0-SCOPE-AND-AUTHORITATIVE-UNIVERSE.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-3.1-STRUCTURAL-AND-DOMAIN-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-3.2-DATA-MODEL.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 2 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-3.2-NORMALIZATION-ARCHITECTURE.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 2 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-3.3-DISCOVERY-FINDINGS.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-3.4-DOMAIN-MODEL-REVIEW.md` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 2 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-3.4-DOMAIN-MODEL.md` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 5 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-4-MIGRATION-BASELINE.md` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-4-MIGRATION-REPORT.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-5-APPLICATION-SOURCE-SWITCH.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-5-BASELINE-BENCHMARK.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-5-OPTIMIZATION-CANDIDATES.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.0-PRODUCT-DOMAIN-GAP-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.1-PER-FIGURE-SOURCE-PROVENANCE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.2-SECOND-WINE-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 2 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.3-SECOND-WINE-STATUS-DISPLAY.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.4-PROVENANCE-EVIDENCE-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.5-PROVENANCE-DISPLAY.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.6-PERFORMANCE-OPTIMIZATION.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.6-PERFORMANCE-PROFILE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.6-TEST-HYGIENE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.7-LONGITUDINAL-VINTAGE-SLICE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.8-HEADING-SEMANTICS-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-6.9-HEADING-AND-COVERAGE.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M0-HISTORICAL-SCHEMA.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 2 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M1-HISTORICAL-STRUCTURAL-EXTENSION.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M2-DOCUMENT-DATES.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3-EXPLICIT-HISTORICAL-CLAIMS.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.10A-ARTIFACT-REGISTRATION.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.10B-EVIDENCE-DECISIONS.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.10C-VALUE-APPLICATION.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.11-VALUE-APPLICATION-RUNNER.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.2-EXISTING-DATA-RECOVERY.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.3-HIGHEST-YIELD-SOURCES.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.4A-MAPPING-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 4 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.4B-MAPPING-APPLICATION.md` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.5-HELD-DOCUMENT-REVIEW.md` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.6A-RERUN.md` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.6B-APPLICATION.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.6C-CUVEE-MONGRAVEY-IDENTITY.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.7-SOURCE-CONFIRMATION.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.8-ACQUISITION-PILOT.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/PHASE-M3.9-EVIDENCE-REVIEW.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase report, audit or design record (historically accurate) |
| `docs/TEST-SUITE-COST-AUDIT.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | a phase report, audit or design record (historically accurate) |
| `docs/phase32-fixtures.json` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 3 | a phase report, audit or design record (historically accurate) |
| `docs/phase32-model.json` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 5 | a phase report, audit or design record (historically accurate) |
| `docs/phase34-fixtures.json` | HISTORICAL-BUT-RETAIN | KEEP | 4 | 6 | a phase report, audit or design record (historically accurate) |
| `docs/phase34-model.json` | ACTIVE | KEEP | 12 | 13 | the backlog, a generated register, or a contract model_schema reads |
| `docs/schema/check_historical_m1_proposal.py` | ONE-OFF/EXPERIMENT | KEEP | 0 | 4 | the M0 proposal checker the M0-M2 reports cite |
| `docs/schema/historical-m1-contract.json` | ACTIVE | KEEP | 2 | 1 | the backlog, a generated register, or a contract model_schema reads |
| `docs/schema/historical-m1-proposal.json` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 2 | a phase report, audit or design record (historically accurate) |
| `index.html` | ACTIVE | KEEP | 0 | 0 | site or repository configuration |
| `manifest.webmanifest` | ACTIVE | KEEP | 0 | 0 | site or repository configuration |
| `progress-history.tsv` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 0 | generated by tools/progress.py from the frozen legacy files |
| `reports/estates/LEDGER.md` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/batailley.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/belgrave.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/beychevelle.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/boyd-cantenac.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/branaire-ducru.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/brane-cantenac.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/calon-segur.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/cantemerle.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/cantenac-brown.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/clerc-milon.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/cos-destournel.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/cos-labory.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/croizet-bages.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/darmailhac.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/dauzac.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/de-camensac.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/desmirail.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/du-tertre.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/ducru-beaucaillou.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/duhart-milon.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/durfort-vivens.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/ferriere.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/giscours.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/grand-puy-ducasse.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/grand-puy-lacoste.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/gruaud-larose.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/haut-bages-liberal.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/haut-batailley.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/haut-brion.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/issan.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/kirwan.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/la-lagune.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/la-tour-carnet.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/lafite.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/lafon-rochet.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/lagrange.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/langoa-barton.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/lascombes.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/latour.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/leoville-barton.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/leoville-las-cases.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/leoville-poyferre.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/lynch-bages.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/lynch-moussas.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/malescot.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/margaux.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/marquis-dalesme.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/marquis-de-terme.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/montrose.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/mouton.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/palmer.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/pedesclaux.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/pichon-baron.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/pichon-comtesse.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/pontet-canet.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/pouget.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/prieure-lichine.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/rauzan-gassies.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/rauzan-segla.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/saint-pierre.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `reports/estates/talbot.md` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 1 | the hand-written estate pass (.gitignore keeps it tracked on purpose) |
| `service-worker.js` | ACTIVE | KEEP | 0 | 0 | site or repository configuration |
| `tools/add-dutch.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 1 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/add-sheet.py` | ACTIVE | KEEP | 3 | 2 | model, migration, app, evidence or test infrastructure in current use |
| `tools/add-wine.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 4 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/app-boundary.py` | ACTIVE | KEEP | 3 | 2 | model, migration, app, evidence or test infrastructure in current use |
| `tools/app-reference.py` | ACTIVE | KEEP | 3 | 12 | model, migration, app, evidence or test infrastructure in current use |
| `tools/app-source.py` | ACTIVE | KEEP | 2 | 3 | model, migration, app, evidence or test infrastructure in current use |
| `tools/apply-value-manifest.py` | ACTIVE | KEEP | 2 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/ask-site.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 1 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/attribute.py` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/audit-consistency.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 3 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/audit-estate.py` | LIKELY-LEGACY | KEEP | 2 | 7 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/audit-grand-marks.py` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/audit-multiwine.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 2 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/audit-provenance.py` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/audit-sources.py` | LIKELY-LEGACY | KEEP | 5 | 3 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/audit-structure.py` | ACTIVE | KEEP | 1 | 3 | model, migration, app, evidence or test infrastructure in current use |
| `tools/audit-websites.py` | LIKELY-LEGACY | KEEP | 2 | 1 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/benchmark-phase5.py` | ACTIVE | KEEP | 7 | 11 | model, migration, app, evidence or test infrastructure in current use |
| `tools/build-app-data.py` | ACTIVE | KEEP | 20 | 42 | model, migration, app, evidence or test infrastructure in current use |
| `tools/build-data-gap-register.py` | ACTIVE | KEEP | 8 | 4 | model, migration, app, evidence or test infrastructure in current use |
| `tools/build-fiche-links.py` | LIKELY-LEGACY | KEEP | 3 | 5 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/build-indexes.py` | ACTIVE | KEEP | 11 | 4 | model, migration, app, evidence or test infrastructure in current use |
| `tools/build-phase34-model.py` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 5 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/build-universe.py` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 6 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/build-workbook.py` | LIKELY-LEGACY | KEEP | 1 | 3 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/canonical-view.js` | ACTIVE | KEEP | 4 | 4 | read by the Phase 4/5 app and reader checks |
| `tools/census-compact.py` | ONE-OFF/EXPERIMENT | KEEP | 2 | 2 | a measurement a phase report cites as how its decision was made |
| `tools/census-conflicts.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 2 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/census.py` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 2 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/check-data.py` | LIKELY-LEGACY | KEEP | 8 | 7 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/check-language.py` | ACTIVE | KEEP | 3 | 2 | model, migration, app, evidence or test infrastructure in current use |
| `tools/check_cache.py` | ACTIVE | KEEP | 22 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/compare-universe.py` | HISTORICAL-BUT-RETAIN | KEEP | 5 | 4 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/compare-v3.py` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/compare-v4.py` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 4 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/compare-v5.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 2 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/conflicts-v4.py` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/conflicts.py` | ACTIVE | KEEP | 7 | 10 | model, migration, app, evidence or test infrastructure in current use |
| `tools/crawl-pages.py` | ACTIVE | KEEP | 5 | 3 | model, migration, app, evidence or test infrastructure in current use |
| `tools/data_gap_analysis.py` | ACTIVE | KEEP | 20 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/datapoints.py` | LIKELY-LEGACY | KEEP | 2 | 2 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/diagnose-second-mode.py` | ONE-OFF/EXPERIMENT | KEEP | 4 | 6 | a measurement a phase report cites as how its decision was made |
| `tools/discover.py` | ACTIVE | KEEP | 8 | 7 | model, migration, app, evidence or test infrastructure in current use |
| `tools/discover_extract.py` | ACTIVE | KEEP | 6 | 3 | model, migration, app, evidence or test infrastructure in current use |
| `tools/discover_report.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 2 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/document_dates.py` | ACTIVE | KEEP | 2 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/dryrun-grand-identity.py` | ONE-OFF/EXPERIMENT | KEEP | 1 | 3 | a measurement a phase report cites as how its decision was made |
| `tools/dryrun-second-identity.py` | ONE-OFF/EXPERIMENT | KEEP | 1 | 2 | a measurement a phase report cites as how its decision was made |
| `tools/dual-read.py` | ACTIVE | KEEP | 3 | 3 | model, migration, app, evidence or test infrastructure in current use |
| `tools/echo-baseline.py` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 2 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/estate-report.py` | LIKELY-LEGACY | KEEP | 2 | 62 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/evidence-wines.py` | ACTIVE | KEEP | 7 | 7 | model, migration, app, evidence or test infrastructure in current use |
| `tools/evidence.py` | ACTIVE | KEEP | 72 | 33 | model, migration, app, evidence or test infrastructure in current use |
| `tools/evidence_store.py` | ACTIVE | KEEP | 46 | 6 | model, migration, app, evidence or test infrastructure in current use |
| `tools/extract-document-dates.py` | HISTORICAL-BUT-RETAIN | KEEP | 6 | 6 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/extract-historical-m3.py` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/find-doc-urls.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 16 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/find-vintages.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 2 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/fixtures/app-reference.json` | ACTIVE | KEEP | 1 | 4 | read by the Phase 4/5 app and reader checks |
| `tools/harvest.py` | ACTIVE | KEEP | 25 | 36 | model, migration, app, evidence or test infrastructure in current use |
| `tools/historical_evaluator.py` | ACTIVE | KEEP | 1 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/historical_m2_scope.py` | ACTIVE | KEEP | 43 | 5 | model, migration, app, evidence or test infrastructure in current use |
| `tools/historical_m3.py` | ACTIVE | KEEP | 2 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/legacy-dump.js` | ACTIVE | KEEP | 2 | 0 | read by the Phase 4/5 app and reader checks |
| `tools/link-duplicates.py` | ACTIVE | KEEP | 0 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/m310a-register.py` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 2 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m310b-accept.py` | HISTORICAL-BUT-RETAIN | KEEP | 4 | 2 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m310c-values.py` | HISTORICAL-BUT-RETAIN | KEEP | 6 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m32-ocr.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m32-recovery.py` | HISTORICAL-BUT-RETAIN | KEEP | 5 | 4 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m32_recovery.py` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 1 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m33-source-plan.py` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m33_report.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m34a-mapping-audit.py` | ACTIVE | KEEP | 14 | 5 | model, migration, app, evidence or test infrastructure in current use |
| `tools/m34a_report.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m34b-apply.py` | HISTORICAL-BUT-RETAIN | KEEP | 5 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m34b_report.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m35-review.py` | HISTORICAL-BUT-RETAIN | KEEP | 7 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m35_report.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m35_rubric.py` | ACTIVE | KEEP | 25 | 4 | model, migration, app, evidence or test infrastructure in current use |
| `tools/m36a-rerun.py` | HISTORICAL-BUT-RETAIN | KEEP | 7 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m36a_rerun_report.py` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 0 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m36b-apply.py` | HISTORICAL-BUT-RETAIN | KEEP | 6 | 4 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m36b_report.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 0 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m36d-cuvee.py` | HISTORICAL-BUT-RETAIN | KEEP | 7 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m36e-apply.py` | HISTORICAL-BUT-RETAIN | KEEP | 4 | 1 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m36f-vintages.py` | HISTORICAL-BUT-RETAIN | KEEP | 7 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m36g-acquisition.py` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 1 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m36h-apply.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m37-source-confirmation.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 1 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m38-acquire.py` | ACTIVE | KEEP | 3 | 4 | model, migration, app, evidence or test infrastructure in current use |
| `tools/m38-acquisition-pilot.py` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 2 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/m39-evidence-review.py` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 1 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/merge-proposals.py` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 4 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/mig_m2_identity.py` | ACTIVE | KEEP | 9 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/mig_m3_grand.py` | ACTIVE | KEEP | 2 | 0 | model, migration, app, evidence or test infrastructure in current use |
| `tools/mig_m4_wines.py` | ACTIVE | KEEP | 2 | 0 | model, migration, app, evidence or test infrastructure in current use |
| `tools/mig_m5_vintages.py` | ACTIVE | KEEP | 3 | 0 | model, migration, app, evidence or test infrastructure in current use |
| `tools/mig_m6_provenance.py` | ACTIVE | KEEP | 21 | 2 | model, migration, app, evidence or test infrastructure in current use |
| `tools/mig_m7_observations.py` | ACTIVE | KEEP | 3 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/migrate-evidence-store.py` | ONE-OFF/EXPERIMENT | KEEP | 2 | 4 | a measurement a phase report cites as how its decision was made |
| `tools/migrate.py` | ACTIVE | KEEP | 27 | 20 | model, migration, app, evidence or test infrastructure in current use |
| `tools/migration_lib.py` | ACTIVE | KEEP | 87 | 1 | model, migration, app, evidence or test infrastructure in current use |
| `tools/missing-fiches.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 2 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/model_reader.py` | ACTIVE | KEEP | 10 | 7 | model, migration, app, evidence or test infrastructure in current use |
| `tools/model_schema.py` | ACTIVE | KEEP | 30 | 6 | model, migration, app, evidence or test infrastructure in current use |
| `tools/phase4-baseline.py` | ACTIVE | KEEP | 2 | 8 | model, migration, app, evidence or test infrastructure in current use |
| `tools/progress.py` | LIKELY-LEGACY | KEEP | 4 | 5 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/promote-urls.py` | HISTORICAL-BUT-RETAIN | KEEP | 3 | 4 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/proposal-compat.py` | ACTIVE | KEEP | 1 | 2 | model, migration, app, evidence or test infrastructure in current use |
| `tools/propose.py` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 3 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/provenance.py` | ACTIVE | KEEP | 64 | 40 | model, migration, app, evidence or test infrastructure in current use |
| `tools/quality-audit.py` | ACTIVE | KEEP | 1 | 2 | model, migration, app, evidence or test infrastructure in current use |
| `tools/raw_store.py` | ACTIVE | KEEP | 4 | 2 | model, migration, app, evidence or test infrastructure in current use |
| `tools/read-fiches.py` | ACTIVE | KEEP | 24 | 21 | model, migration, app, evidence or test infrastructure in current use |
| `tools/read-plantings.py` | ACTIVE | KEEP | 5 | 5 | model, migration, app, evidence or test infrastructure in current use |
| `tools/read-sheets.py` | LIKELY-LEGACY | KEEP | 11 | 7 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/read-terroir.py` | ACTIVE | KEEP | 3 | 6 | model, migration, app, evidence or test infrastructure in current use |
| `tools/recharacterize.py` | ONE-OFF/EXPERIMENT | KEEP | 2 | 7 | a measurement a phase report cites as how its decision was made |
| `tools/recheck-sources.py` | HISTORICAL-BUT-RETAIN | KEEP | 2 | 1 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/reconcile.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 3 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/reconstruct.py` | ACTIVE | KEEP | 2 | 2 | model, migration, app, evidence or test infrastructure in current use |
| `tools/recover-urls.py` | LIKELY-LEGACY | KEEP | 1 | 11 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/refile-wine.py` | LIKELY-LEGACY | KEEP | 1 | 4 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/refile.py` | LIKELY-LEGACY | KEEP | 2 | 2 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/review-corpus.py` | HISTORICAL-BUT-RETAIN | KEEP | 1 | 2 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
| `tools/run-tests.py` | ACTIVE | KEEP | 3 | 6 | model, migration, app, evidence or test infrastructure in current use |
| `tools/sheetreader.py` | ACTIVE | KEEP | 73 | 15 | model, migration, app, evidence or test infrastructure in current use |
| `tools/test-check-cache.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-data-gap-register.py` | ACTIVE | KEEP | 1 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-data.py` | ACTIVE | KEEP | 1 | 11 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-historical-m1.py` | ACTIVE | KEEP | 0 | 3 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-historical-m2.py` | ACTIVE | KEEP | 0 | 2 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-historical-m3.py` | ACTIVE | KEEP | 0 | 2 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m310a.py` | ACTIVE | KEEP | 0 | 0 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m310b.py` | ACTIVE | KEEP | 0 | 0 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m310c.py` | ACTIVE | KEEP | 0 | 0 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m32.py` | ACTIVE | KEEP | 1 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m33.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m34a.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m34b.py` | ACTIVE | KEEP | 1 | 2 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m35.py` | ACTIVE | KEEP | 1 | 2 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m36a-r1.py` | ACTIVE | KEEP | 2 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m36a-rerun.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m36b.py` | ACTIVE | KEEP | 1 | 2 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m36c.py` | ACTIVE | KEEP | 0 | 3 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m36d.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m36e.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m36f.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m36g.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m36h.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m37.py` | ACTIVE | KEEP | 1 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m38.py` | ACTIVE | KEEP | 1 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-m39.py` | ACTIVE | KEEP | 1 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase2.py` | ACTIVE | KEEP | 0 | 8 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase21.py` | ACTIVE | KEEP | 1 | 7 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase210.py` | ACTIVE | KEEP | 0 | 4 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase211.py` | ACTIVE | KEEP | 0 | 4 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase212.py` | ACTIVE | KEEP | 1 | 4 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase22.py` | ACTIVE | KEEP | 0 | 8 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase23.py` | ACTIVE | KEEP | 0 | 7 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase24.py` | ACTIVE | KEEP | 0 | 6 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase25.py` | ACTIVE | KEEP | 0 | 7 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase26.py` | ACTIVE | KEEP | 0 | 4 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase27.py` | ACTIVE | KEEP | 0 | 4 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase28.py` | ACTIVE | KEEP | 0 | 4 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase29.py` | ACTIVE | KEEP | 0 | 6 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase30.py` | ACTIVE | KEEP | 1 | 6 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase31.py` | ACTIVE | KEEP | 2 | 5 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase32.py` | ACTIVE | KEEP | 1 | 4 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase33.py` | ACTIVE | KEEP | 1 | 3 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase34.py` | ACTIVE | KEEP | 0 | 3 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase4.py` | ACTIVE | KEEP | 2 | 5 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase5.py` | ACTIVE | KEEP | 2 | 6 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase61.py` | ACTIVE | KEEP | 1 | 4 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase63.py` | ACTIVE | KEEP | 1 | 3 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase65.py` | ACTIVE | KEEP | 1 | 5 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase67.py` | ACTIVE | KEEP | 1 | 2 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-phase69.py` | ACTIVE | KEEP | 2 | 2 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-reader.py` | ACTIVE | KEEP | 5 | 13 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-run-tests.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/test-value-application-manifest.py` | ACTIVE | KEEP | 0 | 1 | a suite: tools/run-tests.py discovers tools/test-*.py by glob |
| `tools/to-translate.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 1 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/trace-second-wine-cases.py` | ONE-OFF/EXPERIMENT | KEEP | 1 | 3 | a measurement a phase report cites as how its decision was made |
| `tools/unread.py` | LIKELY-LEGACY | KEEP | 2 | 37 | the pre-model legacy-file workflow, frozen since Phase 4 |
| `tools/web_evidence.py` | ACTIVE | KEEP | 15 | 3 | model, migration, app, evidence or test infrastructure in current use |
| `tools/whose-site.py` | LIKELY-LEGACY | INVESTIGATE | 0 | 1 | the pre-model legacy-file workflow, frozen since Phase 4; no code caller |
| `tools/wine-identity.py` | HISTORICAL-BUT-RETAIN | KEEP | 0 | 4 | a phase tool: its committed output is a migration input or is re-checked by a frozen suite, or it is the recipe of a protected record |
