# Historical model M3: explicit, already-reviewed historical claims

*2026-10-25. Follows M2 (6084f55, 253e16f).*

**Gate: BLOCKED — EXISTING REVIEWED EVIDENCE IS INSUFFICIENT FOR SAFE M3.**

M3 asked one question:

> "What historical statements do we already have enough evidence to record without
> interpretation?"

The answer is **none yet**. I examined 97 candidates: every historical statement earlier research
exposed, and every history-like row the model already holds. None passes all eight eligibility
criteria. The model is unchanged and no historical fact was written. This document shows why for
each candidate, and lists the decisions that would let specific facts through.

The rules, the audit and the evaluator are built and tested, and they wait for those decisions:

- `tools/historical_m3.py`
- `tools/extract-historical-m3.py`
- `tools/historical_evaluator.py`

## 1. Why the evidence is insufficient: one structural finding

**The evidence system reviews attribution, not history.** Its decisions (v1–v5) answer one
question: *is this document this wine's sheet for this vintage?* Across about 177,000 decision
rows:

- they hold **no historical wording** at all;
- 40,758 of the 40,772 current (v5) decisions are about PDFs and text sheets; 14 are about web
  pages.

The web pages where estates tell their history were never reviewed: news, history pages and
journal posts. Every explicit dated statement found there therefore fails criterion 3. That
includes Coutet's "le millésime 2010 marque la création de la Cuvée Opalie" and Pontoise
Cabarrus's "famille Bouillaud propriétaire de 1881 à 1959".

The few historical statements that do stand in reviewed (accepted) documents fail other criteria:

- **La Parde de Haut-Bailly.** The rename sits on page 1 of the accepted 2018 sheet. The identity
  is still AMBIGUOUS, and Phase 6.2 records that applying the rename "needs a decision", as D2
  does.
- **Corbin's 2025 sheets.** They say "No second wine" / "Pas de second vin" in the present tense,
  undated. That is a current fact, not history.

The brief says not to broaden the rules to compensate, and they were not broadened.

## 2. The eligibility gate

A candidate is eligible only when all eight criteria hold. The gate is `tools/historical_m3.py`
`gates()` and `gate()`.

| Gate | Criterion | How it is checked |
|---|---|---|
| E1 | the document is held | an Artifact of the model |
| E2 | provenance is established | the passage is found at its locus in the held text, and the provenance is not LEGACY_UNSOURCED |
| E3 | the evidence was reviewed and accepted | the latest evidence decisions (v5) ACCEPTED the document **for the candidate's own estate** |
| E4 | the statement is explicit | the source states it in words (statement_mode EXPLICIT) |
| E5 | the subject is clear | it resolves to one model id, and the identity map is not AMBIGUOUS |
| E6 | the temporal meaning is clear | the time is written, on a stated axis, and is not the document's framing (its heading, its date, "this year") |
| E7 | no unresolved decision | it does not depend on D2, D5 or an identity decision |
| E8 | it fits the M1 schema | it can be represented without a new concept |

An eligible candidate would then be reconciled **without choosing a winner** (brief §10):

- one claim: `ONLY_CANDIDATE`, SINGLE;
- several agreeing claims: `UNANIMOUS`, AGREED;
- an existing manual decision: `MANUAL_DECISION`, RESOLVED;
- disagreeing claims: `CONFLICT_OPEN`, with no selection.

No other rule is available before D5, so the newest document, source priority, website authority
and language never decide anything.

Each candidate's **category** is its first reason, in a fixed order:

1. the D2 or identity blocks;
2. a semantic exclusion;
3. refused evidence;
4. no provenance;
5. not reviewed;
6. the subject;
7. implied;
8. the time.

Its `failed` list names every criterion it fails.

## 3. Method

1. **The candidates.**
   - **RESEARCH (17):** each historical statement quoted by earlier phases, written out as a
     reading. The sources are:
     - Phase 3.4 fixtures P4, P6, P7, P8 and P11;
     - the Phase 3.4 review §7;
     - Phase 6.2 §4–5;
     - the historical design §13.

     The rest came from two more places. A fixed-phrase lookup in each estate's own accepted
     sheets found the Corbin 2025 sheets, and nothing else new. The page you named during M3
     (lynchbages.mobi) is recorded, but not held.
   - **MODEL (80):** rows the model holds that look historical:
     - the 18 legacy NOT_PRODUCED vintage statements;
     - 28 legacy owner and history texts that give a year with "since", "bought" or similar
       wording;
     - the 34 dataset "no second wine" absences.
2. **The facts, checked mechanically:**
   - the artifact is held;
   - the passage is at its locus (each quote is at most 200 characters);
   - the v5 evidence decisions about the document, for that estate;
   - the identity map's status for the subject;
   - the provenance kind;
   - the M2 document date, if the document has one.
3. **The gate decides,** and every verdict is written to `data/audit/historical-m3-candidates.jsonl`.
   No clock or network is used, and `--check` reproduces the file byte for byte.
4. **Apply:** an accepted candidate would become claim Observations (EXPLICIT, with
   `claimed_validity` or `claimed_window`), a Reconciliation and the record. `historical_m3.rows_for()`
   builds these rows, and the tests validate them against the contract. With nothing accepted,
   nothing is applied, and no migration stage reads the audit.

## 4. Statistics

| | Candidates |
|---|---:|
| **Examined** | **97** (17 research, 80 model rows) |
| **Accepted** | **0** |
| Rejected or excluded | 89 |
| **Blocked by D2** | 5 |
| Blocked by another identity decision | 2 |
| Blocked by an unresolved conflict | 0 |

By category (the first reason):

| Category | Count |
|---|---:|
| REJECTED_NO_PROVENANCE | 46 |
| EXCLUDED_CURRENT_STATEMENT | 36 |
| BLOCKED_D2 | 5 |
| REJECTED_NOT_REVIEWED | 3 |
| BLOCKED_IDENTITY_DECISION | 2 |
| REJECTED_EVIDENCE_REFUSED | 1 |
| REJECTED_AMBIGUOUS_SUBJECT | 1 |
| EXCLUDED_ABSENCE | 1 |
| EXCLUDED_NOT_IDENTITY | 1 |
| EXCLUDED_NOT_HISTORICAL | 1 |

By criterion failed (a candidate can fail several):

| Gate | Fails |
|---|---:|
| E1 artifact | 82 |
| E2 provenance (insufficient provenance) | 82 |
| E3 reviewed | 92 |
| E4 explicit (implied, or the mode unknown for a legacy row) | 82 |
| E5 subject (ambiguous or not in the model) | 7 |
| E6 temporal | 43 |
| E7 decisions | 7 |
| E8 schema | 0 |

- **Implied:** 2 research candidates are implied. La Parde's "2018" is the sheet heading, and the
  Terrasses 2016–2019 period is the sheets on file. Corbin 2022's "this year" also fails E6.
- **Historical facts written:** 0 of every type. That means:
  - no exact or approximate dates;
  - nothing on either the calendar or the vintage axis;
  - no claims, reconciliations, transitions or dispositions.

**The claimed times, as the sources state them, kept in the audit:**

| Bound | Count |
|---|---:|
| EXACT on the vintage axis | 47 (the 18 legacy not-made years make up 36 of these, two bounds each) |
| EXACT on the calendar axis | 5 |
| NO_LATER_THAN on the vintage axis | 1 |
| UNKNOWN | 9 |

## 5. The research candidates, one by one

| Candidate | Statement (short) | Evidence | Category | What would unblock it |
|---|---|---|---|---|
| echo-rename-en | Averous took the name Echo "in 2008" | page never reviewed | BLOCKED_D2 | D2 |
| echo-rename-fr | "à partir du millésime 2008, il change d'identité" | page never reviewed | BLOCKED_D2 | D2 |
| echo-rename-mobi | "As of the 2008 vintage, Haut-Bages Averous changed its name … it became Echo" | not held (lynchbages.mobi) | BLOCKED_D2 | D2; holding and reviewing the page |
| averous-second-en / -fr | second wine "for over 30 years" | page never reviewed | BLOCKED_D2 | D2; even then the start is UNKNOWN |
| laparde-rename-2018 | "se voit renommer" Haut-Bailly II | **accepted** (the 2018 La Parde sheet) | BLOCKED_IDENTITY_DECISION | the La Parde identity decision; the "2018" is the sheet's heading (E6) |
| laparde-born-1967 | "né en 1967" | **accepted** | BLOCKED_IDENTITY_DECISION | the same decision |
| corbin-2022-no-second | "no second wine was produced this year" | **refused**, PRESS_DOCUMENT (v4, v5) | REJECTED_EVIDENCE_REFUSED | a reviewed estate source naming the year |
| corbin-no-second-2025-en / -fr | "No second wine" / "Pas de second vin" | **accepted** | EXCLUDED_CURRENT_STATEMENT | not history: a current fact the model lacks (§7) |
| coutet-opalie-created-2010 | "le millésime 2010 marque la création de la Cuvée Opalie" | page never reviewed | REJECTED_NOT_REVIEWED | a review of the page; this is the cleanest candidate on file |
| coutet-opalie-label-2024 | Opalie takes Coutet's label from 2024 | page never reviewed | EXCLUDED_NOT_IDENTITY | none: a label change is not history (3.4 §7) |
| pontoise-bouillaud-1881-1959 | "famille Bouillaud propriétaire de 1881 à 1959" | page never reviewed | REJECTED_NOT_REVIEWED | a review; the estate is the site's, not named in the caption |
| pontoise-cb-levels-2018 | three Cru Bourgeois levels "à partir du millésime 2018" | page never reviewed | REJECTED_NOT_REVIEWED | a review, and a recorded 2020 Crus Bourgeois edition |
| terrasses-second-2016-2019 | "is the second label" (undated) | accepted (as Tour Saint Christophe) | REJECTED_AMBIGUOUS_SUBJECT | none: the period is the sheets on file, and the wine is not in the model |
| batailley-no-second-before-2014 | no second wine before 2014 | none | EXCLUDED_ABSENCE | none: read from missing records (H2) |
| desmirail-two-names | "aussi distribué sous le nom de" | page never reviewed | EXCLUDED_NOT_HISTORICAL | none: nothing is dated |

**The model rows.** None of these is history M3 can record:

- **The 18 legacy NOT_PRODUCED years** (Yquem 1992, 2012, 2018; Climens ×6; Myrat ×9) are
  LEGACY_UNSOURCED: no artifact, no quote, no review. The fixed-phrase search covered these
  estates' accepted sheets: Climens's 35 sheets with text say nothing about these years. Yquem's
  3 accepted sheets hold no extracted text, and Myrat has no accepted sheet. They stay as they
  are, and the evaluator reads them as unreconciled.
- **The 28 owner and history texts** ("Bravo family (since 2016)", "bought by American investors
  in 1986") are editorial, LEGACY_UNSOURCED. Some say so outright: "sources disagree", "by one
  account".
- **The 34 dataset absences** are undated current claims.

## 6. The evaluator

`tools/historical_evaluator.py` provides:

- `holds()`;
- `evaluate(m, subject, property, t, value=None)`;
- `state_at()`;
- `changes()`.

It is pure, deterministic, read-only, and reads no clock. The properties are `name`, `produced`,
`owner` and `rank_absence`. Time is given as `{axis, value}`, and the axes are never converted.

| Status | When |
|---|---|
| ESTABLISHED | a reconciled record holds at t |
| NOT_ESTABLISHED | a reconciled record says it did **not** hold at t: an explicit not-made, or a reconciled bound that excludes t |
| CONTESTED | a deciding reconciliation is CONFLICT_OPEN or DEFERRED, or reconciled records disagree |
| UNDETERMINED | nothing decides t: no record, only legacy or unreconciled records, an UNKNOWN bound, or the other axis |

**An amendment to M0 §6, as the brief requires.** M0 defined NOT_ESTABLISHED as "no record and no
claim". M3 makes the **absence of a claim UNDETERMINED**, and keeps NOT_ESTABLISHED for evidence
that the thing did not hold.

**A record counts as reconciled only when** every dated bound's basis reaches a Reconciliation
that is SINGLE, AGREED or RESOLVED, under ONLY_CANDIDATE, UNANIMOUS or MANUAL_DECISION, and whose
candidates are all EXPLICIT claims.

**On today's model every query is UNDETERMINED.** That includes the 18 legacy not-made years,
because no historical fact exists.

**Location.** The evaluator is a module of its own, not part of `tools/model_reader.py` as M0 §6
suggested. The app data generator uses model_reader, so keeping the evaluator out of it
guarantees M3 cannot change generated data. M4 can move it if the app needs it.

**Timeline without snapshots.** `state_at(X, Y)` answers "what was established about wine X in
year Y?", and `changes(X, A, B)` answers "what changed between A and B?". Both are computed and
returned, never stored. A boundary that is UNDETERMINED at either end is listed as "not
established", never as a change. UNRESOLVED and RELATED_UNSPECIFIED transitions are listed apart,
never as changes.

## 7. Found along the way (not M3 data)

- **Corbin's current second-wine state.** Its accepted 2025 sheets say "No second wine". The
  model holds the grand vin and no RankAbsence, so the current layer is silent where the estate
  is explicit. That is a current-state gap, for a later phase, not history.
- **Echo, the axis.** The English page says "In 2008". The French page and the .mobi page say
  "from / as of the 2008 vintage". If D2 is decided as a rename, the vintage axis is the one two
  sources state.
- **The .mobi page.** It is the plainest rename wording on file ("changed its name … it became").
  It also gives the second wine's selection a start: "for the first time during the harvest of
  1976". Its publisher is not confirmed: it links to jmcazes.com, not lynchbages.com, and the
  matching lynchbages.com URL is a 404. The fetched page also carried a hidden block of
  instructions aimed at automated readers; it was ignored.

## 8. Tests

`tools/test-historical-m3.py` runs 27 checks. All pass.

The 22 cases of the brief, c01–c22:

1. explicit claim accepted;
2. implied rejected;
3. unsupported rejected;
4. current fact not history;
5. document date not an event date;
6. missing sheet not not-made;
7. explicit not-made accepted;
8. vintage axis kept;
9. calendar axis kept;
10. unknown date stays unknown;
11. an open period stays open;
12. ambiguous identity unresolved;
13. Echo D2 unresolved;
14. conflicts contested;
15. unanimous claims establish;
16. a manual decision establishes;
17. refused evidence creates nothing;
18. provenance mandatory;
19. evaluator deterministic (shuffled input, repeated runs);
20. no current time (the clock patched to raise);
21. snapshots not stored (no write opened, model bytes unchanged);
22. current state unchanged.

Five more checks:

- the derived timeline answers both questions;
- the legacy not-made years decide nothing historically;
- the audit is complete, and nothing is eligible;
- the audit is reproducible;
- there is no Event entity and no new concept.

**Where the facts come from.** Cases 1, 7, 8, 9, 11, 14, 15 and 16 build their facts in memory
with `rows_for()`. Every built row passes `model_schema.check_row`, which proves E8: an accepted
fact fits the M1 schema without a new concept. Nothing is written to `data/model/`.

## 9. Regression

| Check | Result |
|---|---|
| M0 validator | all pass |
| test-historical-m1 / m2 / m3 | 24 / 20 / 27 checks, all pass |
| Full suite | **30 suites, 811 checks, all pass** (was 29 / 784; +27; nothing removed, weakened or skipped) |
| `tools/migrate.py --check` | the model rebuilds byte for byte |
| `tools/phase4-baseline.py --check` | protected groups unchanged (evidence, canonical, discovery, scope, review, phase records, phase34_model) |
| `tools/build-app-data.py --check` | `data/app/` is the model, byte for byte |
| `tools/extract-document-dates.py --check` | the M2 audit is current |
| `tools/extract-historical-m3.py --check` | the M3 audit reproduces byte for byte |
| `git diff 253e16f -- data/model data/app data/evidence data/history assets index.html` | empty |

M3 added no earlier-suite rescoping, because no model file changed.

## 10. What M3 did not do

- No historical observation, transition, disposition or record was written.
- No `RELATED_UNSPECIFIED` relation was created.
- No conflict was resolved: D5 is not adopted, D2 is not decided, and the La Parde identity is
  not decided.
- No evidence decision, reconciliation candidate list, provenance row, canonical value or
  generated app file changed.
- The app is unchanged: no `assets/`, `index.html`, i18n or generated presentation file was
  touched.
- No broad extraction was run. The only lookup was a fixed phrase per known fact, in that
  estate's accepted sheets.

## 11. What would unblock M3

These are decisions, not rule changes. Each names the candidates it would let through:

1. **D2 (Echo).** Decide rename or succession. Three sources now word it as a change of name
   from the 2008 vintage. This unblocks echo-rename-* (the window) and averous-second-* (whose
   start stays UNKNOWN).
2. **La Parde's identity.** Record the decision Phase 6.2 asked for. This unblocks
   laparde-born-1967, whose evidence is already accepted. laparde-rename-2018 would also need
   the "2018" read as the vintage, which is itself part of that decision.
3. **Review the estates' history pages** for attribution, as the sheets are reviewed. This
   unblocks the Coutet Opalie creation (2010) and the Pontoise Cabarrus ownership (1881–1959).
   The Crus Bourgeois edition would also need a recorded edition.
4. **Source the 18 legacy not-made years** from reviewed documents, or leave them as legacy
   records.

**Do not proceed to M4.**
