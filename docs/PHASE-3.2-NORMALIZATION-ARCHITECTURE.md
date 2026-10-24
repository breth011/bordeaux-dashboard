# Phase 3.2 — Normalized Domain Architecture and Migration Design

**Input:** commit `a842bb7`, Phase 3.1 gate `SAFE — STRUCTURAL AUDIT
COMPLETE`. This is a design phase only. No record was migrated, no file of
the dataset was changed, and no schema, database or table was created.
Phase 3.0 stays the scope baseline and Phase 2 the evidence baseline.

| Deliverable | What it is |
|---|---|
| this document | the design and its reasons, 21 sections |
| `docs/PHASE-3.2-DATA-MODEL.md` | every entity, field by field |
| `docs/phase32-model.json` | the same model, machine-readable: 32 entities, 26 enums, 21 relationships, 68 current→target mapping rows, 10 migration stages, 22 invariants, 8 open decisions |
| `docs/phase32-fixtures.json` | eight real cases from this repository expressed in the model, 190 records: the evidence that the design holds them |
| `tools/test-phase32.py` | checks the model, the fixtures, the mapping's coverage of every current field, and that nothing was migrated |

One file outside the design was edited: `tools/test-phase31.py`. Its
two reproduction checks rebuild a report from the live tree. They already
stood down once a later phase had *committed*, but not while a later
phase's files were still uncommitted, so this phase's new test made them
fail. They now stand down in both cases, and still run whenever the tree
is as Phase 3.1 left it. This is the same class of correction made to
`test-phase212` and `test-phase30`.

## 1. Design goals

1. Separate the six layers the brief names: **identity**, **time-dependent
   state**, **document/artifact**, **observation**, **reconciliation**,
   **canonical value**. Provenance and quality connect them without
   merging them.
2. Resolve the three Phase 3.1 blockers (B1, B2, B3) structurally, with
   no workaround that invents a role, a date or a source.
3. Answer every structural risk (R1–R12) and migration risk (M1–M5).
4. Keep every boundary Phase 3.1 found sound (S1–S8): the evidence store
   is immutable and stays so; proposals and the authoritative universe
   stay apart from canonical data.
5. Work while the wine universe is incomplete (I20): absence of knowledge
   is a state, not a gap the migration must fill.
6. Be migratable additively. Every stage adds beside what exists and can
   be removed without loss, until a final retirement that is archived.

## 2. The three Phase 3.1 blockers

| Blocker | What the design adds | Shown by |
|---|---|---|
| **B1** No unknown role | `WineRole.UNKNOWN` on a `RoleAssignment` of an `EstateWineRelationship`. Membership (the relationship) and role (the assignment) are separate records, so "this wine is the estate's, its role is not established" is two true statements and no invented one. Legacy `other` migrates to UNKNOWN with `legacy_term: 'other'`. | C1 Terrasses, C2 Murets, C3 Blanc de Lynch-Bages |
| **B2** No temporal state | Every STATE record carries a `Validity` of two `TemporalBound`s with kind, **axis** (CALENDAR or VINTAGE), precision and basis. Changes are added, never written over. Classifications have editions; appellations have their own validity; names, ownership and identity transitions are dated records. | C3 Echo from vintage 2008; C4 Mouton 1973-06, Cantemerle 1855-09-16, Saint-Émilion 2012/2022, La Tour Haut-Brion 2006, Crus Artisans vintages 2022–2026, Pessac-Léognan 1987; C5 ownership 2012, 2016 |
| **B3** No persistent observations | `Observation` (append-only, versioned by extractor), `Reconciliation` (persistent, rule-named, lists every candidate), `CanonicalValue` (a projection pointing at its reconciliation). A loser is a candidate that was not selected; it is never deleted. | C6 Badette 2020: EN 80 %, FR 50 %, both kept |

## 3. Entity definitions

Full definitions are in `PHASE-3.2-DATA-MODEL.md`. By layer:

| Layer | Entities | Purpose |
|---|---|---|
| Identity | Estate, Wine, Vintage, Source, Party, IdentityMap, NameRecord, IdentityTransition | what things are, apart from what is said about them |
| State | EstateWineRelationship, RoleAssignment, RoleAbsence, ClassificationScheme, ClassificationEdition, ClassificationMembership, Appellation, AppellationMembership, Ownership, EstateLocation, VintageStatement, EditorialCollectionMembership | what holds of them, and when |
| Document | Artifact, Locator, Placement, ArtifactAssessment, Attribution, LegacyDocumentReference | the bytes, where they were, what kind they are, what they may concern |
| Observation | Observation, EvidenceLink | what was said, and how the existing evidence connects |
| Reconciliation | Reconciliation | which statement is accepted, and why |
| Canonical | CanonicalValue | the projected accepted value |
| Cross-cutting | Provenance, QualityFinding (with Validity and TemporalBound as value types) | where everything came from; what is wrong with it |

Three departures from the brief's list, each justified by the audit:

1. **`WineRole` is two axes, rank and range.** The rank is GRAND_VIN,
   SECOND_WINE, OTHER_CUVEE or UNKNOWN. The range is RED, DRY_WHITE,
   SWEET_WINE, ROSE, SPARKLING or UNKNOWN. The brief's DRY_WHITE and
   SWEET_WINE become ranges, because the domain has grand and second wines
   *within* a white range:
   - Caillou's Myosotis is "grand vin blanc sec".
   - The 2023 Murets sheet says "Second Vin blanc sec".
   - Olivier has a second wine in red and in white.
   - A Graves classified white is the grand vin of its colour.

   A single axis would force a choice between "dry white" and "second
   wine". All six requested values are representable.
2. **Classification and appellation memberships attach to the Wine**,
   not the Estate:
   - Graves classifies per colour (R10).
   - Crus Artisans classifies Moutte Blanc twice, once in each of its two
     appellations.

   "The estate is classified" becomes a derived view.
3. **Further entities beyond the list:**
   - Placement and Locator (location history);
   - ArtifactAssessment (document type, apart from attribution);
   - LegacyDocumentReference (bare filenames);
   - EvidenceLink (reading the immutable store);
   - RoleAbsence (stated NO_SUCH_WINE);
   - EditorialCollectionMembership (the dashboard's own groupings, kept
     out of classification).

## 4. Relationship model

```text
IDENTITY            Estate ───────── EstateWineRelationship ───────── Wine ── Vintage
                      │  │                    │ (validity)               │      │
STATE                 │  │              RoleAssignment                   │      └─ VintageStatement
                      │  │              (role × range, validity)         │
                      │  ├─ RoleAbsence (stated "none")                  ├─ ClassificationMembership ── ClassificationEdition ── ClassificationScheme
                      │  ├─ Ownership ── Party                           └─ AppellationMembership ── Appellation (own validity)
                      │  ├─ EstateLocation
                      │  └─ EditorialCollectionMembership
                      └─ NameRecord / IdentityTransition / IdentityMap  (also for Wine)

DOCUMENT            Source ── Placement ── Locator (path | URL)
                                 │
                              Artifact (digests) ── ArtifactAssessment
                                 │
                                 ├─ Attribution ──▶ Estate? Wine? Vintage? role?   (judgement; many per artifact)
                                 │
OBSERVATION                      └─ Observation ──▶ subject: Estate | Wine | Vintage | EstateWineRelationship
                                         │                    EvidenceLink ──▶ (immutable evidence row)
RECONCILIATION              Reconciliation (all candidates, rule, status)
                                         │
CANONICAL                         CanonicalValue (subject × field)

CROSS-CUTTING       Provenance ── on every record of every layer        QualityFinding ── on anything, changes nothing
```

The relationships that matter most:

- **Estate → EstateWineRelationship → Wine.** Estate and wine are never one
  record. Time and status sit on the link:
  - a wine can end its relationship with an estate (Haut-Bages Averous,
    up to 2007);
  - a wine can belong to an estate with an unknown role (Terrasses).
- **RoleAssignment on the relationship, not the wine.** A role is relative
  to an estate and to time. The same wine can be one estate's second and,
  under another arrangement, something else.
- **Source → Placement → Artifact.** A source serves bytes at locations.
  It is linked to estates only through Attribution, never by identity
  (I15).
- **Artifact → Attribution.** Attribution is a judgement with a method and
  a status, many per artifact. It is not the artifact's identity, and not
  the dataset's belief about the estate.
- **Observation → Reconciliation → CanonicalValue.** These are three
  records, and each points backwards.

## 5. Role model

A `RoleAssignment` is `{relationship, role, range, source_term,
legacy_term, validity, provenance}`.

| State | How it is held |
|---|---|
| Role known | RoleAssignment with role GRAND_VIN, SECOND_WINE or OTHER_CUVEE, with its source's term |
| **Wine belongs, role not established** | RoleAssignment **UNKNOWN** (C1, C2) |
| Estate states it has no such wine (NO_SUCH_WINE) | RoleAbsence (C8 Rauzan-Gassies, from `second:'—'`) |
| Nothing known (UNKNOWN) | no assignment and no absence; never filled in by a migration (I20) |
| Known to the universe, not to the dataset (NOT_YET_MODELED) | a QualityFinding SCOPE_DISCREPANCY against the Phase 3.0 statement |
| Role changes over time | successive assignments with validity (C3 Averous then Echo) |
| Several wines of one rank | several assignments (Olivier: SECOND_WINE in RED and in DRY_WHITE) |
| An observation suggests a role | an Observation on the relationship, reconciled. It is DEFERRED until a decision, and never written straight into the assignment (C1 "second label", C2 "Second Vin blanc sec") |

Legacy roles migrate without invention:

- `second` → SECOND_WINE (legacy_term `second`).
- `other` → **UNKNOWN** (legacy_term `other`). B1 showed `other` meant both
  "another cuvée" and "not known", so it cannot be read as OTHER_CUVEE.
- `'—'` → RoleAbsence.

Each of the 58 legacy `other` wines then needs a review, for which UNKNOWN
is the honest starting point.

## 6. Temporal model

A `TemporalBound` is `{kind, axis, value, precision, basis}`.

| Kind | Value | Means |
|---|---|---|
| EXACT | yes | at this value, at this precision |
| APPROXIMATE | yes | about this value (the source says so) |
| NO_LATER_THAN / NO_EARLIER_THAN | yes | inclusive one-sided bound |
| UNKNOWN | no | a bound exists; nobody has said what it is |
| OPEN | no | (valid_to only) still holds as of `as_of` |
| NOT_APPLICABLE | no | the record has no such bound |

The cases the brief asks the model to distinguish:

| Case | Held as |
|---|---|
| **Date unknown** | kind UNKNOWN. It is not OPEN and not NOT_APPLICABLE. |
| **Date not applicable** | kind NOT_APPLICABLE. |
| **Current** | `valid_to` OPEN, with `as_of`, the date of the latest source confirming it. |
| **Historical** | `valid_to` is any kind that takes a value, or UNKNOWN. |
| **Exact** | EXACT, at the source's precision. |
| **Approximate** | APPROXIMATE, or a one-sided bound. |

**Axis.** Wine facts change by vintage ("à partir du millésime 2008");
institutions by calendar ("juin 1973", "8 septembre 2022"). The two are
not convertible. A 2008 vintage is harvested in 2008 and released years
later, so the axis is part of the bound.

**Precision follows the source and never exceeds it:**

| Source wording | Bound | Fixture |
|---|---|---|
| "juin 1973" | MONTH `1973-06` | C4 |
| "16 septembre 1855" | DAY | C4 |
| "Né en 1990" | YEAR `1990` | C3 |
| "since 2016", in a legacy string | YEAR, with the string as basis | C5 |
| "pendant plus de 30 ans" | UNKNOWN, with the words kept as the basis | C3 |
| "from the 2008 vintage" (Averous's end) | NO_LATER_THAN vintage 2007: the source says Echo starts in 2008, and does not say Averous was made in 2007 | C3 |

**Validity is justified where it is used.**

- Identity records (Estate, Wine, Artifact) have none; they are not states.
- NameRecord, IdentityTransition and every STATE record have one.
- Classification editions have one.
- An Appellation has one only where its creation is sourced. Pessac-Léognan
  has one; the Margaux appellation record carries NOT_APPLICABLE.

**History is added, never overwritten (I7).**

- A promotion ends one membership and starts another (Mouton).
- A merger is an IdentityTransition and ends a membership (La Tour
  Haut-Brion).
- A rename is a NameRecord FORMER plus a CURRENT. Whether it is also a new
  Wine is a recorded decision (D2).

All nine Phase 3.0 fixtures are representable (C3, C4, C5):

| Case | Held as |
|---|---|
| T1 Mouton | two memberships split at 1973-06 |
| T2 Cantemerle | membership from 1855-09-16 |
| T3, T4 merges | transitions plus ended memberships |
| T5 Saint-Émilion | two editions |
| T6 Tour Saint-Christophe | membership from 2022-09-08 |
| T7 Crus Artisans | an edition on the VINTAGE axis |
| T8 Averous → Echo | relationships plus a transition |
| T9 Pessac-Léognan | an Appellation's validity |

## 7. Document / artifact model

| Situation | Held as |
|---|---|
| Identical bytes at several paths | one Artifact, several Placements (C1 Terrasses, C7 Belgrave/Rahoul; 665 such documents today) |
| One path, different bytes over time | one Locator, several Placements, each to its own Artifact. Superseded bytes keep their sha1 with `bytes_available: false` (C7 Moulin Rouge; 204 such paths) |
| Same filename, different bytes, different paths | different Artifacts. The filename alone resolves to candidates, never to one (C7 Mongravey) |
| Renamed file | a new Locator, a new Placement, the same Artifact |
| URL changes, mirrors | URL Locators, each a Placement of the same Artifact (C7 Moulin Rouge URL) |
| Shared documents (group libraries, négociant pages) | one Artifact, a Placement per location, an Attribution per estate it may concern |
| Known path, bytes absent | a Placement with `artifact: null`, status MISSING or NAME_MISMATCH, plus a finding (C7; the 123) |

**Artifact identity is its digests.** sha256 is used where the evidence
path hashed it, sha1 where only the manifest recorded it. Two records
sharing either digest are one artifact. **A filename or path is never
identity (R9).**

**Historical filename references stay resolvable** through
`LegacyDocumentReference`. The reference resolves to every Placement of
that name:

- **ACTIVE** when those candidates hold one artifact (Belgrave: two folders,
  the same bytes).
- **AMBIGUOUS** otherwise (Braude 1981 citing `FT-Ch-Mongravey-2016.pdf`:
  three rows, two byte versions, two estates). It stays AMBIGUOUS until a
  reviewed decision (I22).

No tool may resolve one by first match.

## 8. Observation model

An `Observation` is one statement:

- from one **locus** of one **artifact** (or from a person, a legacy file
  or a cited critic);
- about one **subject** (Estate, Wine, Vintage or EstateWineRelationship)
  and one **field**;
- with `raw_value` as printed, a normalised `value`, `unit` and
  `qualifier`;
- with `extraction` {method, reader, code_commit, dirty}, `confidence` and
  `observed_at`;
- with a Provenance.

Rules:

- **Append-only, versioned by extractor**, like the evidence store. A
  re-extraction under a new reader adds observations and leaves the
  earlier ones.
- **Uniqueness:** (artifact, locus, subject, field, extractor). Two
  statements of the same field in one document, such as a table and a
  paragraph, are two observations.
- **Kinds of origin are explicit,** each with its Provenance kind:
  DOCUMENT, MANUAL, LEGACY_*, CITATION_UNVERIFIED, AUTHORITATIVE_SOURCE.
- **Normalisation keeps the raw form.**
  - Translation is a derivation on the canonical value.
  - Ranges are normalised but keep their raw text: Chevalier's "16-20"
    against "18".
  - Qualifiers (`under`) and units (H₂SO₄ / tartaric) are fields of the
    observation, not separate fields of the record.

The lifecycle:

```text
Artifact ─(extract, with reader + code state)→ Observation ─(group by subject × field)→ conflict detection
        ─→ Reconciliation (rule, status, every candidate) ─→ CanonicalValue (projection) ─→ generated views
```

## 9. Reconciliation model

A `Reconciliation` holds:

- `candidates`, every observation for (subject, field);
- `selected`;
- `rule` and `status`;
- `reason`, `resolver` and `decided_at`;
- `supersedes`, the reconciliation it replaces;
- a Provenance.

A new decision supersedes the old one; the old one remains.

| Status | Meaning |
|---|---|
| SINGLE | one candidate |
| AGREED | several candidates, one value |
| RESOLVED | a rule chose among disagreeing candidates |
| CONFLICT_OPEN | they disagree and no policy has chosen; a retained value may still be projected |
| DEFERRED | a decision is pending on domain grounds (C1, C2) |
| LEGACY_RETAINED | today's value kept by a named legacy rule |
| SUPERSEDED | replaced by a later reconciliation |

**First-writer-wins is not a rule.** The two rules that name what
`read-fiches.py` did, LEGACY_FIRST_IN_SORT_ORDER and
LEGACY_NEVER_OVERWRITE, exist only to describe today's winners honestly.
No new reconciliation may use them. Until a policy is set (D5), new
disagreements are CONFLICT_OPEN and the legacy value is retained, never
silently replaced.

The brief's example, in C6:

| Record | Value | Source |
|---|---|---|
| Observation | 80 | Badette 2020 EN sheet |
| Observation | 50 | Badette 2020 FR sheet |
| Observation | 80 | the legacy canonical value |
| Reconciliation | retains 80 | rule LEGACY_NEVER_OVERWRITE, status CONFLICT_OPEN |
| CanonicalValue | 80 | status LEGACY_RECORD_SOURCE_ONLY |

The 50 remains queryable.

## 10. Canonical-value model

A `CanonicalValue` is (subject, field) → value, with a status, a
reconciliation and a provenance. Today's data files become **generated
views** of canonical values (M7), and are regenerated byte for byte before
any consumer switches.

| Status | Meaning, and which current values it covers |
|---|---|
| SOURCED | chosen from document observations with resolvable artifacts |
| LEGACY_FIELD_SOURCE | `field-src.js`/`cuvee-src.js` names the field's document, resolvable to one artifact (5,844 grand-vin and 2,646 other-wine values name a document; the resolvable part of those) |
| LEGACY_AMBIGUOUS_SOURCE | the named document matches several artifacts (364 values: 301 + 63) |
| LEGACY_RECORD_SOURCE_ONLY | no field provenance; the record's `src` names its last writer, which is **not** asserted to be this field's source (Badette 2020: `src` is the FR sheet, which states 50, not 80) |
| LEGACY_UNSOURCED | no provenance at all |
| MANUAL_UNSOURCED | entered by hand from Phase 4 on, without a source |
| CITED_UNVERIFIED | a named critic or publication, no artifact (`overrides.js`) |
| DERIVED | computed: an aggregate (`ratings.js`), a parse (`wy`), a translation |

Today's values without field provenance are 6,647 of 12,491 grand-vin
values and 2,063 of 4,709 other-wine values. They are
**LEGACY_RECORD_SOURCE_ONLY or LEGACY_UNSOURCED, not MANUAL_UNSOURCED**:
`field-src.js` itself says such a field "was entered by hand or predates
the reader", so "manual" cannot be asserted. No source is fabricated
(I13).

## 11. Provenance model

One `Provenance` shape serves every layer: kind, artifact, locator, source,
quote, actor, code_state, at, derived_from, secondary, legacy_reference.

| Used by | Typical kinds |
|---|---|
| Observations | DOCUMENT, MANUAL, CITATION_UNVERIFIED, AUTHORITATIVE_SOURCE, LEGACY_* |
| State records | ESTATE_PUBLICATION, AUTHORITATIVE_SOURCE, LEGACY_UNSOURCED |
| Reconciliations | DERIVATION (derived_from the candidates), MANUAL |
| Canonical values | that of the selected observation |
| Quality findings | the detecting tool, with code state |
| Placements and attributions | LEGACY_MANIFEST, EVIDENCE_DECISION |

The Phase 2 standard (exact artifact, hash, reader, commit, dirty, status
hash) becomes the standard for every new record. Legacy kinds say exactly
what is known and no more. `secondary: true` marks Wikipédia-sourced
statements (Graves colours, mergers, 1987).

## 12. Quality model

A `QualityFinding` targets any record, never changes it, and has a status
(OPEN, ACKNOWLEDGED, RESOLVED, WONT_FIX). The kinds cover every anomaly
the audits found:

| Kind | Example |
|---|---|
| MISSING | Bouscaut's classified white (C5) |
| CONFLICT | Badette 2020 (C6); prose such as "Sources give the estate as 31, 40 or 41 hectares" |
| SUSPICIOUS_CHANGE | |
| IDENTITY_UNCERTAIN | v5 accepting `Cap-Castera-Petit-Verdot-2023-EN.pdf` as Castera's grand vin (C8) |
| EXTRACTION_FAILURE / SOURCE_FAILURE | the 20 name mismatches and the 103 missing files (C7) |
| ORPHAN_PROVENANCE | the 16 `cuvee-src.js` keys with no record |
| CROSS_SUBJECT_CITATION | Braude 1981 citing a Mongravey 2016 file (C7) |
| JUNK_VALUE | a letter's signature block in `cellar.js` |
| AMBIGUOUS_SEMANTICS | the estate-level `blend` (D1) |
| SCOPE_DISCREPANCY | the Phase 3.0 discrepancies, e.g. Les Erables' legacy role (C2) |

Missingness is *not* a finding by default. With an incomplete universe,
absence is UNKNOWN, and a MISSING finding is raised only against a
sourced expectation.

## 13. Attribution model

An `Attribution` holds `{artifact, estate?, wine?, vintage?, role?,
method, status, supersedes, provenance}`.

- **Many per artifact.** Group letters, négociant pages and multi-wine
  sheets each get one per subject (I14). A shared site's document is one
  artifact with an attribution per estate (C7 Belgrave/Rahoul), not one
  estate.
- **Optional parts stay null when unknown.** A null wine is "not
  established", **never the grand vin** (answers R1). A reader that
  cannot name the wine records the attribution without one, and nothing
  downstream may default it.
- **Status:**
  - PROPOSED for the reader's or a person's new claims;
  - LEGACY for the manifest's existing claims;
  - ACCEPTED only through a reviewed decision;
  - REJECTED and SUPERSEDED kept;
  - UNATTRIBUTED where a document was examined and could not be placed.
    That covers the 908, which stay representable without being resolved
    (I17).
- **Method** says how: DOCUMENT_TEXT, FILENAME, FOLDER, SITE_LIBRARY,
  PAGE_NAME, READER_GUARD, MANUAL, LEGACY_UNKNOWN. Folder attributions keep
  `FOLDER` (R8), so they can be weighed as the weak evidence they are.
- **Evidence decisions inform attributions,** linked through Provenance
  EVIDENCE_DECISION, but an ACCEPTED decision is never itself an
  attribution, still less a canonical fact (S1, I16).
- C1 shows the corrected form of the 15 Terrasses proposals: estate *and*
  wine, role UNKNOWN, status PROPOSED.

## 14. Identity and alias model

**Stable ids are minted once and opaque.** They are never derived from a
display name and never parsed (R12). Their spelling is Phase 4's (D4).

**`IdentityMap` is the bridge for every legacy key.** Its namespaces:

| Namespace | Holds |
|---|---|
| `estate` | all 470 canonical keys, including the 298 name-derived ones; every `ctx.estate` and `target_estate` in v1–v5; every manifest `estate` |
| `wine-by-slug` | `estate\|slug` |
| `wine-by-display-name` | `estate\|name`, which is how evidence `target_wine` and manifest `wine` name wines |
| `phase30-universe` | the universe's candidate ids |
| `manifest-row` | row index → Placement and Attribution |

A key maps to one stable id (ACTIVE), to candidates (AMBIGUOUS), or to a
retired id (RETIRED). **Keys are never deleted and evidence is never
rewritten (I2, I8, I19).** C8 resolves a v5 row for
`bourgeois-chateau-castera` and its `target_wine` "Château Castera" this
way.

**Names are records.**

- CURRENT, FORMER, ALIAS, SPELLING_VARIANT and SOURCE_RENDERING are
  NameRecords with validity.
- The Council's "Château PICHON-BARON" is a SOURCE_RENDERING of the estate
  the dashboard calls "Château Pichon-Longueville Baron" (C8).
- The universe's candidate mapping stays AMBIGUOUS until reviewed.

**Identity changes are transitions.** MERGED_INTO, SPLIT_FROM, RENAMED and
SUCCEEDED_BY carry a certainty.

- POSSIBLY_SAME / DISTINCT_FROM records *unresolved* sameness. Bellevue
  (Saint-Émilion) and Bellevue (Médoc) are two estates with one
  POSSIBLY_SAME transition, UNRESOLVED.
- **Name equality never merges.**
- A merge never deletes: both ids stay, the transition links them, and the
  IdentityMap entry of a merged-away id points through it.

## 15. Manifest decomposition

`data/sources.json` currently does three jobs. The design splits it by
question, not by copying it into one new file:

| Question | Structure | From these fields |
|---|---|---|
| What documents exist? | **Artifact** | `sha1`, `bytes`; sha256 from the evidence path |
| Where was each found, when, how? | **Locator + Placement** | `folder`, `file`, `url`, the retrieval half of `how`, the row index |
| What kind of document is it? | **ArtifactAssessment** | `role` = skip, page, group report, combined, unknown |
| What might it concern? | **Attribution** (many per artifact) | `estate`, `estateName`, `wine`, `slug`, `year`, `role` = grand, second, other, `colour`, the attribution half of `how`, `note` |
| What did the reader conclude? | **EvidenceLink** to the unchanged evidence store | — |
| What does the dataset accept? | **EstateWineRelationship, RoleAssignment, CanonicalValue**, never written from a manifest row | — |

The writers change accordingly:

- **Retrieval** (`harvest`, `crawl-pages`, `add-sheet`, `find-doc-urls`)
  writes Artifacts and Placements only.
- **Readers** write Observations, ArtifactAssessments and PROPOSED
  Attributions, never canonical files and never the register.

That ends the 13-tool cycle (R7), the canonical → manifest back-flow, and
dry runs that write (R6).

## 16. Current → target mapping

The full mapping is `docs/phase32-model.json` → `mapping`: 68 rows, each
`current → target → rule → risk`. `test-phase32` checks it covers every
field of every current structure, read at `a842bb7`. The decisive rows:

| Current | Target | Rule |
|---|---|---|
| estate files `id` / compact lists' name-derived ids | IdentityMap → Estate | mint; map; never recompute |
| estate files `second` | Wine + EstateWineRelationship + RoleAssignment SECOND_WINE | `'—'` → RoleAbsence; absent → nothing |
| estate files `growth`, `cls`, `wine` | ClassificationMembership on the classified Wine(s) | Graves "red and white" → two wines |
| estate files `owner` | Party + Ownership | year only where the string states one |
| `fiches.js` key `estate\|vintage` | Vintage(grand-vin Wine, year) | through IdentityMap |
| `fiches.js` values | LEGACY Observation → Reconciliation LEGACY_RETAINED → CanonicalValue | field-src where it names the field; the record's `src` never promoted |
| `fiches.js` `ttl`…`wtl`, `sugl`, `tau`, `wy`, `via` | derivation TRANSLATED / qualifier / unit / PARSED / channel | not separate facts |
| `field-src.js`, `cuvee-src.js` | LegacyDocumentReference → Provenance | ACTIVE or AMBIGUOUS, never a first match |
| `cuvees.js` wines | Wine + IdentityMap (slug, display name) + RoleAssignment | `other` → UNKNOWN |
| `sources.json` | Artifact, Placement, ArtifactAssessment, Attribution | §15 |
| `fiches-url.js`, `cuvee-url.js` | generated views | regenerated in M7 |
| `ratings.js` | CanonicalValue DERIVED | aggregate kept as such |
| `overrides.js` | CITED_UNVERIFIED observations; VintageStatement NOT_PRODUCED | its `blend` is reconciled, not trusted |
| `cellar.js`, `terroir.js`, `plantings.js` | Observations (with locus, language; terroir on the VINTAGE axis) | through LegacyDocumentReference |
| `data/field-conflicts.jsonl` | Reconciliation candidates | does not exist today |
| `data/evidence/`, proposals, `data/scope/` | EvidenceLink; PROPOSED attributions; AUTHORITATIVE_SOURCE statements | unchanged, separate |

**The six `estate|vintage` structures** are `fiches.js`, `field-src.js`,
`fiches-url.js`, `ratings.js`, `cellar.js` and `overrides.js`
(BDX_SCORES). They map through one rule: legacy estate → IdentityMap →
Estate → its grand-vin Wine (M2) → Vintage. So they move together or not
at all (M1).

## 17. Migration sequence

Every stage before M8 is **additive**: it writes new structures beside the
old and changes nothing that exists, so its reverse is to drop what it
added. M8 switches consumers one at a time behind switches, and M9
retires only after an archive tag. Each stage has a gate of invariants
(§18) that must pass before the next begins.

| Stage | Does | Reverse | Gate |
|---|---|---|---|
| **M0 Freeze** | tag; hash every canonical file, the manifest and the evidence index; pin today's semantics as tests (key shapes, role vocabularies, sparse-id rule, the meaning of `'—'`) | none needed | I19 |
| **M1 Stable identities** | mint ids; IdentityMap for every legacy key, including evidence's `target_wine` display names | drop | I1, I2, I3, I8 |
| **M2 Estate/Wine split** | a grand-vin Wine per estate; relationships for all wines; `estate\|vintage` → (Wine, Vintage) | drop | I4, I1, I3 |
| **M3 Roles and time** | RoleAssignments (`other` → UNKNOWN), RoleAbsences, memberships on wines, Ownership; every bound UNKNOWN unless a source states it; the universe as AUTHORITATIVE_SOURCE statements | drop | I5, I6, I7, I20 |
| **M4 Artifact identity** | Artifacts by digest; Placements per (path, digest); MISSING / NAME_MISMATCH for the 123; LegacyDocumentReferences for every bare filename | drop | I9, I10, I17, I18 |
| **M5 Observations** | LEGACY observations for every canonical value, with exactly-known provenance; EvidenceLinks (v4+ to bytes; v1–v3 through identity only); LEGACY attributions and assessments | drop | I8, I12, I13, I14, I15, I19 |
| **M6 Reconciliation** | a Reconciliation per (subject, field), LEGACY_RETAINED; re-extraction adds candidates and opens conflicts | drop | I11 |
| **M7 Canonical projection** | CanonicalValues, and from them **byte-identical** regenerations of today's files; any difference is a migration defect | stop projecting | I12, I13, I16 |
| **M8 Consumers** | app, readers and tools switch one by one; readers emit observations and PROPOSED attributions | flip the switch | I1, I3, I16 |
| **M9 Retirement** | archive tag; stop generating obsolete files; identity maps and legacy references stay for ever | restore from tag | I2, I8, I19 |

M7's byte-identical regeneration is the safety mechanism. The new layers
are proven to *contain* today's dataset before anything reads from them.

## 18. Migration invariants

Twenty-two invariants are defined. Each is an executable statement for
Phase 4, listed in full in `phase32-model.json` → `invariants`. The first
twenty are the brief's:

| # | Invariant | Where the design guarantees it |
|---|---|---|
| I1 | every current estate addressable | IdentityMap(estate) covers all 470 keys |
| I2 | every historical estate id resolvable | keys never deleted; RETIRED points through transitions |
| I3 | every current wine addressable | grand-vin Wine per estate; (estate, slug) map |
| I4 | grand vins become Wines without changing what they denote | one grand-vin Wine per estate, every `estate\|vintage` → it |
| I5 | no silent role | provenance on every assignment; `other` → UNKNOWN |
| I6 | UNKNOWN representable | WineRole.UNKNOWN; C1, C2 |
| I7 | history not overwritten | add-only state with validity |
| I8 | evidence interpretable | IdentityMap + display-name map; C8 |
| I9 | artifact hashes unchanged | digests copied, never recomputed over other bytes |
| I10 | file versions distinguishable | Placement per (path, digest); C7 |
| I11 | losers recoverable | candidates on every reconciliation; C6 |
| I12 | provenance kept where it exists | LegacyDocumentReference; LEGACY_FIELD_SOURCE |
| I13 | no fabricated provenance | record `src` not promoted; LEGACY_UNSOURCED; C6 |
| I14 | multi-estate documents | Attribution many-per-artifact |
| I15 | shared source ≠ shared identity | Source linked only via Placement/Attribution |
| I16 | proposals separate | PROPOSED attributions only; never read into state |
| I17 | the 908 representable | UNATTRIBUTED attribution; C7 |
| I18 | the 123 representable | Placement MISSING/NAME_MISMATCH + finding; C7 |
| I19 | v1–v5 not rewritten | EvidenceLink beside the store |
| I20 | no complete wine universe required | absence = UNKNOWN; nothing waits |

Two invariants are added by this design:

- **I21:** the authoritative universe reaches state only through
  reconciliation.
- **I22:** a legacy filename never resolves by first match.

## 19. Open decisions

These genuinely need a decision before or during implementation; the
design does not take them silently. Everything else above is decided.

| # | Decision | Why it is open | Default until decided |
|---|---|---|---|
| D1 | What the estate-level `blend` means, per estate (plantings, or usual assemblage) | domain review; one field holds both today | AMBIGUOUS_SEMANTICS observation |
| D2 | Haut-Bages Averous → Echo: one wine renamed, or a succession of two | the source's "change d'identité pour devenir" supports both | SUCCEEDED_BY, UNRESOLVED (C3) |
| D3 | Storage and format of the normalised layers | implementation (Phase 4) | — |
| D4 | The concrete syntax of minted ids | implementation; the rules are fixed | — |
| D5 | The reconciliation policy for new conflicts: estate sheet vs trade copy, language versions, document vs authoritative universe | policy, with domain judgement (Badette EN/FR, Chevalier EN/FR) | CONFLICT_OPEN; legacy value retained |
| D6 | Splitting the 85 manifest `how` texts into retrieval method and attribution method | a reviewed table | LEGACY_UNKNOWN, text kept |
| D7 | How the app consumes the layers in M8: regenerated files or a new loader | implementation | regenerated files (M7) |
| D8 | Names for classified wines no source names (four Graves whites) | research, or accept UNKNOWN | name_status UNKNOWN (C5) |

Settled here rather than left open, as the brief suggested might be needed:

- **Who owns temporal role state?** The RoleAssignment, on the
  relationship.
- **Is Vintage an entity?** Yes, a composite (wine, label).
- **How are duplicate artifacts represented?** One Artifact, several
  Placements.
- **How are observations keyed?** (artifact, locus, subject, field,
  extractor).
- **How do canonical fields map to observations?** One reconciliation per
  (subject, field).
- **How are manual values represented?** MANUAL observations, with
  MANUAL_UNSOURCED from Phase 4 and LEGACY_* before.
- **How are memberships exposed?** On wines, with estate-level views
  derived.
- **Source and publisher:** Source, operated by a Party.

## 20. Risks

| Risk | Mitigation in the design |
|---|---|
| The six `estate\|vintage` structures rekeyed inconsistently | one mapping rule through IdentityMap; M7 byte-identical regeneration |
| A name-derived id "corrected" during migration | ids mapped, never recomputed; I2 |
| Legacy values given better provenance than they have | five legacy statuses; record `src` never promoted (I13, C6) |
| Legacy `other` read as a real role | `other` → UNKNOWN with legacy_term (I5) |
| A wine-less attribution defaulting to the grand vin again | null wine stays null; no consumer may default it (R1, C1) |
| Ambiguous filenames resolved by first match | LegacyDocumentReference AMBIGUOUS (I22) |
| Overwritten bytes lost from history | Artifact with sha1 and `bytes_available: false` |
| Evidence made uninterpretable | EvidenceLink beside the store; maps for ids and display names (I8, I19) |
| The universe silently promoted into canonical | AUTHORITATIVE_SOURCE statements reconciled like others (I21) |
| Migration blocked on the incomplete wine universe | UNKNOWN is a state (I20) |
| Reconciliation policy decided ad hoc during migration | CONFLICT_OPEN with the legacy value retained until D5 |
| Scale: one observation per legacy value (≈17,200 for `fiches.js` and `cuvees.js`, plus estate-level values) and per re-extracted statement | storage choice (D3) must handle it; append-only versioning as in the evidence store |
| Fixtures mistaken for data | marked "WORKED EXAMPLES, NOT DATA"; nothing loads them |

## 21. Phase 4 implementation prerequisites

1. Decide D3, D4 and D7 (storage, id syntax, app consumption) before M1.
2. Decide D5, at least a first policy, before re-extraction feeds M6.
3. Build M0 first: the freeze tag and the semantic pin tests, so every
   later stage is checked against today.
4. Implement each invariant as a test before the stage it gates.
5. A provenance-safe extractor that emits Observations, built on
   `provenance.py`'s exact lookup and hashing, before any re-extraction.
6. The D6 table for the 85 `how` texts before M4.
7. Retire the eleven first-match lookups and the ungated writers
   (`promote-urls.py`, `read-sheets.py`'s pre-gate write) in the tools that
   survive M8, or route them to the new layers.
8. Keep Phase 2's proposals (Echo, Terrasses, Murets) out of every
   migration step. They enter the new model as PROPOSED attributions and
   DEFERRED reconciliations, as C1 and C2 show, and are decided there.

**SAFE — NORMALIZATION ARCHITECTURE COMPLETE**
