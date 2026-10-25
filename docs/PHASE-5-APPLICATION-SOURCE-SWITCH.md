# Phase 5 — Application source switch

Gate: **SAFE — APPLICATION RUNS FROM NORMALIZED MODEL**

The application now loads its estate, wine and vintage data from files generated from the normalized
model:

normalized model → generated application data → application

No domain question was decided to make this work. The model, the canonical data, the evidence, the
discovery corpus, the identity decisions and the unresolved mappings are unchanged.

| Commit | What |
|---|---|
| `037a241` | A: the two known raw-file anomalies pinned by test |
| `7db543e` | B: the switch, its tools, its control fixture and its tests |
| this commit | C: the regression measurements, this report, the backlog, LF for `data/app/` |

## 1. Preconditions

Each was checked at `5946fb8`, the decision checkpoint, before anything changed:

- the working tree was clean;
- all 22 suites passed, including test-phase4 (66) and test-phase5 (18 with the hard-link checks);
- the model rebuilt byte for byte;
- the dual read passed;
- the protected hashes were unchanged.

The anomaly guard was added first, as commit A, and passed before the switch began.

## 2. The two raw-file anomalies

`tools/test-phase5.py known_raw_file_anomalies_preserved` pins both files. Their bytes match no version
the source list records, and the test checks that they still don't.

| File | Size | sha256 | Note |
|---|---:|---|---|
| `domaine-de-chevalier/2020-rouge-domaine-de-chevalier-francais.pdf` | 394,634 | `0c1a5429…89139896` | equal to its v4/v5 read |
| `valandraud/VIRGINIE-DE-VALANDRAUD.pdf` | 135,273 | `57f351bc…3a65bdc4` | never read |

This preserves the files; it does not validate them. If either hash changes, the test fails. The
expected values may change only in a separately documented data-integrity decision.

## 3. The application boundary

| Layer | Files | Used by |
|---|---|---|
| Legacy inputs (before) | the 23 contract files in `data/` (estate files, compact lists, `cuvees.js`, `fiches.js`, `fiches-nl.js`, `fiches-url.js`, `cuvee-url.js`, `ratings.js`, `cellar.js`, `overrides.js`, `plantings.js`, `terroir.js`, `coords.js`, `websites.js`) | the page, until this switch. Still in `data/`, untouched: they are the protected canonical data and the rollback source. |
| Model-generated inputs (now) | `data/app/*.js`: the same 23 files and the same globals, written by `tools/build-app-data.py` from the model's projection (`tools/model_reader.py`) | the page |
| Page assets outside the contract | `data/` `classifications.js`, `appellations.js`, `geography.js`, `water.js`, `climate.js`, `notes*.js`, `grapes*.js`, `vintages*.js`, `rightbank.js`, `phenology.js` | the page, as before (M12) |
| Build tooling only | `data/model/`, `tools/model_reader.py`, `tools/build-app-data.py`, `tools/migrate.py` and its stages | never the page |
| Outside the boundary | `sources/` (raw documents), `data/evidence/`, `data/discovery/`, `data/sources.json`, `data/scope/`, proposals and audits, `data/model/checks/`, reconciliation and quality internals | never the page |

`tools/app-source.py` performs the switch. It rewrites only the 23 script tags in `index.html` and the
same 23 entries of the service worker's precache list, and it bumps the cache name so installed copies
fetch the new files.

The generated files contain nothing but `window.BDX_* = …` assignments. The page's scripts are
`assets/*.js` and data files, and none of them refers to a tool, the model, the evidence, the discovery
data or the raw store. No migration runs at page load.

## 4. The control

`tools/app-reference.py --capture` recorded what the running application showed under the legacy
source. The fixture, `tools/fixtures/app-reference.json`, holds hashes, counts and orders, not a copy of
the data. It covers:

- every `BDX_*` global the page holds after `init()`, value by value, with the order of every list;
- the expanded estate list (470 estates; 471 cards, with Haut-Brion listed twice);
- 13 searches: the 8 benchmark queries plus *margaux*, *saint-emilion*, *blanc*, *second* and *echo*.
  Each records its list cards, its autocomplete rows and its result label;
- the app's own lookups for the benchmark workloads;
- the rendered detail drawer of 13 estates, for each of their wines (wine navigation), with vintage
  rows opened (vintage navigation). The estates are Lafite, Margaux, Haut-Brion, Yquem, Lynch-Bages,
  Saint-Pierre, Caillou, Smith Haut Lafitte, Badette, Beaumont, Lauga, Commanderie and L'Enclos;
- the page's health: JavaScript exceptions, console errors, and failed or non-2xx requests.

A second capture under the same source compared as 10,770 identical items, so the capture is
deterministic.

## 5. Equivalence after the switch

`python tools/app-reference.py --compare`, run in the switched application:

| Class | Count |
|---|---:|
| IDENTICAL | 10,748 |
| EXPECTED: PRESENTATION ORDER | 22 |
| UNEXPLAINED | **0** |

- **Identical:** every value of every global, every search's set of cards and its label, every lookup,
  and every drawer (each wine, each opened vintage). Missingness behaves the same, because the records
  that hold no value and the records kept verbatim are reproduced as they were.
- **Presentation order:** the model holds no display order, so the generated files list records by id.
  The producers list reorders within 24 of its 28 growth groups (the 1855 first growths now show
  Haut-Brion first), and so do the list and key order of several globals and the card order of four
  searches. Phase 4 M8 classified order as an expected structural difference. The reordering was
  accepted for this switch, and presentation order is on the backlog (`docs/BACKLOG.md`).
- **The autocomplete for *chateau*:** it shows the first nine matches in list order, so a reordered list
  shows other, equally valid matches. The comparison proves this rather than assuming it. Both lists are
  at the nine-row limit, the card set is identical, the place rows are identical, and every estate shown
  matches the query.
- **Wine order:** the wine switcher's order is unchanged; all 80 estates with listed wines match.

The Phase 4 dual read (`tools/dual-read.py`) still passes, and so does test-phase4's M12 check, which
now requires the switched page to load exactly the M12 file list with the 23 paths moved to
`data/app/`.

## 6. The application in the browser

The real page ran in headless Chrome over the DevTools protocol (the M0 harness):

- it loads, with all 36 data requests served and 23 of them from `data/app/`;
- estate navigation (the producers list and the drawers), wine navigation (the wine switcher) and
  vintage navigation (opened vintage rows) work;
- the search and the autocomplete work, and the map redraws with the list;
- there were no JavaScript errors, no console errors, no failed requests and no empty drawers.

## 7. Performance against the M0 baseline

The switched application was measured three times; M0 measured it once. Each figure is the median of
five page loads, or of 15 searches.

| Measure | M0 (`b1ce39b`) | After the switch (`7db543e`): run 1 / 2 / 3 |
|---|---:|---|
| Cold app ready | 654.7 ms (567–719) | 674.1 / 461.5 / 723.6 ms |
| Warm app ready | 147.5 ms | 134.1 / 134.6 / 142.5 ms |
| Cold data loading | 292.2 ms | 347.9 / 219.0 / 312.7 ms |
| Search, broadest (*chateau*) | 39.6 ms | 45.5 / 39.5 / 37.7 ms |
| Search, the other seven | 19.0–30.8 ms | 20.0–30.8 ms (run 1) |
| App lookups | ≤ 0.034 ms | ≤ 0.030 ms |
| Data bytes loaded | 3,669,262 | 3,705,147 (+1 %: the generated files' headers and serialization) |

- **Cold startup** varies more between runs at one commit (462–724 ms) than it differs from M0. Its
  median over the three runs, 674 ms, is within M0's own range. No material regression.
- **Warm startup** is slightly faster.
- **Search** is in the same band.

C4 and C5 were not touched.

## 8. Memory

The full suite (21 suites, 641 checks, 0 failures) peaked at **1,463.5 MB** cold and **1,462.8 MB** warm
after the switch, against the accepted **1,463 MB** of C1–C3. There is no additional memory. Its time
was 174.0 s and 171.4 s.

## 9. Protected data

All of these are unchanged, each checked by `test-phase5` or `test-phase4` after the switch:

- canonical data;
- evidence (v1–v5, no v6);
- discovery data;
- scope data;
- the Phase 3.4 contract;
- the Phase 2 proposals;
- the normalized model, which also rebuilds byte for byte;
- the raw-source contents, including the C3 links;
- the anomaly hashes.

## 10. Rollback

```text
python tools/app-source.py --legacy     # the application loads data/ again
python tools/app-source.py --model      # and back
python tools/app-source.py              # which source is in use
```

A rollback rewrites only the 23 script tags and precache entries, and bumps the cache name again so
installed copies refetch. It reverts no other Phase 5 work and deletes nothing: the normalized model
and `data/app/` stay, and the model remains the authoritative candidate source.

`test-phase5 switch_rollback_restores_the_legacy_source` tests it in a copy of the site:

1. the copy starts switched;
2. it is rolled back;
3. the application starts and its outputs equal the control exactly, all items identical with no
   order differences;
4. it is switched again, with zero unexplained differences;
5. no protected group changes.

## 11. Tests

`tools/test-phase5.py` now has 25 checks. The ones added by this stage cover:

- the anomaly hashes;
- that the application reads the generated model output (`data/app/` is the model, byte for byte);
- that it reads no prohibited input;
- that no migration runs at runtime;
- that its outputs equal the control;
- the rollback;
- the dual read.

Two existing checks were rescoped to the switch, not weakened:

- **Application unchanged:** `index.html` and the service worker must differ from Phase 4 by exactly
  the switch, and nothing else.
- **test-phase4's M12:** the switched page must load exactly the M12 list with the 23 paths moved.

All 22 suites pass.

## 12. Out of scope, and still unresolved

The switch works without any of these, and none was decided:

- Echo, rename or succession;
- D5;
- the four Graves white names;
- Terrasses after 2019;
- the 11 differing second-wine names;
- plantings or assemblage;
- owner normalization;
- the unresolved legacy identities and filename references;
- C4 and C5.

The evidence is still evidence, and the proposals are still proposals.
