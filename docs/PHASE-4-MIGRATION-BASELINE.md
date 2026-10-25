# Phase 4 migration baseline (M0)

Written by `tools/phase4-baseline.py`; the machine-readable copy is `data/model/baseline.json`, which `tools/test-phase4.py` and `python tools/phase4-baseline.py --check` hold every later stage to.

## Starting point

- Starting commit: `91a5b8b` (Phase 3.4), equal to `origin/main` when M0 ran.
- Working tree clean when M0 ran.
- All 20 existing test suites passed before M0 (test-data, test-phase2 to test-phase34, test-reader; 2 minutes in all).

## Protected groups

Each group is hashed file by file (sha256); the group digest is the sha256 of the sorted file-to-hash map. Phase 4 may not change any of them before the canonical switch gate.

| Group | Files | Digest |
|---|---:|---|
| canonical | 39 | `f565386959c11a80` |
| phase_records | 14 | `7296115a0e392720` |
| evidence | 8 | `ca73da58b284d3bb` |
| discovery | 571 | `e6c8a40bc0b2d132` |
| scope | 3 | `c2a1463108c9776f` |
| review | 1 | `5f4724a04a7e389c` |
| phase34_model | 4 | `effff82f6cedc4d0` |

## Counts

| Measure | Value |
|---|---:|
| canonical_estates | 470 |
| full_record_estates | 172 |
| name_derived_estate_ids | 298 |
| estate_file_records | 172 |
| second_named | 103 |
| second_dash | 34 |
| cuvee_wine_estates | 80 |
| cuvee_wines | 135 |
| cuvee_wines_by_role: other | 58 |
| cuvee_wines_by_role: second | 77 |
| BDX_FICHES | 2,725 |
| BDX_FIELD_SRC | 2,277 |
| BDX_FICHE_URL | 1,378 |
| BDX_RATINGS | 2,479 |
| BDX_CELLAR | 644 |
| BDX_SCORES | 35 |
| BDX_NOT_PRODUCED | 3 |
| BDX_CUVEES | 1,174 |
| BDX_CUVEE_SRC | 977 |
| BDX_CUVEE_URL | 326 |
| BDX_PLANTINGS | 93 |
| BDX_TERROIR | 81 |
| BDX_COORDS | 100 |
| BDX_SITES | 409 |
| BDX_FICHES_NL | 816 |
| BDX_CLASSIFICATIONS | 11 |
| fiche_values | 11,838 |
| cuvee_values | 4,623 |
| manifest_rows | 13,032 |
| manifest_paths | 12,771 |
| manifest_multiversion_paths | 204 |
| evidence_lines: data/evidence/decisions-v1.jsonl | 13,065 |
| evidence_lines: data/evidence/decisions-v2.jsonl | 41,259 |
| evidence_lines: data/evidence/decisions-v3.jsonl | 41,259 |
| evidence_lines: data/evidence/decisions-v4.jsonl | 40,772 |
| evidence_lines: data/evidence/decisions-v5.jsonl | 40,772 |
| evidence_lines: data/evidence/provenance-failures-v4.jsonl | 123 |
| evidence_lines: data/evidence/provenance-failures-v5.jsonl | 123 |
| discovery_artifacts | 29,517 |
| discovery_observations | 163,582 |
| proposals | 1,107 |
| attribution_candidates | 908 |

## Canonical files

| File | sha256 |
|---|---|
| `data/appellations.js` | `dd7863eaf4407c0a` |
| `data/batch2.js` | `f99e21285568f9cc` |
| `data/batch3.js` | `be291ea9d69371a7` |
| `data/batch4.js` | `9710ec9823f001d9` |
| `data/cellar.js` | `d2bef10cf0f407db` |
| `data/chateaux.js` | `c6fbb8c48b257d9f` |
| `data/classifications.js` | `aba9d5215d236685` |
| `data/climate.js` | `7a82ea88f5a343ac` |
| `data/coords.js` | `1817921ced5b4b53` |
| `data/cruartisan.js` | `bbbcded43edc6b60` |
| `data/crubourgeois.js` | `e05045f41c2085a8` |
| `data/cuvee-src.js` | `415019d1cc0598e1` |
| `data/cuvee-url.js` | `1ee22d6270a052ae` |
| `data/cuvees.js` | `daf827784a475e9e` |
| `data/fiches-nl.js` | `7f597deeee10a88f` |
| `data/fiches-url.js` | `b8bb868bb17e1cb8` |
| `data/fiches.js` | `c947bccce8afb84c` |
| `data/field-src.js` | `e872a07f0d3be40b` |
| `data/geography.js` | `36643c48b697380c` |
| `data/grapes-nl.js` | `5d40feff70245d77` |
| `data/grapes.js` | `e7d8856da9f5c5b7` |
| `data/graves.js` | `c2479119e9079f25` |
| `data/libournais.js` | `6be7f31cc28378fc` |
| `data/notes-nl.js` | `a138031e185c8cb0` |
| `data/notes.js` | `c18822eb656f1e0a` |
| `data/overrides.js` | `5dab636f3bab5081` |
| `data/phenology.js` | `f1243938d7023860` |
| `data/plantings.js` | `80d809dcfbdd5584` |
| `data/pomerol.js` | `800a7449a738a753` |
| `data/ratings.js` | `2ba26ee4e70eb8b3` |
| `data/rightbank.js` | `13be8c9d583d1714` |
| `data/saintemilion.js` | `4f93b337b7b42158` |
| `data/sauternes.js` | `ee145db61a29bb55` |
| `data/terroir.js` | `02e6dfaa824ff66d` |
| `data/vintages-nl.js` | `5a442e7b22c0e2c6` |
| `data/vintages.js` | `24ee0e1d73eb5f27` |
| `data/water.js` | `31a8a90dd44962ac` |
| `data/websites.js` | `080de4bc6ec251e8` |
| `data/sources.json` | `6b297e44982b778c` |

## Semantics frozen as tests

`tools/test-phase4.py` checks these against the baseline:

- the key shapes: `estate|vintage` (fiches, field-src, fiches-url, ratings, cellar, BDX_SCORES) and `estate|slug|vintage` (cuvees, cuvee-src, cuvee-url);
- the sparse id rule: `cls + '-' + slug(name)` for the Cru Bourgeois, Cru Artisan, Saint-Émilion grand cru classé and Pomerol lists (298 ids);
- the role vocabulary of BDX_CUVEE_WINES (`second`, `other`) and the meaning of `second: '—'` (no second wine; 34 estates);
- the counts above, and the group hashes.
