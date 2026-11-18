# Integration contract: identity, reader, statement v2, C6

Status: **design and dry run only.** Nothing in production calls the modules below. The dry run is `tools/integration-dryrun.py`, its tests are `tools/test-integration-dryrun.py` and its report is [PHASE-INTEGRATION-DRYRUN.md](PHASE-INTEGRATION-DRYRUN.md).

The dry run:
- writes no model, evidence, provenance, source, gap-register or app data;
- accepts no evidence;
- writes no manifest.

## 1. The layers as they are implemented

Each layer below is described from its code, not its name.

### Identity (production)

**M3.4A `decide`** (`tools/m34a-mapping-audit.py`, fingerprinted) returns `(disposition, reason, basis, facts)`. The disposition is one of:

- `SAFE_TO_MAP`
- `ESTATE_VINTAGE_ONLY`
- `WINE_AMBIGUOUS`
- `VINTAGE_AMBIGUOUS`
- `MULTI_WINE_AMBIGUOUS`
- `COLOUR_AMBIGUOUS`
- `CONFLICT`
- `IDENTITY_BLOCKED`
- `ALREADY_MAPPED`
- `NOT_FOUND`
- `EVIDENCE_INSUFFICIENT`

It reads the document through `document_text(id)`.

**M3.9 `judge`** (`tools/m39-evidence-review.py`) first tries the title rule (`RB.judge`, rule `T`). Only if that has no answer does it call `decide` (rule `M34A`). It renames `ESTATE_VINTAGE_ONLY` to `ESTATE_ONLY`, `ALREADY_MAPPED` to `ALREADY_SUPPORTED` and `NOT_FOUND` to `EVIDENCE_INSUFFICIENT`.

**P1 `Reader.claim`** (`tools/m312-p1-review.py`) returns `{disposition, basis, kind, rule, reader, gate, media, doc_type}`. The disposition is `SAFE_TO_MAP` only when all three hold:
- `judge` says `SAFE_TO_MAP`;
- the reader veto (`X.reader_verdict`) says `ACCEPTED`;
- the R1 gate (`X.r1_gate`) passes.

**Competing identity.** The P1 review asks about every other wine of the estate with the same call. A sibling that is also `SAFE_TO_MAP` makes the claim a `CONFLICT`. A sibling that is `SAFE_TO_MAP` while the target is not makes it the sibling's document.

### Identity (candidate)

`tools/identity_rules_candidate.py` holds rules R1, R1b, R2, R3, R4 and G1. They come from the M3.12 rule-layer proposal, moved out of the scratchpad unchanged in substance.

- `applied(m34a_module)` wraps `decide` for the duration of a `with` block and restores it afterwards. Inside the block, `decide` runs unchanged on rewritten or masked text, or has its result vetoed.
- The rules never edit the fingerprinted file.
- `REVIEW_HOLD` lists the five rescues the rule audit classified `LIKELY_RESCUE_REQUIRES_REVIEW`. Those are the claims the rules settle but nobody has accepted.
- One change from the scratchpad: R1 now orders two names of the same length by name. The scratchpad left that tie to set order, which made the rule trace differ between processes (for Cantenac-Brown 2024: "brio de cantenac brown" and "chateau cantenac-brown"). No result changed.

### Reader

`R.figures` calls `sheetreader.fields_of` on the held PDF and returns `(fields, how)`. `how` carries the words read and a `refused` map. The reader does not depend on identity: it reads the same figures whichever wine is claimed. It reads PDFs only.

### Statement v2

`tools/statement_check.py`:

- `stated(field, j)` returns `(value | None, words)`, where `j` is the folded text with lines joined by `" / "`.
- `check(field, value, j)` returns one of `CONFIRMED`, `CONTRADICTED_BY_STATEMENT` or `NOT_FOUND_AS_STATED`.
- `verify(identity, field, value, j)` returns `NOT_EVALUATED` unless the identity is `SAFE_TO_MAP`, returns `NOT_READ` when the value is None, and otherwise returns `check`'s answer.

It never produces a figure the reader did not read.

### C6 yield layout

`tools/yield_layout.py` provides `read_yield(pdf_bytes, identity, reader_yld, vintage, wine_name, other_wine_names)`. It returns one of:

- **NOT_RUN** at guard 1 (identity) or guard 2 (the reader read a yield);
- **REFUSED**, with `failed_guard` set to 3–10 or `arithmetic`;
- **READ**, with `value`, `unit: hl/ha`, `unit_basis: LAYOUT_DERIVED…`, `field_basis`, `evidence` (the label and value lines as printed, with coordinates), `arithmetic` (PASSED, NOT_DISCRIMINATING or UNAVAILABLE) and `guards`.

## 2. The one boundary

A claim is one document, wine, vintage and field. `integration-dryrun.evaluate` runs every layer in a fixed order. Each layer keeps its own result in the claim's record:

| key | holds |
|---|---|
| `precondition` | The P1 review's own gates: the model holds no value for the field, the source is first-party (tier A), the text is held. A claim outside P1 is `NOT_ASSESSED`. Admissibility is not decided here. |
| `identity.production` | `Reader.claim` and its siblings, with `decide` as production runs it. For P1 rows this reproduces the committed `reader_status`; any other result stops the run. |
| `identity.candidate` | The same call with the candidate rules applied, plus the rules that fired, their trace and notes, and the file-series mapping. |
| `identity.status` | `IDENTITY_SETTLED`, `IDENTITY_REFUSED`, `IDENTITY_CONFLICTED` or `IDENTITY_REVIEW_REQUIRED`. Recorded with `settled_by` (`PRODUCTION` or `CANDIDATE_RULES`), `review_hold` and `regimes_disagree`. |
| `reader` | `VALUE_READ`, `NO_VALUE` or `NOT_RUN` (a web page), with the value, the words and the reader's own refusal. `mode` is `GATED` when the identity is settled and `DIAGNOSTIC` otherwise. |
| `statement` | `gated`: `verify()` after the identity. `diagnostic`: `check()` regardless of identity, never used for a decision. Also `stated_value` and `statement` (the document's words), and `v1_reference` (what M3.9's version 1 says, for comparison). |
| `c6` | `NOT_APPLICABLE` (not yld), `NOT_ELIGIBLE` (identity not settled, or not a PDF), `NOT_RUN` (the reader read a yield), or `READ`/`REFUSED` as the module returns them. A `READ` adds a `literal` block: the French and English labels and lines as printed. When C6 is not eligible only because of identity, `diagnostic_if_identity_were_settled` records what the layout would have done. |
| `final` | One disposition, one reason code, the value and its unit and source only for a candidate, and `recording_path`. |
| `audit_refs`, `tags` | The P1 review row (decision, status, reason), the identity refusal audit's verdict, and the audited sets the claim belongs to. |

No layer's result overwrites another's, and no single boolean stands for the claim.

## 3. Precedence

The order is fixed. The first rule that applies gives the final disposition, but every layer is still recorded.

1. **Preconditions first.** If the model already holds the field, the claim is `REFUSED MODEL_HOLDS_VALUE`. Otherwise:
   - a source that is not first-party gives `REFUSED NOT_FIRST_PARTY`;
   - a claim outside P1 gives `REFUSED SOURCE_NOT_ASSESSED`;
   - no held text gives `REFUSED NO_HELD_TEXT`.
2. **Identity comes next.** No later layer can establish a wine or a vintage.
   - `IDENTITY_CONFLICTED` gives `CONFLICT`.
   - `IDENTITY_REVIEW_REQUIRED` gives `REVIEW_REQUIRED`.
   - Anything not settled gives `REFUSED IDENTITY_NOT_SETTLED`.

   The candidate identity governs. Where the two identity regimes disagree, the claim is settled only if the candidate is settled, and the disagreement is recorded. A rescue on the review hold is never settled.
3. **A document already linked to the vintage** is `REFUSED DOCUMENT_ALREADY_LINKED`. This is the P1 review's duplicate rule.
4. **A web page** is `REFUSED WEB_PAGE_FIGURES_NOT_READ`.
5. **When the reader has a value, the statement decides.**
   - `CONFIRMED` makes it a candidate (`READER_CONFIRMED_BY_STATEMENT`).
   - `CONTRADICTED_BY_STATEMENT` gives `CONFLICT`. Neither the reader nor the statement is chosen.
   - Otherwise it is `REFUSED STATEMENT_NOT_FOUND`.
6. **C6 is the reader's fallback, for yld only.** It is eligible only when the identity is settled, the field is yld and the reader read no yield. If the reader read one, C6 does not run and its bytes are not even fetched.
   - A C6 `READ` makes the claim a candidate (`C6_LAYOUT_CONFIRMED`). The exception is when the document's own statement gives a different yield: that is `CONFLICT LAYERS_DISAGREE`.
7. **A statement does not make a value.** When the document states the field but the reader reads nothing, the claim is `REFUSED STATEMENT_STATED_VALUE_UNRESOLVED`.
8. **Otherwise** the claim is `REFUSED C6_GUARD_FAILED` or `REFUSED VALUE_NOT_READ`.

## 4. What a candidate is

`ACCEPTABLE_TO_NEXT_STAGE` means that, if this orchestration were enabled, the datapoint would be eligible to go on to acceptance and application. A candidate needs all of the following:

- a passed precondition;
- a settled identity;
- exactly one value from exactly one layer:
  - the reader's figure confirmed by v2, or
  - a C6 read with no contradicting statement.

A candidate is not a canonical value and not accepted evidence.

`recording_path` says whether the unchanged acceptance runner could record the candidate. It applies the P1 review's own blockers (a web page, identity not from a text rule, no stated vintage) and adds what the new layers introduce:
- the identity rests on candidate rules, not production;
- the wine is named by the file listing (R4), not the text;
- the value is a C6 observation with a derived unit.

## 5. Unresolved decisions

None of these is decided here. The dry run's report gives the counts.

1. **Adopting the candidate identity rules.** Every candidate in the dry run is settled by the candidate rules, and none by production identity. Integration therefore means changing how M3.4A's `decide` is used, and that file is fingerprinted and hashed into the M3.5–M3.12 evidence.
2. **The review hold.** These five claims stay `REVIEW_REQUIRED` until each is decided:
   - Paloumey 2022 (a heading that may be a table label);
   - Chapelle 1998 (identity from the listing alone, the year from a bare last line);
   - Brane-Cantenac 2023 ×2 (critics' score sheets);
   - Corbin 2003 (a press compilation).
3. **G1 on critic prose.** G1 refuses Grand Mayne 2005 because a quoted review says "This cuvee tends to be made in a dense, chewy style". The cuvée is the grand vin itself. G1 is conservative by design: narrowing it is a rule change, not something the integration should do.
4. **Recording a C6 value.** No production path records a value whose unit is derived from layout, together with the printed lines as its evidence. A provenance shape for that is needed before any C6 value can be applied.
5. **Identity from the file listing (R4).** R4 settles the Desmirail and Issan candidates. The P1 review's acceptance path counts identity that is not from a text rule as blocked. Recording R4 identities needs a policy.
6. **No stated vintage form.** Some candidates' documents state the vintage in a form M3.8's vintage basis does not recognise. The acceptance runner blocks those.
7. **Outside the P1 corpus**, source admissibility is not assessed. The extra claims (the brochure and the C6 negatives) are there to test the boundaries, not to become candidates.
8. **Still deferred, unchanged:**
   - La Clarté identity;
   - the Figeac primeur pH (the model has no stage);
   - Taillan's partial blend;
   - multi-estate brochures (identity refuses them; no attribution of a blend list to one wine is attempted);
   - C5 (Issan's "Alcool (en % vol.)").

## 6. Implementation status

The four blockers in [DECISION-RECORDING-POLICY.md](DECISION-RECORDING-POLICY.md) stand in this order:

1. **The identity wrapper: built, not wired.** `tools/identity_rules.py` (`identity-rules/1`) holds the adopted rules beside `decide`:
   - `identify(m34a_module, args)` calls the module's own `decide` and never assigns it;
   - the rewritten text reaches `decide` through `document_text`, the `text_hook` seam, and is restored on every exit;
   - R2 reads only `NAMED_BLOCK`;
   - R4 goes through `recording_policy.listing_identity`, so only `APPROVED_R4` entries attribute or veto;
   - `CLAIM_DECISIONS` (two holds, three refusals) replaces `REVIEW_HOLD`, and a listed claim is never `SAFE_TO_MAP`.

   The user signed the 13 approved R4 entries off on 2026-11-18. Every R4 step is marked `entry_signoff: USER_SIGNED_OFF_2026-11-18`. An entry approved later needs its own sign-off.

   `tools/test-identity-rules.py` (8 checks) replays every `decide` call over the dry run's corpus. It finds the candidate rules' answer everywhere except at Chapelle 1998, Paloumey 2022, Issan 2004 and Issan 2010, which are no longer settled, and Caillou 2014, which is refused for a different reason. That takes the dry run's 57 candidates to 51. `tools/identity_rules_candidate.py` is unchanged, so the committed dry run still reproduces.
2. **The `REVIEWED_LISTING` enum value:** not started.
3. **A listing branch in `check_review`:** not started.
4. **A C6 branch in the value runner:** not started.

Nothing in production calls `identity_rules.py`.
