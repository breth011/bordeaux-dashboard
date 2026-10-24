# Phase 3.2 — Data Model (conceptual)

The entities of the target architecture, field by field. This is a
**conceptual** model: types are conceptual (`id`, `text`, `enum`, `ref`,
`Validity`), and nothing here chooses a storage engine, a file format or an
id syntax (decisions D3 and D4).

- `docs/phase32-model.json` is the same model, machine-readable, and is the
  one the tests read.
- `docs/phase32-fixtures.json` expresses eight real cases from this
  repository in it.
- `docs/PHASE-3.2-NORMALIZATION-ARCHITECTURE.md` explains why each entity
  is here.

## Conventions

- **Identity.** Every `id` is minted once and opaque. It is never derived
  from a name and never parsed for meaning. Composite identities are named
  where they apply (Vintage, Locator, IdentityMap, CanonicalValue).
- **Validity.** `{valid_from, valid_to, as_of}`, where each bound is a
  **TemporalBound**: `{kind, axis, value, precision, basis}`.
  - `kind`:
    - EXACT, APPROXIMATE, NO_LATER_THAN, NO_EARLIER_THAN (inclusive), which
      take a value;
    - UNKNOWN, OPEN, NOT_APPLICABLE, which take none.
  - `axis`: CALENDAR (an ISO partial date) or VINTAGE (a harvest year).
  - `precision`: DAY, MONTH, YEAR, DECADE, VINTAGE, or NONE.
  - `basis`: required whenever a value is given.

  OPEN appears only as `valid_to`. The derived status of a validity is
  CURRENT, HISTORICAL or TIMELESS.
- **Provenance.** Every record of the STATE, OBSERVATION, RECONCILIATION
  and CANONICAL layers, and every QualityFinding, carries a `provenance`.

---

## Identity layer

### Estate
A property. It is separate from its wines, its names and its owners.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | minted |
| name_status | NameStatus | yes | KNOWN, or UNKNOWN when no source names it |

Names live in NameRecord; the legacy keys in IdentityMap.

### Wine
A wine or cuvée, identified apart from its vintages. **The grand vin is a
Wine.**

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | minted |
| name_status | NameStatus | yes | UNKNOWN for a classified wine no source names (the Bouscaut white) |
| range | WineRange | yes | RED, DRY_WHITE, SWEET_WINE, ROSE, SPARKLING, UNKNOWN |
| non_vintage | bool | no | NV wines (a crémant) |

### Vintage
A wine in a given year. Its identity is the composite (`wine`, `label`).

| Field | Type | Req | Meaning |
|---|---|---|---|
| wine | ref Wine | yes | |
| label | text | yes | the harvest year, or `NV` |

### Source
A site, publisher or body that serves documents. **Never an estate**,
however closely it serves one.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| kind | SourceKind | yes | ESTATE_SITE, GROUP_SITE, NEGOCIANT, CLASSIFICATION_BODY, REGULATOR, CRITIC, AGGREGATOR, ENCYCLOPEDIA, ARCHIVE, UNKNOWN |
| name | text | yes | |
| operator | ref Party | no | who runs it (Vignobles K runs vignoblesk.com) |
| base_urls | list text | no | |

### Party
An owner, group, family, company or institution.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| kind | PartyKind | yes | PERSON, FAMILY, COMPANY, GROUP, INSTITUTION, UNKNOWN |
| name | text | yes | |

### IdentityMap
Maps a legacy key to a stable id. It is never rewritten, so every key
ever used stays resolvable. Its identity is (`namespace`, `legacy_key`).

| Field | Type | Req | Meaning |
|---|---|---|---|
| namespace | text | yes | `estate`, `wine-by-slug`, `wine-by-display-name`, `phase30-universe`, `manifest-row`, … |
| legacy_key | text | yes | `bourgeois-chateau-castera`; `lynch-bages\|echo-de-lynch-bages`; `bourgeois-chateau-castera\|Château Castera` |
| stable_id | ref | no | the one target, when there is one |
| candidates | list ref | no | the possible targets, when AMBIGUOUS |
| status | IdentityMapStatus | yes | ACTIVE, RETIRED, AMBIGUOUS |
| provenance | ref Provenance | yes | |

### NameRecord
One name of an estate or wine, in time.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| subject | ref Estate or Wine | yes | |
| name | text | yes | verbatim |
| kind | NameKind | yes | CURRENT, FORMER, ALIAS, SPELLING_VARIANT, SOURCE_RENDERING |
| validity | Validity | yes | |
| provenance | ref Provenance | yes | |

### IdentityTransition
A merger, split, rename, succession, possible sameness or stated
distinctness. **Name equality is never one of these.**

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| kind | TransitionKind | yes | MERGED_INTO, SPLIT_FROM, RENAMED, SUCCEEDED_BY, POSSIBLY_SAME, DISTINCT_FROM |
| from | ref Estate or Wine | yes | |
| to | ref Estate or Wine | yes | |
| at | TemporalBound | yes | |
| certainty | Certainty | yes | CONFIRMED, PROBABLE, UNRESOLVED |
| source_term | text | no | the source's words |
| provenance | ref Provenance | yes | |

---

## State layer (time-dependent)

### EstateWineRelationship
*Estate X has wine Y.* The link is held apart from its role.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| estate | ref Estate | yes | |
| wine | ref Wine | yes | |
| status | RelationshipStatus | yes | ESTABLISHED, PROBABLE, CLAIMED, DISPUTED, ENDED_UNKNOWN_WHEN |
| validity | Validity | yes | usually on the VINTAGE axis |
| provenance | ref Provenance | yes | |

### RoleAssignment
The wine's role for this estate, in time. This is where UNKNOWN lives.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| relationship | ref EstateWineRelationship | yes | |
| role | WineRole | yes | GRAND_VIN, SECOND_WINE, OTHER_CUVEE, **UNKNOWN** |
| range | WineRange | yes | the range the role is within |
| source_term | text | no | the source's wording ("second vin", "grand vin blanc sec") |
| legacy_term | text | no | the pre-migration value carried (`second`, `other`) |
| validity | Validity | yes | |
| provenance | ref Provenance | yes | |

### RoleAbsence
*This estate has no wine of this role in this range*, stated by a source.
This is NO_SUCH_WINE. When no assignment and no absence exists, the state
is UNKNOWN.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| estate | ref Estate | yes | |
| role | WineRole | yes | |
| range | WineRange | yes | |
| validity | Validity | yes | |
| provenance | ref Provenance | yes | |

### ClassificationScheme
A classification system, which is never merged with another.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| name | text | yes | |
| body | ref Party | yes | |

### ClassificationEdition
One edition of a scheme (Saint-Émilion 2012, 2022) with its validity.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| scheme | ref ClassificationScheme | yes | |
| label | text | yes | |
| validity | Validity | yes | CALENDAR (1855, 2022-09-08) or VINTAGE (Crus Artisans 2022–2026) |
| ranks | list text | no | as the body names them |
| provenance | ref Provenance | yes | |

### ClassificationMembership
**A classified wine,** with its rank, in time.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| edition | ref ClassificationEdition | yes | |
| wine | ref Wine | yes | the classified wine: per colour for Graves, per appellation for Crus Artisans |
| rank | text | no | the body's term, verbatim |
| rank_status | NameStatus | yes | UNKNOWN when membership is known and its rank is not (Mouton before 1973) |
| appellation_listed | text | no | as the source lists it |
| validity | Validity | yes | |
| provenance | ref Provenance | yes | |

### Appellation
An appellation, with its own validity (Pessac-Léognan from 1987).

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| name | text | yes | |
| validity | Validity | yes | |
| provenance | ref Provenance | yes | |

### AppellationMembership
A wine's appellation, in time. It belongs to the wine because Moutte Blanc
is classified as two wines in two appellations.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| wine | ref Wine | yes | |
| appellation | ref Appellation | yes | |
| validity | Validity | yes | |
| provenance | ref Provenance | yes | |

### Ownership
An owner, operator or group of an estate, in time.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| estate | ref Estate | yes | |
| party | ref Party | yes | |
| role | OwnershipRole | yes | OWNER, OPERATOR, GROUP_MEMBER |
| source_term | text | no | the legacy or source wording ("Bravo family (since 2016)") |
| validity | Validity | yes | |
| provenance | ref Provenance | yes | |

### EstateLocation
An estate's commune and position, in time.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| estate | ref Estate | yes | |
| commune | text | no | |
| lat | number | no | |
| lng | number | no | |
| method | text | no | `osm`, surveyed, appellation fallback … |
| validity | Validity | yes | |
| provenance | ref Provenance | yes | |

### VintageStatement
A statement about a vintage as a whole, such as a vintage that was not
produced (`BDX_NOT_PRODUCED`).

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| vintage | ref Vintage | yes | |
| kind | VintageStatementKind | yes | NOT_PRODUCED, PRODUCED |
| provenance | ref Provenance | yes | |

### EditorialCollectionMembership
The dashboard's own groupings. **Never a classification.**

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| estate | ref Estate | yes | |
| collection | text | yes | `pomerol`, `libournais`, `cotes`, `graves-doux`, `medoc-hors` |
| tier | text | no | the editorial tier |
| provenance | ref Provenance | yes | |

---

## Document layer

### Artifact
A document, identified by its bytes.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | minted; two artifacts sharing a digest are one |
| sha256 | text | no | as hashed by the evidence path |
| sha1 | text | no | as recorded by the manifest |
| bytes | number | no | |
| media_type | text | no | |
| bytes_available | bool | yes | false for versions overwritten on disk before Phase 4 |

At least one digest is required.

### Locator
A path or URL. Its identity is (`kind`, `value`).

| Field | Type | Req | Meaning |
|---|---|---|---|
| kind | LocatorKind | yes | LOCAL_PATH, URL |
| value | text | yes | |

### Placement
*These bytes were at this locator at this time.* There is one per
(locator, artifact), so a path holds its versions and an artifact holds its
copies.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| locator | ref Locator | yes | |
| artifact | ref Artifact | no | null when the path is known and the bytes are not |
| status | PlacementStatus | yes | PRESENT, SUPERSEDED, MISSING, NAME_MISMATCH, BYTES_UNAVAILABLE |
| source | ref Source | no | |
| retrieval_method | text | no | the retrieval half of the manifest's `how` |
| observed | Validity | yes | |
| legacy_manifest_row | number | no | the `sources.json` row it came from |
| provenance | ref Provenance | yes | |

### ArtifactAssessment
What kind of document it is, judged apart from what it concerns.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| artifact | ref Artifact | yes | |
| document_type | DocumentType | yes | TECHNICAL_SHEET, WEB_PAGE, BROCHURE_OR_DOSSIER, PRESS_REVIEW, GROUP_REPORT, MULTI_WINE_SHEET, LETTER_OR_FORM, OTHER, UNKNOWN |
| language | text | no | |
| status | AttributionStatus | yes | |
| provenance | ref Provenance | yes | |

### Attribution
A judgement that an artifact concerns an estate, wine, vintage or role.
There may be several per artifact, and none of them is identity.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| artifact | ref Artifact | yes | |
| estate | ref Estate | no | |
| wine | ref Wine | no | **null means not established, never "the grand vin"** |
| vintage | ref Vintage | no | |
| role | WineRole | no | |
| method | AttributionMethod | yes | DOCUMENT_TEXT, FILENAME, FOLDER, SITE_LIBRARY, PAGE_NAME, READER_GUARD, MANUAL, LEGACY_UNKNOWN |
| status | AttributionStatus | yes | PROPOSED, ACCEPTED, REJECTED, LEGACY, UNATTRIBUTED, SUPERSEDED |
| supersedes | ref Attribution | no | |
| provenance | ref Provenance | yes | |

### LegacyDocumentReference
A bare filename cited by a legacy file, kept resolvable **to candidates,
never to a first match**. Its identity is (`origin`, `record_key`,
`field`, `basename`).

| Field | Type | Req | Meaning |
|---|---|---|---|
| origin | text | yes | `data/field-src.js`, `data/cuvee-src.js`, a record's `src` … |
| record_key | text | yes | the legacy key (`bourgeois-chateau-de-braude\|1981`) |
| field | text | no | |
| basename | text | yes | |
| candidates | list ref Placement | yes | every placement of that name |
| resolution | IdentityMapStatus | yes | ACTIVE when the candidates share one artifact; AMBIGUOUS otherwise |

---

## Observation layer

### EvidenceLink
Points from an immutable evidence row to the new identities. The evidence
store itself is not touched. Identity: the evidence `row_key`.

| Field | Type | Req | Meaning |
|---|---|---|---|
| row_key | text | yes | `evidence.row_key()` of the decision |
| evidence_version | number | yes | 1–5 |
| artifact | ref Artifact | no | through `read.sha256` (v4 and later only) |
| estate | ref Estate | no | through IdentityMap (`ctx.estate`, `target_estate`) |
| wine | ref Wine | no | through the (estate, display name) map (`target_wine`) |

### Observation
What one locus of one artifact says about one field of one subject.
Observations are append-only, and versioned by extractor.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | unique on (artifact, locus, subject, field, extractor) |
| subject | ref Estate, Wine, Vintage or EstateWineRelationship | yes | |
| field | text | yes | |
| raw_value | any | no | as printed |
| value | any | no | normalised |
| unit | text | no | |
| qualifier | text | no | `under` (the legacy `sugl`), H₂SO₄ / tartaric (the legacy `tau`) |
| artifact | ref Artifact | no | null for MANUAL and LEGACY observations |
| locus | text | no | page or label within the document |
| source | ref Source | no | |
| extraction | object | yes | {method, reader, code_commit, dirty} |
| confidence | text | yes | STATED, READ, READ_UNVERSIONED, INFERRED, LEGACY |
| observed_at | date | yes | |
| provenance | ref Provenance | yes | |

---

## Reconciliation layer

### Reconciliation
A persistent, rule-named choice. **All candidates stay listed.**

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| subject | ref | yes | |
| field | text | yes | |
| candidates | list ref Observation | yes | every observation for (subject, field) |
| selected | ref Observation | no | null while DEFERRED or CONFLICT_OPEN without a retained value |
| rule | ReconciliationRule | yes | ONLY_CANDIDATE, UNANIMOUS, SOURCE_PRIORITY, MOST_RECENT_DOCUMENT, AUTHORITATIVE_OVER_CORPUS, MANUAL_DECISION, LEGACY_FIRST_IN_SORT_ORDER, LEGACY_NEVER_OVERWRITE |
| status | ReconciliationStatus | yes | SINGLE, AGREED, RESOLVED, CONFLICT_OPEN, DEFERRED, LEGACY_RETAINED, SUPERSEDED |
| reason | text | yes | |
| resolver | text | yes | rule id or person |
| decided_at | date | yes | |
| supersedes | ref Reconciliation | no | |
| provenance | ref Provenance | yes | |

---

## Canonical layer

### CanonicalValue
The accepted value of (subject, field). It is a projection of the latest
effective reconciliation, and never the only record of what sources said.

| Field | Type | Req | Meaning |
|---|---|---|---|
| subject | ref | yes | |
| field | text | yes | |
| value | any | yes | |
| status | CanonicalStatus | yes | SOURCED, LEGACY_FIELD_SOURCE, LEGACY_RECORD_SOURCE_ONLY, LEGACY_AMBIGUOUS_SOURCE, LEGACY_UNSOURCED, MANUAL_UNSOURCED, CITED_UNVERIFIED, DERIVED |
| reconciliation | ref Reconciliation | yes | |
| derivation | text | no | TRANSLATED (the legacy `ttl`/`ntl`/`dtl`/`ftl`/`wtl`), PARSED (the legacy `wy` from `window`), AGGREGATED (ratings) |
| provenance | ref Provenance | yes | |

---

## Cross-cutting

### Provenance
One shape for every layer.

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| kind | ProvenanceKind | yes | DOCUMENT, EVIDENCE_DECISION, AUTHORITATIVE_SOURCE, ESTATE_PUBLICATION, CITATION_UNVERIFIED, DERIVATION, MANUAL, LEGACY_FIELD_SOURCE, LEGACY_RECORD_SOURCE, LEGACY_AMBIGUOUS_SOURCE, LEGACY_UNSOURCED, LEGACY_MANIFEST |
| artifact | ref Artifact | no | |
| locator | ref Locator | no | |
| source | ref Source | no | |
| quote | text | no | the words relied on |
| actor | text | yes | tool and version, or person |
| code_state | object | no | {commit, dirty, status_hash}, as on the evidence path |
| at | date | no | |
| derived_from | list ref | no | |
| secondary | bool | no | a secondary source (Wikipédia) |
| legacy_reference | ref LegacyDocumentReference | no | |

### QualityFinding
A persistent finding. **It never changes the thing it is about.**

| Field | Type | Req | Meaning |
|---|---|---|---|
| id | id | yes | |
| target | ref | yes | anything |
| kind | QualityKind | yes | MISSING, CONFLICT, SUSPICIOUS_CHANGE, IDENTITY_UNCERTAIN, EXTRACTION_FAILURE, SOURCE_FAILURE, ORPHAN_PROVENANCE, CROSS_SUBJECT_CITATION, JUNK_VALUE, AMBIGUOUS_SEMANTICS, SCOPE_DISCREPANCY |
| status | QualityStatus | yes | OPEN, ACKNOWLEDGED, RESOLVED, WONT_FIX |
| detail | text | yes | |
| detected_by | text | yes | |
| provenance | ref Provenance | yes | |
