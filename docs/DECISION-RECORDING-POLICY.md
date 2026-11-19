# Decision: R4 independent review, and the recording policies for R4 identities and C6 values

Documentation and audit only. No model, evidence, source, gap-register or app data changed, no production caller was added, and nothing was pushed.

What this phase adds:
- **The second review of the R4 listing:** `tools/r4-listing-review.py` writes `data/audit/r4-listing-review.jsonl` and [PHASE-R4-LISTING-REVIEW.md](PHASE-R4-LISTING-REVIEW.md).
- **The policy as executable rules:** `tools/recording_policy.py`. Nothing in production calls it.
- **Its adversarial tests:** `tools/test-recording-policy.py`, 13 checks.

It builds on [DECISION-CANDIDATE-IDENTITY-RULES.md](DECISION-CANDIDATE-IDENTITY-RULES.md) (5589f7c).

## Part A — the 31 R4 entries, reviewed independently

### The listing and the evidence

The listing is exactly R4's: `identity_rules_candidate.FILE_SERIES_PAGES`, 31 (host, path prefix, wine) entries. The review reads only what R4 itself reads:
- the held discovery pages under each entry;
- the documents those pages link;
- the model's own source-estate relationships.

It does not read today's sites, search results, or filenames as evidence.

The M3.12 rule audit was the first review. This second pass uses a fixed checklist, and the tool's docstring states it in full. Per entry it records:
1. the entry;
2. the estate;
3. the wine;
4. whether the host is an `OFFICIAL_SITE` of that estate in the model;
5. exactly one wine per entry (by construction);
6. the linked files another wine's page also links;
7. whether the page's main heading (else its title) names the wine and no other wine of the estate;
8. that the filename serves only as a locator, including how many file names stand for more than one held edition;
9. suitability for R4;
10. the disposition.

It adds one coverage condition: every wine of the estate has its own entry on the host. Without that, a cross-link to an uncovered wine could not be seen.

### Result

| disposition | entries | which |
|---|---:|---|
| `APPROVED_R4` | **13** | Desmirail: Château Desmirail, Initial, Iris Pourpre, La Perle (fr and en, 8); Rosé de Desmirail (fr and en, 2), **veto only** since the model does not list that wine, so it can refuse a claim and never make one; Moulin d'Issan (fr, en, zh, 3) |
| `REQUIRES_REVIEW` | **13** | Château d'Issan and Blason d'Issan, fr, en and zh (6): their pages link the same 2016–2025 sheets (10 shared in fr and en), so the site cross-links, and which page is the anomaly cannot be decided without filenames or document text. The three Japanese Issan pages (3): they name their wine only in katakana (シャトー・ディッサン, ブラゾン・ディッサン, ムーラン・ディッサン), which the checklist does not read; the Blason title also names シャトー・ディッサン. La Clarté de Haut-Brion on haut-brion.com (3): its double identity is deferred, and the Chinese pages are headed 克兰特侯伯王. La Chapelle on mission-haut-brion.com, fr (1): it shares a release sheet with the La Clarté pages, and the grand vin has no entry, so cross-links cannot be seen |
| `REJECT_INSUFFICIENT_IDENTITY` | **5** | La Clarté de Haut-Brion **Blanc** on mission-haut-brion.com, fr, en and zh (3): every page is headed "La Clarté de Haut-Brion" and none names the Blanc, so the listing does not identify that wine. La Chapelle, en and zh (2): no page under the entry is held, so there is no listing evidence |
| `REJECT_SHARED_DOCUMENT`, `REJECT_OTHER_WINE` | 0 entries | recorded per document instead: every shared file is `REJECT_SHARED_DOCUMENT` in its entry's document list |

**Not all 31 entries are approved.** 13 are approved (11 that attribute, 2 that only veto), 5 are rejected, and 13 are unresolved.

**Effect on the integration dry run** (derived, not re-run):
- The 32 candidates that rest on R4 for Desmirail stay.
- Six lose their R4 identity: Château d'Issan 2004 and 2010, blend, pH and yld (`gs_eccc4afd2daf`, `gs_dd04f3148961`, `gs_e0dab80ce8cc`, `gs_c655425d035f`, `gs_08395b0b4a39`, `gs_ad0c9ecec15c`).
- With the R2 narrowing already decided, the 57 candidates become **51**.
- Issan 2008 is unaffected: R1b and R3 settle it, not R4.

**What would resolve the 13:**
- **Issan château and Blason:** read the shared 2016–2025 sheets to establish which page cross-links the other's documents. That decides whether the château pages are exclusive for 2000–2015.
- **Issan, Japanese pages:** a reader of Japanese confirms the three headings.
- **La Clarté:** the deferred identity decision.
- **Chapelle:** an entry for the La Mission grand vin, so that the site's cross-links become visible.

**A legacy record to keep visible.** The legacy manifest attributes `FT-DM-2010-GB.pdf` to Initial de Desmirail (`pv_01447f513753`), "listed by /wp-json/wp/v2/media". That is the media library (`SITE_LIBRARY`), not a listing relationship. The reviewed listing files the FT-DM sheets under Château Desmirail. A listing attribution must not overwrite the legacy one: it stands beside it, and the disagreement stays recorded.

### The hard R4 rules, confirmed

Each rule is a check in `test-recording-policy.py`.

| rule | policy | check |
|---|---|---|
| Single-wine listing | a document listed only from approved entries of one wine establishes that wine (`LISTING_IDENTITY`) | `r1`: synthetic, and the real Desmirail FT-DM 2005 |
| Shared listing | listed from two wines' pages, it establishes nothing about either; the wine in the filename is not chosen | `r2`: synthetic, and the real Issan 2016 (château and Blason pages) |
| Other-wine listing | listed under another wine, it is evidence against the target (`LISTED_UNDER_OTHER_WINE`) | `r3`: synthetic "GRAND-VIN-2010.pdf" listed under the second wine, and the real Rosé de Desmirail sheet claimed for the grand vin |
| Filename | only a locator: (host, file name) matches a page's link to a held document. There is never `wine = prefix(filename)` | `r4`: "FT-GRAND-2099.pdf" and "FT-DM-2099-FR.pdf" with no listing, refused |
| Listing provenance | the identity comes from the reviewed listing relationship, never from the filename, the URL's shape, the contents alone, a search result or a page title alone. The review's disposition is part of it | `r5` reads no text; `r6` refuses an unapproved entry, a page outside every entry, and the real Issan 2004 |

**R4 establishes the wine, never the vintage.** The vintage must come from the document's own text (its opening, or R2's title block), as it does for every dry-run R4 candidate.

## Part B — the R4 recording contract

An R4 identity is recorded as a listing identity, never as textual evidence.

**Attribution.** The fields:
- `artifact`, `estate`, `wine`, `vintage` and `role`;
- **`method: REVIEWED_LISTING`**, the extension below. A text identity keeps `DOCUMENT_TEXT`;
- `status: ACCEPTED`, only through a reviewed evidence decision, as today;
- `provenance`, the listing provenance below.

`SITE_LIBRARY`, `PAGE_NAME` and `CRAWL_CONTEXT` already exist, but mean other, weaker things: the media library, an undefined page name, and the site something was found on. They must not be reused for this.

**Listing provenance.** It uses the existing Provenance shape:
- `kind: ESTATE_PUBLICATION`, since the listing page is the estate's own publication;
- `source`: the host's source (for example `sr_00226`, desmirail.com);
- `locator`: the listing page URL;
- `quote`: the listing page's heading naming the wine;
- `derived_from`: the DOCUMENT provenance of the text that states the vintage.

Its `code_state` carries everything `recording_policy.listing_identity` returns:
- `identity_basis: LISTING_IDENTITY`;
- `rule: R4` and `rules_version`;
- `site`;
- `listing`: for each linking entry, the entry id, its pages, and `review: {audit: data/audit/r4-listing-review.jsonl, entry, disposition: APPROVED_R4, version}`;
- `relationship: THE_LISTING_PAGE_LINKS_THE_DOCUMENT`;
- `locator`: the (host, file name) keys;
- `locator_role`, stating that the key matches links to documents and is never identity evidence;
- `filename_used_as_identity_evidence: false`;
- the document's artifact and sha256.

**The evidence decision.** The acceptance path today refuses any identity that is not textual. `apply-vintage-creation-manifest.check_review`, used by the acceptance runner, requires `identity_source` in the text rules and says so: "identity is not established by the document's own text". Recording R4 identities therefore needs a separate, explicit listing branch in that check. The branch must require an approved review entry and a textual vintage, and must name `R4` as the identity source. It must not loosen the text branch.

**Mixed cases.** The Desmirail sheets name "Château Desmirail", which is both the estate's name and the grand vin's. The text alone is refused as `ESTATE_ONLY`, and it is the listing that decides. Such a case is `LISTING_IDENTITY`, its text quoted through `derived_from`, never `TEXT_IDENTITY`.

## Part C — the C6 recording contract

**Canonical semantics.** C6 records a yield observation with a reconstructed unit.

It establishes no wine, no vintage, no "harvested yield" meaning and no production volume. The field is `yld`, the field sheetreader's yield row maps to, and the field's existing semantics decide what it means (M3.9 `UNITS['yld'] = 'hl/ha'`). C6 runs only after a settled identity, and only when the reader read no yield.

**The observation.** These are the fields `recording_policy.c6_observation` returns:
- `subject`: the vintage;
- `field: yld`;
- `value: NN`;
- `unit: hl/ha`;
- `raw_value: ["NNhl", "NNha"]`, the two lines as printed. It is never "NN hl/ha";
- `artifact`;
- `locus`, for example "p1: the rendement / YIELD row, value lines at y 457.9 and 468.3" (Grand Mayne 2004);
- `extraction.method: yield-layout/1`;
- `confidence: UNIT_FROM_LAYOUT`;
- `lang`.

**Its provenance** has `kind: DOCUMENT`, the artifact, and `quote: "NNhl | NNha"`: the words relied on, both lines, never "hl/ha". The `code_state` holds:
1. the French line, its text and coordinates;
2. the English line, its text and coordinates;
3. the labels, page and table region that establish the two lines' correspondence;
4. `c6: yield-layout/1` and `unit_basis`, the layout-derived explanation;
5. `unit_derived: true` and `source_prints_hl_per_ha: false`.

It also keeps the guards and the arithmetic, which is `UNAVAILABLE` for 1955 with nothing in its place. These are references to the held document's lines, not copies of its text.

**Reconciliation and canonical value.** The reconciliation is as the value runner's (`ONLY_CANDIDATE`, with a DERIVATION provenance). The canonical value is `{subject, field: yld, value: NN, status: SOURCED, derivation: UNIT_FROM_LAYOUT}`, so that the derived unit is visible to anyone reading only the canonical layer.

**The boundary with the reader:**
- When the reader reads a yield, the yield takes the reader's literal path: `EXPLICIT_LABELLED`, with `raw_value` the printed statement, and C6 does not run.
- A source that prints "37 hl/ha" is a literal value, never C6 evidence. C6 refuses that layout, and `value_path` returns `READER`.
- When the document's statement gives a different yield from C6, the claim is a conflict, with no winner (the dry run's `LAYERS_DISAGREE`).

**The value runner.** `apply-value-manifest.py` today accepts only `source_basis: explicit_document_statement`, one quote string per artifact, and a hard-coded `EXPLICIT_LABELLED`. Recording a C6 value needs an explicit C6 branch in the runner that writes the fields above. Passing the two lines off as one quote would misrepresent the source.

## Part D — provenance vocabulary

| distinction | existing field | literal / textual | derived / listing | schema change |
|---|---|---|---|---|
| identity evidence | `Attribution.method` (enum) | `DOCUMENT_TEXT` | `REVIEWED_LISTING` | **one enum value** |
| value evidence | `Observation.confidence` (text) | `EXPLICIT_LABELLED` (in use) | `UNIT_FROM_LAYOUT` | none: free text |
| what was printed | `Observation.raw_value` (any) | the quote | the two lines, as a list | none |
| canonical mark | `CanonicalValue.derivation` (text) | absent | `UNIT_FROM_LAYOUT` | none: free text |
| provenance kinds | `Provenance.kind` (enum) | `DOCUMENT` | `ESTATE_PUBLICATION`, `DERIVATION` | none: both exist |

No generic provenance framework is added: one enum value, and three vocabulary values in existing free-text fields.

## Part E — the adversarial cases

| case | expected | result | check |
|---|---|---|---|
| R4-1 one wine page → document → target | approve | `LISTING_IDENTITY` | `r1` |
| R4-2 two wine pages → same document | refuse | `SHARED_LISTING` | `r2` |
| R4-3 target filename, listed under a sibling | refuse | `LISTED_UNDER_OTHER_WINE` | `r3` |
| R4-4 wine prefix in the filename, no reviewed listing | refuse | `NO_REVIEWED_LISTING` | `r4` |
| R4-5 the listing names the wine, the text does not | may establish | `LISTING_IDENTITY` (no text read) | `r5` |
| R4-6 ambiguous listing | refuse | `LISTING_ENTRY_NOT_APPROVED` | `r6` |
| C6-1 `37hl` + `37ha` aligned | derive 37 hl/ha | `RECORDABLE`, raw `["38hl", "38ha"]` (Grand Mayne 2004, real) | `c1` |
| C6-2 `37hl` + `38ha` | refuse | C6 refused at guard 4, nothing recorded | `c2_to_c5` |
| C6-3 `37hl` only | refuse | refused at guard 4 | `c2_to_c5` |
| C6-4 `37ha` only | refuse | refused at guard 4 | `c2_to_c5` |
| C6-5 a competing yield row | refuse | refused at guard 7 | `c2_to_c5` |
| C6-6 the layout holds, identity unsettled | do not record | `IDENTITY_NOT_SETTLED` for refused, conflicted and held identities | `c6` |
| C6-7 the reader found a yield | C6 does not run | C6 `NOT_RUN` at guard 2; `READER_PATH` | `c7` |
| C6-8 the source prints `37 hl/ha` | the reader's path | C6 refuses that layout (guard 4); `value_path` → `READER` | `c8` |

## Decision

### R4

- **Approved entries: 13** (11 that attribute, 2 that only veto).
- **Rejected: 5.**
- **Unresolved: 13** (`REQUIRES_REVIEW`).
- R4 runs only on approved entries. A document linked from any entry that is not approved establishes nothing.
- The provenance contract is Part B: `Attribution.method REVIEWED_LISTING`, an `ESTATE_PUBLICATION` provenance carrying the listing, the review disposition and `filename_used_as_identity_evidence: false`, and a textual vintage through `derived_from`.

### C6

- **The canonical value:** `yld = NN`, `status SOURCED`, `derivation UNIT_FROM_LAYOUT`. Its meaning is the field's existing one, and nothing more.
- **The derived unit:** `unit hl/ha` with `confidence UNIT_FROM_LAYOUT`, `raw_value ["NNhl", "NNha"]`, and `unit_derived: true`. It never claims the source prints "hl/ha".
- **The evidence:** the French line, the English line, the labels, page and table region, `yield-layout/1` with its `unit_basis`, and the guards and arithmetic.
- **The boundary:** C6 only after a settled identity and only with no reader yield. A literal "NN hl/ha" is always the reader's path, and a contradicting statement is a conflict.

### Schema impact

MINIMAL SCHEMA EXTENSION REQUIRED

The only extension is one value, `REVIEWED_LISTING`, in the `AttributionMethod` enum. It is not implemented here.

The project's way to add it without touching any protected or fingerprinted file is the extension contract already in force: `docs/schema/historical-m1-contract.json`, `enum_values_added`, which `tools/model_schema.py` merges into the protected Phase 3.4 contract when it loads. A new, separate extension file would need `model_schema.py` to load it, and that file is fingerprinted. That would be a migration to design on its own.

Everything C6 needs fits existing fields.

### Remaining blockers

These are the blockers that actually prevent controlled production integration:

1. **The identity wrapper.** The adopted rules must sit beside M3.4A's `decide` without patching it. They also need R2 narrowed to the title block, the reasoned claim list (two holds, three refusals) and the R4 approved-entry filter. All of this was decided in 5589f7c and in this record, and none is implemented. This blocks all integration.
2. **The `REVIEWED_LISTING` enum value.** It blocks recording any R4 identity.
3. **A listing branch in the acceptance path.** `check_review` refuses non-textual identity by design. This blocks recording any R4 identity.
4. **A C6 branch in the value runner.** It needs two printed lines, `UNIT_FROM_LAYOUT` and the derivation mark. This blocks recording any C6 value.

The 13 unresolved R4 entries do not block integration. R4 simply does not run on them, and only the six Issan 2004/2010 candidates wait on them.

- No production data changed.
- No evidence changed.
- No source registry changed.
- No fingerprinted file changed.
- No production wiring added.
- Nothing pushed.

RECORDING POLICY COMPLETE — NO PRODUCTION MUTATION

## Status since this decision (2026-11-19)

The record above stands as decided. Since then the four remaining blockers have been built (2607da1, a323055), the listing branch and the `REVIEWED_LISTING` value are in force, and the work is pushed through 0ef5a85.

1. **R4 is a separate identity evidence method.** A listing identity passes its own gate, `recording_policy.check_listing_review`. That gate requires:
   - an approved review row and the exact reviewed entry;
   - a single wine, with no shared-document or other-wine veto;
   - the recorded sign-off;
   - the exact sha256 of the artifact.

   It never passes R1's gate as M34A, and `decide` is never its identity source. `decide`'s verdict on the text that R4 annotated is kept as a veto only (`text_check`).
2. **R4 is attribution-only for this integration.** A vintage-creation row whose artifacts all rest on a listing identity is refused when the vintage does not exist. Creating a vintage needs at least one artifact whose own text names the wine beside the year.
3. **C6 (`UNIT_FROM_LAYOUT`) is implemented in the value runner** (`source_basis: layout_derived_unit`). It has no production records.
4. **The adopted vintage forms are not a global change.** The title block and the short name beside the year are accepted only from a claim that the adopted identity rules decided, and the short name only where R1b read it. M3.9's recognition and results are unchanged.
5. **The 13 approved R4 entries are signed off** by the user (2026-11-18, `recording_policy.SIGNOFF`). The 13 entries marked `REQUIRES_REVIEW` and the 5 rejected entries establish nothing.
