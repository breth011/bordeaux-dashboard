# Phase 4 — Normalized domain model: implementation and reversible migration

Gate: **SAFE — NORMALIZED MODEL IMPLEMENTED — DUAL READ PASS**

The Phase 3.4 contract (`docs/phase34-model.json`) is implemented beside the existing data as a
normalized model in `data/model/`. It is built by `tools/migrate.py`, stage by stage (M0–M13), and
nothing outside `data/model/` was written. It reconstructs today's dataset with zero unexplained
differences (M8). The page's own logic reads the same 470 estates from it (M9). Every stage can be
rolled back.

The application has **not** been switched to it. That is the separate, controlled step the canonical
switch gate reserves. No undecided domain question was settled along the way. Each one is held in
the model as unresolved.

| | |
|---|---|
| Start | `91a5b8b` (Phase 3.4) |
| Commits | `84f80d6` M0 · `9ef3d1d` M1 · `ba2386e` M2 · `677eef8` M3 · `303bbba` M4 · `61bf112` M5 · `8ba8716` M6 · `5228f8f` M7 · `91d694b` M8 · `2d4faad` M9 · `c7333e4` M10 · `7175ca5` M11 · `2e83a27` M12 · `2e297a5` M13, and this report |
| Tests | `tools/test-phase4.py`: 66 checks, all pass; every existing suite passes (21 suites) |
| Canonical / evidence / discovery changes | 0 / 0 / 0 |
| Migration errors | 0 |
| Unresolved legacy mappings | 57 identity-map entries; 281 filename references with no unique document |

---

## 1. Baseline

M0 (`tools/phase4-baseline.py`) recorded the state at `91a5b8b`, which was equal to `origin/main` with a clean tree and
all 20 suites passing. It wrote:

- `data/model/baseline.json`: the sha256 of every file in the seven protected groups, plus the counts;
- `docs/PHASE-4-MIGRATION-BASELINE.md`: the same, readable.

The protected groups are:

- canonical data (39 files);
- phase records (14);
- evidence (8);
- discovery (571);
- scope (3);
- review (1);
- the Phase 3.4 contract (4).

The counts the migration is held to:

| Measure | Value |
|---|---:|
| Canonical estates (as app.js expands them) | 470 |
| Full records / name-derived ids | 172 / 298 |
| Other wines (BDX_CUVEE_WINES), second / other | 135 (77 / 58) |
| 'estate\|vintage' records (fiches) / values | 2,725 / 11,838 |
| 'estate\|slug\|vintage' records (cuvees) / values | 1,174 / 4,623 |
| Manifest rows / paths / multi-version paths | 13,032 / 12,771 / 204 |
| Evidence decisions v1–v5 / provenance failures per version | 177,127 / 123 |
| Discovery artifacts / observations | 29,517 / 163,582 |

Phase 3.2 counted 12,491 fiche values. That figure included the record metadata (src, url and the
translation flags). The count of values alone is 11,838.

## 2. New physical representation

**D3 (storage), decided:** files, not a database.

- **Layout:** one JSON Lines file per entity of the contract, in a directory per layer (`identity/`,
  `state/`, `document/`, `observation/`, `reconciliation/`, `canonical/`, `cross/`). Each file is sorted by
  its key, so a rebuild is byte-identical and a diff can be reviewed.
- **Why no database:** the volumes need none (at most 82,000 rows a file), the app is a static page,
  and the contract forbids a database for convenience.
- **Manifest:** `data/model/manifest.json` lists every file with its entity, row count and sha256.
- **Line endings:** `data/model/**` is pinned to LF.
- **Size:** the model is 77 MB in all. The evidence links are 20 MB of that.

The raw bytes are not copied; there is not the disk for it.

- **Locating bytes:** `tools/raw_store.py` finds an artifact by digest, either in the
  content-addressed discovery blobs or at its legacy path.
- **Overwritten paths:** a legacy path is returned only while its bytes still hash to the digest asked
  for.
- **Read in place:** the 163,582 harvested observations and the 177,127 evidence decisions are read
  where they are (`tools/model_reader.py`, the evidence store), not duplicated.

**D4 (ids), decided:**

- **Identity entities** (Estate, Wine, Source, Party, Artifact) have opaque sequential ids (`es_00001`,
  `wn_00001`, `ar_000001`). They are minted once and reused from the identity map on every rebuild.
- **Every other record's id** is a prefix plus a hash of its natural key.
- **Vintage references** are written `vt:<wine>:<year>`.
- **No name in an id:** no id is derived from a name.

**Validation:** `tools/migrate.py` validates every row against the contract before writing:
fields, enums, temporal bounds (a dated bound needs a basis; OPEN appears only as `valid_to`) and
references (none may dangle).

| File | Rows | | File | Rows |
|---|---:|---|---|---:|
| identity/estates | 470 | | state/estate-wine | 639 |
| identity/wines | 639 | | state/rank-assertions | 684 |
| identity/vintages | 5,286 | | state/rank-absences | 34 |
| identity/artifacts | 37,067 | | state/classification-memberships | 399 |
| identity/sources | 367 | | state/appellation-memberships | 376 |
| identity/parties | 5 | | state/estate-locations | 272 |
| identity/names | 1,104 | | state/editorial-memberships | 78 |
| identity/identity-map | 56,531 | | state/source-estate | 409 |
| document/placements | 19,394 | | state/vintage-statements | 18 |
| document/attributions | 12,128 | | observation/observations | 22,437 |
| document/assessments | 7,577 | | observation/evidence-links | 81,544 |
| document/legacy-references | 13,230 | | reconciliation/reconciliations | 12,959 |
| cross/provenance | 25,895 | | canonical/values | 12,959 |
| cross/findings | 444 | | canonical/translations | 1,072 |

These contract entities have homes but no rows yet, because no legacy data holds them:

- **Not in the legacy data:** IdentityTransition, Ownership, WineDescriptor, ArtifactDate,
  ArtifactRelation, DocumentFamily.
- **Left for later on purpose:** Ownership needs the owner strings decomposed into parties (L10).
  Artifact dates and families belong to the discovery data, which is read in place.

## 3. Identity mapping

**Estates:**

- **One Estate per canonical id:** 470 are minted.
- **Coverage:** the identity map holds every legacy estate id used by any data file, the manifest, or
  the evidence (`ctx.estate`, `target_estate`): 471 ids.
- **Name-derived ids:** the 298 are mapped as they stand, never recomputed, and so is each compact-list
  entry (298).
- **Unresolved:** one id, `saint-julien` (17 keys of `ratings.js` the app never shows). It has no stable
  id, no candidates and an IDENTITY_UNCERTAIN finding.

**Artifacts:** one per digest, 37,067 in all: 12,019 manifest sha1s and 25,048 sha256 artifacts with no
sha1 (the harvest's and the reader's). A sha1 and a sha256 are joined into one artifact only when it is
proven they hash the same bytes:

- **Harvest proof:** 4,526 joins. The harvest hashed the fetched bytes both ways.
- **Evidence-path rule:** 7,206 joins. The manifest records one version at the path and every v4/v5
  read there hashed one sha256.
- **Refused:** 22 joins, as conflicting.
- **Unproven reads:** 76 reads are proven to be no recorded version. They are placements and findings
  of their own, not guessed joins.

**Placements:** one per (locator, artifact), 19,394 in all:

| Status | Placements |
|---|---:|
| PRESENT | 12,588 |
| BYTES_UNAVAILABLE | 279 |
| MISSING (no artifact) | 103 |
| NAME_MISMATCH (no artifact) | 20 |
| URL | 6,328 |

- **Multi-version paths:** the 204 paths keep every version. A version is PRESENT only where it is
  proven to be the bytes that were read.
- **Provenance failures:** the 123 are placements with no artifact. The manifest's claimed digest stays
  on their provenance.

**Filenames:** 13,230 legacy filename references, each listing every placement of its basename as a
candidate.

- **Resolution:** ACTIVE only when the candidates hold one artifact. There is never a first match.
- **Field references with several candidates:** 370. Of these, 174 differ in bytes and stay
  AMBIGUOUS.
- **No document at all:** 39 references. They are 38 Latour page citations with no file and one
  Pagodes de Cos text missing from the manifest.

## 4. Estate migration

**Estate-level state:**

- **Names:** one CURRENT name per estate, verbatim, provenance LEGACY_UNSOURCED.
- **Editorial collections:** Pomerol, Libournais, Côtes, Graves & Entre-Deux-Mers and Médoc beyond the
  lists stay estate-level EditorialCollectionMemberships (78), never classifications.
- **Locations:** 272. Each estate file's commune and position, and coords.js separately with its method.
  A two-element coords entry is given no invented method.

**Estate fields that become observations:** the vineyard area, owner, blend, perf, style, history,
terroir and sources (M7). Of these, only the vineyard area (class A) has a canonical value.

Owner and the estate blend stay observations. Owner needs Ownership parties nobody has established,
and the blend is plantings or assemblage, to be decided per estate (D1). They carry an
AMBIGUOUS_SEMANTICS finding.

## 5. Wine migration

**Grand vins (M3):** 458 Wines, minted only where the legacy data supports one:

- a classification listing (the classification's unit is the cru);
- a full estate record;
- an 'estate|vintage' record; or
- a manifest 'grand' attribution.

| Point | Result |
|---|---|
| No support | 12 Pomerol compact-list names have nothing beyond the list, so they get no Wine. The app's defaults for them are page behaviour. |
| Type | From the full record's cat: 138 RED, 7 WHITE_DRY, 27 WHITE_SWEET. The 286 compact-list wines stay UNKNOWN. |
| Name | The estate's own, as the dataset shows it. |
| Relationship and rank | PRODUCED_BY, and FIRST within the estate's range, claimed by the DATASET (`legacy_term` 'grand'). |
| Classification | On the Wine: six schemes, each with the dataset's edition and its body as the Phase 3.0 sources name it, verbatim. |

The classification memberships per scheme:

| Scheme | Memberships |
|---|---:|
| 1855 | 61 |
| Sauternes | 27 |
| Saint-Émilion | 85 |
| Graves | 15, plus Haut-Brion's cross-listing |
| Crus Bourgeois | 170 |
| Crus Artisans | 34 |

There are also 376 appellation memberships.

**Other wines (M4):**

- **The 135 wines of BDX_CUVEE_WINES:** one Wine per (estate, slug), with type from colour.
- **Their ranks:** each carries a DATASET claim. `second` becomes SECOND. `other` becomes **UNKNOWN**
  with `legacy_term` 'other', never a rank of its own.
- **Red and white seconds:** estates listing both get an AMBIGUOUS_SEMANTICS finding (Guiraud,
  Olivier, Smith Haut Lafitte).

The estate files' 137 `second` strings were mapped mechanically, without judgement:

| Outcome | Count |
|---|---:|
| `'—'`: RankAbsence SECOND, not UNKNOWN | 34 |
| …of which contradicted by cuvees.js (Batailley, Lynch-Moussas): CONFLICT finding, both kept | 2 |
| A listed wine, exact name | 42 |
| A listed wine, by typography only (case, apostrophe form, hyphen/space) | 3 |
| Minted, because the estate lists no wines | 41 |
| Another name than the wines the estate lists: AMBIGUOUS, the listed wines as candidates (a rename or succession, not decided: La Parde / Haut-Bailly II, Le Sillage / Le Comte de Malartic) | 11 |
| Commentary, not a name (Yquem's "a dry white, not a second wine"): no wine, no rank | 4 |
| Named as the second of two estates (La Réserve de Léoville-Barton): AMBIGUOUS | 2 |

Every string stays in the identity map, so the field remains reconstructable.

The 8 Graves estates classified 'red and white' (the white wine is not named, D8):

| Outcome | Estates |
|---|---:|
| The estate's one listed white wine | 1 |
| Several listed whites: waits, AMBIGUOUS | 2 |
| A white Wine minted with name_status UNKNOWN | 5 |

**Display names**, which evidence `target_wine` resolves through, follow the same decisions:

- **Resolved:** 637.
- **Undecided seconds:** 17, which keep their candidates.
- **Unresolved:** 1, L'Enclos. The reader asked about a grand vin the data never supports, and refused
  every time.

## 6. Vintage migration

- **Grand vins:** every key of the seven structures sharing 'estate|vintage' maps through the identity
  map to the Vintage of that estate's grand-vin Wine (10,337 keys). The structures are fiches,
  field-src, fiches-url, ratings, cellar, BDX_SCORES and fiches-nl.
- **Other wines:** every 'estate|slug|vintage' key maps to a Vintage of the slug's Wine (2,459 keys).
- **Totals:** 5,196 Vintages from the data, plus 90 from manifest attributions, giving 5,286.
- **Not produced:** BDX_NOT_PRODUCED gives 18 VintageStatements NOT_PRODUCED.
- **Kept verbatim, not attached:**
  - the 17 `saint-julien` ratings;
  - 2 cuvee records whose slugs are not listed (`ch-teau-dauzac-blanc`, `clart-de-haut-brion-blanc`).

  Each sits on a provenance record that names its file, global and key, with a finding.
- **Orphan provenance:** the 16 cuvee-src keys with no record (a mangled Giscours slug) are
  ORPHAN_PROVENANCE findings. Their filename references keep them.

## 7. Provenance migration

A value's provenance is its field's, never its record's (I13):

| Status | Meaning | Canonical values |
|---|---|---:|
| LEGACY_FIELD_SOURCE | field-src names the field and one artifact | 5,827 |
| LEGACY_AMBIGUOUS_SOURCE | field-src names the field, not one artifact | 131 |
| LEGACY_RECORD_SOURCE_ONLY | only the record has a src | 6,830 |
| LEGACY_UNSOURCED | neither (the estate vineyard areas) | 171 |

- **The Badette 2020 oak case:** the value stays LEGACY_RECORD_SOURCE_ONLY, never the record's sheet.
- **Artifacts on a value's provenance:** one is attached only through a resolved field source.

**Sources:** 367 in all.

- **Hosts:** 365, one per host named in websites.js and the discovery targets. A host gets kind
  ESTATE_SITE when one estate lists it, and UNKNOWN for the 30 that several estates list.
- **Others:** bordoverview.com (the aggregator behind ratings.js) and the Wine Advocate (the critic
  BDX_SCORES names).
- **Never identity:** an estate reaches a source only through a SourceEstateRelationship.

**The manifest:** each of the 13,032 rows is one ranked Attribution LEGACY (5,455) or one
ArtifactAssessment (7,577). A row of the second kind that names an estate also keeps that claim as an
Attribution with no rank (6,673).

- **Null wines:** a null wine stays null, except under role 'grand', which names the grand vin.
- **Method:** every row is LEGACY_UNKNOWN. The legacy `how` table (D6) is not decided; the row's own
  words are kept on its provenance, with its path, colour, note and year.

**Evidence links:** 81,544, one per v4 and v5 decision.

- **Key:** exactly as `tools/evidence.py` builds it.
- **Targets:** the hashed artifact, plus the estate and wine asked about where those resolve
  (74,804 have a wine).
- **v1–v3:** not linked to bytes they never hashed.

## 8. Observation migration

**Observations:** 22,437 in all, one per legacy value. They are taken from what the files already
hold; nothing was re-extracted. They are:

- all 11,838 fiche values, and 4,619 cuvee values (the other 4 belong to the unresolved records);
- 2,462 ratings, 644 cellar notes, 61 cited scores, 93 plantings and 81 soil statements;
- the 1,704 document URLs;
- the estate fields.

**Record metadata:** what a record says about its values rides on each value's extraction record,
verbatim:

- the record's src, url and via;
- the translation flags on the translated text fields;
- the qualifier on sugar and the unit on acidity;
- the parsed window years on the window.

**Translations:** the 1,072 Dutch texts are Translations of their source observations, never
observations themselves.

**Canonical values** exist only for taxonomy class A: alc, blend, harvest, pick, months, oak, ph, sug,
ta, yld, and the estate's vineyard area. That is 12,959, each with one Reconciliation (rule
LEGACY_NEVER_OVERWRITE, status LEGACY_RETAINED) whose candidates include every observation. No class
B–F value was promoted.

**Pre-existing defects, kept verbatim with findings:**

- three fiche records holding only a src (Latour-Martillac 2020, Malescot 1995, Prieuré-Lichine 2021);
- one field flag without its field;
- five Dutch translations of a field the English record lacks.

## 9. Canonical reconstruction

`tools/model_reader.py` projects the model back into the legacy shapes without reading a legacy file.
`tools/reconstruct.py` compares the projection, value by value, with every legacy global the page reads
and every row of `sources.json` (`data/model/checks/reconstruction.json`).

| Class | Count | What |
|---|---:|---|
| EXPECTED STRUCTURAL DIFFERENCE | 47 | presentation order (15), empty provenance records (19), files outside the contract the page keeps reading (13) |
| LEGACY AMBIGUITY | 273 | kept, meaning undecided: the estate blend (D1), undecided seconds, reads of multi-version paths |
| PRE-EXISTING DATA ISSUE | 13 | records holding no value, orphan translations, five sha1s the manifest gives two byte counts |
| UNRESOLVED | 19 | kept verbatim: saint-julien, the two unlisted slugs |
| **TRUE MIGRATION ERROR** | **0** | |

A test injects errors into the projection (a changed value, a dropped record, an invented second, a
dropped list entry, a changed role, a changed sha1) to show the comparison sees each one.

## 10. Dual-read results

`tools/dual-read.py` (`data/model/checks/dual-read.json`): **PASS**.

- **The page's path.** The model's projection is written as page-loadable files into a temporary
  directory, never `data/`. The page's own estate expansion (`canonical-view.js`, the app.js replica
  that test-phase30 guards) yields the same **470 estates, field for field**, from those files as
  from `data/`. Only the order differs: the model holds none.
- **Queries.** The new reader resolves each legacy key through the identity map to a model subject and
  reads its observations, canonical values, relationships and references. It agrees with the legacy
  globals on:
  - 2,722 fiches (the three records holding no value aside);
  - 1,172 cuvee records;
  - 2,462 ratings;
  - 8,524 field sources;
  - the wines of all 470 estates;
  - the sheet counts of 251 estates.

## 11. Quality audit

`tools/quality-audit.py` (`data/model/checks/quality-audit.json`) runs fourteen detectors. Every hit
is a **proposal**; nothing was fixed.

| Detector | Hits | Note |
|---|---:|---|
| duplicate estates | 2 | two Bellevues, two Commanderies: likely distinct, review |
| duplicate wines | 0 | |
| duplicate wine aliases | 18 | undecided seconds, L'Enclos |
| impossible estate/wine relationships | 0 | |
| conflicting temporal intervals | 0 | |
| overlapping mutually exclusive rank claims | 5 | red and white 'seconds' (Guiraud, Olivier, Smith Haut Lafitte); a dash against a listed second (Batailley, Lynch-Moussas) |
| classification contradictions | 212 | the Phase 3.0 differences against the authoritative lists |
| appellation contradictions | 0 | |
| orphan documents | 723 | manifest artifacts no attribution assigns to an estate (the 908 unattributed rows) |
| orphan observations | 0 | |
| provenance-less canonical values | 0 | 171 are marked LEGACY_UNSOURCED |
| unresolved legacy references | 320 | AMBIGUOUS filename references and identity-map entries |
| duplicate document identities | 76 | reads not proven to be any manifest version: hash what is on disk to decide |
| invalid source relationships | 30 | one site as the official site of several estates |

## 12. Proposal compatibility

`tools/proposal-compat.py` (`data/model/checks/proposal-compatibility.json`) writes each pending
proposal as the rows it would add. The rows refer to the model's real ids and are validated against
the contract. **All three are representable with no schema change.** None is applied: no proposal row
is in the model.

| Proposal | How it fits |
|---|---|
| Echo de Lynch-Bages | The existing wine. A PRODUCER claim of SECOND from vintage 2008, with its observation. The predecessor, Haut-Bages Averous, is a SUCCEEDED_BY transition of certainty **UNRESOLVED** (D2 undecided). |
| Les Murets de Caillou (blanc) | Its own WHITE_DRY Wine, apart from the RED Murets of the same name and the estate's other wines. SECOND within TYPE_RANGE WHITE_DRY. |
| Les Terrasses de Saint Christophe | Its own Wine, FROM_ESTATE_VINEYARD and MADE_BY_GROUP_TEAM of Tour Saint-Christophe. SECOND for 2016–2019; **UNKNOWN** from 2020. |

## 13. Known legacy ambiguities

These are kept in the model and not resolved:

- **The estate blend** (172 records): plantings or the usual assemblage, per estate (D1).
- **Owner strings:** they mix several parties and caveats (L10). No Party or Ownership is minted from
  them.
- **Seconds:** 11 named seconds differ from the wines the estate lists (renames or successions),
  4 seconds carry commentary, and 2 names are the second of two estates.
- **The legacy role `second`:** it does not say within which range. Three estates list a red and a
  white 'second'.
- **The legacy role `other`:** it meant both 'another cuvée' and 'not known' (UNKNOWN).
- **The Graves white wines:** two estates list several whites; five white wines are unnamed (D8).
- **The legacy how table** (D6): every attribution method is LEGACY_UNKNOWN.
- **Multi-version paths:** 279 placements whose bytes cannot be shown to be on disk.

## 14. Unresolved migration issues

None blocks the gate. Each is classified, kept and reported:

| Kind | Count |
|---|---:|
| Legacy estate id resolving to no estate (`saint-julien`) | 1 |
| 'estate\|vintage' / 'estate\|slug\|vintage' keys kept verbatim | 17 / 2 |
| Undecided seconds / Graves whites waiting | 17 / 2 |
| Evidence target wine with no supported wine (L'Enclos) | 1 |
| Display names ambiguous (undecided seconds) | 17 |
| Identity-map entries without a stable id, in all | 57 |
| Filename references with no unique document (AMBIGUOUS 242, no candidate 39) | 281 |
| Reads not proven to be a manifest version | 76 |
| Manifest wine names that resolve to no wine (kept on provenance) | 181 |

Phase 4 did **not** decide:

- Echo rename versus succession;
- D5;
- the four Graves white names;
- Terrasses after 2019;
- any historical identity, uncertain relationship or source conflict.

None of these was needed to migrate.

## 15. Exact hashes and counts

The protected groups, at M0 and now (`python tools/phase4-baseline.py --check`):

| Group | Files | Digest at M0 | Digest now |
|---|---:|---|---|
| canonical | 39 | `f565386959c11a80` | `f565386959c11a80` |
| phase_records | 14 | `7296115a0e392720` | `7296115a0e392720` |
| evidence | 8 | `ca73da58b284d3bb` | `ca73da58b284d3bb` |
| discovery | 571 | `e6c8a40bc0b2d132` | `e6c8a40bc0b2d132` |
| scope | 3 | `c2a1463108c9776f` | `c2a1463108c9776f` |
| review | 1 | `5f4724a04a7e389c` | `5f4724a04a7e389c` |
| phase34_model | 4 | `effff82f6cedc4d0` | `effff82f6cedc4d0` |

The model files and their sha256 are in `data/model/manifest.json`, and the per-file baseline hashes
in `data/model/baseline.json`. No `decisions-v6` exists, and the reader is still `7e8cfed1c24e`.

`python tools/migrate.py --check` rebuilds the whole model twice, from scratch and from the identity
registry, and compares it byte for byte with what is committed. Reproducing the derived artifacts:

| Command | Output |
|---|---|
| `python tools/reconstruct.py` | the reconstruction report |
| `python tools/dual-read.py` | the dual-read report |
| `python tools/quality-audit.py` | the quality audit |
| `python tools/proposal-compat.py` | the proposal compatibility report |
| `python tools/app-boundary.py` | the application boundary |
| `python tools/build-indexes.py` | the derived indexes |

## 16. Rollback procedure

Nothing outside `data/model/` was ever written, so rolling back never touches the legacy data.

- **Undo a stage:** `python tools/migrate.py --revert Mx` rebuilds the model up to the stage before
  Mx, and removes the tables no earlier stage writes.
- **Undo the migration:** `python tools/migrate.py --revert M2` leaves only `manifest.json`.
  Deleting `data/model/` removes the model entirely. The app is unaffected either way: it reads
  `data/*.js`.
- **Undo a commit:** each stage is one commit, so `git revert <commit>` undoes it.
- **Tested:** `test-phase4` reverts M7 in a temporary copy and gets exactly the bytes of a fresh build
  up to M6. It then reverts to M1, which leaves only the manifest, and checks that no protected group
  changed.

## 17. Phase 5 boundary

**D7, decided in M12 (`tools/app-boundary.py`):**

- **What the app reads:** page-loadable files generated from the model's projection. That means
  canonical values, observations and provenance where the page shows them (class B text such as
  tasting and cellar notes), and the derived indexes (`data/model/derived/`: estate → wines, wine →
  vintages, vintage → documents, source → documents, wine → current rank, estate → classifications).
- **What it never reads:** scraper output, the discovery data, the evidence logs, the manifest,
  migration files or the raw store.
- **What it loads today:** 23 files the model projects, and 13 page assets outside the contract (map
  geometry, notes, regional vintages, classification prose). It loads nothing forbidden.

**The canonical switch gate.** Its conditions are met:

- all migration and existing tests pass;
- reconstruction has zero unexplained differences;
- the identity mappings are complete or classified;
- provenance is preserved;
- no evidence was rewritten and no discovery data changed;
- no proposal was applied;
- the dual read passes;
- rollback is tested;
- the tree is clean and `origin` matches.

**The switch itself** has not been made. Making the model authoritative is a separate, controlled
step:

1. Generate `data/*.js` from the projection.
2. Diff the generated files against today's, and confirm the only differences are the expected ones
   (order).
3. Point the service worker at them.
4. Retire the hand-maintained files only after a release on the generated ones.

**What Phase 5 inherits as decisions, not as migration work:**

- D2 (Echo);
- D5;
- D6 (the legacy how table);
- D8 (the Graves white names);
- D1 per estate;
- the undecided seconds;
- Terrasses from 2020;
- the 212 Phase 3.0 classification differences;
- Ownership parties from the owner strings.
