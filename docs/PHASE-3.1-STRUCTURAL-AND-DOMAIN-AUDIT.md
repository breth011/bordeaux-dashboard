# Phase 3.1 — Structural and Domain-Model Audit

Starting commit `e100b25` (Phase 3.0, gate
`BLOCKED — SCOPE OR AUTHORITATIVE UNIVERSE INCOMPLETE`, carried forward as
a domain-data limitation). Read-only: no canonical file, manifest row,
evidence decision, proposal or Phase 3.0 artifact was changed, and nothing
was redesigned.

| Deliverable | What it is |
|---|---|
| this document | the audit, 19 sections, 40 findings |
| `tools/audit-structure.py` | a read-only static reader of `tools/` and `data/`; `--check` rebuilds and compares |
| `data/audit/phase31-structure.json` | its report: every tool's reads, writes (by line), flags, network use; every data file's kind, consumers and writers; 308 `INPUT → TOOL → OUTPUT` edges; cycles; the measures cited below |
| `tools/test-phase31.py` | the audit's invariants |

One file outside the audit was edited: the first three checks of
`tools/test-phase30.py`. They asked whether anything had changed since
Phase 3.0's base, across the whole tree, so this phase's new files failed
them. They now examine Phase 3.0's own commits, or the working tree while
that phase has none, which is the fix applied to `test-phase212` in
Phase 3.0. `test-phase31` is written the same way from the start.

Every count in this document comes from that report or from a measurement
described where it is used. Where the static reading needed help (a path
built at run time), the write was placed by reading the code, and the
report lists those placements (`PLACED_BY_HAND` in the tool).

## 1. Executive summary

**Sound.** The boundaries built in Phase 2 and 3.0 hold:

- The evidence store has one writer, and it is append-only.
- Exact artifact lookup is hashed and stamped with code state on the
  evidence path.
- None of the 16 tools that read evidence writes canonical data or the
  manifest.
- No tool that writes canonical data reads the proposal files.
- The Phase 3.0 universe is kept apart from the app.
- A document cannot create a wine: other-wine records exist only for
  wines already listed in `BDX_CUVEE_WINES`.
- For those other wines, `estate → wine → vintage` exists as data
  (`cuvees.js`, 1,174 records, 135 wines).

**Not sound.** The canonical model collapses the domain in four places
that matter:

1. **The grand vin is not a wine.** It is the estate: `fiches.js` is keyed
   `estate|vintage`, 2,725 records. A document whose wine is unknown is
   therefore read as the grand vin by default (`read-fiches.py` routes
   role `unknown`, 4,368 manifest rows, into it). This is the mechanism
   behind the Terrasses misattribution.
2. **Role has no "unknown".** `BDX_CUVEE_WINES` knows `second` and
   `other`. "A wine of this estate whose role is not established"
   cannot be stored without inventing one.
3. **Nothing is temporal.** Classification, owner, name, appellation and
   second wine are single current values. None of Phase 3.0's nine dated
   changes can be stored as data without overwriting history.
4. **A value has no observations behind it.** `fiches.js` holds the
   winner. The winner is chosen by sort order and never overwritten.
   Losing values are not kept: `data/field-conflicts.jsonl`, which
   `conflicts.py` exists to write, is absent. Provenance is a bare
   basename: 364 field values name a document that matches more than one
   manifest row.

The manifest (`data/sources.json`) is the busiest shared object. It is the
document register, the attribution, and a cache of reader judgements all
at once. It has 11 writers, and two of them write it without any flag.
Through it, 13 tools form one dependency cycle.

**Gate:** the audit is complete. The defects are findings for Phase 3.2,
not gaps in the audit (§19).

## 2. Repository structure

| Path | Owns | Consumed by | Truth / derived / evidence / generated | Overlap |
|---|---|---|---|---|
| `index.html`, `assets/`, `service-worker.js`, `manifest.webmanifest` | the PWA | browsers | source code | `service-worker.js` hand-lists 37 data files under a hand-bumped cache name (`v168`) |
| `data/*.js` | everything the page shows | `index.html` loads 37 | **mixed** (§3): canonical values, references, derived views | canonical estate data is spread over 12 files by collection and batch |
| `data/sources.json` | the document register | 60 tools | manifest: identity + attribution + reader judgement | is also evidence-like (§8) |
| `data/evidence/` | reader decisions v1–v5 | evidence tools | **evidence**, append-only | — |
| `data/proposals.jsonl`, `attribution-candidates.jsonl` | dry-run corrections | nothing that writes | proposals | — |
| `data/*.jsonl`, `data/*.json` (12 files) | phase analyses | docs, tests | generated analysis | they sit beside canonical data, in the folder the app is served from |
| `data/scope/` | the Phase 3.0 universe | `compare-universe.py`, tests | scope (sourced), generated from `sources/scope/` | — |
| `data/audit/` | this phase's report | tests | generated analysis | — |
| `sources/` (gitignored, 12.5 GB) | downloaded documents | readers | **source artifacts** | `fiches/<estate-id>/` names a crawl location after an estate, and is read as attribution (§8) |
| `tools/` | 63 tools, 16 tests | the maintainer | code | §10 |
| `reports/` (ignored but for `estates/`) | generated reports, plus 62 committed hand-written estate reports | the maintainer | **mixed**: generated output and a hand-written deliverable in one folder | `.gitignore` documents a past loss caused by this mix |
| `docs/` | phase documents | — | documentation | — |
| `PROGRESS.md`, `progress-history.tsv` | coverage | readers of the repo | generated by `progress.py`, committed at the root | generated files that look like documentation |

## 3. Canonical data model

| File | Entity | Granularity / key | Time | Source / provenance | Writers | Mixes layers? |
|---|---|---|---|---|---|---|
| `chateaux.js` + `sauternes.js`, `saintemilion.js`, `pomerol.js`, `graves.js`, `libournais.js`, `batch2–4.js` | estate (172 full records) | `id` | none | header prose; no per-field source | **hand-edited** (no tool writes them) | **yes**: estate (name, commune, lat/lng, ha), ownership (`owner`, one string), classification (`growth`; `cls` by file or defaulted from `cat`), grand vin (`cat`, `blend`, `style`), the estate→second-wine relation (`second`, one string), an editorial score nudge (`perf`) |
| `crubourgeois.js`, `cruartisan.js`, `BDX_STEM_GCC`, `BDX_POMEROL_OTHER` | estate (298 compact) | none: the id is **derived from the display name** (`cls + '-' + slug(name)`) | none | header prose | hand-edited | classification membership, estate and appellation in one row |
| `fiches.js` | **grand-vin vintage** | `estate|vintage` (2,725; all two-part) | the vintage | `src` = last writer's filename (2,724) | `read-sheets.py`, `merge-proposals.py`, `read-fiches.py`; and by hand | **yes**: the grand vin is the estate; values from documents, by hand and merged, in one record |
| `field-src.js` | provenance of `fiches.js` fields | `estate|vintage` → field → **basename** (5,845 values) | — | — | `read-fiches.py` | provenance with no folder, hash or code state |
| `cuvees.js` `BDX_CUVEE_WINES` | wine + its role | estate → [slug, name, role, colour] (135 wines) | none | none | `add-wine.py`; by hand | role and colour stored on the wine, unqualified by time |
| `cuvees.js` `BDX_CUVEES` | other-wine vintage | `estate|wine|vintage` (1,174) | the vintage | `src` | `read-fiches.py --cuvees` | — |
| `cuvee-src.js` | provenance of `BDX_CUVEES` | as `field-src.js` (2,679 values) | — | — | `read-fiches.py` | as `field-src.js` |
| `sources.json` | document register | row: (folder, file) + sha1, url, estate, wine, role, colour, year, how, note | `year` = the vintage | `how` (prose), `url` | 11 tools | **yes**: document identity, source URL, attribution, wine identity, reader verdict (`role: skip/page/unknown/...`) |
| `plantings.js`, `terroir.js`, `cellar.js` | estate- and vintage-level reads | estate or `estate|vintage` | `from/to` (terroir only) | `src` basename | `read-plantings.py`, `read-terroir.py` | `plantings.js` holds both vineyard plantings and grand-vin blends (memory: "a vineyard label can carry the assemblage") |
| `ratings.js`, `overrides.js`, `coords.js`, `websites.js` | critic scores; not-produced vintages; positions; estate sites | `estate|vintage` or estate | — | inline tags | hand-edited | ratings keyed by estate, i.e. the grand vin implicitly |
| `fiches-url.js`, `cuvee-url.js` | links to sheets | as their records | — | derived from `sources.json` | `build-fiche-links.py` | derived views loaded by the app as data |

Filenames mislead in three places:

- `fiches.js` is not "the sheets". It is the grand vin's canonical values,
  partly typed by hand.
- `cuvees.js` holds two entity types: the wine list and the vintage
  records.
- `sources.json` is not a list of sources. It is the document register
  plus attribution.

## 4. Domain entities

| Entity | Identity stored | Identified by | Independent? | Temporal? | Duplicated / embedded / confused | Provenance separate from value? | Several observations? Conflicts coexist? |
|---|---|---|---|---|---|---|---|
| 1 Estate | estate files | `id`, or display name for 298 | yes | no | **confused with the grand vin**; spread over 12 files | no | no |
| 2 Wine | grand vin: nowhere; others: `BDX_CUVEE_WINES` | slug within estate | others only | no | **estate = wine** for the grand vin | no | — |
| 3 Role | `BDX_CUVEE_WINES.role`; `chateaux.second`; manifest `role` | — | no | no | three places, three vocabularies; manifest role mixes wine role with document type (`skip`, `page`, `unknown`, `group report`) | no | no |
| 4 Vintage | inside record keys | the year | no | is time | embedded in every key; sound as a key part | — | — |
| 5 Document | manifest row | (folder, file) path | yes | no | **path, not bytes**: 243 paths have several rows, 204 of them with different sha1; 810 byte-identical documents under 1,781 paths, 665 across folders | sha1 (manifest), sha256 (evidence): two hashes | — |
| 6 Source / site | `websites.js` (estate → site), manifest `url`, `how` prose | the estate | no | no | **source = estate**: a site is listed under an estate; a négociant's library is filed as estate folders | — | — |
| 7 Observation | **nowhere for canonical fields**; evidence holds decisions, not values | — | — | — | the winning value *is* the observation; losers are dropped (§9) | — | **no** |
| 8 Canonical value | `fiches.js`, `cuvees.js`, estate files | record key + field | no | no | written first-wins; hand values indistinguishable from read values except by absence from `field-src.js` | partly (`field-src.js`, basename only) | no |
| 9 Provenance | `field-src.js`, `cuvee-src.js`, `src`, evidence `read{}` | basename (canonical); path + sha256 + commit (evidence) | — | — | **two standards**; canonical provenance cannot name bytes | — | — |
| 10 Reconciliation | `read-fiches.py` sort order; `conflicts.py` | — | no | no | ephemeral: decided at write time; the conflicts file is absent | — | no |
| 11 Quality / anomaly | guard refusals (evidence), `check-data.py`, `audit-*.py` reports | — | no | no | no persistent anomaly entity; e.g. `cellar.js` holds "SIGNATURE : RÈGLEMENT À ENVOYER À" as a cellar note | — | — |
| 12 Classification | `growth`, `cls` (file or default), `classifications.js`, `BDX_GRAVES_CROSSLIST` | collection id | no | no | **embedded in the estate**: one membership per record, a special list for Haut-Brion, `cls` defaulted from colour (`cat === 'sweet' ? 'sauternes' : '1855'`) | no | — |
| 13 Appellation | `appellation` string | text | no | no | one per estate; Moutte Blanc's two cannot be held | no | — |
| 14 Ownership / group | `owner` string | text | no | no (7 strings carry a year in prose) | groups (Vignobles K, owner libraries) exist only as manifest `how` notes | no | — |

Conflations, as the audit was asked to test for:

| Conflation | Found? | Where |
|---|---|---|
| `estate = wine` | **yes** | `fiches.js` key, `ratings.js` key, `chateaux.blend`/`cat`/`style` |
| `wine = vintage` | no | other wines have both keys; the grand vin's "wine" part is missing, not merged into the vintage |
| `document = observation` | **yes, partially** | a canonical field cites a document; no record of what each document said |
| `source = estate` | **yes** | `sources/fiches/<estate>/` folders, read as attribution ("from the folder, which serves one estate", 143 rows); `websites.js` |
| `canonical value = source fact` | **yes** | `fiches.js` presents the first document's figure as the value, with no observation behind it; `merge-proposals.py` writes a manifest role (`grand`) because a blend was merged |

## 5. Estate / wine / vintage model

`one estate → many wines → many vintages` holds **for other wines only**.

| Case | What the model does | Finding |
|---|---|---|
| **Lynch-Bages / Echo** | Echo is a `second` wine with 13 vintage records, and the Blanc is `other`. 50 Echo sheets are filed in the manifest as the Blanc. | Representable. The misfiling is a manifest value, not a model defect. |
| **Tour Saint-Christophe / Les Terrasses** | No wine listed, so the manifest rows default to the grand vin. | **Unknown wine identity becomes the grand vin** (R1). |
| **Caillou / Les Murets** | `chateaux.second` = Les Erables; `BDX_CUVEE_WINES` has nothing for Caillou. | Representable only with an invented role (B1). |
| **Dry whites** | 30 white wines in `BDX_CUVEE_WINES`, all `other` or `second`. | Representable as an other wine. |
| **Several named wines** | Margaux 3, Haut-Brion 3, La Mission 3; Olivier, Guiraud and Smith Haut Lafitte each have two `second` wines. | Representable. `chateaux.second` holds one name and diverges from the list. |
| **Graves, two colours** | A classified white is a different wine from the classified red, but the estate *is* the red. Domaine de Chevalier Blanc and Olivier Blanc are `other`. The classified whites of Bouscaut, Carbonnieux, Latour-Martillac and Malartic-Lagravière are absent. | **A classified wine can be only the estate's grand vin** (R10). |
| **Names overlapping the grand vin** | Handled by reader guards (Phase 2), not by the model. | The model has no wine identity to check against for the grand vin. |
| **Historical relationships** | Haut-Bages Averous (Lynch-Bages' second wine until 2007). | Not representable (B2). |

`UNKNOWN`, `NO_SUCH_WINE` and `NOT_YET_MODELED` are not distinguished.
For an estate's second wine:

- `second: '—'` (34 estates) means none.
- `second` absent (35 full records) and the 298 compact estates mean
  unknown.
- The reader turns `'—'` into `None` (`sheetreader.estates`), so "none"
  and "unknown" become the same value before any rule sees them.
- `NOT_YET_MODELED`, a wine the universe knows that the dataset does not,
  has no representation; only the Phase 3.0 discrepancy file records it.

## 6. Role model

| Question | Answer |
|---|---|
| Role a property of the wine or of the relationship? | Of the wine record (`BDX_CUVEE_WINES.role`), which is effectively the relationship, since the record sits under one estate. |
| Inferred from the name? | In the reader. Phase 2's positive second-wine mode decides from the document, and the manifest caches that verdict as `role`. |
| Stored canonically? | `second` and `other` only. `grand_vin` is implicit (the estate). There is no `unknown`. |
| Different roles over time? | No. |
| Several wines of the same broad type? | Yes: Olivier, Guiraud and Smith Haut Lafitte each have two `second` wines. |
| A wine with an unresolved role? | **No** (B1). `other` serves as the catch-all, so "another cuvée" and "not yet known" are the same value. |

The three proposals, against this model:

- **Echo** needs nothing new.
- **Terrasses and Murets** both need the state "a wine of this estate,
  role not established". That state cannot be written today without
  choosing `second` or `other`. Murets also has a red and a white under one
  name; `BDX_CUVEE_WINES` would hold them as two slugs.

## 7. Temporal model

Stable identity is not separated from time-dependent state. The nine
Phase 3.0 cases as fixtures:

| Case | Today's model | Representable without overwriting? |
|---|---|---|
| T1 Mouton promoted 1973 | `growth: 1`; prose in `classifications.js` | no |
| T2 Cantemerle added 1855 | `growth: 5` | no |
| T3 La Tour Haut-Brion merged 2006 | still a current classified estate | no |
| T4 Laville Haut-Brion merged 2009 | still a current classified estate | no |
| T5 Saint-Émilion 2012 → 2022 | one `year` per collection | no |
| T6 Tour Saint-Christophe promoted 2022 | `growth: 3`, current only | no |
| T7 Crus Artisans lists | the site roster under `year: 2006` | no |
| T8 Haut-Bages Averous → Echo (2008) | Echo only | no |
| T9 Pessac-Léognan created 1987 | `appellation` string | no |

**0 of 9** can be stored as data. The rest of the list behaves the same way:

- Ownership changes are prose ("since 2016").
- Wine introductions and discontinuations are inferred from which
  vintages have records.
- Renaming would replace the name, and the name is the id for 298
  estates.

Only vintage-keyed values (`fiches`, `cuvees`) are time-indexed, and only
by vintage.

## 8. Evidence and provenance model

**Phase 2's standard holds on its own path.** `provenance.py` resolves a
document by exact folder and name, hashes it with sha256 before and after
reading, and stamps every decision with commit, dirty flag and status
hash. `evidence_store.py` is the only writer of `data/evidence/`. Only
`evidence-wines.py` and `recharacterize.py` produce decisions, through
`evidence.py`, and both go through `provenance.py`.

**It is bypassed everywhere else:**

- **Basename first match.** 11 tools build a basename index with
  `os.walk` and `setdefault`, so whichever copy is reached first wins.
  Among them are `read-fiches.py` and `read-plantings.py`, which write
  canonical data. In `read-fiches.py` it is a fallback after the
  manifest's folder path. `promote-urls.py` and `refile-wine.py` also use
  it, and they write the manifest.
- **Basename provenance.** `field-src.js` and `cuvee-src.js` name a
  document by basename only, with no folder, hash or code state.
  - 146 + 32 of the names match more than one manifest row.
  - 46 + 26 of those rows differ in bytes, and 40 differ in estate.
  - 301 + 63 canonical values cite such an ambiguous name.
- **Path identity.** The manifest identifies a document by (folder, file).
  Of 243 paths with more than one row, 204 carry different sha1s: files
  were re-downloaded over themselves, so at most one row describes the
  bytes on disk.
- **The folder used as source and attribution.** In 143 rows the
  attribution is "from the folder, which serves one estate". 665
  documents sit byte-identical under several estates' folders, as the
  Terrasses sheets do.
- **Scraping mixed with registration.** `harvest.py`, `crawl-pages.py`,
  `add-sheet.py` and `find-doc-urls.py` fetch, name, and register in the
  manifest in one run.
- **Extraction mixed with normalisation and canonical writing.**
  `read-sheets.py` and `read-fiches.py` read the document, apply guards,
  normalise values to ranges, choose winners and write canonical data.

## 9. Observation / canonical boundary

"Document A says area = X, document B says area = Y" cannot be stored as
two observations:

- **The winner** is the first document in a sort order: the estate's own
  page before its news feed, then filename (`read-fiches.py`).
- **The loser.** `conflicts.py` notes it as `SUPERSEDED` into
  `data/field-conflicts.jsonl`, which is **absent from the repository**.
  Reconciliation is therefore ephemeral in practice.
- **Never overwriting.** A value already on the record, including a
  hand-typed one with no provenance, beats every document forever. That
  keeps re-runs safe, but it turns first-writer-wins into a permanent
  rule.
- **What a document said is not stored** unless it won.
  `reports/fiches-read.json` holds one run's readings, gitignored and
  overwritten by the next run.
- **Winner provenance** is a basename (§8).

The evidence store is the one place observations survive. It holds
decisions (accept, refuse, why), not field values.

## 10. Tool responsibilities

63 tools and 16 tests. The full table, with every tool's reads, writes,
flags and network use, is `data/audit/phase31-structure.json` → `tools`.

| Responsibility | Tools |
|---|---|
| Discovery and retrieval (network) | `harvest`, `crawl-pages`, `add-sheet`, `find-doc-urls`, `find-vintages`, `ask-site`, `whose-site` |
| Fetch + register in the manifest, in one run | `harvest`, `crawl-pages`, `add-sheet`, `find-doc-urls` |
| Parsing + extraction | `sheetreader` (imported by 43 tools) |
| Extraction + guards + normalisation + reconciliation + canonical write | `read-fiches`, `read-sheets`, `read-plantings`, `read-terroir` |
| Canonical writers | `read-fiches`, `read-sheets`, `merge-proposals`, `add-wine`, `add-dutch`, `read-plantings`, `read-terroir` |
| Manifest writers | 11 (§11) |
| Evidence | `evidence-wines`, `recharacterize` (decisions); `evidence_store` (storage); 16 readers |
| Proposals | `propose`, `attribute` |
| Quality checks | `check-data`, `check-language`, `audit-*`, `census*`, `reconcile`, tests |

**Proposed boundary,** to be designed in 3.2, not built here:

```text
discover → retrieve (bytes, hash) → register (document)
         → attribute (estate, wine; a judgement, kept apart from the register)
         → extract (observations)
         → reconcile (choose, keep the losers) → canonical
```

**Flag conventions differ.** `--write` 18 tools, `--apply` 11,
`--apply` with `--dry-run` 3, `--dry-run` alone 2. Some tools act unless
told not to (`read-plantings`, `read-terroir`, `harvest`).
`read-terroir.py` and `harvest.py` say so in a comment.

## 11. Data flow and dependencies

`data/audit/phase31-structure.json` → `edges` lists 308
`INPUT → TOOL → OUTPUT` edges.

- **One cycle, through the manifest and the canonical files.** It spans
  13 tools: `add-sheet`, `add-wine`, `audit-multiwine`, `crawl-pages`,
  `find-doc-urls`, `harvest`, `merge-proposals`, `promote-urls`,
  `read-fiches`, `read-sheets`, `recheck-sources`, `recover-urls`,
  `refile-wine`.
- **36 tools rewrite their own input** (read, modify, write), most of
  them `sources.json`.
- **Unflagged manifest writes.** `promote-urls.py` rewrites `sources.json`
  on every run and has no flag at all. `read-sheets.py` writes manifest
  roles and attributions before its `--apply` exit, so a **dry run
  changes the manifest**.
- **Canonical → manifest back-flow.** `merge-proposals.py` sets a
  manifest row to `role: grand` because its blend was merged, so a
  canonical write becomes attribution.
- **Reader judgement → manifest.** `read-sheets.py` sets `role: other`
  when its colour guard refuses.
- **Canonical data consumed as configuration.** Every reader takes its
  guards' inputs (names, second wine, other wines, colour) from the
  canonical estate files via `sheetreader.estates`. A canonical error
  becomes a reader error. This is how Terrasses passed: there was no
  second wine to refuse it with.
- **Three implementations of one expansion.** The sparse-list expansion
  exists in `assets/app.js`, `sheetreader.estates` and
  `tools/canonical-view.js`.
- **Ordering assumptions.** Tools print "now run …" chains
  (`refile` → `read-sheets` → `check-data`; `recover-urls` →
  `build-fiche-links`). Nothing enforces the order.
- **A hidden dependency.** `service-worker.js` hand-lists the data files.

## 12. Persistent versus derived

| Dataset | Is | Treated as | Problem |
|---|---|---|---|
| `fiches.js`, `BDX_CUVEES` | canonical values | canonical | contains values that are really unrecorded observations (§9) |
| `field-src.js`, `cuvee-src.js` | canonical provenance | canonical | basename only |
| `sources.json` | register + attribution + judgement cache | source of truth | judgements cached as facts (`role`, `how`) |
| `data/evidence/` | evidence | evidence | sound |
| `proposals.jsonl`, `attribution-candidates.jsonl` | proposals | proposals | sound |
| `fiches-url.js`, `cuvee-url.js` | derived views | app data | derived, committed, loaded; acceptable as a build output, but nothing regenerates them automatically |
| `PROGRESS.md`, `progress-history.tsv` | generated | committed documentation | regenerated as a side effect of canonical writers (`_refresh_progress`) |
| phase `.jsonl`/`.json` in `data/` | analyses | committed beside app data | location only |
| `reports/fiches-read.json` | what each document said in one run | temporary | **should be persistent**: it is the observation layer, discarded each run |
| `data/field-conflicts.jsonl` | losing values | absent | **should be persistent** |
| hand-typed values in 16 canonical files no tool writes | persistent truth with no provenance | canonical | cannot be re-derived |

## 13. Identity and naming

| Thing | How identified | Stable? |
|---|---|---|
| Full-record estates (172) | hand-chosen id (`lafite`, `stem-chateau-tour-saint-christophe` …) | yes, unless renamed by hand |
| Compact estates (298) | `cls + '-' + slug(display name)`, derived in `app.js` and `sheetreader.py` | **no**: correcting a spelling changes the id. The id keys `coords.js`, `plantings.js`, `terroir.js`, `cuvees.js`, the manifest's `estate`, and **the evidence store's `target_estate`, which is immutable** |
| Wines | slug within the estate; the grand vin has none | other wines: yes |
| Documents | (folder, file) | **no**: the path is reused for new bytes (§8) |
| Aliases, historical names | nowhere | — |

The Phase 3.0 cases:

- **Bellevue and La Commanderie** (same name, Saint-Émilion and Crus
  Bourgeois) stay apart only because their ids carry a collection prefix.
  That is safe by accident. There is no way to record "possibly the same,
  unresolved".
- **Pichon-Baron and Marquis d'Alesme Becker** are name variants of
  full-record estates, so their ids are stable. But no alias can be
  stored, so the Council's name cannot be held beside the dashboard's.
- **Trottevieille / Trotte Vieille and Malescot St./Saint** are the same.

Unresolved identity can therefore be represented safely **only outside
canonical data**, as Phase 3.0 does in `data/scope/`.

## 14. Scope integration

| Question | Answer |
|---|---|
| Classification systems kept separate? | Only by collection file and `cls`. Haut-Brion's second membership needs a special list. |
| An estate in several classifications? | One record, one `growth`, one cross-list exception. **No** in general. |
| Several appellations? | **No** (Moutte Blanc). |
| Many wines? | Yes for other wines; the grand vin is the estate. |
| Wine membership with unknown role? | **No** (B1). |
| Temporal relationships? | **No** (B2). |
| Authoritative membership alongside incomplete wine knowledge? | Yes, because the universe lives apart, in `data/scope/`. |
| Universe kept apart from operational canonical data during migration? | **Yes, today.** `data/scope/` is written only by `build-universe.py` and `compare-universe.py`, loaded by no page, and read by no canonical writer (measured; `test-phase31` keeps it so). Nothing forces a universe fact into canonical data. |

## 15. Partial wine universe limitation

> The incomplete authoritative wine universe is a domain-data limitation carried forward from Phase 3.0. It is not treated as a structural blocker for this audit.

The audit asked whether the model can *hold* what the universe knows and
does not know. Where it cannot, the finding is about structure:

- B1: no unknown role.
- R1: an unknown wine becomes the grand vin.
- R11: "none" and "unknown" are collapsed.

None of these is about the 385 estates whose wines were not researched.

## 16. Proposed conceptual model

Concepts and relations only. These are not tables, objects or files.

```text
Source (site, publisher, body)          ClassificationSystem (body, validity)
   │ publishes                                 │ has
   ▼                                           ▼
Document (bytes: hash; paths: many)     ClassificationMembership
   │ is read into                          (estate or wine, rank, appellation,
   ▼                                        valid from/to, source)
Observation (document × subject × field × value,                │
             reader version, read provenance)                   │
   │ reconciled by                                              │
   ▼                                                            │
Reconciliation (candidates, rule, winner, losers kept) ──▶ CanonicalValue
                                                         (subject × field,
Estate (stable id) ◀── HistoricalIdentity (names,         value, chosen-from,
   │                    aliases, merges, valid from/to)   provenance)
   ├── Ownership (owner/group, valid from/to, source)
   ├── Appellation membership (valid from/to)
   └── WineEstateRelationship (valid from/to, source)
          │
          ├── Wine (stable id; grand vin is a Wine)
          ├── WineRole (grand_vin | second | other | … | UNKNOWN; valid from/to)
          └── Vintage (wine × year)  ◀── subject of Observations / CanonicalValues

Quality/Anomaly: attaches to a Document, an Observation or a CanonicalValue.
Provenance: on Observation (document hash + reader + code state) and on
CanonicalValue (which observations, which rule).
Attribution (document → estate/wine/vintage) is itself a judgement with
provenance, not a property of the Document.
```

Every concept the brief lists is needed, and each corresponds to a
finding:

| Concept | Why it is needed |
|---|---|
| **Estate** | separated from the grand vin (R2) |
| **Wine** | gives the grand vin an identity (R2, R10) |
| **WineEstateRelationship** | the place for time and role (B1, B2) |
| **WineRole** | with `UNKNOWN` (B1) |
| **Vintage** | already sound as wine × year |
| **Document** | identified by bytes (R9) |
| **Source** | separated from the estate (R8) |
| **Observation** | B3 |
| **CanonicalValue** | chosen from observations (R5) |
| **Provenance** | one standard (R3, R4) |
| **Reconciliation** | persistent (R5) |
| **Quality/Anomaly** | persistent (L-findings) |
| **ClassificationMembership** | per wine, with validity (R10, B2) |
| **Appellation** | a membership, not a string (L3) |
| **HistoricalIdentity** | names, aliases, merges (B2, L12) |

One addition the repository's evidence supports: **Attribution** as its
own judgement. Today it lives inside the manifest row, written by
eleven tools.

## 17. Findings classification

40 findings. Each has exactly one class.

### A. SOUND (8)

| Id | Finding |
|---|---|
| S1 | Evidence store: one writer, append-only, sha256 and code state per decision; 16 readers, **0** write canonical data or the manifest. |
| S2 | Proposals are inert: written by `propose` and `attribute`, read by no tool that writes canonical data or the manifest. |
| S3 | The Phase 3.0 universe is separate: written only by its two tools, loaded by no page, read by no canonical writer. |
| S4 | Documents cannot create wines: other-wine rows are read only into wines listed in `BDX_CUVEE_WINES`. |
| S5 | `estate → wine → vintage` exists for other wines (`estate|wine|vintage`, 1,174 records, 135 wines, several of one role per estate). |
| S6 | Exact lookup, hashing and code-state provenance on the evidence path (`provenance.py`). |
| S7 | Vintage-level descriptions (`vintages.js`, `phenology.js`) are kept apart from wine values. |
| S8 | Most store writes are flag-gated; manifest rewrites keep `.bak` copies; `read-sheets` re-reads before writing back. |

### B. LIMITATION (12)

| Id | Finding |
|---|---|
| L1 | The estate record mixes estate, ownership, classification, grand-vin and editorial fields. |
| L2 | Classification is encoded by file, a colour default and `growth`; one membership per record plus a Haut-Brion exception. |
| L3 | One appellation string per estate. |
| L4 | Four flag conventions; some tools act unless told not to. |
| L5 | Manifest `role` mixes wine role with document type. |
| L6 | 16 canonical files are hand-edited only; their values carry no provenance. |
| L7 | `service-worker.js` hand-lists data files under a hand-bumped cache name. |
| L8 | `reports/` mixes generated output with committed hand-written reports. |
| L9 | The sparse-list expansion is implemented three times. |
| L10 | Ownership is one string; dates live in prose. |
| L11 | Source/site is not an entity (estate → site in `websites.js`; per-row `url`). |
| L12 | No aliases or historical names; unresolved identity can live only outside canonical data. |

### C. STRUCTURAL RISK (12)

| Id | Finding |
|---|---|
| R1 | **An unknown wine becomes the grand vin**: rows with role `unknown` (4,368), `page`, `grand` or `combined` are read into `estate|vintage`. Applying the 15 Terrasses "set estate" proposals as they stand would route them there. |
| R2 | **The grand vin has no wine identity**: `fiches.js` is keyed `estate|vintage` (2,725), and so is `ratings.js`. |
| R3 | **Canonical provenance is a basename**: 364 values cite a name matching more than one manifest row (72 of those names differ in bytes, 40 in estate). There is no hash and no code state. |
| R4 | **Basename first-match** in 11 tools, including canonical writers (`read-fiches` fallback, `read-plantings`) and manifest writers (`promote-urls`, `refile-wine`). |
| R5 | **First-writer-wins, forever**: winner by sort order, never overwritten; hand values with no provenance beat documents. |
| R6 | **Unflagged manifest writes**: `promote-urls` (no flag), `read-sheets` (before its `--apply` exit). |
| R7 | **The manifest is register, attribution and judgement cache**, with 11 writers, a 13-tool cycle, and canonical → manifest back-flow (`merge-proposals` sets `role: grand`). |
| R8 | **The folder is read as attribution**: 143 rows; 665 documents byte-identical across estates' folders. |
| R9 | **Document identity is the path**: 243 paths with several rows, 204 with different sha1; sha1 in the manifest, sha256 in the evidence. |
| R10 | **A classified wine can only be the grand vin**: Graves classified whites appear as `other` (2) or are absent (4). |
| R11 | **"None" and "unknown" are collapsed**: `'—'` (34) becomes `None`, as do absent fields (35) and all 298 compact estates. |
| R12 | **The display name is the id** for 298 estates; a correction rekeys them. |

### D. BLOCKER (3)

The current structure cannot represent these concepts safely.

| Id | Finding |
|---|---|
| B1 | **No unresolved role.** Roles are `{second, other}`; "a wine of this estate, role not established" (Terrasses, Murets) requires inventing one. |
| B2 | **No temporal state.** Classification, ownership, names, appellation and wine relationships are current single values; 0 of 9 dated fixtures can be stored without overwriting history. |
| B3 | **No observation layer** for canonical fields. Two documents disagreeing cannot both be kept; losers are discarded and the conflicts file does not exist. |

### E. MIGRATION RISK (5)

| Id | Finding |
|---|---|
| M1 | `estate|vintage` keys are shared by `fiches.js`, `field-src.js`, `fiches-url.js`, `ratings.js`, `cellar.js` and `overrides.js`. Giving the grand vin a wine identity rekeys all of them at once. |
| M2 | Name-derived ids are referenced by immutable evidence (`target_estate`). A rename must be an id mapping, never a rewrite, or v1–v5 point at retired ids. |
| M3 | Hand-typed canonical values have no provenance and cannot be re-derived. A migration must carry them as unattributed observations, not drop or "re-read" them. |
| M4 | Paths with several sha1s: moving to content identity must decide which row describes today's bytes, and keep the others as history. |
| M5 | `'—'` means "none" in data and display (`app.js` shows it), but `None` in the reader. Changing either side alone changes behaviour. |

## 18. Phase 3.2 prerequisites

The normalisation architecture must:

1. **Give the grand vin a Wine identity,** separate from the Estate (R2,
   R10, M1), so that a classified wine can be any of an estate's wines.
2. **Make unknown explicit:** an unknown wine stays unattributed instead
   of defaulting to the grand vin (R1), and `UNKNOWN`, `NONE` and
   `NOT_YET_MODELED` are distinct values (R11, M5).
3. **Add a WineRole with `UNKNOWN`** on a time-bounded
   WineEstateRelationship (B1).
4. **Add an observation layer:** every value each document states, with
   the document's hash, the reader version and code state. Canonical
   values are chosen from observations by a recorded rule, and the losers
   are kept (B3, R5).
5. **Identify documents by bytes,** with paths as locations. Settle on one
   hash (R9, M4).
6. **Adopt one provenance standard,** Phase 2's, for canonical values too
   (R3, R4). Retire first-match lookups.
7. **Separate attribution from the document register,** as its own
   judgement with provenance. Settle which tools may write it (R7, R8),
   and gate every write (R6).
8. **Give stable ids that are not names,** with an alias and history
   store, and map old ids to new ones without touching the evidence store
   (R12, M2, L12).
9. **Model time:** classification and appellation memberships, ownership,
   names and wine relationships with validity, able to hold the nine
   Phase 3.0 fixtures (B2).
10. **Carry hand-typed values forward** as unattributed observations (M3).
11. **Keep the boundaries that are sound** (S1–S4). In particular, keep
    the authoritative universe apart from operational data until a
    reconciliation step, not a migration, brings a fact across.

## 19. Phase 3.1 gate

The audit covered every stage the brief set: baseline, structure,
canonical data, entities, the estate/wine/vintage chain, roles, time,
documents and sources, observations, the evidence boundary, tools, data
flow, persistence, identity, scope integration, and the conceptual model.
Each finding is classified and evidenced. Three blockers were found. They
are blockers *of the current structure* for Phase 3.2 to design around,
not gaps in this audit, and none of them is the partial wine universe.
Nothing was changed to address them.

**SAFE — STRUCTURAL AUDIT COMPLETE**
