# Longitudinal vintage experience — design audit

Gate: **SAFE — LONGITUDINAL VINTAGE PRODUCT SLICE DEFINED — READY FOR IMPLEMENTATION**

A research and design artifact for the first user-facing slice of the longitudinal vintage experience.

**Nothing was implemented.** No model, data, evidence, generated file, application file or test
changed. The baseline is `05690ab` (Phase 6.6C), with 25 suites and 708 checks.

**Measurements** were made with read-only queries of `data/model/` and with the application in
headless Chrome. The scratch scripts were removed.

**Terminology** follows the project's domain contract (`docs/PHASE-3.4-DOMAIN-MODEL.md`, review §17)
throughout.

## 0. A terminology decision this design must keep

**"FicheFamily / FicheInstance" is not a domain entity in this project.** The Phase 3.4 review (§11)
measured 849 sheet families in the harvest and concluded that the idea survives only as
`DocumentFamily`:

- a derived extraction aid, attached to a Source;
- "evidence that its members share a layout, never that they share a wine or a vintage";
- `document/families.jsonl` has 0 rows by design.

Phase 6.0 (§2, §7) confirmed this.

**In this document**, *Fiche Family* and *Fiche Instance* are therefore **product terms only**, the
two levels a user meets on a wine's page:

- **Fiche Family:** the enduring identity a page is about. In the model that is the existing `Estate`,
  `Wine` and `EstateWineRelationship`, with their `NameRecord`, `RankAssertion`,
  `ClassificationMembership` and `AppellationMembership`.
- **Fiche Instance:** one year of that wine. In the model that is the existing `Vintage` and the
  `Observation`s, `VintageStatement`s and documents scoped to it.

No new entity is proposed, and `DocumentFamily` keeps its meaning.

## 1. The existing domain decisions, re-read

| Concept | Where it is decided | What it holds | Temporal |
|---|---|---|---|
| Estate | 3.4 contract; `identity/estates.jsonl` (470) | identity; names via NameRecord | through its records |
| Wine | 3.4 §3, §17; `identity/wines.jsonl` (639) | identity and `type`; no rank, no colour range (WineRole and WineRange removed) | through its records |
| EstateWineRelationship | 3.4 §6; `state/estate-wine.jsonl` (639) | `kind` (PRODUCED_BY, FROM_ESTATE_VINEYARD, MADE_BY_GROUP_TEAM, …) | `validity` |
| RankAssertion / RankAbsence | 3.4 §1, §17; `state/rank-assertions.jsonl` (684), `rank-absences.jsonl` (34) | tier (FIRST, SECOND, THIRD, ABOVE_FIRST, UNRANKED, UNKNOWN), scope, **claimant** | `validity`; vintage-scoped absence representable |
| NameRecord | `identity/names.jsonl` (1,104) | CURRENT, FORMER, MARKET_ALIAS | `validity` |
| HistoricalIdentity / IdentityTransition | `identity/transitions.jsonl` (0) | renames and successions, with transition evidence criteria (3.4 req. 10) | dated by design |
| Vintage | `identity/vintages.jsonl` (5,286) | wine × year | is the year |
| VintageStatement | `state/vintage-statements.jsonl` (18) | NOT_PRODUCED | per vintage |
| ClassificationEdition / Membership | 3.4 §8; editions (6), memberships (399) | on the **Wine**, not the estate; editions can be ANNULLED | edition dated; membership `validity` |
| Appellation / Membership | 3.4 §8; appellations (21), memberships (376) | on the Wine | `validity` |
| Observation | `observation/observations.jsonl` (22,437) | a value as a document or record states it; `observed_at` | per statement |
| Document | artifacts (37,067), placements, assessments; ArtifactDate (0) | "when the document speaks" | via ArtifactDate |
| Provenance | `cross/provenance.jsonl` | per record and field | — |
| Reconciliation | `reconciliation/reconciliations.jsonl` | candidates and selection; all LEGACY_NEVER_OVERWRITE | `decided_at` |
| Temporal validity | 3.4 §7 | two axes (CALENDAR, VINTAGE); bounds EXACT, NO_LATER_THAN, UNKNOWN, OPEN, …; three dates kept apart: when the document speaks, when the fact holds, when it was retrieved | — |
| Source/evidence boundary | 3.4 §10, §19 | classes A–F; only class A is canonical; discovery stays outside; nothing is resolved by inference | — |

## 2. What longitudinal information exists

Measured in `data/model/` at `05690ab`.

### A. Already represented and trustworthy

These are trustworthy as what the dataset records; all are `LEGACY_UNSOURCED` dataset
transcriptions:

| Information | Count | Note |
|---|---:|---|
| a wine's **current** name | 1,104 NameRecords, all `CURRENT` | the name in use as the dataset records it |
| the wine–estate link | 639, all PRODUCED_BY, ESTABLISHED | |
| rank within the estate's range | 684 (FIRST 458, SECOND 163, UNKNOWN 63), claimant DATASET | |
| classification **edition years** | 6 editions, each EXACT CALENDAR year: 1855 Médoc, 1855 Sauternes & Barsac, Graves 1959, Saint-Émilion 2022, Crus Artisans 2006, Crus Bourgeois 2025 | **one edition per scheme**: the current list |
| **vintage-specific values** | 5,286 vintages; the sheet observations per vintage (blend, yield, alcohol, barrel, oak, pH, picking, notes) | Phase 6.1 per-figure provenance applies |
| **vintage-scoped absences** | 18 NOT_PRODUCED: Yquem 1992, 2012, 2018; Myrat 1982–1990; Climens 1984, 1987, 1992, 1993, 2012, 2017 | already shown as "not made" |
| which vintages hold a sheet | per wine; for example Echo 2011–2025 (13 of 44 years), Haut-Bailly II 2018–2025 (7), Lions de Batailley 2014–2017 (4) | |
| second-wine **status** | 86 resolved, 32 none, 13 not established, 4 notes, 2 conflicts (Phase 6.3) | |

### B. Representable but currently undated or empty

| Structure | State |
|---|---|
| the `validity` of every NameRecord, relationship, rank assertion and absence, classification and appellation membership, location and source link | **all from UNKNOWN, to OPEN** (3,917 records: the 3,474 Phase 6.0 counted, plus 34 rank absences and 409 source links) |
| FORMER and MARKET_ALIAS names | 0 |
| IdentityTransition (renames, successions) | 0 rows |
| Ownership | 0 rows |
| ArtifactDate (when a document speaks) | 0 rows |
| ArtifactRelation (revisions, language versions) | 0 rows |
| WineDescriptor | 0 rows |
| vintage-scoped RankAbsence | representable (test-phase4 t13), none recorded |
| superseded classification editions (Saint-Émilion before 2022, Crus Bourgeois before 2025) | representable, none recorded |
| appellation membership | 263 of 639 wines have none |

### C. In source or evidence material, not reconciled into the model

These are design cases (`docs/phase34-fixtures.json`) citing harvested artifacts by sha256, or
Phase 2 proposals:

| Case | Statement | Model today |
|---|---|---|
| P7 Lynch-Bages | the second wine was Haut-Bages Averous; "Echo de Lynch-Bages" from the 2008 vintage | one CURRENT name, "Echo de Lynch-Bages", undated; D2 (rename versus succession) recommended RENAMED, **not adopted** |
| P11 Haut-Bailly | "La Parde de Haut-Bailly, né en 1967", renamed Haut-Bailly II with 2018 | the wine is "Haut-Bailly II"; the estate file's string "La Parde de Haut-Bailly" is AMBIGUOUS (Phase 6.3, "Not established") |
| P6 Corbin 2022 | "no second wine was produced this year" | no RankAbsence for 2022 |
| P1 Batailley, P3 Caillou | third wines | not modelled |
| P10 Climens | Barsac for the sweet wine, Bordeaux for the dry white (Asphodèle) | Asphodèle is not a modelled wine; Les Cyprès de Climens has no appellation |
| corpus wording (3.4 §7) | "since/depuis YYYY" 2,631 artifacts, "formerly" 859, "renamed" 1,312, "from the YYYY vintage" 305, classification change 138 | discovery observations (163,582, CANDIDATES_ONLY), unattached; dated events need an event-extraction design (3.4 §20, class F) |
| Phase 6.2 contrary website evidence | Rauzan-Gassies, Croizet-Bages, Belair-Monange, Pouget name a second wine the dataset records as none | not in the model |

### D. Not currently supported

- **Event extraction.** No extractor turns "since 1967" or "from the 2008 vintage" into a dated
  record (3.4 §20).
- **Document dates.** PDF metadata, upload paths and Last-Modified are known in the harvest (3.4 §7),
  but no ArtifactDate is written.
- **Vintage-level classification.** A classification applies to a wine through an edition's validity,
  and no wine's membership in an *earlier* edition exists.

### E. Explicitly unresolved, to stay unresolved

- **Batailley and Lynch-Moussas:** "—" against a listed second wine (CONFLICT; Phase 6.2 S3).
- **Haut-Bailly:** La Parde as recorded, Haut-Bailly II as listed; rename not adopted (S4).
- **Pichon Baron:** Les Tourelles de Longueville recorded, Les Griffons listed.
- **The 11 differing second names, and the shared La Réserve.**
- **D2:** rename versus succession, for Echo.
- **Terrasses 2020–2023:** no role statement exists.
- **Braude and Mongravey 1999:** a 2015 sheet cited for both (Phase 6.4 F5).

## 3. The current user experience across vintages

Observed in headless Chrome at `05690ab`.

**What changes from year to year.** In the drawer each vintage row changes:

- rating, drink window, maturity;
- that year's sheet figures with their own sources (Phase 6.1);
- the season and tasting notes, picking dates, the cellar count;
- "not made", for the 18 NOT_PRODUCED vintages.

**What stays fixed.** The estate's fact grid shows the same values above every year:

- classification ("5ème Cru · 1855", "Grand Cru Classé · 2022");
- appellation, vineyard area, proprietor;
- second wine, website;
- house style and typical blend.

**Estate against wine.** The wine selector ("Which wine") separates them: "Echo de Lynch-Bages —
second wine · 13 vintages on file". That is the only place a wine is presented as an identity apart
from its estate.

**What the page implies about history.** Selecting a wine titles the vintage list
"**Echo de Lynch-Bages, 1982–2025** · 13 of 44 with a sheet on file", and lists all 44 years under
that name. 1982–2007 read "No sheet on file for this wine".

- **Echo:** the evidence (P7) says the wine was Haut-Bages Averous until 2007, so the page implies an
  Echo history it does not have.
- **Haut-Bailly II:** listed under its name from 1982, while the same drawer's fact grid says its
  second wine is "Not established / recorded as La Parde de Haut-Bailly".
- **Lions de Batailley:** listed from 1982 under a fact that reads "Conflicting records".

**The user questions:**

| Question | Can the user tell today? |
|---|---|
| when a wine's name changed | no; nothing on the page says the name is the current one, or that its start is unknown |
| when the second wine changed | only the Phase 6.3 status (conflict, not established), not when |
| when classification or appellation changed | the edition year is shown ("· 2022"), but not that it is today's list, nor that earlier years fell under other editions. Compare's vertical view repeats `rankLabel(ch)`, the current rank, under every vintage column. |
| that history is simply not established | no; absence is shown only as "No sheet on file", which is about documents, not about the wine |

**Duplicated across vintages:**

- the fact grid (estate-level, rightly once);
- the regional vintage report, repeated in every estate's row for that year;
- "No sheet on file for this wine", repeated for every empty year of a wine with a few sheets.

**The biggest conceptual gap is not a missing timeline.** It is that **the page presents today's
identity as if it spanned every year shown**:

- **the wine-list heading:** the wine's name over a 1982–2025 span;
- **the fact grid:** the current classification over all years;
- **Compare:** the current rank under each vintage column.

The model knows these are current values whose start is unknown (`CURRENT`, `valid_from UNKNOWN`).
The page drops that qualification.

## 4. Fiche Family and Fiche Instance, concretely

### Fiche Family: the enduring identity

| Level | Belongs here | Example |
|---|---|---|
| Estate | the estate's identity and current names; location; sources (website); classification as a derived view of its classified wine | Château Lynch-Bages (`es_00322`) |
| Wine | identity and type; NameRecords (today only CURRENT, undated); RankAssertion with its claimant; ClassificationMembership with its edition; AppellationMembership | Echo de Lynch-Bages (`wn_00547`): current name, SECOND as the dataset claims it |
| Relationship | EstateWineRelationship.kind, with validity | Echo PRODUCED_BY Lynch-Bages, from UNKNOWN |

### Fiche Instance: one year

| Belongs here | Example |
|---|---|
| the Vintage (wine × year) | Echo de Lynch-Bages 2011 |
| its sheet observations and their documents | 2011: yield 45 hl/ha, alcohol 13.2 %, new oak 75 % (source on file), pH 3.61 |
| VintageStatements | Château d'Yquem 2012: NOT_PRODUCED |
| ratings, derived drink window, cellar count | per vintage |
| a document's statement *as of that year* | the Haut-Bailly 2018 sheet that announces the rename (an observation; not reconciled) |
| the historical state of family records *at* that year | the validity of a NameRecord or membership at the vintage. **Today none is dated**, so no instance can claim a historical family state. |

**Repetition is not identity.** Lynch-Bages' grand vin shows "In barrel: 18 months" and
"New oak: 75 %" across many vintages. These are 30-odd separate vintage observations from separate
sheets. Moving them to the family as a constant would assert something no source states, and would
hide the years that differ (15 months and 65–80 % in others). The same holds for the
"typical blend": it is a separate estate-level record (the D1 question), not a summary of vintages,
and the app already labels it "the estate's usual blend".

## 5. Candidates for the first slice

| Candidate | Built from trusted data? | Useful with incomplete history? | Verdict |
|---|---|---|---|
| vintage timeline of established changes | no: 0 dated changes in the model | would be empty for every wine | rejected for now (Phase 6.0 §6 reached the same conclusion) |
| compact "over time" section | the only dated items are edition years and NOT_PRODUCED | thin and repetitive | folded into the chosen slice |
| current against historical identity | historical identity is empty; FORMER = 0 | only the "current" half exists | its honest half is the chosen slice |
| family/instance navigation model | the wine selector already is one | a re-architecture with no new information | later |
| **a wine identity header that states what is current and what is not established, above the vintage-specific content** | **yes: every field exists** | **yes: it corrects the page's implied history with no history data** | **chosen** |

## 6. The proposed first slice: "What is established about this wine"

### User goal

Today a user cannot tell, from a wine's page:

- that the name, rank, classification and second-wine status shown are the dataset's **current**
  values, not values established for each year;
- which years this wine actually has on file;
- which years it is recorded as not made;
- that a missing sheet is not evidence of anything about the wine.

After the slice they can. They see:

- which facts are **established for this wine**, and whether they are current or dated;
- which facts belong to **a specific vintage**;
- where **history is not recorded**, with that said plainly rather than implied away.

### UI location

1. **The drawer, at the top of each wine's vintage list** (the section titled today
   "*Wine name*, 1982–2025"). The heading is replaced by a compact identity block for the selected
   wine. The vintage rows beneath are unchanged.
2. **The Compare tab's vertical view.** Rank and Appellation rows are identical under every vintage
   column, so they say once that they are current values, not per-vintage ones.

No new tab or page.

### Data shown

| Line | Content | From |
|---|---|---|
| Name | the current name, labelled **"current name"** | NameRecord CURRENT |
| Name history | "When this name was adopted, and any earlier names, are not recorded." | validity.valid_from UNKNOWN; FORMER = 0 |
| Role | "second wine of Château Lynch-Bages, as the dataset lists it" | RankAssertion tier and claimant DATASET; EstateWineRelationship |
| Second-wine status | for the grand vin, the Phase 6.3 state, shown as now | `second-status.js` |
| Classification | "5ème Cru, Classification of 1855 — the current list"; for a wine without a membership, nothing | ClassificationMembership and edition year |
| Appellation | as recorded, "current"; for the 263 wines with none, nothing | AppellationMembership |
| Years on file | "Sheets on file for 13 vintages, 2011–2025" | Vintages with observations |
| Not made | "Recorded as not made: 1992, 2012, 2018" | VintageStatement NOT_PRODUCED |
| Coverage note | "Years without a sheet are years we have no document for, not years the wine was not made." | the model's rule: absence of a record is absence of evidence |

Then the vintage list, unchanged. Its span stays the reference's years (1982–2025), worded as such:
"Vintages 1982–2025 in this reference", not "*Wine*, 1982–2025".

### Historical semantics

"Over time" means only what the model holds with a date:

- classification **edition years**, worded as the year of the list, not of the membership;
- **vintage-scoped statements** (NOT_PRODUCED);
- **which vintages have documents.**

Everything else is a **current state with an unknown start**, and is labelled so. No interval is
shown that the model does not hold, and no year in the list is said to have had the current name or
rank.

### Missingness behaviour

The wording reuses Phase 6.3's states and Phase 6.1's "the honest blank":

| Situation | Behaviour | Wording (draft) |
|---|---|---|
| known historical change: a dated FORMER/CURRENT pair or an IdentityTransition | show the change with its bound and source | "Named Haut-Bages Averous until the 2007 vintage; Echo de Lynch-Bages from 2008" (**none exists yet**; shown only once reconciled) |
| current state, no start date (every record today) | label as current; say the start is not recorded | "current name; when it was adopted is not recorded" |
| vintage-specific evidence, no reconciled interval (a sheet naming the wine one year) | stays in that vintage row with its source; never lifted to the header | the sheet's own text, under the year |
| nothing historical established | one plain line, never silence that reads as "unchanged" | "No earlier names or changes are recorded for this wine. That does not mean there were none." |
| conflicting historical statements | show both, no winner (as 6.3) | "Conflicting records: one record lists no second wine; the wine list names Lions de Batailley" |
| an edition superseded or annulled (none recorded) | show the edition's status | "Saint-Émilion classification of 2022 (the current list)"; an ANNULLED edition named as annulled |

### Provenance behaviour

- **Identity facts carry no source link.** Every NameRecord, RankAssertion, classification membership
  and NOT_PRODUCED statement is `LEGACY_UNSOURCED`. As in Phase 6.1 and 6.3, that is the honest blank
  plus the words "as the dataset records it", not a link and not a claim of verification
  (Phase 6.5 wording rules).
- **The years-on-file line** links nothing itself. Each vintage below keeps its per-figure sources
  and the Phase 6.5 summaries.
- **When dated history is reconciled later**, each dated line takes the existing source mark and
  summary (`figSrc` pattern) from its record's provenance.

### Representative examples

Real cases, unresolved ones kept unresolved:

| Case | Situation exercised | The slice shows |
|---|---|---|
| **Château Lynch-Bages** grand vin (`wn_00322`) | stable identity, many vintages | "Château Lynch-Bages — current name; when adopted not recorded · first wine as the dataset lists it · 5ème Cru, 1855 (the current list) · Pauillac · sheets for 31 vintages, 1988–2025 · no earlier names recorded" |
| **Echo de Lynch-Bages** (`wn_00547`) | a known rename in evidence (P7), not in the model | "current name; when it was adopted, and earlier names, are not recorded · second wine as the dataset lists it · sheets for 13 vintages, 2011–2025". The list no longer reads "Echo de Lynch-Bages, 1982–2025". Haut-Bages Averous is **not** shown until D2 and the rename are reconciled. |
| **Haut-Bailly II** (`wn_00522`) and Haut-Bailly's second-wine status | an unresolved identity (P11 evidence; Phase 6.3 "Not established") | "Haut-Bailly II — current name … sheets for 7 vintages, 2018–2025"; the grand vin's block keeps "Not established: recorded as La Parde de Haut-Bailly; the wine list names Haut-Bailly II". No rename is stated. |
| **Lions de Batailley** (`wn_00459`) | conflicting second-wine records | "sheets for 4 vintages, 2014–2017"; Batailley's block keeps "Conflicting records". No winner. |
| **Château d'Yquem** and **Château Climens** | established vintage-scoped facts | "Recorded as not made: 1992, 2012, 2018" (Yquem); Climens' six years. Climens' Les Cyprès shows no appellation, because none is recorded; the dry white of P10 is not a modelled wine and does not appear. |
| **Château Corbin** (`stem-chateau-corbin`) | classification by edition | "Grand Cru Classé, Saint-Émilion classification of 2022 (the current list)". Earlier editions are not recorded, and nothing implies Corbin held that rank in 2005. The 2022 "no second wine" statement (P6) is not shown: it is not in the model. |

### Data prerequisites

| Prerequisite | Status |
|---|---|
| current name per wine, with its kind and `valid_from` | **available, needs transformation**: in the model, not in `data/app/`; one generated file, as `second-status.js` was |
| rank tier and claimant per wine | available, needs transformation (same file) |
| classification membership, edition label, edition year, edition status | **available**: the app already shows "· 2022"; the edition status needs adding to the same generated file |
| appellation membership per wine | available, needs transformation |
| years with sheets per wine | **available** (the app counts them: "13 of 44") |
| NOT_PRODUCED vintages | **available** (`BDX_NOT_PRODUCED`) |
| second-wine status | **available** (`second-status.js`, Phase 6.3) |
| FORMER names, rename years (Echo, La Parde) | **requires reconciliation** (P7, P11 evidence) **and a domain decision** (D2). Not needed for this slice. |
| superseded classification editions | requires new research (the earlier lists). Not needed. |
| vintage-scoped RankAbsence (Corbin 2022) | requires reconciliation. Not needed. |
| document dates (ArtifactDate) | requires extraction (3.4 §7). Not needed. |
| dated events from the corpus | requires an event-extraction design (class F). Not needed. |

**No model change is needed.** The slice reads fields the model already holds, including the fact
that their start is UNKNOWN. That fact is the information the page currently loses.

### Risks

| Risk | Mitigation |
|---|---|
| "current name" read as "the name it always had" | the "not recorded" line says the opposite on every wine; tests assert it is present wherever `valid_from` is UNKNOWN |
| the years-on-file range read as the wine's lifetime ("Echo 2011–2025" read as "began 2011") | worded as "sheets on file for", never "made from"; the coverage note says missing years are not evidence |
| the edition year read as the membership year ("Grand Cru Classé · 2022" read as "since 2022") | worded as "the Saint-Émilion classification of 2022 (the current list)" |
| evidence-level history (P7, P11) leaking into the header to make demos richer | the generated file is built from model records only (the 6.3 pattern); a test asserts no FORMER name or interval is shown while the model has none |
| contradicting Phase 6.3 | the block reuses `second-status.js` states verbatim |
| more text in a dense drawer | one compact block per wine, with the coverage and history lines muted (`.sitenote` pattern), and the existing tokens |
| Compare's current-rank note read as a rank change | one line under the table, not per cell |

## 7. Smallest decisions for later slices (not needed now)

Each would let a later slice show real change, without changing the model. The model already holds
all of these structures.

1. **D2 (rename versus succession), adopted:** Echo becomes a FORMER and CURRENT name pair with a 2008
   VINTAGE bound (P7), and Haut-Bailly II likewise (P11). That is the first dated history the slice
   would show.
2. **Reconcile vintage-scoped absences:** Corbin 2022 (P6), as a RankAbsence on the VINTAGE axis.
3. **ArtifactDate population:** from PDF metadata and upload paths (3.4 §7). It anchors "as of" for
   every document statement.
4. **Event extraction design:** class F, for "since / renamed / from the YYYY vintage".

## 8. Recommendation

**READY FOR IMPLEMENTATION.** The first slice can be built from records the model already holds and
trusts. It needs one generated data file, display changes in the drawer's wine heading and Compare's
vertical view, wording, and focused tests. No domain-model change, no new historical date, and no
resolved identity are involved. It invents no history; it stops the page from implying history.
