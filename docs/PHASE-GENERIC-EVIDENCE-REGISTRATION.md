# Phase: generic artifact registration and evidence acceptance

Infrastructure only. Two reusable mechanisms replace the phase-specific pair M3.10A (`tools/m310a-register.py`) and
M3.10B (`tools/m310b-accept.py`) for future work:

| Step | Mechanism | Input | Writes |
|---|---|---|---|
| acquire | an acquisition tool (M3.8's today) | — | held bytes under `sources/`, an acquisition audit |
| **register** | `tools/apply-artifact-registration-manifest.py` | `data/audit/artifact-registration-manifest.jsonl` | the model (through the migration): artifact, identity key, URL placement |
| read / audit | a review audit (M3.9's today) | — | reviewed reader rows |
| **accept** | `tools/apply-evidence-acceptance-manifest.py` | `data/audit/evidence-acceptance-manifest.jsonl` | the evidence store: one decision per row, appended |
| create | V1, `tools/apply-vintage-creation-manifest.py` | `data/audit/vintage-creation-manifest.jsonl` | vintage shell, existence attribution |
| apply values | M3.11, `tools/apply-value-manifest.py` | `data/audit/value-application-manifest.jsonl` | observations, reconciliations, values |

**No production data was added.** Both manifests are committed empty; the model, the evidence store (v1–v9), the
app data, the discovery data and every audit are byte for byte as before. M3.10A, M3.10B, M3.10C, M3.11 and V1 are
unchanged and were not rewritten to use the new mechanisms; the reader, its rules and its fingerprints are unchanged.

## 1. Audit of the existing machinery

| Part | What it is | Kind |
|---|---|---|
| `mig_m2_identity.external_registrations` + the mint loop | mints one artifact per sha256 for each `registration` row, after every other input's digests | **generic mechanism**, bound to M3.10A's file name |
| `mig_m6_provenance.external_placements` | one URL placement per registration in M3.2B's shape, DOCUMENT provenance naming the stream | **generic mechanism**, bound to M3.10A's file and actor |
| `m310a-register.py` `registrations()` | exactly M3.9's four SAFE_TO_MAP Durfort-Vivens documents, `ESTATE = 'es_00263'`, count 4 enforced, the M3.7 relationship of that estate | **M3.10-specific data** |
| M3.10A's registration row shape (sha256, bytes, media type, URL, final URL, status, fetch time, held path, acquired by, origin, retrieval method, source, relationship) | the facts a registration states | **generic shape**, reused here |
| M3.10A's `result` rows and report | read back from the model | M3.10-specific output |
| `m310b-accept.py` `allow_list()` | M3.10A's four artifacts; recomputes M3.9's review (`m39-evidence-review.build`) and requires the committed rows unchanged | M3.10-specific data; the freshness check is **generic in intent** |
| `m310b-accept.py` `rows()` | builds an ACCEPTED `guard` decision in M3.6B's representation: `folder` `acquisition:<sha256>`, `read` the held bytes, the reader's basis and veto, decider fingerprint, `git` state | **generic mechanism**, bound to version 9, Durfort-Vivens and M3.9 |
| decider version 9, `VERSION - 1` check | one phase opens one version | M3.10-specific |
| `mig_m6_provenance.m310b_attributions` | attributions from M3.10B's manifest | superseded for new work by V1's existence attributions |
| M3.9's review row format (`disposition`, `category`, `claims[].evidence_of_document`, `reader`, `claim_year_dated`, `identity_source`, `vintage_evidence`, `reason`) | the reader's verdict on a document's own text | **M3.9-specific review assumptions**, already the format V1 checks (`check_review`) |
| `m39-evidence-review.py` | reviews exactly M3.8's 17 candidates | M3.9-specific (not a generic reading step) |
| `test-m310a.py`, `test-m310b.py`, `historical_m2_scope` (`is_m310a_row`, `m310b_evidence_rows`, `LATER_EVIDENCE_VERSIONS`, `evidence_unchanged_but_m310b`), `data_gap_analysis.m310b_attributions` | assert M3.10A/B's exact rows, v9 as exactly four decisions, the store ending at v9 | **historical frozen validation** |

The evidence store (`tools/evidence_store.py`) is already generic: `append()` is the only writer; it refuses a row of
another version, a changed reader within a version, a v4+ row without read/git provenance, and drops a row whose key
is stored. The row key (`mig_m6_provenance.row_key`, `evidence.row_key`) ends in `v`; the latest version of a
question is its answer (`latest_by_context`). Nothing in the store needed to change.

## 2. Artifact registration

### Contract

A registration establishes one location of one document: the bytes' sha256, size and media type; the held file;
the URL, final URL, HTTP status and fetch time; who acquired it and how; that it was acquired **outside** the
discovery crawl (`origin: EXTERNAL_ACQUISITION`); and, only where the acquisition record attributes the fetch to one,
the confirmed source and relationship. Every one of these is checked against the acquisition record the row names;
none may come from anywhere else. A row names no estate, wine or vintage: registration decides no identity, and no
evidence decision, attribution or value follows from it.

### Manifest row (`data/audit/artifact-registration-manifest.jsonl`)

```json
{"registration_id": "arm_000001",
 "sha256": "<64 hex>", "bytes": 104123, "media_type": "application/pdf",
 "held_path": "sources/acquisition/m3.8/blobs/<sha256>",
 "url": "https://…", "final_url": "https://…", "http_status": 200, "fetched_at": "2026-10-27T13:06:19Z",
 "retrieval_method": "confirmed-source acquisition (tools/m38-acquire.py, the discovery fetch discover/1.0)",
 "acquired_by": "M3.8", "origin": "EXTERNAL_ACQUISITION",
 "acquisition": {"audit": "data/audit/m3.8-acquisition-pilot.jsonl", "row": "m3.8:104"},
 "source": "sr_00239", "source_relationship": "m37:sr_00239:es_00263",
 "notes": "optional"}
```

`acquisition` must name an `item` row of an audit in `ACQUISITION_AUDITS` (today M3.8's, which also fixes
`acquired_by`, `retrieval_method` and the held store). `source`/`source_relationship` are optional and go together;
the relationship must be the record's `attributed_to` and one of M3.7's confirmed relationships, and the source must
be in the model.

### Actions

| Action | When | Effect |
|---|---|---|
| CREATE | no model artifact has the sha256 | the migration mints one (after every other input's digests, after M3.10A's, in sha256 order: no existing id moves on a rebuild from scratch), then the URL placement |
| REUSE | the bytes are an artifact already (crawled, or registered earlier) | the URL placement only; the existing artifact row is not touched; never a second artifact because the URL differs |
| NOOP | the artifact is already placed at this URL | nothing |
| CONFLICT | the artifact records another size or media type, or two rows give one sha256 different sizes or media types | the batch is refused |
| REJECT | any validation failure (a fact not the record's, the held file not hashing to the row, an identity field, a non-external origin, the same bytes at the same URL twice, …) | the batch is refused |

Several rows with one sha256 and different URLs are one artifact with several placements (M3.8 fetched one PDF from
three URLs; the tests register it so).

### How it is applied

The migration is the writer. `mig_m2_identity.documents` calls `artifact_registrar().m2_artifacts` for the new digests;
`mig_m6_provenance.artifact_registration_placements` calls `m6_placements`, which adds each row's placement (M3.10A's
shape: URL locator, `PRESENT`, the fetch day as an EXACT bound, `retrieval_method`, `source` where given, a DOCUMENT
provenance whose `code_state` names the stream, runner, manifest, registration id, acquisition record, URL, fetch
time, status, `acquired_by`, `origin`) unless the model being built already has that artifact at that URL. The hooks
re-check the manifest against its acquisition records (committed) but not against the held bytes, which `sources/` does
not carry into a clone; the runner checks those. Stats `artifact-registration manifest artifacts` (M2) and
`… placements` (M6) are recorded only when non-zero.

`--apply` validates, plans, then rebuilds the model in memory through the migration with the registry, and writes
only if the rebuild changes exactly the registration's tables (artifacts, identity map, locators, placements,
provenance) and the model manifest's registration counts, keeps every earlier row, and adds exactly the plan's
artifacts and placements; otherwise nothing is written ("the model is not current with its inputs"). It then rebuilds
the indexes and, outside an isolated copy, checks the app is unchanged.

## 3. Evidence acceptance

### Contract

An acceptance records, against a registered (or crawled) model artifact, that its **own bytes** are evidence for
exactly one estate's grand vin and one vintage. It does not read the document and judges nothing: the verdict is a
reviewed reader row's, checked with V1's `check_review` (unchanged): SAFE_TO_MAP, category
ACCEPTED_EXACT_ESTATE_WINE_VINTAGE, exactly this estate, wine and year, one mapped wine, the year not a dated line,
identity from the document's own text (M34A or T1–T7), the vintage stated in the document, the reader's veto
ACCEPTED, and a DOCUMENT (not a web page) claim. Identity is checked as V1 checks it: the wine is the estate's grand
vin, not a candidate of an ambiguous identity, the estate has no open identity finding, the wine one settled current
name. The held file must hash to the artifact's sha256. `--apply` first runs the review audit's own `--check`
(`m39-evidence-review.py --check`: the existing reader recomputing the audit), which is M3.10B's freshness check made
generic: a row is accepted only while the reader still judges the document as the audit recorded.

### Manifest row (`data/audit/evidence-acceptance-manifest.jsonl`)

```json
{"acceptance_id": "eam_000001", "artifact_id": "ar_037071",
 "estate_id": "es_00263", "wine_id": "wn_00263", "vintage": 2024,
 "decision": "ACCEPTED", "evidence_version": 10, "reader": "6f68a0af15d3",
 "review": {"audit": "data/audit/m3.9-evidence-review.jsonl", "row": "m3.9:4"},
 "read": {"path": "acquisition/m3.8/blobs/<sha256>", "extraction": "acquisition/m3.8/extracted/<sha256>.json"},
 "document_name": "commercialandtechnicalargumentationdv2024.pdf",
 "notes": "optional"}
```

`read.path` is under `sources/`, in a held store (`acquisition/` as M3.10B, `discovery/` as M3.6B; a `.gz` is read
as the bytes it compresses); the decision's `folder` is `<store>:<sha256>`. `document_name` must be the basename of
one of the artifact's locators (M3.10B named the document by its URL's file name). No source text is copied: the
basis is read from the review row.

### The decision written

M3.10B's representation, field for field: `kind` `guard`, `decision` and `code` `ACCEPTED`, `raw` `''`, `ctx`
`{estate (slug), folder, wine: null, vintage, target_wine (name), target_role: grand, target_vintage, evaluated_as}`,
`evidence` `[<rule> rule: <basis>, whose_sheet with year=<y>, is_second=False: <reader decision>, <the reviewed row,
its audit, the artifact and the acceptance id>]`, `points_at` `{role: null, wine: null}`, `read` `{path, sha256,
bytes[, extraction]}`, `git` (the state it is written in), `reader` (the row's fingerprint), `v`, `re_evaluable`
true.

### Versions and actions

The store's rule is kept: new decisions append, old ones stay byte for byte, the highest version of a question is its
answer. **v1–v9 are closed** (`CLOSED_THROUGH = 9`: v1–v5 the reader's passes, v6 M3.6B, v7 M3.6E, v8 M3.6H, v9
M3.10B); a row names the store's newest version or the next one. A version is one reader: a row naming an existing
version written by another fingerprint is refused, and a row is appended only if its `reader` is the current decider
fingerprint (`tools/m35_rubric.py` + `tools/web_evidence.py`, as M3.6B–M3.10B computed it). No new versioning scheme
was introduced.

| Action | When |
|---|---|
| APPEND | the question (row key without `v`) is new, or this version supersedes an earlier answer (reported as "supersedes vN") |
| NOOP | the store holds exactly this decision (every field but `git`) |
| CONFLICT | the store holds another decision under the same key (same question, same version) |
| REJECT | a version older than the question's latest answer (stale), a closed version, a version beyond the next, a reader that is not the decider, and every validation failure |

Any REJECT or CONFLICT refuses the batch before anything is written. Writing goes through `evidence_store.append`,
one call per version, all rows of a batch sharing one git state. `--check` requires every manifest row NOOP and
written at a commit in HEAD's history, every decision of v10+ named by a manifest row, and `evidence_store.verify()`
clean. `BDX_EVIDENCE_DIR` points the runner at an isolated copy of the store (the store's code is unchanged).

Recording a decision creates no attribution, vintage or value. V1 consumes it by row key (`evidence_decisions`), and
its existence attribution is what M3.11 reads.

## 4. Golden equivalence

Both golden cases run on isolated copies only; M3.10A/B's data and tools are untouched.

**M3.10A.** M3.10A's four registrations, written as generic rows from M3.8's records (every fact equal to M3.10A's
row: sha256, size, media type, URL, final URL, status, fetch time, retrieval method, acquired by, origin, source,
relationship, held path), with M3.10A's own input set aside, rebuilt from scratch and with the registry:

- `identity/artifacts.jsonl`, `identity/identity-map.jsonl`, `document/locators.jsonl`: **byte for byte** (the same
  ids ar_037068–ar_037071, the same digests and metadata);
- `document/placements.jsonl`: the same four placements but for their `id` and provenance (the `observed` bounds'
  `basis` follows the provenance);
- `cross/provenance.jsonl`: M3.10A's four DOCUMENT provenance rows replaced by four whose URL, fetch time, status,
  `acquired_by` and `origin` are the same, naming the generic actor;
- `manifest.json`: M3.10A's placement count 4→0, the generic counts 4 and 4; nothing else;
- every other model file byte for byte.

**M3.10B.** M3.10B's four acceptances replayed through the generic runner on a store copy without v9 (closed through
v8 in the copy): v9 again, the **same four row keys** as M3.10B's manifest, every field equal but `git` and the third
evidence line (which names the review row and the artifact in both; M3.10B's adds its phase and commit, the generic
one its review audit and acceptance id); the index entry's reader and row count equal; v1–v8 and their index entries
byte for byte.

## 5. Tests

`python tools/test-generic-evidence-registration.py` — 22 checks covering the 28 required cases, on real material:
M3.8's acquisition records and held bytes (89 documents the model does not hold, 19 whose bytes it does, one PDF
fetched from three URLs) and M3.9's review rows.

| Check | Cases |
|---|---|
| g01 | 1 new artifact (CREATE on a copy: the next id, identity key, M3.10A-shaped placement, no evidence/attribution/value; then NOOP) |
| g02 | 2 existing content reused (REUSE: a crawled artifact gains the placement; artifacts and identity map unchanged) |
| g03 | 3 the same URL and content (M3.10A's rows NOOP); one PDF, three URLs: one artifact, three placements; the same location twice REJECT |
| g04 | 4 contradictory immutable metadata (CONFLICT; refused by the runner and the CLI, nothing written) |
| g05 | 5 deterministic ids (sha256 order after every existing id), plan order-independent, rebuild from scratch and with the registry equal to `--apply` |
| g06 | 6 provenance (DOCUMENT, every `code_state` field; the stats) |
| g07 | 7 external acquisition only; the discovery data untouched |
| g08 | 8 no invented fact (each stated fact, the relationship, identity fields, the held bytes; the migration hook refuses too) |
| g09–g10 | 9 valid acceptance, 10 exact identity (the full decision) |
| g11–g13 | 11 wrong estate, 12 wrong wine (the second wine), 13 wrong vintage; another artifact's review |
| g14 | 14 ambiguous identity, open finding, unsettled name, two mapped wines |
| g15 | 15 rejected reader results (disposition, category, identity source, vintage basis, the reader's veto; REFUSED not recordable) |
| g16–g17 | 16 missing artifact, 17 wrong bytes, missing held file, other store, wrong document name |
| g18 | 18 wrong review reference, an audit without a check, a malformed or non-current reader, a changed reader within a version |
| g19 | 19 stale rows; V1 refuses a superseded decision |
| g20 | 20 append-only: v1–v9 files and index entries byte for byte; closed and skipped versions refused; the newest version takes more rows |
| g21–g22 | 21 exact duplicate NOOP (also through the CLI), 22 contradictory same-version decision CONFLICT (CLI refuses, the file unchanged; `--check` flags the stray decision) |
| g23 | 23 M3.10A golden (subprocess, copy) |
| g24 | 24 M3.10B golden |
| g25–g26 | 25 V1 consumes the replayed v9 (3 NOOP) and a v10 answer (ATTRIBUTION_ONLY); 26 M3.11 then validates the five 2024 values at v10 (5 NOOP_EXISTING_IDENTICAL) and refuses them at the superseded v9 |
| g27 | 27 the production store byte for byte, verified, v1–v9 |
| g28 | 28 no production change: both manifests empty, `--check-all`/`--check` pass, no stats, the model, store, app and discovery data clean |

Historical compatibility, with the new files as they are committed: test-m310a, -m310b, -m310c, the M3.11 and V1
suites, -m39, -m38, -m37, -m36a-r1, -m36a-rerun, -m36b to -m36h, -m35, -m34a, -m34b, -m33, -m32, -historical-m1,
-historical-m2, -historical-m3, -data-gap-register, -phase4, -phase5 and -phase31 all pass, no assertion changed (r14
of test-m36a-r1 names the two new manifests among the later phases' audit files).

## 6. Performance

Measured on this machine; isolated copies; real M3.8 rows for registration, synthetic review rows (in memory) for
acceptance.

**Registration** (`--apply --timings`, a fresh copy each):

| Rows (digests) | Model loading | Validation (incl. hashing held bytes) | Planning | Application (migration rebuild + verification) | Indexes | `--check` |
|---:|---:|---:|---:|---:|---:|---:|
| 1 (1) | 0.30 s | 0.005 s | < 1 ms | 8.10 s | 0.63 s | 0.58 s |
| 10 (10) | 0.28 s | 0.013 s | < 1 ms | 8.11 s | 0.64 s | 0.61 s |
| 92 (89) | 0.29 s | 0.143 s | < 1 ms | 8.14 s | 0.60 s | 0.68 s |

The application is one migration rebuild, flat in the number of rows. With the empty manifest `--check` is 0.49 s.

**Acceptance** (in process, an isolated store):

| Decisions | Evidence loading (v6+) | Validation | Planning | Store write | Re-plan | Check (incl. store verify) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.035 s | 0.55 s* | 0.001 s | 2.38 s* | 0.04 s | 0.37 s |
| 10 | 0.038 s | 0.033 s | 0.001 s | 0.111 s | 0.06 s | 0.34 s |
| 100 | 0.034 s | 0.168 s | 0.001 s | 0.119 s | 0.22 s | 0.34 s |

\* first call in the process: the review audit and model read once, and the first `git status` of the working tree
for the decision's git state. `--apply` also runs the review audit's own check once (M3.9's: 6.2 s). The first
measurement showed `--check` at 3.0 s for 100 rows, one `git merge-base` per row; it now asks once per distinct commit
(0.34 s). No caching or parallelism was added.

## 7. Files

- New: `tools/apply-artifact-registration-manifest.py`, `tools/apply-evidence-acceptance-manifest.py`,
  `tools/test-generic-evidence-registration.py`, `data/audit/artifact-registration-manifest.jsonl` (empty),
  `data/audit/evidence-acceptance-manifest.jsonl` (empty), this document.
- `tools/mig_m2_identity.py`: `artifact_registrar()`, and the mint loop takes the generic registrations after
  M3.10A's (adds nothing for an empty manifest).
- `tools/mig_m6_provenance.py`: `artifact_registration_placements` after `external_placements`.
- `tools/test-m36a-r1.py`: r14 names the two new manifests among the later phases' audit files.
- `.gitattributes`: LF for the three new data/doc files.

## 8. Boundaries, and what V2 needs

The generic mechanisms stop where this phase's hard stops are. These are exact:

1. **A reviewed reader row for a new document.** Acceptance and V1 accept review rows only from audits they name:
   M3.9's (`REVIEW_CHECKS` here, `REVIEW_AUDITS` in V1). M3.9's tool reviews exactly M3.8's 17 candidates, so a new
   document needs a review audit in M3.9's row format, with its own `--check`. There is no generic reading/audit step
   yet. Adding that audit's name to V1's `REVIEW_AUDITS` is a change to V1 (a hard stop of this phase); adding it here
   is one line in `REVIEW_CHECKS`.
2. **An acquisition record for a new document.** Registration accepts acquisition records only from M3.8's audit
   (`ACQUISITION_AUDITS`). A new acquisition must produce `item` rows in M3.8's format (url, final_url, status, at,
   sha256, bytes, content_type, retrieval, attributed_to) and be added by name, with its held store and retrieval
   method.
3. **The historical suites' set-aside.** Today's frozen checks name M3.10A–V1 exactly. The first real registration
   adds artifacts, placements and provenance that `historical_m2_scope.model_changes_are_m2_only` and `test-m310a`
   attribute to no phase, and the first real acceptance adds v10, which `evidence_changes_are_m36b_only`,
   `_evidence_unchanged_but`, `protected_group('evidence')` and `test-m310b` (`ST.versions()[-1] == 9`) do not allow.
   V2 needs a mechanism-level exception for both mechanisms, as V1's U7 is for creation — a decision for you, not made
   here. The gap register (`data_gap_analysis`) should be checked for registered artifacts and v10 decisions at the
   same time.
4. **Scope of acceptance.** ACCEPTED decisions only; grand vins only (V1's U4); documents only (a web page's
   representation is M3.6B's `web_page_review`, not built here).

Then V2's first real vintage is: an acquired document with its acquisition record → one `arm_` row, `--apply` → a
review row in a named review audit → one `eam_` row at v10, `--apply` → one `vcm_` row (V1) → M3.11 value rows.
