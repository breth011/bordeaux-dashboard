# Phase 5 M0 — Baseline benchmark

Gate: **SAFE — PHASE 5 BASELINE ESTABLISHED**

This is a measurement of the system exactly as Phase 4 left it. Nothing was optimized, moved,
compressed, deduplicated or deleted, and the application was not switched.

- **Records:** every number below is from `data/performance/benchmarks.jsonl`, 96 records from one run
  of `tools/benchmark-phase5.py`.
- **Storage:** the inventory is in `data/performance/storage-inventory.json`.

## 1. Benchmark scope

The run covers ten families:

| Family | What it measures |
|---|---|
| `env` | the machine and the checkout |
| `suite` | the full existing test suite, cold and warm |
| `startup` | the real application loaded in a browser |
| `search` | the application's own search box |
| `lookup` | the application's lookups, and the same questions answered by the model |
| `model` | direct reads of `data/model/` |
| `rebuild` | a deterministic rebuild of the model, in a temporary directory |
| `storage` | an inventory by category |
| `duplicates` | observed duplication |
| `large` | the largest cases present |

**Repetitions:**

- **Cheap operations:** at least 3.
- **Startup:** 5 repetitions.
- **Search:** 15 repetitions per query.
- **Lookups:** 9 samples, each the mean of 50–2,000 calls.
- **Expensive operations:** the rebuild ran twice, and the full suite once per state (a run takes 3.5
  minutes).

Every record keeps its individual runs, median, minimum and maximum.

**Reproducing it:** `python tools/benchmark-phase5.py` appends a new run to the same file. A single
family runs with `--only <family>`.

## 2. Exact commit

The measured commit is **`b1ce39b`** (Phase 4 M14), which equals `origin/main`. The only uncommitted files
during the run were the two new Phase 5 tools, `tools/benchmark-phase5.py` and `tools/test-phase5.py`.
Every record carries `commit: b1ce39b`. The run started at `2026-10-25T11:42:30`.

## 3. Environment

| | |
|---|---|
| OS | Windows 11 (10.0.26200) |
| CPU | Intel64 Family 6 Model 154, 10 physical / 12 logical cores |
| RAM | 16,068 MB |
| Python / Node | 3.12.10 / v24.20.0 |
| Browser | headless Chrome (installed `chrome.exe`), DevTools protocol |
| Free disk at start / end | 13,806 MB / 13,789 MB |
| Working tree (excl. `.git`, `sources/`) | 408.8 MB |
| `data/` | 390.1 MB, 690 files |
| `data/model/` | 80.1 MB, 52 files |
| `data/discovery/` | 140.0 MB, 571 files |
| `data/evidence/` | 143.1 MB, 8 files |
| canonical data (`data/*.js`, `sources.json`) | 10.8 MB |
| `sources/` (raw store, not in git) | 22.07 GB, 73,908 files |
| `.git` | 146.2 MB |

**How time and memory were measured:**

- **Time:** `time.perf_counter` in the runner, and `performance.now()` inside the page.
- **Memory:** peak working set (psutil `peak_wset`).
  - A Python child reports its own at exit.
  - A test suite's is the last value polled every 50 ms. The value only rises, so at most 50 ms of
    growth can be missed.
  - The browser's is the sum over its process tree.
  - The page's JS heap comes from the DevTools Performance domain.

## 4. Current application boundary

The page reads today's files, as it did before Phase 4:

- `index.html`, `assets/app.js`, `service-worker.js`;
- 36 blocking scripts under `data/`, 3,669,262 bytes in all.

It does not read the normalized model. M12's boundary still holds: the page loads 23 contract files
and 13 page assets, and nothing forbidden. `test-phase5` checks that `index.html`, `assets/`, the
service worker, `data/*.js` and `sources.json` are unchanged since `b1ce39b`.

## 5. Full-suite baseline

The 21 existing suites, as Phase 4 runs them, one after another. `test-phase5` is excluded because it
checks this run's own output.

| Run | Elapsed | Suites | Checks | Failures | Peak memory |
|---|---:|---:|---:|---:|---:|
| cold-ish (first after a clean start) | 215.2 s | 21 | 641 | 0 | 1,183.9 MB |
| warm (immediately after) | 211.1 s | 21 | 641 | 0 | 1,184.1 MB |

The peak memory is test-phase4's. Where the time goes in the cold run:

| Suite | Time | Share |
|---|---:|---:|
| test-phase4 | 83.7 s | 39 % (it rebuilds the model twice, runs migrate three more times for the rollback check, reruns M8/M9) |
| test-phase33 | 35.8 s | 17 % (it crawls a local test site) |
| test-phase25 | 9.6 s | 4 % |
| the other 18 suites | 2.5–7.0 s each | 40 % |

Phase 4 described the suite as "about two minutes". That was before test-phase4 grew to 66 checks.
The measured baseline is now **3.5 minutes**. Cold and warm differ by 2 %, because the suite is
dominated by work, not caches.

## 6. Application startup baseline

The real page is served from the repository by a local `http.server` and loaded in headless Chrome:
five repetitions, each with a fresh browser profile.

- **Cold:** the first visit, with no service worker.
- **Warm:** a second navigation in the same browser, after the service worker is active (data
  transfer: 0 bytes).

| Boundary | Cold, median (min–max) | Warm, median (min–max) |
|---|---:|---:|
| browser process to a DevTools page target | 551.6 ms (537–2,619) | — |
| data loading: response end to `domInteractive` (36 data/asset scripts fetched, parsed, run) | 292.2 ms (274–391) | 93.6 ms (87–110) |
| app init: the `DOMContentLoaded` handler, `init()` renders the first view | 89.6 ms (82–103) | 45.7 ms (40–61) |
| **app ready:** navigation start to the end of `init()` | **654.7 ms** (567–719) | **147.5 ms** (138–177) |
| load event | 658.3 ms | 149.5 ms |

| After load | Value |
|---|---|
| data loaded | 3,669,262 decoded bytes (cold transfer 3,680,062 bytes; warm 0, from the service-worker cache) |
| in memory | 470 estates; the first view renders 42 cards |
| page JS heap used / total | 10.8 / 18.1 MB cold; 20.7 / 34.0 MB warm, measured after the second load in one page |
| browser process tree, peak working set | 716 MB cold, 812 MB warm |

`init()` runs inside the `DOMContentLoaded` handler, so `domContentLoadedEventEnd` is the closest
observable "application ready" boundary without changing the app. It is not a paint metric.

## 7. Lookup baseline

**In the application.** `app.js` runs inside a closure, so its functions cannot be called from
outside. The benchmark runs verbatim copies of its lookup functions (`chateauById`, `fiche`,
`ficheUrl`, `winesOf`, `wineFiche`, `scoreFor`) against the live page's globals. The legacy data has
no wine→estate map and no lookup of a wine by name, so those two are scans over `winesOf` of every
estate (marked in the runner).

**In the model.** The same questions are answered by the normalized model in Python, through its
identity map, derived indexes and canonical values. Loading those structures takes 161.7 ms and
72.6 MB.

The workloads are real cases chosen from the data:

- Margaux, the estate with the most fiches (118) and records (467);
- a one-fiche estate (Château de Lauga);
- a compact-list estate;
- the array's last estate;
- Pavillon Blanc du Château Margaux, the other wine with the most vintages (48);
- a one-record wine (Les Tours de Beaumont);
- a record whose fields cite three or more documents.

Times per call, as medians in microseconds:

| Lookup | Workload | App (page) | Model (Python) |
|---|---|---:|---:|
| estate | small / largest / compact-list / last in the array | 1.95 / 0.0 / 1.90 / 1.25 | 0.12 each |
| wine | most vintages / sparse | 2.0 / 32.0 | 0.10 / 0.10 |
| estate → wines | Margaux / small | 0.10 / 1.45 | 0.15 / 0.16 |
| wine → estates | Pavillon Blanc | 30.0 | 13.9 |
| wine + vintage | many / sparse | 0.30 / 1.40 | 0.33 / 0.33 |
| estate + vintage | largest / small | 0.25 / 1.75 | 0.27 / 0.27 |
| fiche document link | multi-source record | 0.20 | 0.30 |
| field | Margaux blend | 0.10 | 0.33 |
| every vintage of an estate (1900–2026, fiche and score) | Margaux | 34.0 | 0.14 (index) |

In the page, `chateauById` is a linear scan, so its cost depends on the estate's position in the
array: Margaux is near the start, Lauga is not. `performance.now()` is coarsened in the browser, which
is why some medians read 0.0 even at 2,000 calls per sample. All lookups are microseconds; none is
near a frame budget.

## 8. Search baseline

The application has a search box in the Producers & map view. The benchmark types each query into it
and dispatches one `input` event, which runs both of the app's handlers:

- the list filter (`visibleChateaux`), which redraws the list and the map;
- the autocomplete (`acSearch`), which renders its rows.

The time runs from the dispatch to the handlers' return. Each query had 15 repetitions in one warm page.

| Query | Kind | Median | Min–max | List cards | Autocomplete rows |
|---|---|---:|---:|---:|---:|
| Château Pichon-Longueville Baron | exact estate name | 27.1 ms | 23.9–33.8 | 1 | 1 |
| pichon | partial estate name | 22.4 ms | 18.2–24.5 | 2 | 2 |
| Carruades de Lafite | exact wine name | 18.8 ms | 17.6–20.3 | 1 | 0 |
| carruades | partial wine name | 21.5 ms | 18.3–50.1 | 1 | 0 |
| pauillac | common term | 30.8 ms | 24.5–42.3 | 19 | 1 |
| chateau | many matches | **39.6 ms** | 34.7–54.2 | 447 | 9 |
| lafleur | few matches | 19.2 ms | 18.3–20.9 | 1 | 5 |
| zzqxv | no matches | 19.0 ms | 18.3–38.8 | 0 | 0 |

A wine name is found through the estate's `second` field. The autocomplete does not search wine names.

## 9. Normalized-model read baseline

Each read ran in a fresh Python process, 3 repetitions. The time is measured inside the process,
excluding interpreter start.

| Read | Records | Median | Peak memory |
|---|---:|---:|---:|
| estates | 470 | 1.0 ms | 19.4 MB |
| wines | 639 | 1.5 ms | 19.6 MB |
| vintages | 5,286 | 7.0 ms | 21.5 MB |
| principal relationships (estate-wine, ranks, classification, appellation) | 2,098 | 7.6 ms | 20.7 MB |
| observations | 22,437 | 119.6 ms | 70.0 MB |
| identity map | 56,531 | 104.9 ms | 65.9 MB |
| evidence links | 81,544 | 233.0 ms | 89.9 MB |
| **all 38 tables** | 333,022 | **961.9 ms** | 91.3 MB |
| the legacy-shaped projection (`model_reader.project`) | 27,137 entries | 1,045.3 ms | 282.3 MB |
| the dual-read new reader (indexes over observations etc.) | — | 365.8 ms | 164.7 MB |
| the six derived indexes | 5,889 keys | 6.4 ms | 20.9 MB |

This is a model baseline, not a proposal to switch the application.

## 10. Normalized-model rebuild baseline

`tools/migrate.py --until M7` ran into an empty temporary directory: from scratch, with no registry.
It ran twice, and both outputs were compared byte for byte with the committed `data/model/`.

| | |
|---|---|
| Total, median (min–max) | **13.95 s** (13.82–14.08) |
| Output | 39 files, 79,161,399 bytes |
| Byte-identical to `data/model/` | **yes**, both runs |
| Peak memory | 423.6 MB |
| Temporary space used, then removed | 75 MB (free disk 13,806 → 13,790 MB after cleanup) |

Stage timings from one in-memory run, with nothing written (13.37 s, peak 423.9 MB):

| Stage | Time | Share |
|---|---:|---:|
| M2 identity, documents, filename references | 6,332 ms | 47 % |
| render (sort and serialize 38 tables) | 1,890 ms | 14 % |
| M4 other wines, seconds, display names | 1,683 ms | 13 % |
| M6 sources, attributions, evidence links | 1,676 ms | 13 % |
| validate (every row against the contract) | 1,158 ms | 9 % |
| M7 observations and canonical values | 288 ms | 2 % |
| M3 grand vins | 65 ms | <1 % |
| M5 vintages | 37 ms | <1 % |

## 11. Memory baseline

Peak working set, by the methods in section 3:

| Operation | Peak |
|---|---:|
| full suite (its largest suite, test-phase4) | 1,184 MB |
| a smaller suite: test-phase2 / test-phase21 (they parse the manifest and evidence) | 832 / 830 MB |
| browser process tree, app loaded cold / warm | 716 / 812 MB |
| browser process tree during the search benchmark | 1,031–1,168 MB (grows across the queries) |
| page JS heap, app loaded | 10.8–20.7 MB used |
| model rebuild | 424 MB |
| model projection (the largest in-memory model load) | 282 MB |
| all model tables | 91 MB |
| the model's lookup structures | 73 MB |

Most of the browser figure is Chrome itself; the page's own heap is about 11–40 MB. The search-time
growth is the whole browser tree over 120 searches, not a page leak measured as such.

## 12. Storage baseline

From `data/performance/storage-inventory.json`.

- **Bytes:** logical length.
- **Allocated:** rounded up to the 4,096-byte cluster. NTFS compression and sparse files were not
  measured.
- **Classification:** descriptive, not normative.

| Category | Sub-category | Files | Bytes | Allocated | Tracked in git |
|---|---|---:|---:|---:|---:|
| authoritative/protected | canonical data | 39 | 10.8 MB | 10.9 MB | 39 |
| | evidence v1–v5 | 8 | 143.1 MB | 143.1 MB | 8 |
| | discovery data | 571 | 140.0 MB | 141.2 MB | 571 |
| | normalized model | 41 | 79.2 MB | 79.3 MB | 41 |
| | proposal and audit records (phase records) | 14 | 15.3 MB | 15.3 MB | 14 |
| | scope data | 3 | 0.56 MB | 0.57 MB | 3 |
| | review and audit records | 2 | 0.30 MB | 0.31 MB | 2 |
| raw/source (not in git) | technical sheets (legacy, `sources/fiches`) | 11,441 | 10.40 GB | 10.42 GB | 0 |
| | discovery blobs (content-addressed) | 29,738 | 8.19 GB | 8.25 GB | 0 |
| | hydro (map shapefiles) | 15 | 1.85 GB | 1.85 GB | 0 |
| | INAO | 6 | 0.91 GB | 0.91 GB | 0 |
| | ISVV | 384 | 60.2 MB | 61.1 MB | 0 |
| | discovery crawl state | 304 | 26.8 MB | 27.5 MB | 0 |
| | bordoverview | 4 | 11.2 MB | 11.2 MB | 0 |
| | crawled pages (legacy) | 2,477 | 8.6 MB | 13.9 MB | 0 |
| | scope, quinney | 21 | 5.3 MB | 5.4 MB | 0 |
| derived or potentially derived | discovery extracted text (local) | 29,517 | 506.0 MB | 570.5 MB | 0 |
| | discovery derived (local) | 1 | 106.7 MB | 106.7 MB | 0 |
| | caches (`__pycache__`) | 40 | 1.1 MB | 1.1 MB | 0 |
| | reports and docs | 30 | 0.76 MB | 0.82 MB | 30 |
| | model check reports / derived indexes | 11 | 0.86 MB | 0.89 MB | 11 |
| repository overhead | `.git` | 2,989 | 146.2 MB | 154.0 MB | — |
| code | application and tools | 284 | 16.8 MB | 17.4 MB | 191 |

The raw store is **21.46 GB** (99 % of all bytes on disk); everything tracked in git is about 0.4 GB.
The 29,517 small extracted-text files waste 65 MB to cluster rounding (12 %). The legacy pages lose
5.2 MB, 60 % on top of their 8.6 MB.

## 13. Duplicate observations

Nothing was removed. A shared digest is evidence of identical content, not permission to remove a
location.

| Observation | Kind | Size |
|---|---|---|
| Bytes held both under `sources/fiches|pages` and as a discovery blob (proven joins, both copies on disk) | same content, two stores | 4,526 artifacts, **4.33 GB** |
| A manifest sha1 at several on-disk paths | same content, several locations | 810 digests, 971 extra copies, **1.07 GB** |
| Harvested bytes found at several URLs | same content, several locations, one blob each | 482 digests at 1,518 URLs, stored once |
| Evidence v5 against v4: same artifact, context, decision and code | same logical information, appended again by design | 40,685 of 40,772 rows (39.3 MB file) |
| Evidence v3 against v2 | same, by design | 34,758 of 41,259 rows (29.4 MB file) |
| Whole evidence rows identical but for `v` | — | 0 (each row records its commit and reader) |
| Fiche values: `fiches.js` against model observations, canonical values and reconciliations | same information, different representation | 1.55 MB against 16.5 MB |
| Evidence store (v4, v5) against the model's evidence links | same information, different representation | 78.7 MB against 20.7 MB |
| Manifest `sources.json` against model artifacts, locators, placements, attributions and assessments | same information, different representation | 6.6 MB against 18.6 MB |
| Discovery observations against the extracted text they came from | different representation (the text is the source) | 70.5 MB against 506.0 MB |
| Model tables against derived indexes | same information, by design rebuildable | 0.32 MB against 0.41 MB |
| `fiches-nl.js` against model translations | same information, different representation | 0.41 MB against 0.55 MB |
| Byte-identical tracked files under `data/` | — | none |

## 14. Large-data cases

| Case | Value | Benchmarked as |
|---|---|---|
| estate with the most records | Margaux, 467 (fiches, ratings, cellar, URLs, cuvees) | `lookup.app.estate*.large`, `large.estate-every-record.model` |
| estate with the most fiches | Margaux, 118 | `lookup.app.estate-all-vintages.large`: 34 µs |
| wine with the most vintages | Pavillon Blanc du Château Margaux, 48 | `lookup.*.wine*.many*` |
| estate with the most documents | Haut-Brion, 472 manifest rows | — |
| broadest search | "chateau", 446 of 470 estates | `search.many-matches`: 39.6 ms |
| largest in-memory load | the model projection, 282 MB, 1.05 s | `model.read.projection` |
| every record of Margaux through the model | 766 entries; 1,058 ms projection plus 2.3 ms scan | `large.estate-every-record.model` |
| largest model file | `observation/evidence-links.jsonl`, 20.7 MB | `model.read.evidence-links`: 233 ms |
| largest discovery file | `data/discovery/artifacts.jsonl`, 17.1 MB | — |
| largest evidence file | `decisions-v5.jsonl`, 39.3 MB | — |
| largest canonical file | `data/fiches.js`, 1.55 MB | loaded by the page every start |
| largest raw file | `sources/hydro/shp/SurfaceElementaire_FXX.shp`, 953 MB | — |

## 15. Disk-pressure observations

Free disk stayed well above the 6 GB threshold, and no benchmark family was stopped. The openpyxl
temporary files outside the project were not touched, and no caches were cleaned for this run.

| Point | Free |
|---|---:|
| start of the run | 13,806 MB |
| model rebuild: before / after cleanup (75 MB temporary used) | 13,806 / 13,790 MB |
| browser startup, search and lookup (temporary profiles, removed) | 13,787–13,796 MB |
| full suite cold: before / after | 13,795 / 13,797 MB |
| full suite warm: before / after | 13,797 / 13,789 MB |
| end of the run | 13,789 MB |

The free disk is up from about 8.7 GB at the end of Phase 4, a change outside this project.

## 16. Benchmark limitations

- **One machine, one run of record.** A first run was discarded before the commit, because its suite
  family failed: test-phase31's static analyzer read a variable name in the new benchmark tool as an
  evidence write. The variable was renamed and the whole run repeated; no test changed.
- **"Cold" is process-cold, not OS-cold.** The OS file cache was not flushed, and the raw store was not
  read.
- **The suite ran once per state,** because a run takes 3.5 minutes.
- **App ready is the end of `init()`,** not first paint. Headless Chrome measures no paint or GPU work.
  The browser's peak memory is mostly Chrome itself.
- **Lookups run copies of the app's functions** against the live page, because the app's own are inside
  its closure. The browser's timer coarsening limits sub-microsecond resolution.
- **Suite memory is polled every 50 ms.** Python children report their own peak exactly.
- **Allocated sizes are estimated** by cluster rounding. NTFS compression was not measured.
- **The model lookups are Python and the app's are JavaScript.** Their figures are not a like-for-like
  comparison of engines, only of access paths.

## 17. Notable performance findings

These are recorded, not acted on:

1. **The test suite takes 3.5 minutes, and 39 % of it is test-phase4.** That suite rebuilds the model twice,
   builds and reverts the model three times in temporary copies and reruns M8 and M9, and it holds the suite's 1.18 GB memory peak.
2. **A model rebuild takes 14 s, and 47 % of it is stage M2.** M2 reads all five evidence versions (for legacy estate ids), every
   v4/v5 read and every discovery location (to join digests). Rendering takes 14 %, and M4 and M6 13 % each; M4 re-reads all
   five evidence versions for display names.
3. **The application loads all 3.67 MB of data on every start,** in 36 blocking scripts. Cold, that is
   292 ms of a 655 ms app-ready; the service worker brings app-ready to 148 ms.
4. **Each keystroke in the search box costs 19–40 ms,** because the list and the map are redrawn on every
   input event. The broadest query renders 447 cards. This is within a frame budget on this machine,
   with little margin.
5. **Lookups are not a bottleneck.** Every application lookup is microseconds. The slowest are the two
   scans the legacy data forces (wine by name 32 µs; wine → estates 30 µs). The model answers either
   from an index, once loaded.
6. **Loading the whole model takes 0.96 s and 91 MB.** The legacy-shaped projection takes 1.05 s and 282 MB.
   The largest model file is the evidence links (20.7 MB, 233 ms).
7. **4.33 GB of raw bytes are stored twice,** in the legacy folders and in the discovery blob store, and
   1.07 GB more are legacy files duplicated across paths. Together that is a quarter of the 21.5 GB
   raw store.
8. **Evidence v5 repeats v4's verdict on 99.8 % of its rows,** and v3 repeats v2's on 84 %. This is the
   append-only store working as designed.
9. **The model's normalized form of the fiche values is 10.6× the size of `fiches.js`.** The same holds,
   at 2.8×, for the manifest's model form against `sources.json`.
10. **The discovery extracted text** (506 MB in 29,517 small files) loses 12 % to cluster rounding.

## 18. No optimization occurred

No data structure, format, serialization, index, cache, search algorithm, startup path, application
boundary, id, raw document, evidence or discovery representation was changed. Nothing was compressed,
deduplicated, relocated or deleted. The normalized model is byte-identical to `b1ce39b`, as the
rebuild comparison and `test-phase5` show. Canonical data, evidence, discovery data, scope data, the
Phase 3.4 contract and the Phase 2 proposal records all hash as they did at the Phase 4 baseline.
The application still reads today's `data/` files.

The only new files are:

- `tools/benchmark-phase5.py`;
- `tools/test-phase5.py`;
- `data/performance/benchmarks.jsonl`;
- `data/performance/storage-inventory.json`;
- this report.
