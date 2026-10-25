# Phase 6.0 — Product & domain gap audit

Read-only. The only file this phase adds is this document. Every figure was measured from the
repository at `fd2eb81`: the model tables under `data/model/`, the generated `data/app/` files and
`assets/app.js`. Line references are to `assets/app.js` unless another file is named.

## 1. Executive summary

The normalized model can represent far more than the application shows. Most of what it cannot show
was never populated, though; the UI is not withholding it.

- **Provenance is the clearest gap.** The model keeps a source per field. 5,827 canonical values have
  their own field-level document. 6,830 carry only their record's source, 131 an ambiguous source and
  171 none. The generated application files drop all of this and keep one filename and one URL per
  vintage record. The page then shows a single "Read the estate's own sheet" link under every figure
  of a vintage. Of the 4,691 canonical values on records with such a link, the linked sheet is the
  value's own source for **1,833 (39 %)**, a *different* document for **612 (13 %)**, and unestablished
  for **2,245 (48 %)**. The UI implies a provenance that holds for a minority of the values it sits
  beside. **P1**
- **The UI shows legacy contradictions without saying so.**
  - Batailley's facts say "Second wine —" while its wine switcher offers *Lions de Batailley — second
    wine*.
  - Haut-Bailly's facts name *La Parde de Haut-Bailly* while its switcher names *Haut-Bailly II*.

  The model records both as findings (CONFLICT, IDENTITY_UNCERTAIN), but the UI shows both values as
  plain facts. **P1** presentation over **D1**/**Q0** substance.
- **The temporal model is built but empty.** All 639 estate–wine relationships, 684 rank claims, 399
  classification memberships, 376 appellation memberships, 1,104 names and 272 locations hold "valid
  from UNKNOWN, still open". Only the six classification editions carry a year. There is no historical
  fact to show yet, so a temporal UI now would show nothing. **R0/Q0, not P1**
- **The harvested corpus is not connected.** 163,582 observations from the Phase 3.3 harvest have
  attribution candidates on Phase 3.0 universe ids (`u-…`) with status `CANDIDATES_ONLY`. No stage
  maps them to model estates, so neither the model nor the app can use them. **D1/Q0**
- **The core domain distinctions largely hold:**
  - the UI does not equate an estate with one wine;
  - rank and colour are kept apart internally;
  - a sparse estate is labelled as such;
  - "not produced" is distinguished from "no rating".

  The weaker points are smaller: colour is never shown, `'—'` is rendered literally, "another cuvée"
  stands for an unknown rank, and the settings text contradicts the Dutch overlay.

**Recommended next implementation:** carry each value's own provenance into the generated application
data, and show it at the figure, not the record (§13). It is small, it exercises the model's
provenance, legacy-reference and placement layers end to end, and it removes the most misleading
signal in the product.

## 2. Repository and application baseline

| | |
|---|---|
| HEAD | `fd2eb81` (Phase 5 closure), equal to `origin/main`; working tree clean |
| Application source | `model`: the 23 contract files come from `data/app/` (`tools/app-source.py`); the live site serves the same (cache `bordeaux-classified-v169`) |
| Phase 5 verification | test-phase5 25/25, test-phase4 66/66, all 22 suites pass (closure run at `fd2eb81`) |
| Documents read | PHASE-5-APPLICATION-SOURCE-SWITCH, BACKLOG, PHASE-3.4-DOMAIN-MODEL and its REVIEW, PHASE-4-MIGRATION-BASELINE and REPORT |

One earlier description needed correcting against the repository. The brief's *FicheFamily /
FicheInstance* survives only as **DocumentFamily**. The 3.4 review (§11) made it "a derived extraction
aid attached to a Source … not a domain entity", and `data/model/document/families.jsonl` has 0 rows
by design ("derived on demand", 3.4 review §19).

## 3. Current user-facing information architecture

There are seven tabs (`index.html:41-47`; `setView` 4477-4501):

| Tab | What it shows |
|---|---|
| Appellations | cards by bank; each page holds History, Terroir and "The wines" prose, a sources line, a vintage table, and estates grouped by classification (699-780). "No sourced note for this appellation yet." where none exists (756) |
| Classifications | "Official classifications" and "Never classified"; each page covers origin, revision, "The list shown here", a superseded warning and tiers (788-884) |
| Grapes | variety cards, with counts taken from the blends held (1494-1555) |
| Producers & map | estate cards grouped by tier, the map, and the only search box (1591+, 548-570) |
| Vintage reports | regional cards per year (4362-4407) |
| Compare | up to six wines as columns (961-1108) |
| My cellar | the user's bottles, in `localStorage` (1269+) |

**The estate drawer** (`openDrawer` 2925-3079) shows, in order:

1. a head with the rank pill;
2. facts (2944-2965): Classification · year, Appellation, Vineyard, Proprietor, Second wine,
   Classified for, Website;
3. the sparse-estate notice (2969);
4. History with its sources (2986), Terroir (2991), and "The ground, in the estate's words";
5. House style;
6. "Typical blend" (3001);
7. "Which wine" (3011);
8. "All vintages" rows (3027);
9. earlier vintages.

**An expanded vintage row** (`vintageRow` 4031-4093, `fichesBlock` 3284-3405) shows:

- the rating with its critic panel;
- "Blend, YEAR" over a ghost bar of the usual blend;
- the facts: yield, alcohol, months in barrel, new oak, pH, residual sugar, total acidity, serving
  temperature;
- the cellar note;
- the food suggestion;
- the scores reprinted on the sheet;
- "Read the estate's own sheet".

**Search** (559-560) matches name, appellation, commune, owner and the `second` string. The
autocomplete (`acSearch` 2820-2845) matches region and estate names only.

## 4. Information-path audit

The path is source → evidence → model → `data/app/` → UI.

"Temporal" means the model has a Validity or bound for it; "populated" means one is actually set.

| Concept | Stored (model) | Explicit | Temporal: can / populated | Several statements | Provenance kept | Reaches `data/app/` | Visible in UI |
|---|---|---|---|---|---|---|---|
| Estate | `identity/estates` 470, `names` | yes | yes / no | names: yes | yes | as legacy records | yes |
| Wine | `identity/wines` 639 | yes (grand vin minted) | — | names: yes | yes | grand vin implicit in the estate record; others in `BDX_CUVEE_WINES` | yes, through "Which wine" |
| Wine–estate relationship | `state/estate-wine` 639, all PRODUCED_BY | yes | yes / no | yes (by kind) | yes | implicit (keyed by estate) | implicit |
| Vintage | `identity/vintages` 5,286 | yes | — | — | — | as 'estate\|year' keys | yes |
| Classification | `classification-*`: 6 schemes, 6 editions, 399 memberships, on wines | yes | yes / editions only (6 years) | yes | yes | as `cls`/`growth` on the estate | rank pill, `· year`, class pages |
| Appellation | `appellations` 21, memberships 376 (on wines) | yes | yes / no | yes | yes | one string per estate | yes |
| Fiche / document | `artifacts` 37,067, `placements` 19,394, `attributions` 12,128 | yes | ArtifactDate defined / 0 rows | yes | yes | one `src` and `url` per record | a link only; `src` is never shown |
| Source | `sources` 367, `source-estate` 409 | yes | yes / no | yes | yes | websites (url, tag) | Website fact with a source tooltip |
| Observation | `observations` 22,437 (+163,582 harvested, unattached) | yes | `asserted_at` / no | yes | yes | values only | values only |
| Provenance | `cross/provenance` 25,895; canonical status per value | yes | — | — | — | **dropped** (one record `src`) | record-level link (§8) |
| Quality / anomaly | `cross/findings` 444; `checks/quality-audit` | yes | — | — | yes | no | no |
| Historical change | `IdentityTransition` 0, `Ownership` 0, validity unpopulated | defined | yes / no | yes | yes | no | prose only (`ch.history`) |

## 5. Domain mental-model audit

| Risk | What the app does | Finding |
|---|---|---|
| Estate ≠ wine | `winesOf` (3712) lists the grand vin and then every listed wine; "Which wine" appears with two or more (3854). The model has 121 estates with two or more wines (84 with two, 23 three, 8 four, 3 five, 3 six). | **Holds.** One weakness: other wines' names are not searchable (559-560, 2820-2845): **P2** |
| Grand vin ≠ all production | `ROLE_LABEL` = the grand vin / second wine / another cuvée (3736). There is no third or prestige concept. "another cuvée" stands for the model's UNKNOWN rank (58 wines, legacy term `other`). | **Holds without inventing a rank.** The label reads as a statement ("another") where the model means "rank not known": **P2** |
| Rank ≠ type | Colour is used internally only (`wineCat` 3443-3451); it is never displayed. White wines are classified only through the raw "Classified for: red and white" text (2949). The 5 white Graves wines minted with an unknown name, and the 2 that wait, cannot be shown. | **Internally separate, invisible to the user.** Showing colour: **P2**; the classified whites: **P2 / D1 (D8)** |
| Estate mention ≠ estate wine | Wines reach the UI only from `BDX_CUVEE_WINES` (the model's PRODUCED_BY relationships). Harvested mentions never reach the model. | **Holds.** Only one relationship kind is populated (PRODUCED_BY, 639); the others the model defines are unused: **F0** |
| Plantings ≠ assemblage | The estate blend is "Typical blend" (3002) and the ghost bar's caption is "the estate's usual blend" (2676). When missing, BDX_PLANTINGS is used, captioned "what the vineyard is planted with" (3297-3302). | **Labelled apart.** But the estate blend is itself undecided between the two (D1 per estate; 172 AMBIGUOUS_SEMANTICS findings), and the UI calls all of it "typical blend": **D1** |
| No information ≠ negative information | The UI distinguishes "not produced" (`notProduced` 358, 4035) from no rating and no sheet. Missing figures are omitted silently. A grand vin without a sheet says nothing (3286); a cuvée row says "No sheet on file" (4156). `second: '—'` renders literally as "Second wine —" (2948; 34 estates). | **Partly.** The model holds more states than the UI can say: extraction status for 37,067 artifacts (NEEDS_OCR 374, FAILED 2, PENDING 287 …) and RankAbsence for 34 estates. **P2**; the literal `'—'`: **P1** (§12) |

## 6. Longitudinal / temporal audit

Measured:

| Record | Validity held |
|---|---|
| estate–wine, rank assertions, classification and appellation memberships, names, locations (3,474 records) | from UNKNOWN, to OPEN (all of them) |
| classification editions (6) | from EXACT year, to OPEN |
| IdentityTransition, Ownership, ArtifactDate, ArtifactRelation | 0 rows |

What a user can distinguish today:

- the classification **edition year** (2944, 811, 851) and a superseded list (860-865);
- **vintage-specific** values (one record per year);
- the regional **vintage report**.

They cannot distinguish current from historical state, document date, revision, later correction or
unresolved conflict.

This is **not** information hidden by the UI. The model holds no dated state, transition or document
date to show, so a temporal presentation built now would display only "unknown". The capability
exists; the data does not. **R0** (dated facts need extraction: the 3.4 review's "history as dated
events", class F) and **Q0** (artifact dates unpopulated).

Two temporal statements that do exist are flattened:

- **Echo de Lynch-Bages:** a rename or succession from vintage 2008. It is held only as a proposal
  (`data/model/checks/proposal-compatibility.json`), not in the model; D2 is not adopted.
- **Corbin 2022 "no second wine this year":** a vintage-scoped RankAbsence is representable
  (test-phase4 t13), but no such record exists.

## 7. Fiche audit

| Question | Answer, with evidence |
|---|---|
| 1. Can the app identify a recurring fiche structure? | **No.** `document/families.jsonl` has 0 rows by design: families are derived on demand, per source, as an extraction aid (3.4 review §11: 849 families in the harvest analysis). Neither the app nor `data/app/` knows a family. |
| 2. Structural field identity versus a vintage value? | **In the model, partly.** An observation has `field` and, for harvested ones, `raw_label` (`data/discovery/observations`: label, locus, method). The 22,437 legacy observations carry the dataset's field names, not the printed label. **The app has a fixed field set** per record, so structure and value are not separable there. |
| 3. Structure changed over time? | **No.** There are no families or ArtifactRelations (`REVISION_OF`, `LANGUAGE_VERSION_OF`: 0 rows). |
| 4. Instances connected to one family? | **No**, for the same reason. The only link between a wine's vintages is the wine itself. |
| 5. Is an older fiche used as the value source for a newer vintage? | **Not by the app:** `fiche(ch, yr)` reads exactly `estate\|year` (3115), and the blend's ghost bar is labelled as the usual blend, not this year's. **In the data,** values come from the legacy reader. Phase 2's hand pins refuse known reuses (for example Malescot 1995's note, evidence v1 PINNED_BY_HAND), but 2,245 linked values have no field source, so for those the document they came from is not established. **Q0, not measured further here.** |
| 6. Provenance at the right level? | **Model: per field** (canonical status per value). **App: per record**, and the wrong document for 13 % of linked values (§8). |

Earlier fiches are not used as value sources by the app. The project's rule that they are "schema
context, not value sources" is not yet implementable: schema context needs families, which are not
built.

## 8. Provenance and evidence audit

| Layer | In the model | In `data/app/` | In the UI |
|---|---|---|---|
| Source | 367 Sources; source-estate links | websites (url, tag) | Website fact with a source tooltip (2953-2963) |
| Document / artifact | 37,067 artifacts, 19,394 placements | the record's `url` (1,378 fiche and 326 cuvée records) and `src` filename | a link; `src` never shown (§3, 3145-3155, 3388-3399) |
| Observation / statement | 22,437 legacy + 163,582 harvested (unattached) | values only | values only |
| Extracted value | the observation's `value`; harvested `raw_label` and `value` | — | — |
| Canonical value | 12,959, each with a status | the value only | the value only |
| Reconciliation | 12,959 (all LEGACY_RETAINED, one candidate each) | — | — |
| Quality / anomaly | 444 findings, quality audit | — | — |

**Where value jumps straight to displayed value:** every figure in the vintage fact grid (yield,
alcohol, barrel months, new oak, pH, sugar, acidity), the blend, and the estate facts (hectares,
owner). No per-figure source is shown. The record link is the only provenance in reach, and it is
right for 39 % of the linked canonical values (§1).

Prose lines carry "this estate", "this estate, translated" or "Bordeaux" as their source label, linked
to the record's sheet (`srcLine` 3145). They inherit the same record-level limitation.

Elsewhere provenance is good: ratings ("gathered by bordoverview.com", 441-443), the derived drink
window ("derived" flag, 4011-4016) and phenology ("ISVV · this estate").

## 9. Open domain questions

| Question | Classification | Why |
|---|---|---|
| Echo, rename or succession (D2) | **D1 · safe to defer** | Recommended RENAMED, not adopted. The app works: Echo is a wine of Lynch-Bages. Only its history before 2008 is missing. |
| Conflict policy (D5) | **D1 · safe to defer for the app** | Every current value is a single legacy candidate (12,959 reconciliations, one candidate each). It becomes **model-blocking** only when harvested observations enter as competing candidates. |
| The four Graves white names (D8) | **D1 · presentation issue** | 5 white Graves wines minted with an unknown name and 2 waiting. The app cannot show them anyway (§5). |
| Les Terrasses after 2019 | **R0 · safe to defer** | Not in the model (Tour Saint-Christophe has its grand vin only); a proposal with no evidence for 2020–2023. |
| 11 second-wine names differing from estate lists | **D1 · presentation issue** | Visible as two contradicting facts (La Parde against Haut-Bailly II). The identities are not decided. |
| Plantings versus assemblage | **D1 · data quality** | Model resolved (D1); the 172 estate blends are undecided per estate, and the UI calls them all "Typical blend". |
| Owners | **D1 · safe to defer** | 172 owner strings are kept as observations; no Party or Ownership was minted (L10). The app shows the string, as before. |
| Unresolved identities (57 identity-map entries) | **Q0 · safe to defer** | saint-julien, 2 unlisted slugs, the undecided seconds, 2 Graves whites, L'Enclos. None affects a page beyond §5's contradictions. |
| Unresolved filename references (281) | **Q0** | 242 ambiguous, 39 with no candidate. They become product-relevant once per-field provenance is shown (§13): such a value would honestly read "source ambiguous". |
| Harvest attribution (163,582 observations) | **D1 + Q0 · model-blocking for new data** | Candidate attributions point at universe ids that no stage maps to model estates. Acceptance needs a mapping and D5. |

## 10. Coverage and completeness

| Entity / relationship | Total | Populated | Missing / unresolved | Legacy / unsourced | Evidence-backed |
|---|---:|---|---|---|---|
| Estates | 470 | 470 named | 1 legacy id unresolved (saint-julien) | names LEGACY_UNSOURCED | — |
| Estates with a grand vin | 458 | 458 | 12 Pomerol list names unsupported | — | — |
| Wines | 639 | type known 312; name known 634 | type UNKNOWN 327; name UNKNOWN 5 | from legacy lists | — |
| Estate–wine relationships | 639 | 639 PRODUCED_BY | 121 estates with ≥ 2 wines; 12 estates with none | all DATASET | none from a producer statement |
| Rank claims | 684 | FIRST 458, SECOND 163 | UNKNOWN 63 | all claimant DATASET | 0 PRODUCER / CLASSIFICATION_BODY |
| Vintages | 5,286 | 5,179 with an observation; 3,790 with a canonical value | wines with no vintage: 256 of 639 | — | — |
| Grand vins with ≥ 1 vintage record | 241 of 458 | | 217 without | | |
| Classification memberships | 399 (398 wines) | 399 | 212 differences against the authoritative universe (quality audit) | dataset edition | authoritative lists separate (I21) |
| Appellation memberships | 376 | 376 | compact Saint-Émilion and Pomerol estates rely on the app default | LEGACY_UNSOURCED | — |
| Canonical values | 12,959 | — | 131 ambiguous | 6,830 record only, 171 unsourced | **5,827 field source** |
| Observations (legacy) | 22,437 | — | — | 2,690 unsourced, 8,007 record source | 9,039 field source; 2,462 derived; 61 cited |
| Observations (harvest) | 163,582 | — | all unattached (CANDIDATES_ONLY) | — | first-party, by extraction |
| Fiche documents (artifacts) | 37,067 | EXTRACTED 35,707 | NEEDS_OCR 374, PENDING 287, STORED_ONLY 610, UNSUPPORTED 87, FAILED 2 | — | — |
| Fiche families | 0 (by design) | — | — | — | 849 in the 3.4 analysis only |
| Attributions | 12,128 | estate 12,124, wine 4,819, vintage 4,795 | 723 manifest artifacts with no estate | method LEGACY_UNKNOWN (D6) | — |
| Filename references | 13,230 | ACTIVE 12,949 | AMBIGUOUS 242, no candidate 39 | — | — |
| Translations | 1,072 (Dutch) | — | — | legacy | — |

## 11. Application-versus-model gaps

These are demonstrated by the repository: the model holds the information, `data/app/` or the UI does
not.

1. **Field-level provenance:** status per canonical value, the field's own document. `data/app/`
   keeps one `src` and `url` per record (§8).
2. **Quality findings:** 444, including CONFLICT 7, IDENTITY_UNCERTAIN 111 and AMBIGUOUS_SEMANTICS 179.
   None reaches the app, so contradictions show as facts (§1).
3. **Rank absence:** 34 RankAbsences. The app gets the raw `'—'` string.
4. **Wine type:** 312 wines with a known type. The app gets the colour but never shows it.
5. **Classification on the wine:** 399 memberships, including 6 on white Graves wines. The app gets
   `cls`/`growth` per estate, so it cannot show which wine is classified.
6. **Artifact state:** extraction status (NEEDS_OCR, FAILED, …) and the placement status of 123
   missing or name-mismatched files. None reaches the app.
7. **Rank claimant:** every claim's claimant (all DATASET today). The app cannot say who claims a rank.

Not counted as gaps, because the model holds nothing to show: historical state, transitions,
ownership, document dates, revisions, families and wine descriptors (§6, §7).

## 12. Findings by severity

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| F1 | **P1** | One sheet link stands for every figure of a vintage. It is the value's own source for 39 % of linked canonical values, another document for 13 %, and unestablished for 48 %. | §1, §8; `fichesBlock` 3388-3399, `srcLine` 3145; measured on 4,691 values |
| F2 | **P1** | Contradictory legacy facts are shown as plain facts: Batailley "Second wine —" beside a listed second wine; Haut-Bailly *La Parde* beside *Haut-Bailly II*; 11 differing names in all. | 2948, `wineSwitcher` 3854; findings CONFLICT and IDENTITY_UNCERTAIN |
| F3 | **P1** | `second: '—'` renders literally as "Second wine —" on 34 estates, where the model holds a RankAbsence ("no second wine"). | 2948 |
| F4 | **P2** | Colour or type is never shown; white and sweet other wines are not marked as such. | `wineCat` 3443-3451 |
| F5 | **P2** | "another cuvée" stands for an unknown rank (58 wines). | 3736 |
| F6 | **P2** | Other wines' names are not searchable. | 559-560, 2820-2845 |
| F7 | **P2** | The settings note says the châteaux's words stay "in the language it was published in", but Dutch overlays replace them (`withDutch` 3101-3113). | `index.html:33-34` |
| F8 | **P2** | Missing figures are omitted silently; a grand vin without a sheet says nothing. The model's extraction and placement states are not used. | 3286, 4156 |
| F9 | **D1** | The estate blend is undecided between plantings and assemblage (172 records), yet labelled "Typical blend". | 3002; 172 AMBIGUOUS_SEMANTICS |
| F10 | **D1** | The harvest (163,582 observations) is unattached to model estates; it needs a universe-to-estate mapping and D5 before any of it can be accepted. | `data/discovery/attribution.jsonl` (CANDIDATES_ONLY on `u-…`) |
| F11 | **D1** | D2 Echo, D8 Graves whites, the 11 seconds, owners: decisions pending; none blocks the current product. | §9 |
| F12 | **Q0** | 2,245 linked canonical values have no field-level source; 281 filename references are unresolved; 327 wine types are unknown; 217 grand vins have no vintage record. | §10 |
| F13 | **R0** | Dated history (ownership changes, renames, rank changes) is not extracted, so the temporal model is empty. | §6 |
| F14 | **F0** | Families, revisions and language-version relations are unbuilt; nothing depends on them yet. | §7 |
| F15 | **F0** | Rosé is unhandled in the UI (1 wine). | `winesOf` 3714 |

No **P0**: no core concept is misrepresented so badly that users cannot use the product. No **D0**: the
model can represent every concept raised. Its temporal, provenance and absence structures are present
and validated (test-phase4); they are only unpopulated or unexposed.

## 13. Recommended next implementation

**Immediate: per-figure provenance in the vintage view (F1, with F12's states made visible).**

1. **Generated data.** `tools/build-app-data.py` writes beside each vintage record, per field, the
   value's provenance from the model: the field's own document URL where the field source resolves
   to one artifact with a URL placement, otherwise its status (record source only, ambiguous,
   unsourced). This is additive: a new generated global, with the existing ones byte-identical.
2. **UI.** The vintage fact grid shows each figure's source. That is a link to its own sheet, or an
   honest "source not recorded for this figure" or "several possible sheets". The record-level link
   then stands only for what it is.
3. **Verification.** The control comparison stays at zero unexplained differences for every existing
   global. A new check holds each displayed source to the model.

**Why this one:**

- It is a vertical slice through source → artifact → placement → legacy reference → provenance →
  canonical value → generated data → UI.
- It needs no domain decision.
- It changes no value.
- It removes the one place where the product actively misattributes.

**Secondary candidates, up to three:**

1. **Render RankAbsence and the recorded contradictions honestly (F2, F3).** Show "No second wine"
   for `'—'`, and where the second-wine fact and the wine list disagree, say they disagree rather than
   picking one. This is a presentation change only, and the identities stay undecided.
2. **Show each wine's type in "Which wine" (F4, F5).** Mark white and sweet wines, and word the
   unknown rank as unknown.
3. **Make other wines' names searchable (F6).**

## 14. Explicitly deferred

- **Temporal and historical presentation** (F13): no dated facts exist yet. It needs event extraction
  first (R0).
- **Harvest attribution and D5** (F10): a separate model-acceptance decision.
- **D2, D8, the 11 second names, owners, plantings versus assemblage** (F9, F11): domain decisions.
- **Families, revisions, language versions** (F14).
- **The backlog:** presentation order, C4 lazy loading, C5 search redraw (`docs/BACKLOG.md`).
- **F7 and F8:** wording and missingness copy. They can join the first slice if its UI pass touches
  the same lines, but they are not a reason for one.

## 15. Phase 6.0 gate

- **Data:** no canonical data, evidence, discovery data, normalized model data or generated
  application data was changed. The only new file is this document.
- **Application behaviour:** unchanged; the app still reads `data/app/`.
- **Tests:** the existing suite passes after the audit (final run below).
- **Distinctions:** product gaps (P1/P2) are kept apart from domain decisions (D1), data quality (Q0),
  research (R0) and deferrable limits (F0).
- **Next step:** one implementation (§13), small and evidence-based.
- **Open questions:** every unresolved domain question remains unresolved.

**SAFE — PHASE 6.0 PRODUCT & DOMAIN GAP AUDIT COMPLETE — READY FOR IMPLEMENTATION DECISION**
