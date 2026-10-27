# Data-gap register (M3.1)

*Built by `tools/build-data-gap-register.py` from the committed state; do not edit by hand. The rows are `data/audit/data-gap-register.jsonl`; every number here is computed from them or from `tools/data_gap_analysis.py`. Audit only: nothing was fixed, fetched or OCR'd.*

**580 gaps** in the register: 458 live, 122 deliberately deferred.

## Resolution-first dashboard

| Tier | Gap count | Estimated effort | Confidence | Cascading benefit |
|---|---:|---|---|---|
| R1 | 102 | XS 87 · S 15 | HIGH 69 · MEDIUM 33 | HIGH 22 · MEDIUM 45 · LOW 35 |
| R2 | 189 | XS 152 · S 31 · M 6 | HIGH 8 · MEDIUM 181 | HIGH 14 · MEDIUM 29 · LOW 146 |
| R3 | 23 | S 17 · M 2 · L 4 | MEDIUM 18 · LOW 5 | MEDIUM 12 · LOW 11 |
| R4 | 95 | S 52 · M 42 · L 1 | MEDIUM 3 · LOW 92 | HIGH 21 · MEDIUM 46 · LOW 28 |
| R5 | 49 | XL 2 · UNKNOWN 47 | LOW 49 | HIGH 23 · MEDIUM 14 · LOW 11 · NONE 1 |
| DEFERRED | 122 | — | — | — |

**Effort as work.** A tier's rows that share a method are one script run, so the tier costs about the largest bucket per method, not the sum of the rows:

- **R1:** deterministic mapping S, provenance repair S, targeted local search S.
- **R2:** deterministic mapping M, existing evidence review M, model mapping XS.
- **R3:** deterministic mapping L, existing evidence review L, ocr S, targeted local search M.
- **R4:** targeted first party scrape L.
- **R5:** existing evidence review XL, manual decision UNKNOWN, new source required UNKNOWN, unknown UNKNOWN.

The tiers follow from each row's fields by fixed rules (`tier()`): R1 is XS/S, HIGH or MEDIUM confidence, evidence held, no dependency; R2 is S/M with limited review; R3 processes existing files (OCR, large deterministic runs); R4 needs new retrieval; R5 is UNKNOWN or XL effort, an unavailable source, or a decision not yet taken.

## Which gaps can be resolved without acquiring any new data?

**325 live gaps (154,630 affected items)** need no new data: everything they need is held. They are R1 102, R2 189, R3 23, R4 0, R5 11.

## Which gaps genuinely require new data?

**133 live gaps (1,692 affected items)**: a document no one holds, a site never or only partly crawled, or a source that does not exist yet. All of them are R4 or R5. Of these, 126 are document-less vintages (1,403 vintages), and 7 are other historical or figure sources.

## Mapping before scraping

Gaps where existing data probably holds the answer and the model does not yet connect it (state UNMAPPED): **171 gaps, 80,627 affected items.** They outrank every scrape.

| Kind | Gaps | Affected | Tiers |
|---|---:|---:|---|
| harvested observation → estate/wine/vintage | 4 | 77,126 | R2 1, R3 3 |
| figure → source (the record's own sheet) | 97 | 1,658 | R1 97 |
| document ↔ document (language versions, revisions) | 1 | 1,544 | R2 1 |
| harvested PDF → evidence store | 26 | 100 | R2 26 |
| harvested observation → missing figure | 23 | 88 | R2 23 |
| document → address (same bytes fetched online) | 1 | 71 | R1 1 |
| orphan provenance → record | 1 | 21 | R1 1 |
| image-only document → text | 17 | 17 | R3 17 |
| current statement → current model | 1 | 2 | R2 1 |

## Top 25 fastest resolvable gaps

By rank: tier, then confidence, cascading benefit, effort, provenance and mapping first.

| # | Problem | Affected | Current evidence | Resolution | Effort | Confidence | Cascade | Dependency |
|---:|---|---:|---|---|---|---|---|---|
| 1 | 26 "source unclear" figures: the field's own source name matches several documents; exactly one candidate prints the value | 26 | candidates held | DETERMINISTIC_MAPPING | XS | HIGH | HIGH | NONE |
| 2 | montrose: 21 figures with no field source whose exact value is printed in the record's own held sheet | 21 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | HIGH | NONE |
| 3 | lynch-bages: 28 figures with no field source whose exact value is printed in the record's own held sheet | 28 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | HIGH | NONE |
| 4 | prieure-lichine: 22 figures with no field source whose exact value is printed in the record's own held sheet | 22 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | HIGH | NONE |
| 5 | haut-brion: 158 figures with no field source whose exact value is printed in the record's own held sheet | 158 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 6 | 71 figures cite their own held sheet with no address; the discovery store fetched the same bytes from a URL | 71 | same sha256 fetched online | DETERMINISTIC_MAPPING | S | HIGH | HIGH | NONE |
| 7 | stem-chateau-grand-mayne: 89 figures with no field source whose exact value is printed in the record's own held sheet | 89 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 8 | beychevelle: 42 figures with no field source whose exact value is printed in the record's own held sheet | 42 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 9 | climens: 34 figures with no field source whose exact value is printed in the record's own held sheet | 34 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 10 | gruaud-larose: 168 figures with no field source whose exact value is printed in the record's own held sheet | 168 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 11 | la-mission-haut-brion: 100 figures with no field source whose exact value is printed in the record's own held sheet | 100 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 12 | dauzac: 81 figures with no field source whose exact value is printed in the record's own held sheet | 81 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 13 | bourgeois-chateau-paveil-de-luze: 81 figures with no field source whose exact value is printed in the record's own held sheet | 81 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 14 | pontet-canet: 48 figures with no field source whose exact value is printed in the record's own held sheet | 48 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 15 | stem-chateau-laroque: 39 figures with no field source whose exact value is printed in the record's own held sheet | 39 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 16 | chantegrive: 6 figures with no field source whose exact value is printed in the record's own held sheet | 6 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |
| 17 | la-lagune: 18 figures with no field source whose exact value is printed in the record's own held sheet | 18 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |
| 18 | lafon-rochet: 16 figures with no field source whose exact value is printed in the record's own held sheet | 16 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |
| 19 | carbonnieux: 7 figures with no field source whose exact value is printed in the record's own held sheet | 7 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |
| 20 | batailley: 9 figures with no field source whose exact value is printed in the record's own held sheet | 9 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |
| 21 | lascombes: 10 figures with no field source whose exact value is printed in the record's own held sheet | 10 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |
| 22 | stem-chateau-destieux: 10 figures with no field source whose exact value is printed in the record's own held sheet | 10 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |
| 23 | stem-chateau-franc-mayne: 12 figures with no field source whose exact value is printed in the record's own held sheet | 12 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |
| 24 | clos-haut-peyraguey: 5 figures with no field source whose exact value is printed in the record's own held sheet | 5 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |
| 25 | figeac: 5 figures with no field source whose exact value is printed in the record's own held sheet | 5 | record sheet held; value found in its text | PROVENANCE_REPAIR | XS | HIGH | MEDIUM | NONE |

## Top 10 cascading opportunities

Actionable gaps (R1-R4) with HIGH cascading benefit, by how many items one fix settles.

| # | Problem | Affected | Current evidence | Resolution | Effort | Confidence | Cascade | Dependency |
|---:|---|---:|---|---|---|---|---|---|
| 10 | gruaud-larose: 168 figures with no field source whose exact value is printed in the record's own held sheet | 168 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 5 | haut-brion: 158 figures with no field source whose exact value is printed in the record's own held sheet | 158 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 124 | 111 open IDENTITY_UNCERTAIN findings: a legacy name not resolved to one model id | 111 | recorded by the migration | EXISTING_EVIDENCE_REVIEW | M | MEDIUM | HIGH | MANUAL_REVIEW |
| 11 | la-mission-haut-brion: 100 figures with no field source whose exact value is printed in the record's own held sheet | 100 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 7 | stem-chateau-grand-mayne: 89 figures with no field source whose exact value is printed in the record's own held sheet | 89 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 76 | la-conseillante: 87 figures with no field source; the record's held PDF has no stored text to check against | 87 | record sheet held; text read by the sheet reader at run time, not stored | DETERMINISTIC_MAPPING | S | MEDIUM | HIGH | NONE |
| 12 | dauzac: 81 figures with no field source whose exact value is printed in the record's own held sheet | 81 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 13 | bourgeois-chateau-paveil-de-luze: 81 figures with no field source whose exact value is printed in the record's own held sheet | 81 | record sheet held; value found in its text | PROVENANCE_REPAIR | S | HIGH | HIGH | NONE |
| 6 | 71 figures cite their own held sheet with no address; the discovery store fetched the same bytes from a URL | 71 | same sha256 fetched online | DETERMINISTIC_MAPPING | S | HIGH | HIGH | NONE |
| 123 | haut-brion: 69 figures with no field source; the record's held sheet does not print the value as such (or the field is a date) | 69 | record sheet held with text; value not found verbatim | EXISTING_EVIDENCE_REVIEW | M | MEDIUM | HIGH | MANUAL_REVIEW |

The two largest cascades are blocked (R5): 10495 accepted evidence decisions establish whose sheet a document is, never that its cont (10,495 items, XL_EFFORT); 179 open AMBIGUOUS_SEMANTICS findings: the estate-level blend means plantings or usual ass (179 items, D1, MANUAL_DECISION, UNKNOWN_EFFORT).

## The 2,149 figures shown without a source

Recomputed now (Phase 6.1's measure, the same population of 4,691 figures): linked 2,142, own file without an address 304, "source unclear" 96, **no established source 2,149**.

| Group | Figures | Looks | What it means |
|---|---:|---|---|
| 1. local document exists and is identifiable | 1,247 | deterministic | the record names one held sheet, and that sheet prints the exact value |
| 2. several local documents are candidates | 90 | reviewable | the record's sheet name matches several held documents |
| 3. document held, figure-to-document unclear | 365 | reviewable | the held sheet has text but does not print the value as such (216 of them are dates) |
| 3b. document held, its text not stored | 411 | deterministic | the sheet reader reads the PDF at run time; no stored text to check here (not OCR) |
| 4. source named, document not held | 36 | research-dependent | the record names a sheet no placement resolves |
| 5. source genuinely unavailable | 0 | unavailable | none found |
| 6. completely unknown | 0 | — | every record names a sheet |

Phase 6.4 counted 1,961 one-document, 152 several or ambiguous, 36 unknown documents. Now: 2,023 one-document (groups 1, 3, 3b), 90 several, 36 not held. The value check is conservative: a number must stand as a token with its unit (alcohol with %/°, yield with hl, oak with %, months with mois/months, every blend share with %).

The 96 "source unclear" figures: no stored text 17, none prints it 21, one prints it 26, several print it 32. The 304 file-only figures: 71 have a discovered URL for the same bytes.

## The harvested observation corpus

**163,582 observations** on 20,098 artifacts (`data/discovery/observations`), by how their document maps today, using only recorded links (accepted evidence decisions, legacy attributions, the crawl's attribution):

| Mapping | Observations |
|---|---:|
| estate deterministic (one strong crawl candidate), unreviewed | 63,029 |
| unmappable (no estate evidence) | 38,724 |
| ambiguous (several crawl candidates) | 23,131 |
| estate + wine + vintage, all exact | 22,593 |
| estate exact only | 6,157 |
| estate + vintage exact, wine not | 4,533 |
| estate + wine exact, vintage not | 3,407 |
| one document of several estates (shared sheet) | 1,978 |
| conflicting (record and crawl name different estates) | 30 |

Exactly mappable: to an estate 36,690, to a wine 26,018, to a vintage 27,862, to all three 22,593. Wine-only and vintage-only do not occur: a wine or a vintage is only ever known through an estate's accepted document.

**Recoverable by mapping alone:** 88 vintage figures the model lacks are stated in an exactly mapped sheet (alc 19, blend 48, ph 1, yld 20). They are reviewable, not automatic: crawled label lines carry other years ("Rendement 2023" on a 2024 sheet is excluded) and neighbouring cells, so each is filled only after reading its passage.

## Targeted scraping backlog

Only gaps that need new data, traced to an identified gap; most valuable first.

| # | Problem | Affected | Current evidence | Resolution | Effort | Confidence | Cascade | Dependency |
|---:|---|---:|---|---|---|---|---|---|
| 329 | Château Latour (es_00309): 43 vintage(s) in the model with no document at all (site REACHED) | 43 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 318 | latour: 36 figures with no field source; the record names a sheet the store does not hold | 36 | named, not held | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 319 | Château de Myrat (es_00253): 23 vintage(s) in the model with no document at all (site REACHED) | 23 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 323 | Château Croizet-Bages (es_00243): 22 vintage(s) in the model with no document at all (site REACHED) | 22 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 334 | Château Rauzan-Gassies (es_00376): 22 vintage(s) in the model with no document at all (site REACHED) | 22 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 320 | Château Pavie (es_00341): 21 vintage(s) in the model with no document at all (site REACHED) | 21 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 325 | Château Cos Labory (es_00239): 20 vintage(s) in the model with no document at all (site UNREACHABLE) | 20 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 331 | Château Durfort-Vivens (es_00263): 19 vintage(s) in the model with no document at all (site REACHED) | 19 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 330 | Château Bouscaut (es_00212): 18 vintage(s) in the model with no document at all (site REACHED) | 18 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 332 | Château Bélair-Monange (es_00038): 18 vintage(s) in the model with no document at all (site REACHED) | 18 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 327 | Château du Tertre (es_00260): 17 vintage(s) in the model with no document at all (site REACHED) | 17 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 335 | Château Léoville-Las Cases (es_00317): 17 vintage(s) in the model with no document at all (site REACHED) | 17 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 315 | Château Brane-Cantenac (es_00215): 16 vintage(s) in the model with no document at all (site PARTIAL) | 16 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | MEDIUM | HIGH | SOURCE_DISCOVERY |
| 322 | Château Couhins (es_00240): 16 vintage(s) in the model with no document at all (site REACHED) | 16 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 328 | Château Lynch-Moussas (es_00323): 16 vintage(s) in the model with no document at all (site REACHED) | 16 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 333 | Château Saint-Pierre (es_00384): 16 vintage(s) in the model with no document at all (site UNREACHABLE) | 16 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 321 | Château Doisy-Daëne (es_00255): 15 vintage(s) in the model with no document at all (site REACHED) | 15 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 324 | Château Desmirail (es_00254): 15 vintage(s) in the model with no document at all (site REACHED) | 15 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 326 | Château Figeac (es_00266): 15 vintage(s) in the model with no document at all (site REACHED) | 15 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 336 | Château Valandraud (es_00466): 15 vintage(s) in the model with no document at all (site REACHED) | 15 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 337 | Château Kirwan (es_00285): 15 vintage(s) in the model with no document at all (site REACHED) | 15 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | HIGH | SOURCE_DISCOVERY |
| 364 | Château Belgrave (es_00039): 14 vintage(s) in the model with no document at all (site UNREACHABLE) | 14 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | MEDIUM | SOURCE_DISCOVERY |
| 373 | Château Sigalas-Rabaud (es_00386): 14 vintage(s) in the model with no document at all (site REACHED) | 14 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | MEDIUM | SOURCE_DISCOVERY |
| 376 | Château Doisy-Védrines (es_00257): 14 vintage(s) in the model with no document at all (site REACHED) | 14 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | MEDIUM | SOURCE_DISCOVERY |
| 381 | Château Corbin (es_00398): 14 vintage(s) in the model with no document at all (site REACHED) | 14 | no document held for these vintages | TARGETED_FIRST_PARTY_SCRAPE | M | LOW | MEDIUM | SOURCE_DISCOVERY |

95 scrape targets in all (1,170 items). Crawl coverage of the 388 universe estates: BLOCKED_BY_POLICY 24, NO_KNOWN_SITE 49, PARTIAL 18, REACHED 263, UNREACHABLE 34. Sites blocked by robots.txt stay blocked; their gaps need another source.

## OCR backlog

374 documents are image-only (NEEDS_OCR). **17** would address an identified gap; the other 357 are no record's sheet and the only document of no vintage, so OCR would close nothing today.

| # | Problem | Affected | Current evidence | Resolution | Effort | Confidence | Cascade | Dependency |
|---:|---|---:|---|---|---|---|---|---|
| 292 | image-only Beychevelle-2014_FR.pdf: the only document of vt:wn_00040:2014 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 293 | image-only safari2012.pdf: the only document of vt:wn_00025:2012 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 294 | image-only 2020Micalet.pdf: the only document of vt:wn_00025:2020 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 295 | image-only Fiche-tech-destieux-2013-Version-2021.pdf: the only document of vt:wn_00393:2013 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 296 | image-only sudouestgourmandjuin2016.pdf: the only document of vt:wn_00025:2016 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 297 | image-only Ch-Leoville-Poyferre-Millesime-2015.pdf: the only document of vt:wn_00318:2015 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 298 | image-only Fiche-millesime-2009.pdf: the only document of vt:wn_00420:2009 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 299 | image-only Beychevelle_2024_FR.pdf: the only document of vt:wn_00040:2024 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 300 | image-only Fiche-tech-destieux-2014-Version-2021.pdf: the only document of vt:wn_00393:2014 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 301 | image-only Beychevelle_2025_FR.pdf: the only document of vt:wn_00040:2025 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 302 | image-only Chateau-Destieux-2021.pdf: the only document of vt:wn_00393:2021 | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | MEDIUM | OCR |
| 303 | image-only batailley2008-web_fr.pdf: the record sheet of batailley/2008, 0 figure(s) unsourced there | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | LOW | OCR |
| 304 | image-only batailley2003-web_fr.pdf: the record sheet of batailley/2003, 0 figure(s) unsourced there | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | LOW | OCR |
| 305 | image-only batailley2006-web_fr.pdf: the record sheet of batailley/2006, 0 figure(s) unsourced there | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | LOW | OCR |
| 306 | image-only web-batailley2022_fr-1.pdf: the record sheet of batailley/2022, 0 figure(s) unsourced there | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | LOW | OCR |
| 307 | image-only BRANAIRE_DUCRU_2022_FR_EN.pdf: the record sheet of branaire-ducru/2022, 0 figure(s) unsourced there | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | LOW | OCR |
| 308 | image-only BRANAIRE_DUCRU_2020_FR_EN.pdf: the record sheet of branaire-ducru/2020, 0 figure(s) unsourced there | 1 | bytes held, NEEDS_OCR | OCR | S | MEDIUM | LOW | OCR |

No OCR engine is installed (Phase 3.4, P16: "OCR NEEDED_NO_ENGINE"); installing one is part of R3.

## Blocked decisions

These cannot be resolved by work: each waits on a decision.

| # | Problem | Affected | Current evidence | Resolution | Effort | Confidence | Cascade | Dependency |
|---:|---|---:|---|---|---|---|---|---|
| 411 | 179 open AMBIGUOUS_SEMANTICS findings: the estate-level blend means plantings or usual assemblage (D1) | 179 | recorded by the migration | MANUAL_DECISION | UNKNOWN | LOW | HIGH | D1 |
| 433 | Echo de Lynch-Bages: rename or succession from Haut-Bages Averous (D2); 5 M3 candidates wait on it | 5 | three sources word a change of name from the 2008 vintage; none reviewed | MANUAL_DECISION | UNKNOWN | LOW | MEDIUM | D2 |
| 448 | identity map second-by-name "haut-bailly/La Parde de Haut-Bailly" is AMBIGUOUS between 1 candidate(s) | 1 | candidates recorded | MANUAL_DECISION | UNKNOWN | LOW | LOW | LAPARDE_IDENTITY |
| 449 | La Parde de Haut-Bailly -> Haut-Bailly II: the identity decision (6.2) gates 2 M3 candidates | 2 | accepted 2018 sheet states the rename | MANUAL_DECISION | UNKNOWN | LOW | LOW | LAPARDE_IDENTITY |
| 450 | identity map wine-by-display-name "haut-bailly/La Parde de Haut-Bailly" is AMBIGUOUS between 1 candidate(s) | 1 | candidates recorded | MANUAL_DECISION | UNKNOWN | LOW | LOW | LAPARDE_IDENTITY |
| 451 | Les Terrasses de Saint Christophe is stated as Tour Saint Christophe's second label but is no model wine (2.11) | 1 | accepted sheet states it (undated) | MANUAL_DECISION | UNKNOWN | LOW | LOW | MANUAL_REVIEW |
| 452 | data/chateaux.js says the estate has no second wine ('—'); cuvees.js lists Lions de Batailley as its second | 1 | two legacy statements disagree | MANUAL_DECISION | UNKNOWN | LOW | LOW | D5 |
| 453 | data/chateaux.js says the estate has no second wine ('—'); cuvees.js lists Les Hauts de Lynch-Moussas as its second | 1 | two legacy statements disagree | MANUAL_DECISION | UNKNOWN | LOW | LOW | D5 |

- **D2 (Echo).** Rename or succession; five M3 candidates wait. Three sources word it as a change of name from the 2008 vintage.
- **La Parde → Haut-Bailly II.** The identity decision Phase 6.2 asked for; the evidence (the accepted 2018 sheet) is held.
- **D5.** The conflict policy; the contemporaneous second-wine conflicts (Batailley, Lynch-Moussas) wait on it.
- **D1.** What the estate-level blend means (179 AMBIGUOUS_SEMANTICS findings).

## Deliberately deferred

Not worth resolving yet, unavailable, or not a gap at all.

| Kind | Rows | Items | Why |
|---|---:|---:|---|
| ACCEPTED_UNAVAILABLE | 1 | 0 | checked and clean: every accepted document is held (sha256 proven) |
| CORPUS | 2 | 24,571 | observations already exactly mapped (estate, wine, vintage) or on a document several estates share: nothing to connect |
| FINDING | 1 | 123 | manifest rows naming a file never held; the figures that depend on an unheld sheet are counted in group 4 of the 2,149 |
| HIST | 2 | 39 | current statements and an absence inference: none is history, and M3 refused to treat them as such |
| OCR | 1 | 357 | image-only documents no gap names: OCR them only when one does |
| SITE | 104 | 104 | blocked (robots.txt, respected), unreachable, partly crawled or site-less estates on which no identified gap depends |
| UNSOURCED_OBSERVATION | 9 | 2,480 | the dashboard's own editorial prose; it claims no source |
| WINES_WITHOUT_ESTATE | 1 | 0 | checked and clean: every model wine has an estate |
| WRONG_VINTAGE_REFUSED | 1 | 1,321 | the guard kept these sheets off the wrong vintage; no wrong-vintage attachment exists |

## Resolved since M3.1

Gaps a recovery stream reduced. Each keeps its id, tier and original count; the resolution records what changed and by which commit (`data/audit/m32-resolutions.json`).

| Phase | Commit | Method | Gaps | Items recovered |
|---|---|---|---:|---:|
| M3.10B | `6d91d87` | EXISTING_EVIDENCE_REVIEW | 1 | 2 |
| M3.2A | `ba5aaa4` | PROVENANCE_REPAIR | 58 | 712 |
| M3.2B | `b4ec482` | DETERMINISTIC_MAPPING | 1 | 71 |
| M3.2C | `a556a01` | DETERMINISTIC_MAPPING | 27 | 284 |
| M3.2D | `552c5b3` | EXISTING_EVIDENCE_REVIEW | 12 | 25 |
| M3.4B | `fa2c436` | DETERMINISTIC_MAPPING | 14 | 26 |
| M3.5 | `dbca625` | EXISTING_EVIDENCE_REVIEW | 2 | 9 |
| M3.6B | `bc82827` | EXISTING_EVIDENCE_REVIEW | 3 | 3 |

43 gaps resolved outright, 72 partly; 1,132 of their 1,909 affected items recovered, 777 remain.


## Method and limits

- **State.** MISSING: the information is not held. UNMAPPED: it is held and not connected. CONFLICTING: held statements disagree. UNRESOLVED: evidence exists and does not settle it. Every row has exactly one primary category and one state.
- **Evidence is never promoted.** A probable mapping stays a candidate; a crawl attribution is never treated as an accepted decision; accepting a document's identity is not approving its content (M3).
- **Effort** is for Claude Code to carry out the resolution, by method and size; **confidence** is separate; **cascade** is how many other gaps one fix settles.
- **Limits.** "Value printed" is a conservative token check on stored text; the 411 figures whose sheet has no stored text are not judged. The vintage-document counts use the model's derived index (none 1,403, one 2,339, several 1,544). Nothing was retrieved, so "requires new data" means "not held", not "does not exist".

