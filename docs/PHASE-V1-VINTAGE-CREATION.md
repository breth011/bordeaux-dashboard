# Phase V1: new-vintage creation

V1 implements the approved design (`docs/NEW-VINTAGE-CREATION-DESIGN.md`, `e8d4069`). It can create a **grand vin's
vintage** for an existing wine: an empty vintage shell, plus an **existence attribution** that ties accepted,
reviewed evidence to exactly that estate, wine and vintage. Reviewed values then go through the value-application
manifest (M3.11), unchanged.

**No production vintage was created.** The production manifest `data/audit/vintage-creation-manifest.jsonl` is
committed **empty**. With it, the model, its indexes, the app data, the evidence store and the gap register are
byte for byte as before.

## Scope and the approved decisions

| Decision | As implemented |
|---|---|
| **U1** proof location | Existence attributions only, in M3.10B's shape. `VintageStatement PRODUCED` is not used. |
| **U2** gap register | Created vintages and their links are set aside. The gap register neither gains nor resolves anything because of them. |
| **U3** prerequisites | Not implemented. The artifact must already be registered, its reviewed reader row already committed, and its evidence decision already ACCEPTED in the store. |
| **U4** scope | Grand vins only. Second wines, cuvées, other wines and ambiguous identities are rejected. |
| **U5** years | `1950 ≤ vintage ≤ next calendar year`; integers only; NV and non-integers rejected (see the year rule below). |
| **U6** existing vintage | CREATE / ATTRIBUTION_ONLY / NOOP / CONFLICT; the batch is atomic. |
| **U7** historical scope | One mechanism-level exception in `historical_m2_scope`, keyed on the mechanism's actor and its own record of what it created. It is not per vintage. |

**The year rule.** The model-building code reads no clock: every date in it is a fixed constant. So "next
calendar year" is the only place V1 reads the date (`last_year()`). A row valid when it is applied stays valid on
every later rebuild, and the year never enters a model row, so rebuilds stay deterministic.

## Files

| File | Role |
|---|---|
| `tools/apply-vintage-creation-manifest.py` | the runner: `--validate` (the default), `--plan`, `--apply`, `--check`, `--check-all`, `--manifest`, `--timings` |
| `data/audit/vintage-creation-manifest.jsonl` | the production manifest, **empty** |
| `tools/mig_m5_vintages.py` | M5 hook `vintage_creation`: the shells |
| `tools/mig_m6_provenance.py` | M6 hook `vintage_creation_attributions`: the existence attributions |
| `tools/historical_m2_scope.py` | the V1 exception (U7) |
| `tools/data_gap_analysis.py` | the U2 set-aside |
| `tools/test-vintage-creation-manifest.py` | the focused suite |
| `tools/test-m36a-r1.py` | its list of later phases' audit files names M3.10C's, M3.11's and V1's manifests. The first two were missing, so this suite had failed since `88f8c8d`; the earlier Tier-2 runs had seen those files untracked. |

The runner reuses the value runner's evidence loading, clock and atomic file write unchanged, and changes nothing in
M3.11.

## Manifest contract

One JSON line per requested vintage:

```json
{"manifest_id": "vcm_000001", "estate_id": "es_…", "wine_id": "wn_…", "vintage": 2025,
 "artifact_ids": ["ar_…"], "evidence_version": 10,
 "evidence_decisions": {"ar_…": "<the store's row key>"},
 "review": {"ar_…": {"audit": "data/audit/m3.9-evidence-review.jsonl", "row": "m3.9:<n>"}},
 "creation_class": "EXPLICIT_DOCUMENT_TEXT"}
```

- **Required:** every field above. `notes` is optional. Any other key is refused.
- **References only.** Each artifact names its evidence decision (the store's row key) and its reviewed reader
  row. The runner reads the basis, identity source and vintage source from that row; nothing is copied into the
  manifest. This settles a detail of the design's example, which showed the basis inline while its text said the
  manifest duplicates neither the evidence nor the review.
- **No canonical value, no figure.**
- **Allowed review audits** (`REVIEW_AUDITS`): M3.9's format, `data/audit/m3.9-evidence-review.jsonl`, which is the
  existing path for an acquired document. A later review audit is added there by name.

## Validation

Every check is read-only and runs before anything is written.

- **Structure:**
  - `vcm_NNNNNN` ids, unique;
  - `artifact_ids`, `evidence_decisions` and `review` name the same distinct artifacts;
  - no vintage requested twice;
  - no artifact claimed for two vintages.
- **Identity:**
  - the estate exists and the wine exists;
  - `(estate, wine)` is ESTABLISHED;
  - the wine is the estate's **ACTIVE `grand-vin`** identity entry, so a second wine, a cuvée or any other wine is
    rejected;
  - the wine is not a candidate of any AMBIGUOUS identity-map row;
  - the estate has no OPEN `IDENTITY_UNCERTAIN`, `AMBIGUOUS_SEMANTICS` or `CONFLICT` finding;
  - the wine has `name_status KNOWN`, exactly one CURRENT name, and no identity transition.
- **Year:** an integer, 1950 to the next calendar year.
- **Artifact:**
  - it exists, with its bytes held (`bytes_available`, `sha256`).
- **Reviewed reader row:** it is in an allowed review audit and has:
  - the same sha256;
  - disposition **SAFE_TO_MAP** and category ACCEPTED_EXACT_ESTATE_WINE_VINTAGE;
  - exactly this estate, wine and year;
  - **exactly one** SAFE_TO_MAP claim, for this wine (a second one means a multi-wine document);
  - `claim_year_dated` false, so the year is not a press or event date;
  - identity from the document's own text: M34A or T1–T7 for documents, the main heading (`h1`) for web pages.
    Filename, URL, folder, domain and metadata identity is refused;
  - a vintage basis the document states (`statement …` or `wine and year …`);
  - the reader's ACCEPTED.
- **Evidence decision:**
  - in the store, at the row's `evidence_version`;
  - ACCEPTED;
  - **still the latest** for its context (not superseded);
  - read the artifact's **own bytes**;
  - `estate`, `target_wine`, `target_role` and `target_vintage` equal the estate's slug, the wine's current name,
    `grand` and the year.

## Actions

| State | Action | Adds |
|---|---|---|
| No vintage `(wine, year)` | **CREATE** | the shell `{wine, label}`, and one existence attribution with its DOCUMENT provenance per artifact |
| Vintage present; some artifact has no **exact** existence attribution | **ATTRIBUTION_ONLY** | those attributions only; the vintage and its values are untouched |
| Vintage present; every exact attribution held | **NOOP** | nothing |
| NOT_PRODUCED stated for the vintage, or an artifact ACCEPTED-attributed to another vintage or wine | **CONFLICT** | nothing; the batch stops |
| Any validation failure | **REJECT** | nothing; the batch stops |

**An exact existence attribution** is an ACCEPTED, `DOCUMENT_TEXT` attribution of the artifact to this estate,
wine and vintage whose provenance names the row's evidence decision. M3.10B's attributions qualify: a manifest of
Durfort-Vivens' three accepted vintages is NOOP in production.

**The attribution created** is `{id: hid(Attribution, artifact, 'vcm', vintage), artifact, estate, wine, vintage,
role FIRST, method DOCUMENT_TEXT, status ACCEPTED}`. Its DOCUMENT provenance has:
- **quote:** the review row's basis;
- **`code_state`:** stream `vintage-creation`, runner `apply-vintage-creation-manifest/1`, the manifest, the
  `manifest_id`, the review audit and row, `evidence_decisions [key]`, `evidence_version`, `identity_source`,
  `vintage_source` and `sha256`.

## Migration hooks

- **`mig_m5_vintages.vintage_creation`** runs last in M5, after `m36f_vintages`. It plans against the model being
  built and adds the shells of the rows whose vintage it lacks. It records the vintage refs it created as the M5
  stat `vintage-creation manifest vintages`. A vintage row carries no provenance, so this stat is the model's own
  record of which vintages the mechanism made.
- **`mig_m6_provenance.vintage_creation_attributions`** runs last in M6, after `m310b_attributions`. It plans again,
  now with every attribution present, adds the missing existence attributions, and records the M6 stat
  `vintage-creation manifest attributions`.
- **Shared runner:** both hooks load one runner instance per process, and `--apply` computes the same rows directly
  without a rebuild.
- **Empty or all-NOOP manifest:** adds no row and records no stat.
- **Validated on every build:** an invalid row or CONFLICT stops the migration.

## The historical-scope exception (U7)

`historical_m2_scope` registers the mechanism once:
- `V1_ACTOR` and `V1_STREAM`;
- `v1_created()`, which reads the model manifest's M5 stat;
- `is_v1_row` (its vintages by that record, its attributions and their provenance by actor and stream);
- `v1_links`;
- `without_v1_vintages`.

The guards set these rows aside exactly as they do M3.6F's and M3.10B's:
- **`model_changes_are_m2_only`:** provenance, attributions, `vintage-documents` links, vintages, `wine-vintages`
  and the stats;
- **`_without_m310a_manifest`:** counts and stats;
- **`unchanged_but_m310a`** and **`unchanged_but_m36d`:** rows and the two indexes;
- **`without_m36d`:** counts;
- **`legacy_attributions`.**

No existing assertion was weakened. Each guard still requires every other row to be exactly as before, and only rows
the mechanism itself records are set aside.

**U2.** `data_gap_analysis` lists V1's actor among the later linking actors, so its attributions are set aside
like M3.10B's, and it is never listed among the register's resolutions. Its as-of view leaves out the created
vintages and every row and link on them, `vintage_documents` and `wine-vintages` included.

## Tests

`tools/test-vintage-creation-manifest.py` holds 17 checks covering the brief's 30 cases. **It passed twice, 17/17**
each run (about 71 s).

| Check | Cases |
|---|---|
| c01 | 1 valid creation plan |
| c02–c04 | 2 application on an isolated copy; 3 the exact existence attribution (field for field M3.10B's `at_118b7dcaeeb1`, but for its id and provenance metadata); 4 zero values, and identities, statements and estate-wine byte for byte |
| c05–c07 | 5 unknown estate; 6 unknown wine; 7 wrong estate |
| c08 | 8 ambiguous wine; open estate identity finding; unsettled current name |
| c09–c10 | 9 second wine; 10 cuvée |
| c11–c14 | 11 invalid vintages (`'2024'`, `2024.0`, `True`, `None`); 12 1949; 13 next year + 1; 14 NV |
| c15–c17 | 15 filename-only (no reviewed row, a non-review audit, filename identity); 16 URL-only (vintage basis from a URL); 17 publication-date-only (`claim_year_dated`) |
| c18–c19 | 18 multi-vintage (`VINTAGE_AMBIGUOUS`) and estate-only; 19 multi-wine (two SAFE_TO_MAP claims; `MULTI_WINE_AMBIGUOUS`); a review row for another wine |
| c20–c22 | 20 rejected decisions; 21 superseded by version 10; 22 wrong or unknown version, a missing key, other bytes, another role |
| c23 | 23 existing vintage and attribution → NOOP (Durfort-Vivens' three vintages, in production, with nothing written) |
| c24 | 24 existing vintage without its attribution → ATTRIBUTION_ONLY, applied: vintages and values untouched |
| c25 | 25 NOT_PRODUCED, and an artifact attributed elsewhere → CONFLICT, which verification refuses |
| c26 | 26 no partial write when row 2 is invalid |
| c27 | 27 deterministic plan: twice, and under shuffled rows |
| c28 | 28 deterministic rebuild; the U7 exception; the U2 gap register (synthetic, see below) |
| c29 | 29 M3.11 compatibility (below) |
| c30 | 30 production manifest empty; `--check-all`; model, app, evidence and discovery unchanged |

**c28, synthetic, in a subprocess and an isolated copy only.** A fabricated ACCEPTED decision and review row state
Château Durfort-Vivens **2025** for an artifact with no attribution.
- `--apply` creates it.
- Two migration rebuilds, fed the same manifest through the runner instance the hooks share, are byte-identical
  and equal the applied copy.
- `is_v1_row` picks out exactly the one vintage, attribution and provenance row.
- `legacy_attributions` excludes the attribution.
- The model manifest without M3.10A–C and V1 equals HEAD's.
- `model_changes_are_m2_only('345f892')` (as `test-m310c` calls it) passes over the copy.
- `build-data-gap-register.py --check-all` on the copy reports both register files current.

## M3.11 compatibility (c29)

The design experiment, as a regression test, in memory, with Durfort-Vivens 2024 removed:

1. The value runner refuses M3.10C's five 2024 rows: "vintage 2024 of wn_00263 does not exist".
2. V1 adds the shell. The value runner still refuses all five: "artifact ar_037071 has no accepted attribution
   to vt:wn_00263:2024".
3. V1 adds the existence attribution (ATTRIBUTION_ONLY). The value runner plans **5 APPLY, 0 NOOP, 0 CONFLICT**, and
   the 2024 oak shows as 70%.

The value runner is unchanged. Both the vintage and its existence attribution are required.

## Determinism

- **Plans:** byte-identical across runs and under row order.
- **Rebuilds:** two rebuilds are byte-identical and equal `--apply` (c28).
- **Ids:** `hid` of natural keys (`Attribution: artifact, 'vcm', vintage`; provenance by content).
- **No timestamps:** no date or randomness enters a created row (c02).
- **Empty production manifest:** `migrate.py --check`, `build-indexes.py --check`, `build-app-data.py --check` and
  `build-data-gap-register.py --check-all` all report current.

## Performance

Measured on this machine.

**The empty production manifest:**

| Command | Total | Of which |
|---|---:|---|
| `--validate` | 0.38 s | model loading 0.37 s, evidence loading 0.01 s |
| `--plan` | 0.38 s | as `--validate` |
| `--check` | 0.58 s | deterministic checking 0.20 s |

**A synthetic batch**, in memory, one eligible grand vin per row (437 are eligible), vintage 2027:

| Batch | Validation | Planning | Application (render the three tables and the manifest) |
|---:|---:|---:|---:|
| 1 | < 0.001 s | 0.001 s | 0.255 s |
| 10 | < 0.001 s | < 0.001 s | 0.250 s |
| 100 | 0.002 s | 0.002 s | 0.258 s |

**Fixed costs per run:** model loading 0.36 s, evidence loading (v9) 0.004 s, index rebuild 0.62 s, deterministic
check 0.20 s, and a rebuild check about 15 s (`--check-all`).

**A batch of 100 vintages costs the same as a batch of 1**, about 1.3 s for `--apply`. There is no per-vintage
script, audit, migration or rebuild.

## App

The app is unchanged. A created vintage does **not** appear in the current app: its projection
(`model_reader.project`) shows only legacy-file records. Showing created vintages and their M3.11 values is the
future app phase (A1).

## Prerequisites for V2 (the first real vintage)

1. **An acquired document** for one existing grand vin's new vintage, **registered as an artifact** through a
   committed registration input (today only M3.10A's phase-specific external-registration manifest; generic
   registration is the separate U3 phase).
2. **A committed reviewed reader row** for it in an allowed review audit (M3.9's format), classifying it SAFE_TO_MAP
   from its own text for exactly that wine and year.
3. **An ACCEPTED evidence decision** for it in the store, at a stated version (today only phase tools such as
   `m310b-accept.py` append one; generic acceptance is the separate U3 phase).
4. **One `vcm_` row** referencing 1–3, then `--plan` and `--apply`.
5. **M3.11 value rows** for the new vintage, if values are to be applied.

## Remaining limitations

- **Review audits:** only M3.9's review format is allowed. A new review audit must be registered by name.
- **Wines:** grand vins only (U4). Second wines and cuvées need their own decision.
- **The year bound** reads the calendar, as described above.
- **ATTRIBUTION_ONLY in older reports.** Reports that set later linking phases aside by an **explicit** actor
  tuple (for example `m36b-apply` and `m35-review`, through `vintage_documents((…))`) do not name V1's actor. A
  created vintage is left out of them regardless, through the U2 set-aside. An ATTRIBUTION_ONLY link on an
  **existing** vintage would still reach them, so V2 should check those reports when it uses ATTRIBUTION_ONLY, as
  M3.10B and M3.10C were checked.
- **M3.11's own rows** are not yet set aside by `historical_m2_scope` and `data_gap_analysis` (M3.11's documented
  limitation: its first production batch registers them once). That applies to values on created vintages too.
- **The app** does not show created vintages (A1).
