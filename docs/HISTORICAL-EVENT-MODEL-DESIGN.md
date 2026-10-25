# Historical event model — design

Gate: **SAFE — HISTORICAL EVENT MODEL DESIGNED — READY FOR IMPLEMENTATION**

This is a design document. **No model, data, evidence, provenance, application, generated file or
test changed**, and no historical fact was added to illustrate it. The scenarios in §13 are
conceptual: no row was inserted.

Baseline: `18918d6`, 27 suites, 740 checks.

---

## 1. Problem statement

The product now says precisely what it knows about a wine **now**:

- its current name, rank, classification and appellation;
- the years with a sheet on file, and the years recorded as not made;
- that dates of adoption and earlier names are **not recorded** (Phases 6.7–6.9).

To say more, the model must hold **dated historical facts**:

- renames and successions;
- wines introduced or discontinued;
- second-wine and rank changes;
- classification and appellation changes;
- ownership, estate-name and location changes;
- document revisions;
- explicit "not made" statements;
- the claims that disagree about any of these.

**The risk is not too little history but invented history.** A document date is not an event
date. A missing sheet is not a discontinuation. A current value is not a historical one. The newer of
two documents is not automatically right.

The design must preserve those distinctions, keep every competing claim, and leave unresolved
identities unresolved.

**The conclusion of this design:** the Phase 3.4 contract already holds almost all of the needed
structure. What is missing is a precise **claim layer** (what a source says about time) and
**reconciliation of dated records**. The architecture is an extension, not a new model.

## 2. Existing-model constraints

Re-read for this design:

- Phase 3.1 (structural and domain audit);
- Phase 3.2 (normalization architecture and data model);
- the Phase 3.4 contract and its review (`docs/PHASE-3.4-DOMAIN-MODEL.md`, `docs/phase34-model.json`);
- the Phase 4 model as built;
- Phase 6.0, 6.2, 6.4, 6.7, 6.8 and 6.9.

**What already exists, and must be kept:**

| Construct | Where | What it already gives |
|---|---|---|
| **TemporalBound** | value type | kind (EXACT, APPROXIMATE, NO_LATER_THAN, NO_EARLIER_THAN, UNKNOWN, OPEN, NOT_APPLICABLE; inclusive), **axis** (CALENDAR, VINTAGE), value, precision (DAY … DECADE, VINTAGE, NONE), **basis** (a provenance, required whenever a value is given) |
| **Validity** | value type | valid_from and valid_to bounds, plus `as_of` for an OPEN end |
| **State records with validity** | EstateWineRelationship, RankAssertion, RankAbsence, WineDescriptor, ClassificationEdition (status IN_FORCE, SUPERSEDED, ANNULLED, UNKNOWN), ClassificationMembership, Appellation, AppellationMembership, Ownership, EstateLocation, SourceEstateRelationship | every time-dependent fact is already an interval record |
| **NameRecord** | identity | CURRENT, FORMER, ALIAS, SPELLING_VARIANT, SOURCE_RENDERING, MARKET_ALIAS, with validity |
| **IdentityTransition** | identity | RENAMED, SUCCEEDED_BY, SPLIT_FROM, MERGED_INTO, POSSIBLY_SAME, DISTINCT_FROM; `at` (one TemporalBound), certainty (CONFIRMED, PROBABLE, UNRESOLVED), source_term, provenance; with the required-evidence table for each kind |
| **VintageStatement** | state | NOT_PRODUCED, PRODUCED, per vintage |
| **ArtifactDate** | document | PDF_METADATA, UPLOAD_PATH, HTTP_LAST_MODIFIED, STATED_IN_TEXT, YEAR_IN_TITLE_OR_URL, RETRIEVED |
| **ArtifactRelation** | document | REVISION_OF, LANGUAGE_VERSION_OF, …; status CANDIDATE, CONFIRMED, REJECTED |
| **Observation** | observation | subject, field, raw value, value, qualifier, lang, artifact, locus, extraction, observed_at, **asserted_at** (when the document speaks), **subject_status** (ESTABLISHED, PROPOSED, UNRESOLVED) |
| **Reconciliation** | reconciliation | all candidates kept (I11), a named rule, status SINGLE, AGREED, RESOLVED, CONFLICT_OPEN, DEFERRED, LEGACY_RETAINED, SUPERSEDED |
| **Provenance** | cross-cutting | kind (DOCUMENT, EVIDENCE_DECISION, ESTATE_PUBLICATION, AUTHORITATIVE_SOURCE, CITATION_UNVERIFIED, DERIVATION, MANUAL, LEGACY_…), artifact, locator, source, **quote**, actor, at |
| **QualityFinding** | cross-cutting | CONFLICT, IDENTITY_UNCERTAIN, … with OPEN, ACKNOWLEDGED, RESOLVED |

**Rules already in force:**

- **I7:** records are added with validity, never updated in place.
- **I11:** losing observations stay recoverable.
- **I20:** absence is UNKNOWN.
- **I21:** authoritative statements reach state only through reconciliation.
- **Temporal rules 1–5:**
  - wine facts use the VINTAGE axis and institutional facts the CALENDAR axis;
  - three dates are never confused;
  - "today" is as of `asserted_at`;
  - a bound never claims more precision than its source.
- **Identity:** no identity resolved by inference.

**Decisions not adopted, which this design must not presume:**

- **D2:** rename versus succession, for Echo. Recommended RENAMED, PROBABLE.
- **D5:** the conflict policy. Recommended: no automatic winner across languages or claimants, and
  within one document the later revision wins. **Not adopted.** Until it is, no historical
  reconciliation may use an automatic rule.

**What the data holds today (measured):**

| Holding | Count |
|---|---|
| validity on all 3,917 state records and names | from UNKNOWN, to OPEN |
| IdentityTransition | 0 |
| FORMER names | 0 |
| Ownership | 0 |
| ArtifactDate | 0 |
| ArtifactRelation | 0 |
| classification editions | 6, each the current one, IN_FORCE, dated by year |
| VintageStatement NOT_PRODUCED | 18 |

**The gaps this design fills:**

1. An Observation cannot yet say **when** something held. It carries `asserted_at` but no claimed
   validity, so "named La Parde from 1967" has nowhere to put "from 1967".
2. A state record's **bounds are not reconciled**. Reconciliation works per (subject, field) for
   canonical values; a NameRecord's start is not traceable to the claims behind it.
3. `IdentityTransition.at` is a **single bound**. "Between 2005 and 2008" needs an occurrence window.
4. No construct says **"these two names are related, and how is not established"**. POSSIBLY_SAME
   asserts possible identity, not an unspecified relation.

## 3. Event, state, claim and reconciled fact

| Concept | Definition | Persisted as | Why |
|---|---|---|---|
| **Historical claim** | a source's assertion about a state or an event, with its own wording, date and locus | **Observation**, extended (§11) | Observations already keep individual statements, their language, document date and subject status. A claim is an observation whose value has a time. |
| **Historical state** | a value that holds during an interval | **the existing state records and NameRecords**, with validity | Every kind of history in scope is already an interval record. Adding records (I7) is how history is kept. |
| **Historical event** | something that happened at a point or within a window | **derived, except three primary kinds** (below) | Most "events" are the boundary between two states. A rename is where one NameRecord's validity ends and the next begins, and storing the boundary separately would duplicate it and let the two drift. |
| **Reconciled historical fact** | the project's current conclusion | **a state record or transition, with each value-bearing bound backed by a Reconciliation** | The conclusion is the record. The Reconciliation shows which claims support it, which contradict it, and the rule or decision that chose. |

**Primary events.** Three events are persisted in their own right, because they are **not** the
boundary of a single state:

1. **IdentityTransition:** it relates two identities, or two names of one identity, and its kind
   (rename or succession) is a fact neither state record carries.
2. **VintageStatement:** a statement about one vintage (NOT_PRODUCED, PRODUCED). It is a point and
   has no interval to bound.
3. **ArtifactRelation REVISION_OF:** a document event, about the evidence itself.

**Everything else is a state transition, and is derived:**

- name changes;
- rank changes;
- classification, appellation and ownership changes;
- estate–wine relationship changes;
- location changes.

```text
                    ┌────────────── claims (Observation + claimed_validity) ──────────────┐
 Artifact ─ Placement ─ Observation ──┬─ Reconciliation (per record bound / existence) ─┐ │
     │ ArtifactDate (document date)   │   candidates: every claim, with a disposition    │ │
     │                                └─ Reconciliation (transition kind and window) ──┐ │ │
     ▼                                                                                 ▼ ▼ │
 asserted_at  ≠  validity / occurrence window  ≠  Placement retrieval date        State records
                                                                                 NameRecord, RankAssertion,
                                                                                 Membership, Ownership …
                                                                                 IdentityTransition
                                                                                 VintageStatement
                                                                                       │
                                                                     derived on demand ▼
                                                                  state at T · changes between T1 and T2
```

## 4. Temporal semantics

Every time in the model is a **TemporalBound** or a pair of them. Nothing is a bare `start_year`.

| Meaning | Representation |
|---|---|
| exact date | `EXACT`, CALENDAR, value `2022-09-08`, precision DAY |
| year only | `EXACT`, CALENDAR, `2018`, YEAR. Precision says a year; a day is never implied. |
| vintage | `EXACT`, VINTAGE, `2008`, VINTAGE |
| before year *Y* | `NO_LATER_THAN` *Y−1* on the claim's axis (inclusive bounds), with the source's wording kept in `basis` |
| after year *Y* | `NO_EARLIER_THAN` *Y+1* |
| "in or before *Y*" | `NO_LATER_THAN` *Y* |
| date range for an **event** ("between 2005 and 2008") | an **occurrence window** {earliest: `NO_EARLIER_THAN 2005`, latest: `NO_LATER_THAN 2008`} (§11) |
| date range for a **state** | Validity {valid_from, valid_to} |
| open-ended | valid_to `OPEN`, with Validity.as_of = the latest source's `asserted_at` |
| unknown start or end | `UNKNOWN`: a bound exists and is not known |
| no such bound | `NOT_APPLICABLE` (a point statement) |
| approximate | `APPROXIMATE` with a value and precision (DECADE for "the 1970s") |
| "since", "for over 30 years" | `UNKNOWN`, the wording kept as the basis quote (contract rule 5) |
| **source publication date** | ArtifactDate (one or more kinds per artifact) → `Observation.asserted_at` |
| **retrieval date** | Placement (and ArtifactDate RETRIEVED) |
| **event date** | the transition's occurrence window |
| **effective date** | the state's validity on the axis it takes effect on. For example: "classification from the 2018 vintage" is valid_from `EXACT VINTAGE 2018`, while the announcement's calendar date belongs to the claim's `asserted_at`, or to the edition's CALENDAR validity. |

**When a source said something is not when it happened.**

- **The source date is `Observation.asserted_at`**, from ArtifactDate. A 2008 sheet that calls the
  wine Echo gives `asserted_at ≈ 2008` and supports *"named Echo as of 2008"*. That is a claim that
  the name's validity covers 2008. It is **not** a claim that the rename happened in 2008.
- **What the start bound can say.** From that sheet alone, at most valid_from `NO_LATER_THAN VINTAGE
  2008`, and only where the sheet is for that vintage.
- **The rename date needs a statement about the change.** "In 2008, a new identity was given to the
  second wine" fixes the window. A document dated 2008 does not.

**The two axes are never converted automatically.** "Renamed in 2007" (CALENDAR) and "from the 2008
vintage" (VINTAGE) can both be true. A decision announced in 2007 can take effect with the 2008
vintage. They are kept on their own axes, and comparing them is a reconciliation question (§8), not
arithmetic.

## 5. Event taxonomy

There is a controlled vocabulary for **querying and display**. Each type says how it is represented;
there is no `HISTORICAL_EVENT` table with free JSON.

| Event type | Represented as | Persisted? | Notes |
|---|---|---|---|
| `WINE_NAME_CHANGE` | boundary between two NameRecords of one Wine; **with** an IdentityTransition RENAMED when the source states continuity | NameRecords yes; the transition yes; the "event" derived | without a transition, two dated names are just two names (§6) |
| `WINE_SUCCESSION` | IdentityTransition SUCCEEDED_BY between two Wines | yes | distinct from rename: two identities |
| `WINE_INTRODUCED` | the earliest established `valid_from` of the wine's PRODUCED_BY EstateWineRelationship, **only** when that bound has a basis saying so ("first vintage", "créé en") | derived from the bound | **never** from the earliest sheet on file |
| `WINE_DISCONTINUED` | an established `valid_to` on that relationship, with a basis saying so ("last vintage", "discontinued") | derived | never from the latest sheet on file |
| `WINE_ROLE_CHANGE` | boundary between RankAssertions (or a RankAbsence) for one relationship and claimant | derived | per **claimant**: a producer's ranking and the dataset's are separate histories |
| `SECOND_WINE_CHANGE` | the estate-range SECOND tier passing from one wine's RankAssertion to another's | derived, query-level | a specialisation of the above, worth naming because the product asks for it |
| `WINE_ESTATE_RELATIONSHIP_CHANGE` | boundary of an EstateWineRelationship (by kind) | derived | |
| `ESTATE_NAME_CHANGE` | boundary between an Estate's NameRecords, with an IdentityTransition RENAMED on the Estate | as for wines | |
| `CLASSIFICATION_CHANGE` | a wine's ClassificationMembership in consecutive editions of one scheme differs (rank, presence or absence); edition status changes (SUPERSEDED, ANNULLED) | memberships and editions yes; the change derived | absence from a **recorded** later edition is evidence; absence of a recorded edition is not |
| `APPELLATION_CHANGE` | boundary between AppellationMemberships of a wine, or an Appellation's own validity (created, renamed) | derived | |
| `OWNERSHIP_CHANGE` | boundary between Ownership records of an estate | derived | |
| `LOCATION_CHANGE` | boundary between EstateLocation records | derived | rarely real; most differences are geocoding, which stays a quality finding |
| `DOCUMENT_REVISION` | ArtifactRelation REVISION_OF (CONFIRMED) | yes | about evidence, not about the wine |
| `NOT_MADE` | VintageStatement NOT_PRODUCED; a RankAbsence on the VINTAGE axis for "no second wine this year" | yes | point facts, the two scoped differently (§13) |

**Rejected:**

- **one generic `HISTORICAL_EVENT` with arbitrary JSON:** it duplicates state boundaries and has no
  schema to validate;
- **a finer taxonomy** (label change, price change, blend change, team change): either not identity
  history or vintage observations (§14).

## 6. Historical identity semantics

| Relationship | Meaning | Representation | Evidence required (contract table, kept) |
|---|---|---|---|
| **Rename** | same identity, new name | one Wine; NameRecord FORMER then CURRENT, with bounds; IdentityTransition `RENAMED` (from = to = the Wine) | the source names one wine as the continuing subject under a new name |
| **Succession** | the old wine ends, another begins | two Wines; `SUCCEEDED_BY`; the old relationship's valid_to and the new one's valid_from | the source presents the new wine as replacing a discontinued one, without continuity |
| **Rebranding / label change** | the same wine, presentation changed, name **unchanged** | **not an identity change**: an observation at most (Coutet: "Opalie s'habille de la même étiquette", 3.4 §7) | — |
| **Alias** | two names for one wine, no transition | NameRecord ALIAS or MARKET_ALIAS, each with its own validity | a source using both for one wine |
| **Possibly the same** | same or near-same name, no statement either way | `POSSIBLY_SAME`, certainty UNRESOLVED | existing contract |
| **Related, relationship not established** | evidence connects two names, but not as rename, succession or alias | **new kind `RELATED_UNSPECIFIED`**, certainty UNRESOLVED (open decision O3) | a source mentioning both in one context, without saying how they relate |
| **Distinct** | explicitly not the same | `DISTINCT_FROM` | a statement, or authoritative separate listings |

**Unresolved stays unresolved.** A transition with certainty UNRESOLVED never moves names between
wines, never ends a validity, and is never shown as a change (only as "a relationship is recorded but
not established").

PROBABLE requires a recorded decision (as D2 would be) before the product presents it as a change.

## 7. Evidence linkage

Every historical record reaches its evidence through objects that already exist.

| Need | Path |
|---|---|
| source document | Observation.artifact → Artifact (bytes, sha256) |
| exact source artifact | the artifact's sha256 (proven, Phase 4) |
| document date | ArtifactDate (kind and value), copied into Observation.asserted_at |
| publication date | ArtifactDate STATED_IN_TEXT or PDF_METADATA; several may disagree and all are kept |
| retrieval date | Placement, and ArtifactDate RETRIEVED |
| source URL | Placement → Locator (URL) |
| the statement | the Observation itself (raw_label, raw_value, lang, locus) |
| passage or quote | `Provenance.quote` and `Observation.locus`. Both fields exist. They stay empty until extraction can fill them, and the design does not require them. |
| extraction method | Observation.extraction (method, version) |
| claimant and source identity | Observation.source → Source; RankAssertion.claimant (PRODUCER, CLASSIFICATION_BODY, PRESS, TRADE, DATASET); Provenance.kind |
| the record's support | each value-bearing bound's `basis` → a Provenance of kind EVIDENCE_DECISION or DERIVATION that names its Reconciliation |

**The hard cases:**

- **Two documents disagree:** two Observations, both candidates of one Reconciliation (§8).
- **Two languages disagree:** two Observations with `lang`; an ArtifactRelation LANGUAGE_VERSION_OF
  links the documents. D5's recommendation is that there is no winner across languages.
- **No publication date:** `asserted_at` UNKNOWN. The claim still counts, but it cannot anchor
  "today" wording (contract rule 4).
- **A document shared by several estates:** Attribution, many per artifact, with subject_status. A
  claim's subject is resolved per estate (Phase 6.4, "a group footer names every property").
- **The same claim in several documents:** one Observation per document. Agreement is visible as
  several candidates with the same value (AGREED), not merged.

## 8. Competing claims

**The example.** Document A says "renamed in 2007", and Document B says "the new name was introduced
in 2008".

```text
Claim A  Observation{subject: wine W, field: transition.RENAMED, value: {from_name, to_name},
                     claimed_window: {earliest: EXACT CALENDAR 2007, latest: EXACT CALENDAR 2007},
                     asserted_at: <A's date>, artifact: A, mode: EXPLICIT}
Claim B  Observation{subject: wine W, field: name, value: "<new name>",
                     claimed_validity: {valid_from: EXACT VINTAGE 2008},
                     asserted_at: <B's date>, artifact: B, mode: EXPLICIT}

Reconciliation{subject: IdentityTransition t1, field: "occurred",
               candidates: [A: CONSISTENT?, B: CONSISTENT?], rule: —, status: CONFLICT_OPEN | DEFERRED}
```

**What the system does:**

- **Both claims are kept** as Observations. Neither is deleted or merged (I11).
- **No automatic winner.** The newer document does not win: MOST_RECENT_DOCUMENT is in the
  vocabulary, but D5 is not adopted, so no historical reconciliation may use it unasked.
- **The axes are compared, not converted.** A's 2007 is on the CALENDAR axis and B's 2008 on the
  VINTAGE axis. A reviewer may record that the two are **consistent** (announced in 2007, effective
  with the 2008 vintage) and resolve `MANUAL_DECISION`. The recorded fact is then
  `occurred: VINTAGE 2008`, plus the rename's CALENDAR window from A.
- **Until then** the transition's window stays UNKNOWN, with status CONFLICT_OPEN or DEFERRED.

**Claim identity:** the Observation id, minted and stable. The same statement in a second document is
a second claim.

**Candidate disposition.** A small extension, §11: each candidate in a Reconciliation carries one of:

| Disposition | Meaning |
|---|---|
| `SELECTED` | it is the chosen value |
| `CONSISTENT` | it agrees with the selection without being it |
| `CONTRADICTS` | it disagrees with the selection, and is kept |
| `REJECTED` | judged wrong, with a reason; the evidence stays |
| `NOT_ASSESSED` | — |

**Claim status** is derived, not stored. The brief's vocabulary maps to it:

| Brief | Derived from |
|---|---|
| UNREVIEWED | in no reconciliation, or NOT_ASSESSED |
| SUPPORTED | SELECTED or CONSISTENT |
| CONTESTED | the reconciliation is CONFLICT_OPEN |
| REJECTED | REJECTED |
| RECONCILED | the reconciliation is RESOLVED or AGREED |

The project's existing ReconciliationStatus stays the authority.

**The relationship between claims** is that they are candidates of the same reconciliation. When
documents are versions of one another, an ArtifactRelation (REVISION_OF, LANGUAGE_VERSION_OF) also
links them.

**The optional canonical conclusion** is the state record or transition whose bound cites the
reconciliation. If nothing is concluded, there is no record, and the product says "not established".

## 9. Uncertainty and confidence

**There is no single `confidence` number.** Observation.confidence exists from the legacy migration
and is not used for history. Four separate properties:

| Dimension | Property of | Represented by |
|---|---|---|
| **evidence strength** | the **claim** | provenance kind (ESTATE_PUBLICATION > TRADE copy > CITATION_UNVERIFIED …); claimant; extraction method and status (NEEDS_OCR, image-only); **assertion mode** (§11: EXPLICIT, the source states it; IMPLIED, it follows from the document's framing, e.g. a sheet's title year); subject_status |
| **reconciliation status** | the **reconciled bound or record** | ReconciliationStatus (SINGLE, AGREED, RESOLVED, CONFLICT_OPEN, DEFERRED, …) and rule |
| **temporal precision** | each **bound** | BoundKind and DatePrecision. "EXACT VINTAGE 2008" and "NO_LATER_THAN 2008" are different knowledge. |
| **identity confidence** | the **relationship** | IdentityTransition.certainty (CONFIRMED, PROBABLE, UNRESOLVED); EstateWineRelationship.status (ESTABLISHED, PROBABLE, CLAIMED, DISPUTED, ENDED_UNKNOWN_WHEN) |

They combine only for display, by rule. For example: a change is shown as established only if its
bound is reconciled, it is not CONFLICT_OPEN, and its identity certainty is CONFIRMED (or PROBABLE
with a recorded decision). They are never multiplied into one score.

## 10. Temporal materialization and queries

**Store intervals and primary events; derive snapshots and diffs.**

- **No per-vintage copies.** Duplicating every fact into every vintage would create 44× the records,
  and copies that can disagree with their source.
- **No stored event table for boundaries.** A boundary is computable from adjacent intervals.

**A deterministic evaluator** (in `tools/model_reader.py`, like `project()`):

```text
holds(record, T, axis) →  YES        T lies inside both bounds, determined on the record's axis
                          NO         T lies outside a determined bound
                          UNDETERMINED  the bound needed is UNKNOWN, APPROXIMATE across T, or on the other axis
state_at(subject, T, axis) = for each record kind: records with holds = YES,
                             plus the UNDETERMINED ones, listed as such (never dropped, never promoted)
changes(subject, T1, T2, axis) = records whose holds goes YES→NO or NO→YES between T1 and T2,
                             plus IdentityTransitions and VintageStatements whose window lies within
```

Its output can be generated per wine for the app (as `wine-established.js` is, Phase 6.7), so the
page never evaluates bounds itself.

**The product queries:**

| # | Question | Answer from |
|---|---|---|
| 1 | What names has this wine had? | NameRecords of the Wine (CURRENT, FORMER, ALIAS), with validity; RENAMED transitions into it |
| 2 | When is each name established? | each NameRecord's bounds and their reconciliations |
| 3 | What historical changes are established? | `changes()` over the record kinds, keeping only reconciled, non-conflicting bounds, plus transitions CONFIRMED (or PROBABLE with a decision) |
| 4 | What changes are disputed? | reconciliations CONFLICT_OPEN or DEFERRED on the subject's records and transitions; transitions UNRESOLVED |
| 5 | The current established name at date or vintage T? | `state_at(W, T)`, names → YES, or "not established" when only UNDETERMINED |
| 6 | What changed between two years? | `changes(W, T1, T2)` |
| 7 | Which source supports a claim? | bound basis → Reconciliation → candidates → Observation → Artifact, Placement, ArtifactDate |
| 8 | Which claims remain unresolved? | Observations with claimed time in no reconciliation, or NOT_ASSESSED; reconciliations CONFLICT_OPEN or DEFERRED |
| 9 | Explicitly recorded as not made? | VintageStatement NOT_PRODUCED for the vintage (and RankAbsence on the VINTAGE axis for a rank) |
| 10 | Explicitly stated, or inferred from documents? | the supporting claims' assertion mode (EXPLICIT against IMPLIED), and whether a bound's basis is DERIVATION |

## 11. Mapping to existing entities

**Extend rather than replace.** Four small extensions, one possible enumeration value, and no new
entity:

| Concept | Extends | New entity? | Migration | Backward compatible? |
|---|---|---|---|---|
| historical claim | **Observation** + `claimed_validity` (Validity, optional) + `claimed_window` (occurrence window, optional) + `assertion_mode` (EXPLICIT, IMPLIED; optional) | no | schema only; existing rows have none | yes: optional fields, absent today |
| claim about a transition | Observation with `field` `transition.<KIND>` and value {from, to} (subjects: the Wine or Estate) | no | — | yes |
| event occurrence window | **IdentityTransition** `at` → `occurred` {earliest, latest} (TemporalBound each) | no | rewrite `at` as earliest = latest = at (0 rows today) | yes |
| reconciliation of a dated record | **Reconciliation** whose subject may be a state record, NameRecord or IdentityTransition id, with `field` `valid_from`, `valid_to`, `exists`, `kind` or `occurred` | no | none (vocabulary of subjects widened) | yes |
| candidate disposition | **Reconciliation.candidates[]**: {observation, disposition, reason?} | no | existing candidates read as SELECTED, or NOT_ASSESSED for losers | yes |
| bound backed by its reconciliation | **TemporalBound.basis** → Provenance (EVIDENCE_DECISION or DERIVATION) naming the reconciliation | no | — | yes (basis already required) |
| unspecified relation | **TransitionKind** + `RELATED_UNSPECIFIED` | no (one value) | — | yes |
| primary events | IdentityTransition, VintageStatement, ArtifactRelation: **as they are** | no | — | yes |
| state history | the existing state records and NameRecords, **added with validity** (I7) | no | — | yes |
| document dates | **ArtifactDate**, populated (0 rows today) | no | an extraction stage | yes |
| snapshots and diffs | derived (`model_reader`), optionally a generated app file | no persisted entity | — | yes |

**Can claims be Observation plus Reconciliation alone?** Yes, with the two optional fields. A claim
without a time is an ordinary observation; a claim with a time is the same row with
`claimed_validity` or `claimed_window` set. A separate claim entity would duplicate Observation's
provenance, language, locus and subject status.

## 12. Migration strategy

Each stage is independently testable and reversible, in the Phase 4 manner: `migrate.py` stages with
`--check` and `--revert`, a model snapshot per stage, and the 27-suite baseline at each.

| Stage | Does | Test | Revert |
|---|---|---|---|
| **M0** | nothing in behaviour: this design, plus a schema validator for the new optional fields **with no data** | the model byte-identical; `migrate --check`; all suites | n/a |
| **M1** | add the structures: Observation optional fields, IdentityTransition `occurred`, Reconciliation candidate disposition and widened subject vocabulary, TransitionKind `RELATED_UNSPECIFIED`, the `holds`/`state_at`/`changes` evaluator. **No rows.** | schema checks; the evaluator on fixtures **in test code only** (never in `data/model`); the model rows byte-identical | drop the fields and the evaluator |
| **M2** | link existing evidence: populate **ArtifactDate** from PDF metadata, upload paths and HTTP Last-Modified (3.4 §7), and `asserted_at` on existing observations. **No claims, no state changes.** | every ArtifactDate has a basis; no state, NameRecord, transition or canonical value changed (group hashes) | delete the ArtifactDate rows; reset `asserted_at` |
| **M3** | reconcile **only explicitly approved facts**, one recorded decision each (as D2): claim Observations from the cited artifacts, a Reconciliation (MANUAL_DECISION), then the dated record or transition. Nothing automatic until D5 is adopted. | per fact: claims cite artifacts; each bound's basis reaches a reconciliation; no record without provenance; the competing claims present; the current facts unchanged except as decided | revert the decision's rows (stable ids; the decision log names them) |
| **M4** | expose in the app: generated per-wine history (as Phase 6.7) and display; established changes, disputed ones and "not established" kept apart | the Phase 6.x equivalence method; the history shown equals the evaluator's output; nothing UNDETERMINED or UNRESOLVED shown as a change | remove the generated file; restore the page |

## 13. Real-project design scenarios

These are conceptual only. **None was inserted.**

### A. Echo de Lynch-Bages and Haut-Bages Averous (P7, D2 not adopted)

**Claims** (artifacts already in the harvest):

- EN: "In 2008, a new identity was given to the second wine, under the name 'Echo de Lynch-Bages'";
- FR: "il change d'identité pour devenir …".

As Observations, both have `field` `transition.RENAMED` and `claimed_window` VINTAGE 2008, and the
two documents are linked as LANGUAGE_VERSION_OF.

**If D2 is adopted as RENAMED**, the records would be:

- one Wine;
- NameRecord FORMER "Haut-Bages Averous", valid_to `NO_LATER_THAN VINTAGE 2007`;
- NameRecord CURRENT "Echo de Lynch-Bages", valid_from `EXACT VINTAGE 2008`;
- IdentityTransition RENAMED, occurred VINTAGE 2008, certainty PROBABLE (CONFIRMED by the decision);
- each bound's basis → its reconciliation (AGREED: two languages, one value).

**Until then:** nothing. The page keeps "not recorded" (Phase 6.7).

### B. La Parde and Haut-Bailly II (P11; Phase 6.3 "Not established")

**Claims:**

- the 2018 sheet: "La Parde de Haut-Bailly, né en 1967, se voit renommer" → `transition.RENAMED`,
  window VINTAGE 2018;
- a FORMER-name claim, valid_from `EXACT CALENDAR 1967` ("né en 1967", the birth of the wine, not of
  the name's use on the VINTAGE axis).

**The estate file's `second` string** "La Parde de Haut-Bailly" remains an identity-map entry
AMBIGUOUS (Phase 6.3). Reconciling the rename is a separate decision. Until it is taken, the
transition, if recorded at all, is `RENAMED` UNRESOLVED or `RELATED_UNSPECIFIED`, and never shown as
a change.

### C. Lions de Batailley (Phase 6.2, CONFLICT)

**Two current claims, no dates:**

- the estate file: RankAbsence SECOND, claimant DATASET, from UNKNOWN;
- the wine list: RankAssertion SECOND, claimant DATASET.

That is a **contemporaneous** conflict, not a historical sequence. The model keeps it as the existing
CONFLICT finding. **No interval is invented** to make them sequential (for example "absent before
2014"): the sheets on file 2014–2017 are evidence of the wine, not of when it became second.

### D. Corbin 2022, "no second wine was produced this year" (P6)

**The claim:** an Observation on the estate, `field` `rank.absence.SECOND`, `claimed_validity`
VINTAGE 2022–2022, asserted_at the document's date, mode EXPLICIT.

**If approved:** a **RankAbsence** {tier SECOND, scope ESTATE_RANGE, claimant PRODUCER, validity
`EXACT VINTAGE 2022` to `EXACT VINTAGE 2022`}. It is a vintage-scoped absence, **not** a
VintageStatement: the grand vin was made, and the claim is about the second rank. It says nothing
about 2021 or 2023.

### E. Yquem's not-made years

**Already modelled:** VintageStatement NOT_PRODUCED for 1992, 2012 and 2018, provenance
LEGACY_UNSOURCED.

**In this model** they are primary point events (`NOT_MADE`) with no interval. A future sourced claim
for one of these years would be added as a candidate of a reconciliation on the VintageStatement's
existence. The legacy statement is not replaced (I7, I11).

### F. Classification editions

**Today:** one edition per scheme, the current one.

**History:** earlier editions are added as ClassificationEdition records (for example Saint-Émilion
2012 SUPERSEDED, 2006 ANNULLED), each with CALENDAR validity, plus the wines' memberships in each.

**A change is derived:** a wine's membership differs between consecutive **recorded** editions.
Absence from a recorded edition is evidence; absence of a recorded edition is not.

**Effective dates:** a scheme effective from a vintage (Pontoise Cabarrus, "à partir du millésime
2018") gives the membership VINTAGE validity, with the edition's CALENDAR date as its own.

### G. A hypothetical ownership change

Ownership{estate, Party A, role OWNER, valid_to `NO_LATER_THAN CALENDAR 1960`} and Ownership{estate,
Party B, valid_from `EXACT CALENDAR 1961`}. Each bound's basis is a reconciled claim ("acquis … en
1961"). `OWNERSHIP_CHANGE` is derived at the boundary; no event row is created.

### H. A hypothetical appellation change

AppellationMembership{wine, appellation X, valid_to …} and {wine, appellation Y, valid_from …}. Where
the appellation itself was created ("Haut-Médoc, créée en 1936"), the Appellation's own validity
holds that. A wine cannot be a member before its appellation exists, which is a reconciliation check.

## 14. What not to model

These are outside the historical-event model:

| Not modelled as history | Why | Where it stays |
|---|---|---|
| arbitrary prose ("a long tradition of excellence") | no assertion to bound | the estate's text fields; discovery text |
| every document mention | a mention is not a statement about change | Attribution and discovery observations |
| changes inferred from **absence**: a missing sheet, a missing listing, a missing edition | absence of evidence (I20) | nothing |
| the first or last sheet on file as introduction or discontinuation | coverage, not history (Phase 6.9) | the block's "sheets on file" |
| vintage-to-vintage value differences (blend, alcohol, oak) | these are vintage observations, not events | Observations on the Vintage |
| label, bottle or packaging changes | not identity (3.4 §7, Coutet) | an observation, if anything |
| "today/now/currently" without a document date | not anchorable (rule 4) | the Observation, asserted_at UNKNOWN |
| raw scraping observations (discovery CANDIDATES_ONLY) | not attributed to model subjects | discovery data until reconciled |
| geocoding differences | method, not history | a QualityFinding |
| UI presentation state (which vintage is open, language) | not data | the page |
| derived drink windows, ratings, the dashboard's editorial collections | derived or editorial | as today |
| undocumented assumptions, including well-known trade lore | no provenance | nothing, until sourced |

## 15. Open decisions

None of these blocks M0–M2.

| # | Decision | Needed for | Recommendation |
|---|---|---|---|
| O1 | **D5**, the conflict policy (adopt or amend) | any **automatic** historical reconciliation | until adopted, M3 uses MANUAL_DECISION only, one fact at a time |
| O2 | **D2**, rename versus succession, for Echo | the first M3 fact | recorded as RENAMED, PROBABLE → CONFIRMED by the decision |
| O3 | add **`RELATED_UNSPECIFIED`** to TransitionKind | "related, not established" (§6) | add in M1; POSSIBLY_SAME asserts possible identity, which is stronger |
| O4 | IdentityTransition `at` → **`occurred` window** | events known only within a range | adopt in M1 (0 rows to migrate) |
| O5 | reconciliation granularity: **per bound** or per record | §8 | per bound, as each bound already has its own basis; record existence as its own field |
| O6 | which **claimants** form a rank history (PRODUCER only, or DATASET too) | WINE_ROLE_CHANGE | per claimant, never mixed: the dataset's current claim is not a historical one |
| O7 | whether snapshots are **generated** for the app or computed in the page | M4 | generated (deterministic, testable), as Phase 6.7 |
| O8 | the source-strength ordering (ESTATE_PUBLICATION over TRADE …) as a **display** rule | §9 | adopt only as a display rule; never as a reconciliation rule without D5 |

## 16. Recommended minimal architecture

> **Claims are Observations with a claimed time. History is the existing interval records. Events
> are derived boundaries, except identity transitions, vintage statements and document revisions.
> Every value-bearing bound is backed by a reconciliation of the claims. Snapshots and diffs are
> computed deterministically, never stored.**

Concretely:

1. **Observation** + `claimed_validity`, `claimed_window`, `assertion_mode` (optional).
2. **IdentityTransition**: `at` → `occurred` {earliest, latest}; TransitionKind + `RELATED_UNSPECIFIED`.
3. **Reconciliation**: subjects may be state records, NameRecords or transitions (fields `valid_from`,
   `valid_to`, `exists`, `kind`, `occurred`); candidates carry a disposition.
4. **TemporalBound.basis** → the reconciliation that fixed it.
5. **ArtifactDate** populated (M2), feeding `asserted_at`.
6. A **`holds` / `state_at` / `changes`** evaluator, three-valued, in `model_reader`.
7. **No new entity. No generic event table.**

### Invariants

They extend the contract's I1–I22:

| # | Invariant |
|---|---|
| H1 | **No historical fact without provenance.** Every value-bearing bound has a basis that reaches a Reconciliation, and through it at least one Observation with an artifact. |
| H2 | **No event inferred solely from absence.** A missing sheet, listing or edition never sets a bound, a transition or a VintageStatement. |
| H3 | **A source's statement date is not the event's effective date.** `asserted_at` never becomes a bound value by itself. At most it supports "as of" (NO_LATER_THAN / NO_EARLIER_THAN) with an IMPLIED mode. |
| H4 | **Axes are never converted.** A CALENDAR bound and a VINTAGE bound are compared only in a recorded reconciliation. |
| H5 | **A bound claims no more precision than its weakest supporting claim** (contract rule 5). |
| H6 | **Conflicting claims remain representable:** every claim stays a candidate; CONFLICT_OPEN is a valid resting state. |
| H7 | **Rejecting a claim deletes nothing.** The Observation stays, with disposition REJECTED and a reason (I11). |
| H8 | **No automatic winner across claimants or languages** until D5 is adopted. Newer is not truer. |
| H9 | **Unresolved identity relationships remain unresolved.** UNRESOLVED transitions move no name, end no validity and are never presented as changes. |
| H10 | **Rename and succession are only asserted on the evidence the contract requires;** otherwise the relation is POSSIBLY_SAME or RELATED_UNSPECIFIED, or nothing. |
| H11 | **Current facts do not silently become historical.** A CURRENT record with valid_from UNKNOWN is never shown as holding at any earlier T. |
| H12 | **A vintage-specific observation is not a historical event** unless an explicit reconciliation makes it one. |
| H13 | **Records are added, never overwritten** (I7). A changed conclusion supersedes; it does not edit. |
| H14 | **Event and record identity are stable:** minted opaque ids that survive re-reconciliation, re-extraction and migration reruns. |
| H15 | **Historical state is derived deterministically:** `holds`, `state_at` and `changes` are pure functions of the model, with the same output on every run. |
| H16 | **UNDETERMINED is a first-class answer.** It is never coerced to YES or NO. |
| H17 | **Every claim keeps its own document date, language, locus and subject status;** a claim repeated in several documents is several claims. |
| H18 | **A point event has no interval** (VintageStatement, an occurrence window of zero length). An interval fact has no single "date". |
| H19 | **A vintage-scoped absence is scoped to its vintages only** (Corbin 2022 says nothing about 2021 or 2023). |
| H20 | **Membership cannot precede its container:** an AppellationMembership's or ClassificationMembership's validity lies within its Appellation's or edition's, or the reconciliation records the contradiction. |
| H21 | **Discovery observations reach history only through attribution and reconciliation,** never directly (I21). |
| H22 | **Displayed history equals the evaluator's output:** the app never computes or rounds a bound itself. |

**22 invariants.**

### Gate

The architecture needs **no new entity and no domain decision** to implement M0–M2. M3 is gated **per
fact** on a recorded decision, as the model has always required (D2 first), and on D5 for anything
automatic. That is a data-decision gate, not a modelling one.

**SAFE — HISTORICAL EVENT MODEL DESIGNED — READY FOR IMPLEMENTATION**
