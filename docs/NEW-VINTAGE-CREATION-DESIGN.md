# New-vintage creation: design

This is a design, and nothing is implemented. Every finding below was read or measured at `7777c1a`. No model,
evidence, app, legacy-file or M3.11 change was made, and no manifest was created.

**In one paragraph.** The model can already represent a new vintage for an existing wine, with no schema change.
A Vintage is the pair `(wine, label)` with no other fields, and 1,490 vintages already hold no canonical value.
The migration already has a precedent for creating vintages outside the legacy files: M3.6F's audited manifest,
read in M5.

What is missing is a fail-closed, reviewed and batched way to create one. It needs to add exactly two things: the
vintage shell (M5), and an *existence attribution* tying the accepted document to that exact vintage (M6). With
both in place, an in-memory probe shows the **M3.11 runner consuming the new vintage unchanged**. Without the
attribution it refuses, as it should.

The proposed mechanism is a second reviewed manifest, processed by a runner modelled on M3.11, with one M5 hook
and one M6 hook. Three things stay outside it, each its own future phase:
- showing such a vintage in the app;
- a generic way to register newly acquired artifacts and record their evidence acceptance;
- using the model's unused `VintageStatement PRODUCED`.

## 1. Problem statement

A new-vintage operation creates the structural Vintage record for an **already-existing wine**, so that reviewed
values and provenance can then be attached to it.

It does **not** create an estate, a wine, an alias, a rename or identity transition, a rank, a colour, an
appellation, a second wine or a cuvée. It does not import scores or collections, and it does not fill a missing
historical vintage by inference. It never infers a vintage from a year that merely appears in a document's
surroundings.

Today no path does this:
- the legacy update path (`docs/ADDING-A-VINTAGE.md`) writes the legacy files, frozen since Phase 4;
- M3.11 applies values only to vintages that already exist;
- M3.6F's vintage creation is fixed to Cuvée Mongravey and its own audit.

## 2. Current-model audit

| Question | Finding (evidence) |
|---|---|
| Where are vintages? | `data/model/identity/vintages.jsonl`, entity **Vintage**, layer IDENTITY. Key `(wine, label)`, built in M5 (`model_schema.LAYOUT`). |
| What is a vintage? | `{"wine": <wine id>, "label": <year or "NV">}`. The contract (`docs/phase34-model.json`) gives it **only these two fields**: no id, no provenance, no status. Elsewhere it is referenced as `vt:<wine>:<label>` (`model_schema.vref`). |
| How is it tied to its wine? | By the `wine` field. The wine's estate comes from `state/estate-wine.jsonl` (640 rows, all `PRODUCED_BY`, `ESTABLISHED`). |
| Same year for several wines? | Yes. The key is per wine: 255 wines have a 2015. |
| Labels in use | 5,292 vintages, all years, from 1900 to 2026. There is no `NV` row although the contract allows one. |
| Empty versus missing vintage | **Missing:** no row for `(wine, label)`. **Empty:** a row with no canonical value. 1,490 vintages hold no canonical value; 105 of those hold no observation at all; 125 have a document attribution. |
| Can a vintage exist with zero values? | **Yes.** Nothing requires a value, and the canonical layer is keyed by `(subject, field)` only where a value exists. |
| Does a vintage have its own identity or provenance? | **No.** Legacy vintages have identity-map rows (`estate|vintage` 4,024, `estate|slug|vintage` 1,174). M3.6F's vintages have none, and their existence basis lives in their audit manifest. The contract has a **`VintageStatement`** (id, vintage, kind, **provenance**) whose kind enum includes **`PRODUCED`**, but none exists: all 18 statements are `NOT_PRODUCED`. |
| Is creation already possible indirectly? | **Yes, once.** `mig_m5_vintages.m36f_vintages` creates vintages from `data/audit/m3.6f-cuvee-vintages.jsonl` (rows `{record: vintage, wine, label, documents, basis, applied}`). It runs after the legacy decomposition, adds the six Cuvée Mongravey vintages, and records the M5 stat "M3.6F Cuvée vintages". This is the precedent to generalise. |
| Tools assuming every vintage is legacy | **`model_reader.project` (the app):** projects only observations whose extraction names a legacy file, so a vintage with no legacy record is not shown (§10). Its `BDX_NOT_PRODUCED` loop reads **every** vintage statement as NOT_PRODUCED and looks the wine up among grand vins only. **`historical_m2_scope`** (line 661): the older suites accept new vintage rows only for M3.6D's wine. **`data_gap_analysis`:** builds the gap register over every vintage; its as-of view sets later rows aside *by provenance*, which a vintage row does not have. |
| Tools that do not assume it | `build-indexes.py`, which derives `wine-vintages.json` from every vintage (M3.6F's commit changed only that derived file); the M3.11 runner, which reads `identity/vintages.jsonl` whatever its origin; and `migrate.validate`, which checks that every `vt:` reference resolves. |
| Reconciliation, observation, provenance | They are keyed by `subject = vt:…`, with no vintage-specific rule, and M3.11 creates them. |
| Ambiguous wine identity | Wines carry no status. Ambiguity is recorded as **identity-map rows with status AMBIGUOUS**: `second-by-name` 17, `wine-by-display-name` 18, `graves-white` 2. They have no stable id but list `candidates`; for example "Les Pagodes de Cos" lists `wn_00485`. Estates can also carry OPEN findings: `IDENTITY_UNCERTAIN` 15, `AMBIGUOUS_SEMANTICS` 7, `CONFLICT` 2. There are no identity transitions. |

## 3. Exact definition of vintage creation

Creating vintage `Y` of wine `W` of estate `E` adds:

1. **M5:** one Vintage row `{wine: W, label: "Y"}`, the *shell*;
2. **M6:** for each accepted document of the row, one Attribution `{artifact, estate: E, wine: W, vintage: vt:W:Y,
   method: DOCUMENT_TEXT, status: ACCEPTED, role: FIRST}`, the *existence attribution*. Its DOCUMENT provenance
   quotes the reader's basis and names the evidence decision key, the evidence version, `identity_source`,
   `vintage_source`, the sha256, the manifest and the `manifest_id`. This is exactly M3.10B's shape, because that
   is the shape M3.11's evidence chain reads.

Nothing else is added: no observation, reconciliation or canonical value, no identity-map row, finding, name,
wine or estate. **The vintage's existence is proved by its existence attributions**, whose provenance is the
model's record of why the vintage exists. The audited manifest keeps the review.

`VintageStatement PRODUCED` would be the contract's own place for that proof. It is not proposed for the first
implementation, because the app's projection would misread it (U1).

## 4. Evidence contract

A vintage is created only from a document whose **own text** names the model wine and the year together, as the
existing readers already decide. There is no new reader and no new rule.

**Accepted.** All of the following must hold for every artifact of a row:

1. The artifact exists in `identity/artifacts.jsonl`. It was registered by the migration from a committed input:
   the sources manifest, the discovery manifest, or an external registration such as M3.10A's.
2. A reviewed audit row classifies it **SAFE_TO_MAP** for exactly this estate, wine and vintage, through one of the
   reader rules already used for attributions:
   - **M34A**: the document names the wine beside the year, with no other wine of the estate named; M3.4A/B, M3.10B;
   - **T1–T7**: the M3.5 title rubric; T4 refuses a year standing in a dated line;
   - **W1–W6 / h1**: the web-page main heading; M3.6A/B.

   Together with `claim_year_dated = false`, this keeps a year taken from a press or event date out.
3. The evidence store holds an **ACCEPTED** decision for it, at the row's `evidence_version`. That decision is:
   - **the latest for its context** (not superseded, as the M3.6E/M3.6H corrections were);
   - for the artifact's **own bytes** (`read.sha256`);
   - for this **target vintage**;
   - for this wine. Its `target_wine` must equal the wine's current name (`identity/names.jsonl`), its estate slug
     must map to `E` through an ACTIVE `estate` identity-map row, and its `target_role` must agree with the wine's
     role: `grand` only for the estate's ACTIVE `grand-vin` entry, `second` only for an ACTIVE `second-by-name`
     entry.

**Rejected.** Each of these stops the row:
- **Year only in the surroundings:** a year found only in a filename, URL, folder, page title, navigation label,
  publication, retrieval or press date, metadata, or a critic rating. The readers above never use these for the
  vintage; legacy filename guards do, which is why an ACCEPTED decision **alone** is not enough and rule 2 is required.
- **Reader dispositions short of SAFE_TO_MAP:** `ESTATE_VINTAGE_ONLY` (estate-only), `WINE_AMBIGUOUS`,
  `COLOUR_AMBIGUOUS`, `MULTI_WINE_AMBIGUOUS` (one document, several wines), `VINTAGE_AMBIGUOUS` (multi-vintage
  documents, or an opening that does not state the year), `EVIDENCE_INSUFFICIENT`.
- **Decisions not accepted:** any evidence-store decision other than ACCEPTED, or one superseded by a later
  version (`WRONG_WINE`, `REFUSED`).

**Known reader limit.** M34A's year pattern covers 1950–2029.

## 5. Proposed manifest

`data/audit/vintage-creation-manifest.jsonl` (name not final). One row per vintage to create:

```json
{"manifest_id": "vcm_000001", "estate_id": "es_…", "wine_id": "wn_…", "vintage": 2025,
 "artifact_ids": ["ar_…"], "evidence_version": 10,
 "evidence_decisions": {"ar_…": "<the store's row key>"},
 "review": {"ar_…": {"audit": "data/audit/<review>.jsonl", "row": "<candidate id>", "rule": "M34A",
                     "identity_source": "M34A", "vintage_source": "statement \"2025 vintage\"",
                     "basis": "the document names \"Château X\" beside 2025; no other wine of the estate is named"}},
 "creation_class": "EXPLICIT_DOCUMENT_TEXT", "notes": "…"}
```

- **Required:** `manifest_id` (`vcm_NNNNNN`, never reused), `estate_id`, `wine_id`, `vintage` (an integer year),
  `artifact_ids`, `evidence_version`, `evidence_decisions` (one store key per artifact), `review` (one per
  artifact: the reviewed audit row and the reader's own basis, copied, never parsed), and `creation_class`
  (`EXPLICIT_DOCUMENT_TEXT` only).
- **Not in it:** any canonical value, any figure, or the evidence decision itself. It points at the store and at
  the review audit and duplicates neither. Values go to M3.11's manifest.
- **One reviewed document can back both facts.** The same artifact may appear in a creation row (existence: the
  attribution) and in M3.11 rows (values: observations quoting their own lines). The two facts stay separate in
  the model as an Attribution and as Observations, with separate provenance.

## 6. Validation rules

Every rule is read-only and runs before any write. It reuses the M3.11 runner's style (View, Evidence and Clock;
everything loaded once) but not its code paths, which stay untouched.

- **Structure:** required keys only; ids unique; one review and one decision per artifact; `creation_class` known.
- **Identity:**
  - the estate exists;
  - the wine exists;
  - `(estate, wine)` is ESTABLISHED in `estate-wine`;
  - the wine is not a candidate of any AMBIGUOUS identity-map row;
  - the estate is not the target of an OPEN `IDENTITY_UNCERTAIN`, `AMBIGUOUS_SEMANTICS` or `CONFLICT` finding.
- **Vintage:** an integer year from 1950 to the current year + 1. NV is refused, as is anything the reader cannot
  state.
- **Evidence:** §4, rules 1–3, for every artifact.
- **Batch:** no `(wine, vintage)` twice; no artifact claimed for two different vintages or wines.
- **Scope (optional):** `--expected-scope` as in M3.11.

## 7. Idempotence and conflicts

| State of the model | Action |
|---|---|
| No Vintage `(W, Y)` | **CREATE**: the shell and its existence attributions |
| Vintage present, and every artifact already has an identical ACCEPTED attribution to `vt:W:Y` | **NOOP** |
| Vintage present, without these attributions | **CREATE_ATTRIBUTION_ONLY** is **not** proposed. It would turn the runner into an attribution tool for existing vintages (M3.10B's job). The row is a **CONFLICT** and names the gap. |
| A `NOT_PRODUCED` VintageStatement for `(W, Y)` | **CONFLICT**: the model says not produced and the document says otherwise |
| An artifact already ACCEPTED-attributed to another vintage or wine | **CONFLICT** |
| Invalid estate or wine, ambiguous identity, rejected, superseded or inexact evidence | **STOP** (invalid) |

Any invalid row or CONFLICT stops the whole batch before anything is written. The runner never overwrites,
never reinterprets an existing vintage, and never writes part of a batch. A second run of the same manifest is
all NOOP.

## 8. Zero-value vintages

They are **legal, and they are the intended creation state.** The vintage exists, its existence attributions
prove it, and every field stays missing until M3.11 applies reviewed values. 1,490 vintages are already in that
state, and no contract rule or validator requires a value. No model change is needed.

## 9. M3.11 integration

```text
accepted evidence  (artifact registered; reviewed SAFE_TO_MAP; store decision ACCEPTED)
   → vintage creation manifest            data/audit/vintage-creation-manifest.jsonl
   → validated creation plan              CREATE / NOOP / CONFLICT, all or nothing
   → vintage shell (M5) + existence attribution (M6)
   → M3.11 value manifest                 data/audit/value-application-manifest.jsonl
   → canonical values (M7)
```

- **Can M3.11 accept a newly created vintage unchanged? Yes**, as measured by an in-memory probe that wrote nothing.
  Durfort-Vivens 2024 was removed from a view of the model:
  - with the vintage gone, the runner refused all five 2024 rows ("vintage 2024 of wn_00263 does not exist");
  - with only the shell put back, it still refused ("no accepted attribution to vt:wn_00263:2024");
  - with the shell and the existence attribution, it planned the five values as APPLY: 5 values, 5 observations,
    5 reconciliations and 10 provenance rows.

  So **no runner change is needed**, provided the existence attribution keeps M3.10B's provenance shape
  (`code_state.evidence_decisions`).
- **Two manifests, not one.** Existence and values are different facts with different reviews, conflicts and
  hooks (M5/M6 against M7). Merging them would let a value batch create identity as a side effect. Neither manifest
  is made safer by the merge.
- **Order:** the creation manifest is applied before any value row for the new vintage. In a rebuild that holds by
  construction (M5/M6 run before M7). With `--apply`, the value runner already refuses a missing vintage.

## 10. App implications

**Nothing changes in the app**, with any number of values.

- **Why:** `model_reader.project` builds the vintage records from observations whose extraction names a legacy
  file (`data/fiches.js` and the other legacy data files). A created vintage has none, so it is not projected;
  M3.11's values for it are not projected either.
- **Precedent:** M3.6F's created vintages changed only `derived/wine-vintages.json`, never `data/app/`.
- **Showing created vintages** and their sourced values is therefore a **separate app phase**. It would make the
  projection enumerate model vintages and canonical values that have no legacy record. That phase is also where
  `BDX_NOT_PRODUCED`'s missing kind filter would need fixing, if `VintageStatement PRODUCED` is ever used (U1).

## 11. Migration and rebuild design

- **Inputs:** the creation manifest becomes a committed migration input, as M3.6F's and M3.11's are. There are two
  generic hooks, each calling the creation runner's own plan, so `--apply` and a rebuild write the same rows:
  - `mig_m5_vintages.vintage_creation(m)` runs last in M5, after `m36f_vintages`, and adds the shells;
  - `mig_m6_provenance.vintage_creation_attributions(m)` runs last in M6 and adds the existence attributions.
- **Fingerprinting:** the same as every other input. The manifest is committed and byte-checked through the
  rebuild (`migrate.py --check`). Its rows name the store keys, which carry the reader fingerprint (`reader`) of
  the decision. No new fingerprint is needed.
- **Fresh rebuild:** M5 evaluates CREATE/NOOP against the model being built, so a from-scratch build recreates
  exactly the committed shells. M6 adds their attributions, and the stats record only when something is created,
  as in M3.11. Historical migrations stay byte-identical: the hooks add nothing while the manifest is empty or
  absent.
- **Older checkpoints and `historical_m2_scope`:** one generic set-aside, registered once for every later batch:
  vintage rows whose `(wine, label)` is in the manifest's applied set (vintage rows have no provenance, so
  membership is the only handle), and attributions and provenance by the creation runner's actor. Line 661's guard
  would then accept those rows. This is the same kind of change every population phase made.
- **Frozen contract:** none beyond the manifest itself and its suite. The Phase 3.4 contract already holds Vintage
  and Attribution, so no contract change is needed.
- **Gap register (U2):** `data_gap_analysis` either sets created vintages aside by manifest membership, as the
  audits do for later phases, or lets the register see them. A created vintage has an accepted document, so it
  raises no `VINTAGE_NO_DOCUMENT` gap.

## 12. Test plan

The focused suite `tools/test-vintage-creation-manifest.py` runs every application on an isolated model copy
(`BDX_MODEL_DIR`), as M3.11's does.

| # | Case |
|---:|---|
| 1 | Valid creation: a shell and its existence attributions, nothing else |
| 2 | Exact wine and vintage evidence: the decision's target wine, role, vintage and sha256 match |
| 3 | Unknown estate rejected |
| 4 | Unknown wine rejected |
| 5 | Wrong estate (wine not ESTABLISHED for it) rejected |
| 6 | Wrong wine (the decision's target wine or role is another wine's) rejected |
| 7 | Ambiguous wine (a candidate of an AMBIGUOUS identity-map row; estate with an OPEN identity finding) rejected |
| 8 | Existing vintage with identical attributions: NOOP |
| 9 | Contradictory existing state (NOT_PRODUCED statement; artifact attributed elsewhere; vintage present without the attributions): CONFLICT |
| 10 | Rejected evidence (decision not ACCEPTED) |
| 11 | Superseded evidence (a later version decides otherwise) |
| 12 | Filename-only evidence (an ACCEPTED legacy decision with no SAFE_TO_MAP review row) rejected |
| 13 | URL-only evidence (as 12, a URL-derived year) rejected |
| 14 | Publication-date-only evidence (`claim_year_dated`, T4) rejected |
| 15 | Wrong-vintage evidence (decision `target_vintage` ≠ row) rejected |
| 16 | Multi-vintage document (`VINTAGE_AMBIGUOUS`) rejected |
| 17 | Zero-value vintage: created with no observation or value; app unchanged |
| 18 | Deterministic rebuild: `--apply` on the copy equals a migration rebuild byte for byte; plan output stable under row order |
| 19 | No partial mutation: an invalid row N leaves rows 1..N−1 unwritten |
| 20 | No identity creation: no estate, wine, name, identity-map row or transition; other tables byte for byte |
| 21 | M3.11 compatibility: after creation, an M3.11 manifest for the new vintage plans APPLY and applies |
| 22 | Idempotent second application: all NOOP, no byte change |
| 23 | Production untouched while the creation manifest is empty |

**Golden reference.** There is no historical new-vintage creation for an existing wine; M3.6F's was for a newly
minted wine. The golden test is therefore a reconstruction. On a copy of the model with Durfort-Vivens 2024's
shell and attribution removed, the creation runner must put back exactly the shell and an attribution equal to
M3.10B's `at_118b7dcaeeb1`, apart from runner metadata. Then M3.11 must give M3.10C's five 2024 values, as in the
probe in §9.

## 13. Performance expectations

All measured on this machine at `7777c1a`:

| Stage | Cost | Basis |
|---|---:|---|
| Model loading (estates, wines, names, vintages, artifacts, identity map, estate-wine, attributions, provenance, findings) | 0.34 s | measured |
| Evidence loading | 0.002 s for v9; 1.09 s for all versions | measured: only the named version and later ones are read, as in M3.11 |
| Validation | ≪ 0.1 s per batch; dictionary look-ups per row | M3.11's validator measured 2 ms for 99 rows; this one does the same kind of work plus four identity look-ups |
| Planning | ≈ 1 ms per 100 rows | as M3.11 |
| Application (render vintages, attributions, provenance and the manifest) | ≈ 0.4 s | M3.11's four-table render measured 0.51 s |
| Index rebuild (`build-indexes.py`) | 0.63 s | measured |
| Deterministic check | 0.06 s (`--check`); a rebuild check about 15 s | measured (M3.11) |

**A batch of 100 vintages should cost about as much as one**, around 1.5–2 s for `--apply`. There is no
per-vintage script, audit file, rediscovery, evidence reload or model reconstruction.

## 14. Unresolved decisions

- **U1. Where the proof of existence lives.**
  - **(a) Recommended:** in the existence attributions only. This needs no app change and matches M3.6F, whose
    vintages keep their basis in the manifest.
  - **(b)** Also add a `VintageStatement PRODUCED` with DOCUMENT provenance. This is the contract's own concept,
    but `model_reader.project` would list it under `BDX_NOT_PRODUCED`, and would fail for a non-grand wine, until
    the app phase fixes the projection.
- **U2. The gap register:** set created vintages aside, keeping the register as it is (as the audits do), or let it
  see them and regenerate it.
- **U3. Prerequisites that are still per-phase.** A new vintage's document must first be registered as an artifact
  (today only M3.10A's phase-specific external-registration manifest) and accepted in the evidence store (today
  only phase tools such as `m310b-accept.py`). Creating vintages at scale needs **generic registration and
  acceptance manifests**, or an agreed way to extend M3.10A's input. Either is a separate phase; this design
  assumes both steps happened.
- **U4. Second wines.** The first implementation could allow only grand vins, or also wines with an ACTIVE
  `second-by-name` entry, which the role check (§4.3) supports.
- **U5. The year window:** 1950 to the current year + 1, which is the reader's own limit; and whether NV is ever
  allowed.
- **U6. Vintage present without the attributions:** a CONFLICT (proposed), or a separate attribution-only step.
- **U7. One-time `historical_m2_scope` set-aside:** that the first implementation registers it (proposed), as
  every population phase has.

## 15. Proposed implementation phases

| Phase | Content | Production change |
|---|---|---|
| **V1: vintage creation runner** | `tools/create-vintage-manifest.py` (`--validate`/`--plan`/`--apply`/`--check`/`--check-all`); the M5 and M6 hooks; the generic `historical_m2_scope` set-aside; `data/audit/vintage-creation-manifest.jsonl` committed **empty**; the focused suite (§12) with the isolated reconstruction golden test | none (empty manifest) |
| **V0, before or alongside: registration and acceptance** | generic external-artifact registration and evidence-acceptance manifests (U3), so new documents need no per-phase tool | none until used |
| **V2: first new vintage** | one acquired, reviewed sheet for one existing wine: registration, acceptance, a creation row, then M3.11 value rows | one vintage, its attributions and values |
| **A1: app** | project model-created vintages and their sourced values; filter vintage statements by kind | app |

**Estimated V1 scope:**
- the runner: about 450 lines, modelled on M3.11;
- two hooks: about 20 lines;
- the set-aside: about 15 lines;
- the suite: about 23 checks;
- the phase report;
- runtime of the focused suite: about a minute, the same as M3.11's.

No reader, evidence, schema, app or historical-migration change is needed, and the M3.11 runner itself is not
changed.
