# Phase 2.12 — Final evidence reconciliation and Phase 2 exit

**Exit decision: `SAFE — PHASE 2 COMPLETE`**

Started from `2072abe`, 2026-10-25. This phase was read-only: one
document, one test, no canonical change, no evidence written.

---

## 1. Purpose

Phase 2 set out to make the reader's conclusions **evidence**: recorded,
versioned, attributable to the bytes read and the code that read them,
and separate from canonical data. Phases 2 to 2.11 built that, corrected
the reader twice, and audited the cases the corrected reader exposed.

This phase looks for nothing new. It reconciles what those phases
established into three lists:

- what is **done**;
- what is **proposed** but not yet safe to write into canonical data;
- what is **unresolved**.

It then checks that the evidence foundation is sound enough to hand on.
Every item below comes from an existing phase document, test, audit
output or evidence row, and each item names its source.

## 2. Evidence baseline

| | |
| --- | --- |
| repository | `2072abe`, clean, equal to `origin/main` |
| evidence store | `data/evidence/`, append-only, one file per decider version, `verify()` clean |
| versions | v1 13,065 · v2 41,259 · v3 41,259 · v4 40,772 · **v5 40,772**: **177,127 decisions** |
| current evidence | **v5**, reader `7e8cfed1c24e`, commit `fb125c8`, clean tree, 0 duplicate identities |
| provenance failures | v4 123, v5 123: 103 `ARTIFACT_NOT_FOUND`, 20 `ARTIFACT_NAME_MISMATCH`; typed, separate from decisions |
| provenance model | exact folder + exact name resolution, SHA-256 of the bytes read (bracketing the reader), full commit + dirty state + status hash; v4+ rows refuse legacy fields |
| idempotence | an exact rerun of v4 and of v5 each appended 0 |
| canonical files | `fiches.js`, `field-src.js`, `cuvee-src.js`, `chateaux.js`, `cuvees.js`, `sources.json` unchanged from `2072abe` |

(The spec gives the fingerprint as `7e8cfed1c24`. The recorded
fingerprint is the 12-character `7e8cfed1c24e`, of which that is the
prefix.)

## 3. Completed corrections (A — COMPLETED / SAFE)

Implemented, validated, and in v5. Phase 3 needs only to preserve their
assumptions.

| # | correction | established in | validated by |
| --- | --- | --- | --- |
| A1 | **Persistent, versioned decision store.** Refusals and acceptances recorded with their reason, decider version and reader fingerprint; decision identity = artifact, folder, estate, wine, field, vintage, target estate/wine/role/vintage, version | Phase 2, 2.1 | `test-phase2`, `test-phase21`; a rerun appends 0 |
| A2 | **Evidence-store reorganisation.** One file per version under a 40 MB part limit, an index of hashes, LF line endings, and a migration proven byte-for-byte against `a36b35c` | 2.4 | `test-phase24`; `migrate-evidence-store.py --check` |
| A3 | **Provenance-safe resolution.** No basename lookup; exact names; SHA-256 of the bytes read, confirmed after reading; git commit, dirty state and status hash; typed failures; the store's own output excluded from the dirty check | 2.5, 2.7 | `test-phase25`, `test-phase27`, `test-phase210`; 278/278 wrong-bytes decisions now carry the audited hash |
| A4 | **Positive second-wine mode and colour-preserving marks.** A document must be shown to be the second wine's; "blanc" kept where it tells two wines apart. **Echo de Lynch-Bages is now recognised**: in v5 all 64 Echo documents are accepted for their own vintage, 0 of 103 grand-vin and 0 of 52 Blanc documents are accepted as the Echo, and the five missing vintages (2008, 2009, 2010, 2015, 2016) are recognised, **with no estate-specific exception** | 2.3, confirmed in v4, v5 | `test-phase23`, `test-phase26`, `test-phase210` |
| A5 | **Specific second-wine identity.** Generic second-wine recognition (`is_second_wine`, unchanged) is separated from *this* second wine; wines no list holds are reported as `UNLISTED_WINE`, not promoted. Withdrew the five known bad acceptances and Haut-Bailly II; restored 31 legitimate ones (Les Hauts du Tertre, La Bastide Dauzac, Haut de Carles) | 2.6, confirmed in v4 | `test-phase26`; the v3 → v4 comparison |
| A6 | **Grand-vin identity.** A wine's own words, common ones included, are kept against the grand vin. **87 false grand-vin acceptances withdrawn, 0 genuine withdrawn, 0 new**; the 8 Les Hauts du Tertre grand-and-second conflicts are gone | 2.9, confirmed decision for decision in v5 | `test-phase29`, `test-phase210`; the prediction matched 87/87 |
| A7 | **V5 evidence baseline.** Every v4 question asked again by the corrected reader, reconciled one for one with v4 | 2.10 | `test-phase210`; idempotent |

**7 completed corrections.** All are infrastructure or reader
corrections. **None is a canonical-data correction.**

## 4. Proposed corrections (B — PROPOSED / REQUIRES EXTERNAL OR DOMAIN EVIDENCE)

Strongly indicated by Phase 2 evidence, and **not written into
canonical data**.

### B1. Les Terrasses de Saint Christophe — `PROPOSED_CORRECTION_PENDING_DOMAIN_EVIDENCE`

Source: `docs/PHASE-2.11-TERRASSES-ATTRIBUTION-AUDIT.md`.

**Findings:**

- **Documents.** 16 distinct documents, each byte-identical in Tour
  Saint-Christophe's and Bellefont-Belcier's folders: 32 manifest rows,
  all with no estate.
- **v5 decisions.** 15 of the Tour Saint-Christophe copies are accepted
  as Tour Saint-Christophe's grand vin; 1 is a press document. The
  Bellefont-Belcier copies are refused, by the accidental "les"
  abbreviation (12) and as trade listings (4).
- **The source.** One Vignobles K group library on `vignoblesk.com`,
  crawled under two properties. Every sheet carries the seven-property
  group letterhead.
- **What the documents say.** The 2016–2019 PRODUCT-SHEETs state that
  Les Terrasses de Saint Christophe "is the **second label** of Château
  Tour Saint Christophe". The 2017–2023 sheets call it a Vignobles K
  cuvée and name Tour Saint-Christophe only in the letterhead.
- **Classification:** all 15 v5 acceptances `MISATTRIBUTED` as the grand
  vin. The canonical data lists no second wine for Tour Saint-Christophe,
  which is why the grand-vin check had nothing to refuse them for.

**Proposed:**

1. Record "Les Terrasses de Saint Christophe" as Château Tour Saint
   Christophe's second wine.
2. Attribute the 16 Tour Saint-Christophe-folder rows to it, role
   second.
3. Reject the 16 Phase 2 `HIGH_CONFIDENCE` attributions of the
   Bellefont-Belcier copies, which rest on the letterhead only.

**Pending:** an outside source for 2020–2023. Those sheets do not say
where the wine comes from, so it may have become a group négoce cuvée.

**Proposals already on file that must not be applied as they stand:**

- `data/proposals.jsonl` holds **15** "set the manifest's `estate` to
  'stem-chateau-tour-saint-christophe'" actions, and they are exactly
  these 15 documents. The estate is right, but with no wine set they
  would read as the grand vin's. They need the wine and role added.
- `data/attribution-candidates.jsonl` marks the 16 Bellefont-Belcier
  copies `HIGH_CONFIDENCE`.

### B2. Echo de Lynch-Bages manifest identity — `PROPOSED_CORRECTION_PENDING_CANONICAL_DECISION`

Source: Phase 2.1 (`wine-identity.jsonl`: 50 `MANIFEST_METADATA_WRONG`;
`proposals.jsonl`: 50 × "set the manifest's `wine` to 'Echo de
Lynch-Bages'"), 2.2, 2.3, and v4/v5.

- **The finding.** 50 Echo sheets are filed in the manifest as Blanc de
  Lynch-Bages. Since v4, the corrected reader accepts the Echo documents
  as the Echo.
- **Evidence is sufficient.** The documents and the reader agree; no
  external source is needed.
- **It was held back on purpose.** Phase 2.2 to 2.10 each said explicitly
  that the 50 corrections were not to be applied, so the reader could be
  proven first, which it now has been (A4).
- **Untouched:** the 13 existing Echo records in `cuvees.js`, and the 50
  manifest rows (`test-phase23` asserts "50 sheets still filed as
  Blanc").

### B3. Les Murets de Caillou — `PROPOSED_CORRECTION_PENDING_DOMAIN_EVIDENCE`

Source: Phase 2.4 §10, 2.6, and v4/v5 (`UNLISTED_WINE`).

- **The document.** `Fiche-technique-FR-MURETS-BLANCS-2023` titles
  itself "LES MURETS DE CAILLOU 2023 · Second Vin blanc sec du Château
  Caillou".
- **The list.** Caillou lists only Les Erables de Caillou.
- **Proposed:** add Les Murets de Caillou to Caillou's wines.
- **Pending a domain decision on its role.** The document makes it the
  second wine of the estate's **dry white**, which the current model
  (one `second` per estate) does not represent. There is one document,
  for one vintage.

**3 proposed corrections.** None is applied.

## 5. Unresolved cases (C — UNRESOLVED / NOT SAFE TO CORRECT)

Phase 2 evidence does not justify a canonical correction for these.
Their current state is preserved: no uncertainty is turned into absence,
and no contextual attribution into identity.

| # | category | what is known | why not correctable now |
| --- | --- | --- | --- |
| C1 | **Other unlisted wine names**: Lacroix-Martillac, Les Arums de Lagrange, Pagus de Lagrange, Les Divertissements de Malle, R de Real Caillou; and Tour Saint-Christophe "ANGELA BLANC" | names found by Phase 2.6's wine-shaped-name model in filenames, addresses and titles (`UNLISTED_WINE`, 97 v5 contexts); Phase 2.11 found ANGELA BLANC in the group library | only the names were established: not the wine's role, colour, years, or for some even the estate. Some of the 97 labels are page furniture (Phase 2.6 §10). |
| C2 | **Names the grand vin's own name contains**: Vivens (Durfort-Vivens), Ségla (Rauzan-Ségla), Mondot (Troplong Mondot); Margaux du Château Margaux | Phase 2.8 category B; unchanged by 2.9 by design | an identity-model limit: no name test can separate them, and only document-level identity can |
| C3 | **Name variants and duplicate listings** | wines written in documents in forms the lists do not hold: "Le Petit **Smith** Haut Lafitte", "Croix-Beaucaillou", `G-Guiraud` (7 v5 grand-vin acceptances of other wines' sheets remain, Phase 2.9 §7, 2.10 §8); La Croix de Beaucaillou / La Croix Ducru-Beaucaillou listed as two wines; 9 spelling-variant pairs (Phase 2.8 E); Haut-Bailly II listed apart from La Parde | aliases and renames need domain decisions per wine; the lists were deliberately not edited |
| C4 | **The 908 unattributed artifacts** | `attribution-candidates.jsonl`: 244 HIGH_CONFIDENCE, 444 CANDIDATE, 95 CONFLICT, 76 REJECTED, 49 UNRESOLVED; `proposals.jsonl`: 908 estate-attribution entries and 143 manifest-vintage cases marked "the right year needs a person" | built from v2-era evidence, before both reader corrections; Phase 2.11 showed HIGH_CONFIDENCE can rest on a group letterhead (the Bellefont-Belcier copies); not safe to apply without regeneration against v5 |
| C5 | **Artifacts never evaluated** | 103 files the manifest names that are not on disk; 20 that exist only under another spelling | no bytes to read; a manifest or corpus matter |
| C6 | **Other cuvées** | 18,449 v5 contexts recorded `GUARD_HAS_NO_CUVEE_MODE` | the reader has no mode for a named cuvée; their grand-vin questions are evaluated (A6), and the cuvée questions are not |

**Known reader and tooling limitations, carried forward.** These are
documented, measured, and not blocking: no current evidence needs new
reader work to explain it.

- `is_second_wine`'s "et" check never fires (2.4 §11, 2.6 §2). Left
  alone because it would change grand-vin refusals.
- "second label" is not among the second-wine phrases (2.11).
- `abbreviates_other_wine`'s accidental "les"-prefix refusals hide a
  sister-estate and non-wine document gap (2.9 §8).
- The grand-vin path has no unlisted-name model (2.11).
- The field-conflict model records only under `--apply` (2.7).
- `read-fiches.py` still falls back to a basename search (2.5, 2.7).

## 6. Canonical safety

Read-only audit against the Phase 2.12 starting state, `2072abe`:

- `git diff --name-only 2072abe` over `data/fiches.js`,
  `data/field-src.js`, `data/cuvee-src.js`, `data/chateaux.js`,
  `data/cuvees.js` and `data/sources.json` is **empty**.
- **No canonical record cites a Terrasses document**: `fiches.js`,
  `field-src.js`, `cuvee-src.js` and `fiches-nl.js` were searched.
- Tour Saint-Christophe still lists no second wine, and no canonical
  list names Les Terrasses.
- The 50 Echo manifest rows and 13 Echo records are as they were.

**The Phase 2 investigation did not contaminate canonical data.**
Evidence findings and proposed corrections remain separate from
canonical truth. Every proposal above is a proposal.

## 7. Evidence safety

- The store verifies. `data/evidence/` is byte-for-byte as at `2072abe`:
  no row was written, no historical file changed, and no identity was
  rewritten.
- v5 is intact: 40,772 decisions, one reader, one clean commit.
- **No v6 exists.** The next evidence version belongs after the
  canonical and domain decisions of §4 are made. A v6 run would then
  withdraw the Terrasses grand-vin acceptances through the existing rule
  (Phase 2.11 §7) and evaluate the Echo rows under their corrected
  identity.
- The store remains append-only.

**Tests.** All suites pass:

| suite | result |
| --- | --- |
| reader | 110 ok |
| data | 11 |
| Phase 2 | 30 |
| Phase 2.1 | 27 |
| Phase 2.2 | 17 |
| Phase 2.3 | 47 |
| Phase 2.4 | 26 |
| Phase 2.5 | 48 |
| Phase 2.6 | 61 |
| Phase 2.7 | 16 |
| Phase 2.8 | 17 |
| Phase 2.9 | 47 |
| Phase 2.10 | 23 |
| Phase 2.11 | 11 |
| **Phase 2.12** | **14** (new) |

## 8. Phase 2 exit decision

| condition | |
| --- | --- |
| evidence store valid | yes |
| provenance model valid | yes |
| v5 internally consistent | yes: unique identities, one reader, one clean commit, reconciled with v4 |
| reader corrections validated | yes: A4–A6, each predicted and confirmed |
| known attribution problems classified | yes: B1, C4 |
| Terrasses recorded as proposed, not silently corrected | yes: B1; `test-phase212` asserts it is not canonical |
| no canonical contamination | yes |
| unresolved cases remain unresolved | yes: §5 |
| no new reader work needed to explain the current evidence | yes: every remaining effect is a documented limitation |
| canonical changes separated from evidence findings | yes |

**`SAFE — PHASE 2 COMPLETE`**

## 9. Handoff to Phase 3

The next phase is **scope definition and authoritative universe
construction**: deciding which estates, wines, roles and vintages the
dataset claims to cover, and building that universe with its sources.
That is the ground on which the proposals of §4 can be decided and the
unresolved categories of §5 placed.

**It is not normalization implementation**, and it does not begin with
canonical corrections. Phase 3 inherits:

- v5 as the evidence baseline, with its reader `7e8cfed1c24e`;
- the provenance and store discipline of A1–A3;
- the three proposals of §4 and the six unresolved categories of §5,
  untouched.
