# Phase 3.0 — Scope Definition and Authoritative Universe Construction

Starting commit `8964131` (Phase 2 closed: `SAFE — PHASE 2 COMPLETE`).
Sources retrieved 2026-10-25. Nothing canonical, nothing in the evidence
store and no Phase 2 proposal was changed. Every number below is produced
by the files this phase adds and is checked by `tools/test-phase30.py`.

| Deliverable | What it is |
|---|---|
| `data/scope/authoritative-universe.json` | sources, systems, 388 estates, 406 wines, 9 temporal cases |
| `data/scope/canonical-discrepancies.jsonl` | the universe against the canonical data (212 records) |
| `data/scope/corpus-discrepancies.jsonl` | the universe against the evidence corpus (221 records) |
| `tools/build-universe.py` | builds the universe from `sources/scope/`; `--check` rebuilds and compares |
| `tools/compare-universe.py` | writes the two discrepancy files; read-only on everything else |
| `tools/canonical-view.js` | the canonical estate list as `assets/app.js` builds it |
| `tools/test-phase30.py` | 26 checks |

## 1. Purpose and starting state

Phases 2.x corrected the *reader*. They never asked what the dashboard is
supposed to contain. This phase answers that from outside the dashboard:
which estates and wines exist under which classification, on whose
authority, and when. It then records, without correcting anything, where
the canonical data and the evidence corpus differ from that answer.

At the start: HEAD `8964131` = `origin/main`, tree clean, evidence store
v1–v5 with 177,127 decisions, reader `7e8cfed1c24e`, `test-phase212` 14/14.

Rules applied throughout. Scope is defined before anything is corrected
(Rule 1). Nothing is inferred from the current corpus (Rule 2). No
technical sheet ("fiche") is used as authority, not even the estate's own
(Rule 3). Historical names and merged estates are kept (Rule 4). Several
wines per estate is the normal case (Rule 5).

## 2. Scope vocabulary

| Term | Meaning here |
|---|---|
| **Estate** | A property as a classification body lists it. Identity is the body's name for it. A name shared across two systems is *not* evidence of one estate (§6). |
| **Wine** (cuvée) | Something sold under its own name. A *classified wine* is what a classification classifies. An *estate wine* is any other wine the estate publishes. |
| **Role** | The wine's place in the estate's range, **in the source's own words**. `grand_vin` is used for the classified wine. `second` is used only where the source says "second vin". Otherwise the role is `null`, with the source's term kept in `source_term`. |
| **Vintage** | The harvest year. The validity of a classification or a name is stated in vintages wherever the source does so. |
| **Appellation** | The AOC/AOP **as the source lists it**. Not normalised to today's name: Haut-Brion stays "Pessac" in the Council's listing. |
| **Classification** | One system, from one body, with one validity period. Systems are never merged (§4). |
| **Geography** | Commune, appellation or region. Recorded only as the source states it: `place_listed` holds the Council's mix of communes and appellations, unchanged. |
| **Owner / group** | Recorded only where a retrieved source states it. That is one estate: Tour Saint Christophe, owned by Vignobles K since 2012. |

## 3. Authoritative source registry

Each entry in `sources[]` of the universe records name, publisher, type,
URL, local path, sha256, authority, geographic and temporal scope,
primary/secondary, current/historical, limitations, and retrieval date.
Retrieved files are kept under `sources/scope/<id>/`, which is gitignored
like the rest of `sources/`. Each was downloaded into its own empty
directory and read with `python -I`.

| Id | Body | Type | Establishes | P/S |
|---|---|---|---|---|
| `gcc-1855-listing` | Conseil des Grands Crus Classés en 1855 | official body list (PDF) | 1855 red and Sauternes–Barsac membership and rank | primary |
| `gcc-1855-histoire` | same | official body page | the two amendments (1855, 1973) | primary |
| `inao-stem-2022` | INAO | communiqué (PDF) | Saint-Émilion 2022 membership and rank | primary |
| `acb-cb-2025` | Alliance des Crus Bourgeois du Médoc | official list (PDF) | Crus Bourgeois 2025 membership, tier, appellation | primary |
| `odg-pl-ccg` | Syndicat viticole de Pessac-Léognan (ODG) | official body page | Graves membership, commune | primary |
| `wp-graves` | Wikipédia (fr), rev. 240039963 | encyclopedia | Graves **colours**; 2006/2009 mergers | **secondary** |
| `sca-proclamation-b`, `-a` | Syndicat des Crus Artisans du Médoc | proclamation (two images) | Crus Artisans 2022–2026 membership, appellation, commune | primary |
| `sca-classement-page` | same | site page | nothing (navigation menu; explains a canonical difference) | — |
| `wp-cru-artisan` | Wikipédia (fr), rev. 225013269 | encyclopedia | Crus Artisans history 2006/2012 | secondary |
| `estate-lynch-bages` | Château Lynch-Bages | estate page | its wines, Echo's history | primary for itself |
| `estate-caillou`, `-murets-blanc`, `-murets-rouge` | Château Caillou | estate pages | its wines | primary for itself |
| `estate-vk-tsc-vins`, `-propriete` | Vignobles K (owner) | estate pages | Tour Saint Christophe's wines, owner, 2022 promotion | primary for itself |
| `ref-jorf-graves-1959`, `ref-jorf-artisans-2022`, `ref-jorf-stem-2022` | ministries | legal texts | **nothing: not retrieved** | — |

**What could not be retrieved, and why.**

- **Légifrance** serves a bot challenge, so none of the three legal texts
  (homologation orders) was read. Every membership therefore rests on the
  official body's own publication, not on the statute.
- **The Union des Crus Classés de Graves** disallows all agents in its
  robots.txt. So do **bordeaux.com** (CIVB) and **Vitisphere**, which
  disallow Claude agents by name. None of the three was fetched.
- **The Crus Artisans list is published only as images.** It was
  transcribed by reading rendering B (which gives communes) and checked
  line by line against rendering A. The two renderings spell two names
  differently, and both spellings are kept. The image hashes are pinned,
  so a changed image invalidates the transcription.

## 4. Classification scope

Six systems, each kept separately. An estate's membership in one says
nothing about another.

| System | Body | Unit | Ranks (count) | Validity |
|---|---|---|---|---|
| `1855-medoc` | Conseil 1855 | cru | Premiers 5 · Seconds 14 · Troisièmes 14 · Quatrièmes 10 · Cinquièmes 18 = **61** | 1855, amended 16 Sep 1855 (Cantemerle) and June 1973 (Mouton); no term |
| `1855-sauternes` | Conseil 1855 | cru | Premier Cru Supérieur 1 · Premiers 11 · Seconds 15 = **27** | 1855; no term |
| `graves` | INAO jury 1953, order rectified 1959 | cru **per colour** | unranked; **14** crus, **20** classified wines | no term |
| `stem-2022` | INAO | cru | PGCC A 2 · PGCC 12 · GCC 71 = **85** | approved 8 Sep 2022; revised every 10 years |
| `cb-2025` | Alliance des Crus Bourgeois | cru | Exceptionnel 14 · Supérieur 36 · Cru Bourgeois 120 = **170** | 2025; vintage range not stated by the source |
| `ca-2022` | Syndicat des Crus Artisans | cru **per appellation** | unranked; **33** entries, 32 estates | vintages 2022–2026 |

Each parser is checked against the source's own total. The build stops if
a count disagrees.

**Outside the universe, retained.** The dashboard's five editorial
collections (Pomerol, Fronsac & Lalande-de-Pomerol, Côtes, Graves &
Entre-Deux-Mers, "the Médoc beyond the lists") have no classification
authority. They are not deleted and not judged. Each is recorded once as
`UNRESOLVED` (§10). The same holds for unclassified Saint-Émilion Grand
Cru and Pomerol estates, and for Ausone, Cheval Blanc and Angélus, which
are absent from the 2022 list. Rule 4 applies to them, but the 2012 list
was not retrieved.

## 5. Appellation and geographic scope

A classification defines geography; geography does not define membership.
The universe therefore covers **12 appellations**, each because a system
names it:

- **Médoc:** Médoc, Haut-Médoc, Saint-Estèphe, Pauillac, Saint-Julien,
  Margaux, Listrac-Médoc, Moulis-en-Médoc. From the CB and CA lists, and
  the 1855 place names.
- **Graves:** Pessac-Léognan. All 14 crus are there, per the ODG. The
  1959 list predates the 1987 appellation (T9).
- **Sauternes, Barsac.** From the 1855 listing.
- **Saint-Émilion grand cru.**

Appellations reached only through an estate wine (Bordeaux, Bordeaux
Supérieur, Crémant de Bordeaux) are recorded on that wine. They do not
widen the scope. An appellation is recorded as listed; for example "Pessac"
in the 1855 listing is a commune and stays so. Moutte Blanc is classified
in two appellations at once, so appellation is a property of the wine,
not of the estate.

## 6. The estate universe

**388 estates.** For each: id, every name the sources use (with source),
memberships (system, rank, rank term, appellation and place as listed,
source), communes where given, owner where given, identity status and
basis, and sources.

Identity rules:

- **Within one system,** a repeated name with the same commune is one
  estate. This happens once: Moutte Blanc, listed under Haut-Médoc and
  Margaux, both "à Macau".
- **Across systems,** two entries are one estate only where a source says
  so. This happens once: Haut-Brion. The ODG lists it among the Crus
  Classés de Graves and calls it "1er Grand Cru du Classement de 1855".
- **The same name in two systems with nothing joining them** is kept
  apart as `UNRESOLVED_IDENTITY`. Two pairs: **Bellevue** (Saint-Émilion
  GCC; Cru Bourgeois) and **La Commanderie** (Saint-Émilion GCC; Cru
  Bourgeois).

## 7. The wine and cuvée universe

**406 wines.**

- **395 classified wines.** One per membership; Graves one per classified
  colour; Haut-Brion's red is one wine classified twice. Role `grand_vin`,
  because each system's unit is the cru, the wine sold under the estate's
  name. Colour is null unless the source gives it. Only Graves gives
  colour, and that comes from the secondary source.
- **11 estate wines,** from the three estates whose own pages were read.
  Source terminology is kept.
  - **Lynch-Bages.** Echo de Lynch-Bages ("second vin", from the 2008
    vintage). Château Haut-Bages Averous ("second vin" for over 30 years,
    to 2007; historical). Blanc de Lynch-Bages (white, since 1990; no role
    word).
  - **Caillou.** Myosotis ("grand vin blanc sec": the grand vin of the dry
    whites, not of the estate). Les Murets de Caillou blanc (Bordeaux Blanc
    Sec) and rouge (Bordeaux Supérieur). Les Tourelles and Les Érables
    (Sauternes). Les Bulles (Crémant). None has a role word.
  - **Tour Saint Christophe.** Les Terrasses de Saint Christophe
    (Saint-Émilion Grand Cru, sheets 2016–2023; no role word). 'Angela'
    (Bordeaux Blanc).

**The gap.** For the other **385** estates, no source for their
non-classified wines was read. Their wine universe is the classified wine
only (`wine_universe: CLASSIFIED_WINE_ONLY`). No official body registers
second wines; the authority is each estate's own publication. Under Rule 5
this part of the universe is **incomplete** (§14).

## 8. Temporal rules

1. A membership is valid for the period its system states (§4). With no
   term, it holds until the body records a change.
2. A change is recorded with its date, its source and a verbatim quote,
   and it never overwrites the earlier state.
3. A merged or renamed estate or wine keeps its own record, marked
   historical, with the date the source gives.
4. Where a source gives no vintage range (CB 2025), none is supplied.

The nine recorded cases:

| Id | Case | Source |
|---|---|---|
| T1 | Mouton Rothschild promoted, June 1973 | Council |
| T2 | Cantemerle added, 16 Sep 1855 | Council |
| T3 | La Tour Haut-Brion merged into La Mission, 2006 | Wikipédia (secondary) |
| T4 | Laville Haut-Brion merged into La Mission, 2009 | Wikipédia (secondary) |
| T5 | Saint-Émilion 2012 list (18 + 64) replaced by 2022 (14 + 71) | INAO |
| T6 | Tour Saint Christophe promoted GCC, Sep 2022 | owner |
| T7 | Crus Artisans 2006 → 2012 → 2022–2026 | proclamation, Wikipédia |
| T8 | Haut-Bages Averous → Echo de Lynch-Bages from the 2008 vintage | estate |
| T9 | Pessac-Léognan created 1987, after both classifications | Wikipédia (secondary) |

## 9. Inclusion and exclusion rules

| Subject | In the authoritative universe when | Otherwise |
|---|---|---|
| **Estate** | a current classification body lists it | kept in canonical if there; recorded, never deleted |
| **Wine** | a classification classifies it, or the estate publishes it | `UNRESOLVED` if canonical lists it and no estate source was read |
| **Vintage** | within the system's stated validity, or the estate publishes it | no vintage is invented |
| **Document** | never a source of scope (Rule 3); evidence only | — |
| **Non-classified estate** | never (editorial collections) | retained as `UNRESOLVED`, not deleted |
| **Historical name** | kept, marked historical, dated | — |
| **Same name, two systems** | two candidates, `UNRESOLVED_IDENTITY` | joined only on a source's word |

## 10. Universe against canonical data

`tools/compare-universe.py` reads canonical data through
`tools/canonical-view.js`, which reproduces app.js's expansion of the
compact lists. 212 records:

| Category | n | What |
|---|---|---|
| `IN_UNIVERSE_NOT_IN_CANONICAL` | 7 | wines: Les Terrasses and 'Angela' (Tour Saint Christophe); Myosotis, Murets rouge, Tourelles, Bulles (Caillou); Moutte Blanc's **Haut-Médoc** classified wine |
| `IN_CANONICAL_NOT_IN_UNIVERSE` | 2 | Château Lamongeau and Château Tour Bel Air, in the canonical Crus Artisans list but not the 2022–2026 proclamation. They come from the syndicate site's navigation menu, which names 34 properties. |
| `TEMPORAL_DIFFERENCE` | 5 | Laville Haut-Brion and La Tour Haut-Brion still separate classified Graves estates (T3, T4). Haut-Bages Averous absent as a historical second wine (T8). The Crus Artisans collection is dated 2006, with text describing the 2006 + 2012 list, over a 2022–2026 roster. The 1855 text says "amended exactly once" (the Council names two changes). |
| `CLASSIFICATION_DIFFERENCE` | 6 | Bouscaut, Carbonnieux, Domaine de Chevalier, Latour-Martillac, Malartic-Lagravière, Olivier: classified red **and** white; canonical carries one category, red. (Colour from the secondary source.) |
| `ROLE_DIFFERENCE` | 1 | Caillou: canonical calls Les Érables de Caillou the second wine; the estate lists it under Sauternes with no role word. |
| `IDENTITY_MAPPING_UNCERTAIN` | 2 | Council "Pichon-Baron" ↔ canonical "Pichon-Longueville Baron"; "Marquis d'Alesme Becker" ↔ "Marquis d'Alesme". Candidates, not asserted. |
| `NAME_VARIANT` | 2 | Malescot Saint-Exupéry ("St."); Trottevieille ("Trotte Vieille") |
| `SOURCE_CONFLICT` | 1 | La Tessonnière (rendering A) vs La Tessonière (rendering B, and canonical) |
| `APPELLATION_DIFFERENCE` | 0 | every CB and CA appellation agrees, once Moutte Blanc is counted as two wines |
| `UNRESOLVED` | 186 | 181 canonical other wines with no estate source read; 5 editorial collections |

Ranks agree everywhere: all 61 + 27 + 85 + 170 memberships, and every one
of the 388 estates, map to a canonical estate. The discrepancies are
recorded and stop there. None was corrected.

## 11. Universe against the evidence corpus

Kept separate: the corpus is what was collected, not what is true. 221
records in `corpus-discrepancies.jsonl`:

| Category | n | What |
|---|---|---|
| `UNIVERSE_ESTATE_NO_CORPUS` | 177 | universe estates with no sheet in the manifest (mostly the sparse CB and CA estates) |
| `CORPUS_ESTATE_OUTSIDE_UNIVERSE` | 40 | 1,046 sheets of 40 estates outside the universe (editorial collections; Laville and La Tour Haut-Brion) |
| `CORPUS_UNATTRIBUTED` | 1 | **908** documents attributed to no estate: counted, not resolved |
| `CORPUS_ROLE_DIFFERS` | 1 | **50** Echo sheets filed as Blanc de Lynch-Bages |
| `CORPUS_DECISION_CONFLICTS_WITH_UNIVERSE` | 1 | **15** v5 acceptances of Terrasses sheets as Tour Saint Christophe's grand vin |
| `CORPUS_WINE_NOT_IN_CANONICAL` | 1 | the Murets de Caillou sheets (2023 blanc, FR and EN) |

The 123 unreadable files were not reopened.

## 12. The Phase 2 proposals, tested

Tested against the universe, not applied.

| Proposal | Phase 2 status | Against the universe | Status now |
|---|---|---|---|
| **B1** Les Terrasses de Saint Christophe → Tour Saint Christophe's second wine | `PENDING_DOMAIN_EVIDENCE` (2020–2023 unsourced) | **Estate relationship supported.** The owner's Tour Saint Christophe wine page lists Les Terrasses as Saint-Émilion Grand Cru, with sheets to 2023, citing "le terroir de Tour Saint Christophe". **Role not supported.** The page uses no role word, and "second label" appears only in the 2016–2019 sheets, which are not authority (Rule 3). The 15 v5 grand-vin acceptances conflict with the universe (§11). | `PROPOSED_CORRECTION_PENDING_DOMAIN_EVIDENCE`: the wine's existence and estate are established; its **role** remains pending |
| **B2** Echo de Lynch-Bages: 50 manifest rows Blanc → Echo | `PENDING_CANONICAL_DECISION` | **Supported.** The estate publishes Echo (red, "second vin", from 2008) and the Blanc (white, since 1990) as two wines. | `PROPOSED_CORRECTION_SUPPORTED_BY_UNIVERSE`: pending only the canonical decision to apply it |
| **B3** Les Murets de Caillou → Caillou's wines, as second dry white | `PENDING_DOMAIN_EVIDENCE` | **Existence supported:** the estate sells it as Bordeaux Blanc Sec and as Bordeaux Supérieur rouge. **Role not supported:** the estate's "grand vin blanc sec" is Myosotis, and Murets has no role word. The universe also shows a red Murets and a Myosotis that the proposal did not know of. | `PROPOSED_CORRECTION_PENDING_DOMAIN_EVIDENCE` (role), with a wider scope than first proposed |

`data/proposals.jsonl` and `data/attribution-candidates.jsonl` are
unchanged. `test-phase30` asserts that Tour Saint Christophe still lists no
second wine, that the 50 Echo rows are still filed as Blanc, and that
Caillou's second wine is still Les Érables.

## 13. What was not done, and verification

Not modified: `fiches.js`, `chateaux.js`, `cuvees.js`, `field-src.js`,
`cuvee-src.js`, `sources.json`, the evidence store, the reader, and the
proposal files. Not done: V6, any rewrite of V5, any change to an evidence
decision, resolution of the 908 or the 123, global normalisation,
deduplication, any redesign, any promotion of evidence into canonical data.

One file outside this phase was edited. The first check of
`tools/test-phase212.py` asserted that nothing but Phase 2.12's files had
changed since `2072abe`, across the whole tree, so any later phase failed
it. It now checks Phase 2.12's own commit range, `2072abe..8964131`. The
other 13 checks are unchanged. This is the same kind of correction made to
earlier phases' whole-tree checks.

`tools/test-phase30.py` has 26 checks, covering:

- **Change scope.** Only this phase's files changed since `8964131`.
- **Protected data.** Canonical files and proposals are unchanged. The
  evidence store is unchanged and verifies (177,127 decisions, no v6), and
  the reader is unchanged.
- **The universe itself.**
  - A rebuild from `sources/scope/` reproduces it.
  - Per-system totals and tiers match the sources.
  - Every estate and wine cites a retrieved, registered source, and none
    cites an unretrieved one.
  - The systems stay apart, Haut-Brion included.
  - The same-name pairs remain unresolved, and Moutte Blanc is one estate
    with two wines.
  - Roles appear only where the source uses the word; colours only from
    the Graves source; an owner only where sourced.
  - Every temporal case is quoted.
- **The comparisons.** Both discrepancy files use their defined, separate
  categories, and the known discrepancies are present.
- **The proposals.** None was applied.
- **The canonical view.** It agrees with `classifications.js`.
- **This document.** It has 14 sections and states the gate.

## 14. Gate decision

The **scope is defined**: vocabulary, six classification systems kept
separately, twelve appellations, inclusion, exclusion and temporal rules.
The **estate universe is complete for that scope**. Its 388 estates are
sourced from the classification bodies' own lists, every count matches
its source, and the two unresolved identities are marked.

The **authoritative universe is not complete**:

1. **Wines beyond the classified wine** are established for 3 of 388
   estates. For the other 385, no estate publication was read, so 181
   canonical other wines (second wines, whites, cuvées) can be neither
   confirmed nor contradicted. Rule 5 makes these part of the universe,
   and Phase 3.1 would be correcting against an empty reference for them.
2. **The Graves colours** rest on a secondary source. The 1959 order and
   the Union's site could not be read.
3. **No membership rests on a legal text.** Légifrance was unreachable.
   Each rests on the official body's own publication instead, which is
   adequate for membership but recorded as a limitation.

Unblocking takes one of two routes:

- Read each estate's own publication for the 385 estates. Robots.txt
  permitting, this is the same procedure as for Lynch-Bages, Caillou and
  Tour Saint Christophe, and it extends `ESTATE_WINES` and `ESTATE_PAGES`
  in `tools/build-universe.py`.
- Or decide explicitly that Phase 3.1 is restricted to classified wines
  and estate identity, leaving other wines out of scope.

The Graves colour could be confirmed from the 1959 text if it becomes
retrievable.

**BLOCKED — SCOPE OR AUTHORITATIVE UNIVERSE INCOMPLETE**
