# Historical model M0 — the M1 schema, proposed and validated

Gate: **SAFE — M0 HISTORICAL SCHEMA VALIDATED — READY FOR M1**

M0 turns `docs/HISTORICAL-EVENT-MODEL-DESIGN.md` (`61540cf`) into an exact schema proposal, and checks
that it fits the model as implemented.

**Nothing was applied.** `docs/phase34-model.json`, `tools/model_schema.py`, `data/model/`, the
generated data, the application, evidence, provenance and the 27 test suites are unchanged. No
historical fact or document date was added. D2 is not resolved and D5 is not adopted.

**The files:**

| File | What it is |
|---|---|
| this document | the proposal |
| `docs/schema/historical-m1-proposal.json` | the same proposal, machine-readable: enumerations, value types, fields, invariants, the evaluator contract and 31 synthetic fixtures |
| `docs/schema/check_historical_m1_proposal.py` | a documentation-level validator, read-only and not one of the production suites; **48 checks, all pass** (§9) |

---

## 1. What inspection of the implementation found

The design was read against `docs/phase34-model.json` and `tools/model_schema.py` (`check_row`,
`check_bound`, `check_validity`, the id prefixes). It holds with **one refinement and one naming
point**.

**Refinement: candidate dispositions get a field of their own.**

- **What the design said:** §8 and §11 put a disposition *inside* `Reconciliation.candidates`.
- **What the implementation shows:** `candidates` is `list:ref:Observation`, a list of observation
  ids, in all 12,959 existing reconciliations. `check_row` validates it as references.
- **Why it matters:** changing its element shape would rewrite every row and break the reference
  check.
- **The proposal:** an **optional, separate `dispositions` field**, keyed by candidate id. The design's
  meaning is unchanged: a disposition is a property of a candidate within one reconciliation. Only
  where it is stored differs.

**Naming: `RELATED_UNSPECIFIED`, not `RELATED_NOT_ESTABLISHED`.**

- **The design's name:** `RELATED_UNSPECIFIED` (§6, decision O3).
- **The brief:** add `RELATED_NOT_ESTABLISHED` *only if the design confirms that exact
  representation*. It does not.
- **The proposal:** carry the design's value. The meaning is identical: related, relationship not
  established, certainty UNRESOLVED. The final name stays O3's to settle before M1 writes the enum.

**Confirmed in the implementation:**

| Finding | Consequence |
|---|---|
| Reconciliation subjects are `ref:*`, and hashed ids (`nm_`, `it_`, `ra_`, `cm_`, …) resolve | a reconciliation can already be about a NameRecord, a transition or any state record |
| `Provenance.derived_from` is `list:ref` | a bound's basis can name its reconciliation **with no schema change** |
| `Observation.asserted_at` (a TemporalBound) already exists, as do `artifact`, `source`, `lang`, `locus` and `subject_status` | claims need **no** source-identity fields |
| `IdentityTransition.at` is a **required** single bound | its change is a contract change; it is safe because there are 0 rows |
| `check_bound` enforces kind, value, axis and basis, but **not** the contract's precision rule, and `check_validity` does not compare the two bounds | both become M1 schema checks (S2–S4) |

## 2. The concrete M1 schema

### Observation: three optional fields

| Field | Type | Values | Optional semantics | Axis and precision | Provenance | Compatibility |
|---|---|---|---|---|---|---|
| `claimed_validity` | **Validity** {valid_from, valid_to, as_of} | TemporalBounds | absent = the observation makes no claim about **when a state holds** (all 22,437 today) | each bound has its own axis; both dated bounds share one (S3); precision per S2 | each dated bound's `basis` (required, S1); the claim cites an artifact or a quote (S18) | absent on every existing row |
| `claimed_window` | **TimeWindow** {earliest, latest} (new value type) | TemporalBounds; no OPEN | absent = no claim about **when an event happened** | as above | as above | absent on every existing row |
| `statement_mode` | enum **StatementMode** | `EXPLICIT`: stated in words. `IMPLIED`: only from the document's framing (its date, a sheet's vintage, a title year) | absent when neither claim field is present; **required** when either is (S7) | — | — | absent on every existing row |

**Not added:** source identity, which the observation already holds (`artifact`, `source`,
`provenance`, `lang`, `locus`, `subject_status`), and the document's date, which is the existing
`asserted_at`.

A claim has at most one of `claimed_validity` (a state) and `claimed_window` (an event). A claim about
a transition uses `field` `transition.<KIND>`, with `value` {from_name, to_name} or the other subject.

### IdentityTransition: an occurrence window

| Field | Type | Values | Optional semantics | Compatibility |
|---|---|---|---|---|
| `occurred` (**new**) | TimeWindow {earliest, latest} | earliest and latest are TemporalBounds (EXACT, APPROXIMATE, NO_EARLIER_THAN, NO_LATER_THAN, UNKNOWN); **no OPEN** | for new rows; a point event is earliest == latest | — |
| `at` (existing) | TemporalBound | — | **required → optional**; a row has `at` **or** `occurred`, never both; `at` reads as {earliest: at, latest: at} | 0 rows exist |
| `kind` | TransitionKind | the six existing kinds unchanged, **+ `RELATED_UNSPECIFIED`** | — | — |

Each window bound carries its own kind, axis and precision, so "after 2005, by 2008" is
{earliest: NO_EARLIER_THAN CALENDAR 2005 YEAR, latest: NO_LATER_THAN CALENDAR 2008 YEAR}.

**No transition is inserted.**

### Reconciliation: historical subjects and candidate dispositions

| Aspect | Proposal |
|---|---|
| **subject** | unchanged type (`ref:*`). A historical reconciliation's subject is the **record**: a NameRecord, state record, VintageStatement or IdentityTransition id. |
| **field** | for historical subjects, one of `valid_from`, `valid_to`, `exists`, `kind`, `occurred` (a documented vocabulary; the field stays text). Canonical reconciliations keep their field names (`alc`, `blend`, …). |
| **candidates** | **unchanged**: `list:ref:Observation`, the claims. Every claim on that subject and field is a candidate (S13). |
| **dispositions** (**new**, optional) | `{observation id: {"disposition": CandidateDisposition, "reason": text}}`; keys ⊆ candidates; a candidate without an entry is `NOT_ASSESSED` |
| **CandidateDisposition** (new enum) | `SELECTED` (it is the reconciled value), `CONSISTENT` (agrees, not chosen), `CONTRADICTS` (disagrees, kept), `REJECTED` (judged wrong, **reason required**, evidence kept), `NOT_ASSESSED` |
| **selection** | **never automatic.** `selected` iff exactly one SELECTED (S14); none while CONFLICT_OPEN or DEFERRED (S15). Before D5 the only rules allowed are ONLY_CANDIDATE, UNANIMOUS and MANUAL_DECISION (S16). |

**Dispositions belong to the candidate, not the observation.** One claim can be SELECTED in the
reconciliation of a NameRecord's `valid_from` and CONTRADICTS in that of its transition's `occurred`,
so the disposition cannot live on the Observation.

**How a record cites its reconciliation:** the bound's `basis` is a Provenance (EVIDENCE_DECISION or
DERIVATION) whose `derived_from` names the Reconciliation. Both fields exist.

**What each reconciliation can cover:**

| Brief's term | Covered by |
|---|---|
| a historical record | subject = the record, field `exists` |
| a date assertion | field `valid_from`, `valid_to` or `occurred` |
| a candidate value | the candidate claims and their dispositions |
| a temporal claim | a candidate whose Observation has `claimed_validity` or `claimed_window` |

## 3. The date primitive

The existing **TemporalBound** stays the primitive, unchanged in shape:

| Part | Values | Meaning |
|---|---|---|
| `kind` | `EXACT`, `APPROXIMATE`, `NO_EARLIER_THAN`, `NO_LATER_THAN`, `UNKNOWN`, `OPEN`, `NOT_APPLICABLE` | inclusive bounds; UNKNOWN = a bound exists and is unknown; OPEN = still holds as of `Validity.as_of` (end bounds only); NOT_APPLICABLE = the record has no such bound |
| `axis` | `CALENDAR`, `VINTAGE` | never converted (S3) |
| `value` | CALENDAR `YYYY-MM-DD`, `YYYY-MM`, `YYYY`, `YYY0s`; VINTAGE `YYYY` | only on dated kinds |
| `precision` | DAY, MONTH, YEAR, DECADE (CALENDAR); VINTAGE | matches the value (S2) |
| `basis` | a Provenance id, or the source's quote | **required with every value**: the source |

**Composed from it:**

| Structure | Holds | Used for |
|---|---|---|
| **Validity** {valid_from, valid_to, as_of} (existing) | an **interval** | a state's effective interval (on its record) or its asserted interval (`claimed_validity` on a claim) |
| **TimeWindow** {earliest, latest} (new) | when a **point event** happened, as tightly as known | a transition's `occurred`; `claimed_window` on a claim |

**The four kinds of time are kept apart, by where they live:**

| Time | Where |
|---|---|
| when the source spoke | `Observation.asserted_at`, from ArtifactDate |
| what the source asserts | `claimed_validity` or `claimed_window` |
| what is effective (reconciled) | the record's `validity` or `occurred` |
| when it was retrieved | Placement and ArtifactDate RETRIEVED |

**No date arithmetic in M0 or M1's schema.** The only comparison specified is the ordering check S4
(year, then month, then day, at the coarser precision), used for validation.

## 4. Validation rules: 26 schema invariants

The full list, with how each is enforced, is in `historical-m1-proposal.json` → `invariants`. In
summary:

| Group | Invariants |
|---|---|
| **temporal** | **S1** dated bounds have value, axis and basis; **S2** precision matches the value; **S3** one axis per Validity or TimeWindow, never converted; **S4** lower ≤ upper; **S5** OPEN only as valid_to and never in a window, UNKNOWN ≠ OPEN; **S6** the document date is never a record's validity or window, and a bound taken from an ArtifactDate is IMPLIED; **S7** a claim has at most one of validity and window, and a statement mode with either |
| **historical identity** | **S8** RENAMED relates a subject to itself, SUCCEEDED_BY two subjects of one type, neither inferred from the other; **S9** RELATED_UNSPECIFIED and POSSIBLY_SAME are UNRESOLVED and establish nothing; **S10** an UNRESOLVED transition ends no validity, moves no name and is never a change; **S11** no name becomes FORMER merely by being replaced as current |
| **evidence** | **S12** every dated bound has a basis, and from M3 that basis reaches a Reconciliation; **S13** every claim is a candidate; **S14** dispositions ⊆ candidates, one SELECTED = selected, REJECTED with a reason, nothing deleted; **S15** no selection while CONFLICT_OPEN or DEFERRED; **S16** no automatic rule before D5; **S17** absence is never a claim; **S18** a dated claim cites an artifact or a quote |
| **backward compatibility** | **S19** every new field optional, every existing row valid unchanged; **S20** no existing id, provenance, reconciliation or canonical value rewritten; **S21** a record from UNKNOWN to OPEN evaluates UNDETERMINED before its `as_of`, never HOLDS; **S22** existing reconciliations without dispositions read as selected = SELECTED, the rest NOT_ASSESSED |
| **evaluation** | **S23** the evaluator is pure, deterministic and read-only; **S24** UNDETERMINED is never coerced, and CONTESTED is never shown as ESTABLISHED; **S25** snapshots and change lists are derived, never stored; **S26** a vintage-scoped statement applies to its vintages only |

**Enforcement.** S2–S4, S7–S9 and S14–S16 are ready-made M1 schema checks: each has a passing and a
failing fixture (§9). S10, S21, S24 and S26 belong to the evaluator; S6, S11–S13 and S17 to the
validator and reconciliation review.

## 5. Existing structures and their historical extension

The default, confirmed: **existing structures stay valid, and new fields are optional.**

| Existing structure | Historical extension | Migration required? | Reason |
|---|---|---|---|
| Estate | none (history lives in NameRecord, Ownership, EstateLocation, IdentityTransition) | no | identity is name-free |
| Wine | none (same) | no | — |
| EstateWineRelationship | none: its `validity` and `status` (ESTABLISHED … ENDED_UNKNOWN_WHEN) already hold history; bounds gain reconciliations from M3 | no | interval record already |
| RankAssertion / RankAbsence (the contract's replacement for WineRole) | none: `validity`, `claimant`, `scope` suffice; vintage-scoped absence is representable | no | per-claimant history needs no field (O6 is a query rule) |
| Vintage | none | no | point identity; VintageStatement carries not-made |
| VintageStatement | none | no | already a primary point event |
| NameRecord (+ HistoricalIdentity) | none: FORMER and CURRENT with validity already exist | no | interval record already |
| IdentityTransition (HistoricalIdentity) | `occurred` (TimeWindow), `at` optional, kind `RELATED_UNSPECIFIED` | contract only; **0 rows** | windows; an unspecified relation |
| ClassificationEdition / ClassificationMembership | none: edition `status` and validity, membership validity | no | history = more editions and memberships (M3 data) |
| Appellation / AppellationMembership | none | no | interval records already |
| Ownership, EstateLocation | none | no | interval records (0 and 272 rows) |
| Observation | `claimed_validity`, `claimed_window`, `statement_mode` | no (optional) | the claim layer |
| Document (Artifact, Placement, ArtifactDate, ArtifactRelation) | none; ArtifactDate **populated in M2** | no schema migration | REVISION_OF is already a document event |
| Provenance | none: `derived_from` names the reconciliation | no | — |
| Reconciliation | `dispositions` (optional); a documented `field` vocabulary for historical subjects | no (optional) | historical reconciliation |
| CanonicalValue | none: `as_of` exists; historical facts are records, not canonical values | no | the canonical layer stays class A, current |

## 6. The evaluator contract (M1, not implemented)

| | |
|---|---|
| **Where** | `tools/model_reader.py`, beside `project()` |
| **Purity** | pure, deterministic, read-only: it reads the model, writes nothing, uses no clock (S23) |
| **Time input** | `{axis: CALENDAR \| VINTAGE, value}`; no conversion between axes |

**Functions:**

- **`holds(record, t)` → `HOLDS | DOES_NOT_HOLD | UNDETERMINED`.** Whether the record's validity covers
  `t` on the record's axis. UNDETERMINED when the deciding bound is UNKNOWN, APPROXIMATE across `t`,
  or on the other axis.
- **`evaluate(subject, property, t, claimant=None)`** → `{status, value, records, supporting_claims,
  contradicting_claims, reconciliations}`. Properties: name, rank, classification, appellation,
  relationship, ownership, location, not_made.
- **`state_at(subject, t)`:** `evaluate` for every property.
- **`changes(subject, t1, t2)`** → `[{property, before, after, kind: STATE_BOUNDARY | TRANSITION |
  VINTAGE_STATEMENT, status}]`.

**Status vocabulary (EvaluationStatus):**

| Status | When |
|---|---|
| `ESTABLISHED` | a record HOLDS, each deciding bound is reconciled (SINGLE, AGREED or RESOLVED) and, for identity, certainty is CONFIRMED, or PROBABLE with a recorded decision |
| `CONTESTED` | a deciding reconciliation is CONFLICT_OPEN or DEFERRED, or competing claims sit on an UNRESOLVED transition |
| `UNDETERMINED` | records exist but nothing decides `t` (an UNKNOWN start, every record today; the other axis; IMPLIED claims only) |
| `NOT_ESTABLISHED` | no record and no claim for the property |

**On today's model** every property of every wine before its current `as_of` is UNDETERMINED (S21).
That is exactly what the page already says in words (Phase 6.7).

## 7. Snapshot semantics

**Snapshots are derived, never authoritative stored facts** (S25):

- "What was established about wine X in 2008?" = `state_at(X, {VINTAGE, 2008})`. Each property gets
  its status, value and supporting claims; UNDETERMINED and CONTESTED are returned as such.
- "What changed between 2007 and 2008?" = `changes(X, 2007, 2008)`. Records whose `holds` goes HOLDS
  to DOES_NOT_HOLD, or the reverse, plus transitions and vintage statements whose window lies within.
  A boundary that is only UNDETERMINED is reported as "not established", never as a change.
- **Nothing in `data/model/` stores a snapshot.** For the app, M4 may **generate** per-wine output (as
  `wine-established.js`, Phase 6.7) from the evaluator. It is a projection, rebuilt and checked
  byte-for-byte like the other generated files, never read back as evidence.

## 8. The seven decisions

| # | Decision | M0 status | How the schema handles it |
|---|---|---|---|
| 1 | **D5**, the conflict policy | **unresolved, not applied** | S16 allows only ONLY_CANDIDATE, UNANIMOUS and MANUAL_DECISION for historical fields until D5 is adopted; adopting it later widens that list and needs no schema change |
| 2 | **D2**, rename against succession, for Echo | **unresolved, not decided** | both are representable (RENAMED with from == to; SUCCEEDED_BY with two Wines); no data depends on the choice |
| 3 | **`RELATED_UNSPECIFIED`** (brief: `RELATED_NOT_ESTABLISHED`) | the value is decided by the design; **the name is open** | one enum value either way; proposed under the design's name, not written in M0 |
| 4 | **the event-date window** | **sufficiently decided** | `occurred` added, `at` kept optional, so both forms are valid (F24 forbids both on one row) |
| 5 | **date reconciliation granularity** | **sufficiently decided: per bound** | fields `valid_from`, `valid_to`, `exists`, `kind`, `occurred`; a per-record reconciliation remains possible as `exists` |
| 6 | **claimant-specific rank history** | **decided for schema** | RankAssertion already has `claimant`; `evaluate(..., claimant)` keeps histories apart; no field needed |
| 7 | **generated snapshots** | **decided for M4** (§7) | no schema impact |

No production data depends on an unresolved decision: M0 adds none, and M1 adds structure only.

## 9. Compatibility proof

Run: `python docs/schema/check_historical_m1_proposal.py` → **48 checks, all pass.**

| Proof | Result |
|---|---|
| **fit**: no added enum or field name collides with the contract; every added field optional; every type known; `IdentityTransition.at` only loosened | 12 checks pass |
| **rules**: 31 synthetic fixtures (valid and invalid) for S2–S9 and S14–S22 get their expected verdict from prototype M1 checks | 31 pass |
| **existing rows**: every row of every model table (**333,022**) gives the **same** `check_row` result under the extended contract as under today's | identical |
| **reconciliations**: the 12,959 reconciliations carry no disposition and no historical field, so S22's read rule covers them with no rewrite | holds |
| **current facts**: all 3,917 state records start UNKNOWN, so S21 makes none historical | holds |
| **transitions**: 0 IdentityTransitions, so `at` → `occurred` rewrites nothing | holds |
| **inert**: `data/model/` and `data/app/` hash the same before and after the check | unchanged |

**Therefore:**

- no existing id needs rewriting;
- no provenance or reconciliation hash changes;
- no generated app data needs regeneration;
- no current behaviour changes;
- the 27 production suites are untouched and pass.

## 10. What M1 must test

M1's own suite (a new `tools/test-*.py`, alongside M1's schema changes) must cover:

| Area | Tests |
|---|---|
| **empty optional fields** | every existing row still validates; `data/model/` rows byte-identical; `migrate --check` and `build-app-data --check` unchanged |
| **exact dates** | DAY, MONTH, YEAR, DECADE, VINTAGE values with matching and mismatching precision (F2–F5) |
| **bounded windows** | NO_EARLIER_THAN / NO_LATER_THAN windows, ordered and misordered (F10, F11); no OPEN in a window (F9) |
| **open and unknown** | UNKNOWN to OPEN valid; OPEN as a start invalid; UNKNOWN never read as OPEN |
| **calendar and vintage axes** | mixed axes in one interval rejected (F6); no conversion anywhere in the evaluator |
| **explicit and implied** | statement mode required with a claim (F13); a bound from the document date must be IMPLIED (F15, F16) |
| **competing claims** | two claims, one reconciliation, CONFLICT_OPEN with both CONTRADICTS (F29); no selection while open (F28) |
| **rejected claims** | REJECTED needs a reason (F26); the Observation still exists after rejection |
| **`RELATED_UNSPECIFIED`** | UNRESOLVED only (F22, F23); the evaluator never reports it as a change |
| **rename and succession** | RENAMED from == to (F18, F19); SUCCEEDED_BY between two subjects of one type (F20, F21) |
| **D5 guard** | MOST_RECENT_DOCUMENT and SOURCE_PRIORITY refused for historical fields (F30) |
| **backward-compatible records** | existing reconciliations read under S22 (F31); every current record UNDETERMINED in the past (S21) |
| **deterministic evaluator** | the same output on repeated runs and with shuffled input order; no writes; fixtures only, **in test code, never in `data/model/`** |

## 11. What M0 does not decide

These stay outside M0:

- **Echo:** rename against succession (D2).
- **Which historical claims win:** D5, and every reconciliation.
- **Historical facts:** ownership, appellation and classification (earlier editions).
- **Document dates:** populating them (ArtifactDate, M2).
- **Event extraction** from documents.
- **The name of the unspecified relation:** O3.
- **UI presentation** of any history (M4).

## 12. Baseline

**27 suites, 740 checks, all pass**, at `61540cf`, before and after this work. Only `docs/` changed.
