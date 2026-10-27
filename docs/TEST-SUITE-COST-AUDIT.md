# Test suite cost audit

A read-only profile of where the full suite's time goes, to design future phase validation around the
expensive parts. Nothing was changed: no test, scheduling, cache, baseline or production code.
No full suite was run for this audit.

**Evidence:**
- the runner's own timing record (`reports/suite-runtime.json`): the baseline run and the last passing run
  per worker count, and the history of totals;
- the logs of three recent full runs: M3.6G (750.5 s), M3.6H (807.7 s), and the first M3.10A attempt
  (2,596.6 s, 7 suites failing);
- each suite's source, read for what it does;
- the Phase 6.6 measurements (`docs/PHASE-6.6-PERFORMANCE-PROFILE.md`,
  `docs/PHASE-6.6-PERFORMANCE-OPTIMIZATION.md`);
- three small measurements: one shared-check cache scan, one call of a model-guard helper, and the
  file count the cache scans.

## The 40-minute run was not the suite's cost

The run that took 2,596.6 s (43 minutes) is not a measurement of the committed suite. Three things inflated it:

1. **A defect in the M3.10A working tree, uncommitted.**
   - The M3.10A set-aside helpers in `tools/historical_m2_scope.py` (`is_m310a_row`) re-read the
     registration manifest on every call: 0.19 ms per call.
   - The model guards call it once per row, on both sides of five large model files (provenance 27k
     rows, placements 19k, locators 19k, identity-map 56k, artifacts 37k). That is about 300k calls,
     **roughly a minute of extra work per guard call, in each of about 15 suites**.
   - It shows in the suites that call those guards:

     | Suite | M3.6H run | M3.10A run |
     |---|---:|---:|
     | `test-m36g` | 1.4 s | 161 s |
     | `test-m36f` | 11 s | 261 s |
     | `test-m35` | 58 s | 483 s |
     | `test-m34b` | 55 s | 414 s |
     | `test-m36b` | 77 s | 536 s |

   - It has to be fixed before M3.10A is committed: read the manifest once and pass sets.
2. **The tree was edited during the run.**
   - Two tools were changed mid-run to fix a failure.
   - The shared-check cache (`tools/check_cache.py`) reuses a result only while every file's size and
     modification time is unchanged, so every check after the edit was rebuilt.
3. **Machine load.** The unaffected suites also ran slower than in clean runs, typically 10–60%.

**The committed suite's cost is the last clean run:** 807.7 s wall time with 2 workers, 1,615.4 s of suite time.
- **Against the baseline:** 610.8 s on 26 October; the growth since is the six M3.6 suites and
  run-to-run variance.
- **Against the performance limit:** the M3.6H run was 32% over the baseline. Phase M3.6H classified the
  slowest suite's jump as an environmental outlier; it did not reproduce.

The cache scan is cheap: 75,365 files in 0.2 s per call. It is not a cost centre.

## A. Current cost profile

From the last clean run (M3.6H, 807.7 s, 47 suites, 1,029 checks). "Range" is the suite's time across
the three clean runs on record (baseline, M3.6G, M3.6H): wide ranges are contention between the two
workers, not work. "% total" is the share of the 1,615.4 s of suite time.

Columns:
- **Browser:** the suite drives headless Chrome (through `tools/benchmark-phase5.py` / `tools/app-reference.py`).
- **Server:** it starts a local HTTP server; every browser suite does.
- **Subprocess:** it runs a tool or `git` in a child process.
- **Full model:** it reads the model tables.
- **Held docs:** it reads held source documents under `sources/`.
- **Migration check:** it runs `tools/migrate.py --check` (or the shared check does).
- **Network:** no suite reaches the internet. `test-phase33`'s crawler test runs against a local server.

| Suite | Runtime (s) | Range in clean runs (s) | % total | Browser | Subprocess | Server | Full model | Held docs | Migration check | Main protection | Focused alternative | Class |
|---|---:|---|---:|---|---|---|---|---|---|---|---|---|
| `test-m36c.py` | 233.4 | 93.5–233.4 | 14.4 | — | yes | — | yes | yes | yes | historical audit (M3.6C identity review), rebuilt twice | `test-m36c.py --check` | frozen historical |
| `test-m36a-rerun.py` | 219.8 | 111.7–219.8 | 13.6 | — | yes | — | — | yes | yes | historical audit (M3.6A rerun); first to build shared migration/gap checks | `m36a-rerun.py --check` | frozen historical |
| `test-phase69.py` | 94.5 | 80.7–110.7 | 5.8 | yes | yes | yes | yes | — | — | app (browser) | none cheaper | end-to-end |
| `test-m36b.py` | 76.8 | 60.0–105.1 | 4.8 | — | yes | — | yes | yes | yes | evidence v6 + model mappings + app/index | `m36b-apply.py --check` | cross-phase regression |
| `test-historical-m2.py` | 75.0 | 50.6–75.0 | 4.6 | — | yes | — | yes | — | — | historical audit (document dates, read by the migration) | `extract-document-dates.py --check` | frozen historical |
| `test-phase4.py` | 72.2 | 68.9–76.3 | 4.5 | — | yes | — | yes | yes | yes | schema + migration + model (66 checks) | `migrate.py --check` | cross-phase regression |
| `test-phase63.py` | 70.9 | 69.3–91.7 | 4.4 | yes | yes | yes | yes | — | — | app (browser) + frozen app c775ea7 re-rendered | none cheaper | end-to-end |
| `test-m34a.py` | 59.4 | 58.0–69.8 | 3.7 | — | yes | — | yes | yes | — | historical audit (M3.4A mapping proposals) | `m34a-mapping-audit.py --check` | frozen historical |
| `test-m35.py` | 57.8 | 44.4–68.1 | 3.6 | — | yes | — | yes | — | yes | historical audit (M3.5 review) + model guards | `m35-review.py --check` | frozen historical |
| `test-m34b.py` | 55.1 | 37.7–55.1 | 3.4 | — | yes | — | yes | yes | yes | model mappings + app/index | `m34b-apply.py --check-all` | cross-phase regression |
| `test-phase5.py` | 52.7 | 52.7–76.4 | 3.3 | yes | yes | yes | yes | yes | — | app source switch (browser, 3 captures) | none cheaper | end-to-end |
| `test-m36h.py` | 52.5 | 52.5–52.5 | 3.2 | — | yes | — | yes | — | — | evidence v8 correction | `m36h-apply.py --check` | phase-local |
| `test-m33.py` | 50.9 | 36.3–50.9 | 3.2 | — | yes | — | yes | yes | — | historical audit (M3.3 source plan) | `m33-source-plan.py --check` | frozen historical |
| `test-phase65.py` | 49.7 | 49.3–59.5 | 3.1 | yes | yes | yes | yes | — | — | app (browser) + frozen app c15b421 re-rendered | none cheaper | end-to-end |
| `test-m32.py` | 45.0 | 45.0–58.1 | 2.8 | — | yes | — | yes | yes | yes | model values (M3.2) + app | `m32-recovery.py --check` | cross-phase regression |
| `test-phase61.py` | 34.9 | 28.0–34.9 | 2.2 | yes | yes | yes | yes | — | — | app per-figure provenance (browser, 1 capture) | none cheaper | end-to-end |
| `test-phase67.py` | 33.2 | 28.6–36.2 | 2.1 | yes | yes | yes | yes | — | — | app (browser) | none cheaper | end-to-end |
| `test-phase25.py` | 30.8 | 10.0–30.8 | 1.9 | — | yes | — | — | yes | — | legacy data pipeline | — | cross-phase regression |
| `test-data-gap-register.py` | 23.5 | 22.4–30.6 | 1.5 | — | yes | — | yes | — | — | gap register | `build-data-gap-register.py --check` | cross-phase regression |
| `test-m36e.py` | 16.6 | 16.6–33.2 | 1.0 | — | yes | — | yes | yes | yes | evidence v7 corrections | `m36e-apply.py --check` | phase-local |
| `test-phase33.py` | 16.1 | 14.8–21.7 | 1.0 | — | yes | yes | — | yes | — | discovery crawler (local server) | — | cross-phase regression |
| `test-historical-m1.py` | 15.7 | 8.5–15.7 | 1.0 | — | yes | — | yes | — | — | schema (historical fields) | — | frozen historical |
| `test-m36d.py` | 14.1 | 12.6–14.1 | 0.9 | — | yes | — | yes | — | yes | model (Cuvée wine) + app/index | `m36d-cuvee.py --check` | phase-local |
| `test-phase210.py` | 12.5 | 5.5–12.5 | 0.8 | — | yes | — | — | yes | — | reader rules | `test-reader.py` | cross-phase regression |
| `test-phase27.py` | 12.1 | 5.0–12.1 | 0.7 | — | yes | — | — | yes | — | reader / evidence decider | — | cross-phase regression |
| `test-m36f.py` | 11.3 | 11.3–40.2 | 0.7 | — | yes | — | yes | yes | yes | model (Cuvée vintages, values) + app/index | `m36f-vintages.py --check` | phase-local |
| `test-phase32.py` | 10.2 | 6.7–10.2 | 0.6 | — | yes | — | — | — | — | legacy normalisation | — | cross-phase regression |
| `test-historical-m3.py` | 9.5 | 8.4–9.5 | 0.6 | — | yes | — | yes | — | — | historical audit (M3 claims) | `extract-historical-m3.py --check` | frozen historical |
| `test-phase24.py` | 9.4 | 8.6–9.4 | 0.6 | — | yes | — | — | — | — | evidence store | — | cross-phase regression |
| `test-phase31.py` | 9.1 | 8.5–9.7 | 0.6 | — | yes | — | — | — | — | estate universe / structure | `audit-structure.py` | cross-phase regression |
| `test-phase30.py` | 8.8 | 7.2–8.8 | 0.5 | — | yes | — | — | — | — | estate universe | `build-universe.py --check` | cross-phase regression |
| `test-data.py` | 8.6 | 7.4–8.7 | 0.5 | — | yes | — | — | — | — | legacy data files | — | cross-phase regression |
| `test-phase28.py` | 8.1 | 6.5–9.1 | 0.5 | — | yes | — | — | — | — | reader rules | `test-reader.py` | cross-phase regression |
| `test-phase2.py` | 7.5 | 5.7–7.9 | 0.5 | — | yes | — | — | — | — | legacy pipeline | — | cross-phase regression |
| `test-phase21.py` | 7.4 | 5.5–8.3 | 0.5 | — | yes | — | — | — | — | evidence store | — | cross-phase regression |
| `test-m36a-r1.py` | 7.4 | 5.8–7.6 | 0.5 | — | yes | — | yes | yes | yes | web-page reader rules (W1–W6) + data scope | — | cross-phase regression |
| `test-phase212.py` | 7.0 | 5.2–7.0 | 0.4 | — | yes | — | — | — | — | reader / evidence | — | cross-phase regression |
| `test-reader.py` | 6.6 | 4.9–6.6 | 0.4 | — | — | — | — | yes | — | reader rules (fingerprint) | itself | cross-phase regression |
| `test-phase34.py` | 6.3 | 5.5–6.3 | 0.4 | — | yes | — | — | — | — | schema / contract (Phase 3.4 model) | `build-phase34-model.py --check` | cross-phase regression |
| `test-phase211.py` | 4.8 | 4.7–6.1 | 0.3 | — | yes | — | — | yes | — | reader rules | `test-reader.py` | cross-phase regression |
| `test-check-cache.py` | 4.2 | 3.2–4.2 | 0.3 | — | yes | — | — | — | yes | test infrastructure (shared-check cache) | itself | cross-phase regression |
| `test-phase29.py` | 4.1 | 3.2–4.1 | 0.3 | — | yes | — | — | yes | — | reader rules | `test-reader.py` | cross-phase regression |
| `test-phase26.py` | 2.8 | 2.8–4.2 | 0.2 | — | yes | — | — | yes | — | legacy pipeline | — | cross-phase regression |
| `test-phase22.py` | 2.7 | 2.4–2.7 | 0.2 | — | yes | — | — | — | — | legacy pipeline | — | cross-phase regression |
| `test-phase23.py` | 2.6 | 2.6–3.8 | 0.2 | — | yes | — | — | — | — | legacy pipeline | — | cross-phase regression |
| `test-m36g.py` | 1.4 | 1.4–8.5 | 0.1 | — | yes | — | yes | yes | — | historical audit (M3.6G acquisition) | `m36g-acquisition.py --check` | phase-local |
| `test-run-tests.py` | 0.4 | 0.3–0.4 | 0.0 | — | yes | — | — | — | — | test runner + performance guard | itself | performance guard |

New suites since the last clean run have no clean timing yet:

| Suite | Time on record | Notes |
|---|---:|---|
| `test-m37` | 2.9 s | measured stand-alone, before M3.10A |
| `test-m38` | — | only the inflated M3.10A run (103 s); its audit's `--check` reads 115 held extractions |
| `test-m39` | — | only the inflated M3.10A run (144 s); it loads the M3.5 review context once |
| `test-m310a` | 274 s | measured stand-alone on the uncommitted M3.10A tree, including the helper defect below; `migrate.py --check`, which rebuilds the model twice (from scratch and with the registry), is its largest single check |

## B. Top cost centres

Cumulative share of the 1,615.4 s:

| Share | Smallest set of suites | Their time |
|---|---|---:|
| **~50%** | `test-m36c`, `test-m36a-rerun`, `test-phase69`, `test-m36b`, `test-historical-m2`, `test-phase4`, `test-phase63` (7 suites) | 843 s (52%) |
| **~75%** | the 7 above, plus `test-m34a`, `test-m35`, `test-m34b`, `test-phase5`, `test-m36h`, `test-m33`, `test-phase65` (14 suites) | 1,221 s (76%) |
| **~90%** | the 14 above, plus `test-m32`, `test-phase61`, `test-phase67`, `test-phase25`, `test-data-gap-register`, `test-m36e`, `test-phase33`, `test-historical-m1`, `test-m36d`, `test-phase210` (24 suites) | 1,463 s (91%) |

The other 23 suites take 152 s together. Every one is under 13 s, and most are under 8 s.

What the large ones spend their time on:

- **`test-m36c` (93–233 s; 67.5 s when run alone).**
  - It rebuilds the M3.6C identity audit twice: once in-process (t05, 33 s) and again through
    `--check` in a subprocess (t12, 29 s) to prove the output is byte-identical.
  - The wide range is contention with `test-m36a-rerun` under two workers.
- **`test-m36a-rerun` (112–220 s).**
  - It runs the M3.6A reader rerun over the held documents.
  - Started first because it is the longest, it is usually the suite that builds the shared checks
    (`migrate.py --check`, the gap register) that later suites then reuse from the cache, so it carries
    that cost for everyone.
- **The six browser suites (5, 61, 63, 65, 67, 69): 336 s, 21% of suite time.**
  - Phase 6.6 measured each `app-reference.capture()` at about 11 s. There are six per run: three in
    `test-phase5`, two in `test-phase63`, one in `test-phase61`.
  - The re-rendering of two frozen older applications (`c775ea7` in `test-phase63`, `c15b421` in
    `test-phase65`) costs about 45 s.
- **The historical audits:** `test-historical-m2`, `test-m34a`, `test-m35`, `test-m33`, part of
  `test-m36c` and `test-m36a-rerun`. They prove that a frozen audit still reproduces byte for byte by
  re-running the tool that wrote it, which re-reads the model and often the held documents.
- **`test-phase4`:** 66 checks over the migration and the model, under the heaviest memory and disk
  contention (Phase 6.6: ×1.81 at 2 workers).

## C. Validation tiers (proposed, not adopted)

| Tier | When | What runs | Typical cost |
|---|---|---|---:|
| **1 — phase gate** | before each phase commit | The phase's own focused test (twice), and the `--check` of every generator whose output the phase changed. If the model changed: `migrate.py --check`, `build-indexes.py --check`, `build-app-data.py --check`, `build-data-gap-register.py --check`. | 1–6 min |
| **2 — local regression** | the same commit, when the phase touches a shared layer | The suites that guard that layer, chosen by what the phase changed (below). | 2–10 min |
| **3 — milestone regression** | at the end of a coherent run of phases (e.g. after M3.10B), before pushing | All cross-phase regression and frozen-historical suites, without the six browser suites. | ~10 min |
| **4 — full suite** | before a push or a release, after a model-schema change, and whenever app output changes | Everything, on an unchanged tree, with the performance check. | ~13–14 min on a quiet machine |

Tier 2 is chosen by layer:

| A phase that changes... | Runs |
|---|---|
| the evidence store | `test-phase21`, `test-phase24`, `test-m36b`, `test-m36e`, `test-m36h` |
| the reader rules | `test-reader`, `test-phase2x`, `test-m36a-r1`, `test-m36a-rerun`; no phase may do this without a decision |
| the migration or the model | `test-phase4`, `test-historical-m1`, `test-m32`, `test-m34b`, `test-m36d`, `test-m36f`, and the phase suites that guard model diffs through `historical_m2_scope` |
| a frozen audit's inputs | that audit's suite: `test-historical-m2`, `test-m33`, `test-m34a`, `test-m35`, `test-m36c`, `test-m36g`, `test-m37`, `test-m38`, `test-m39` |
| the app data | `test-phase5`, `test-phase61`, `test-phase63` |
| acquisition or audit only | Tier 1 alone |

Two rules follow from section 1:
- **Never edit the tree during a full run.** Every check after the edit is rebuilt.
- **Run Tier 4 on a quiet machine,** or its time is noise.

## D. Candidate optimizations (none implemented)

| # | Candidate | Estimate | Class | Why |
|---|---|---:|---|---|
| 1 | Fix M3.10A's per-row manifest re-read: read the registrations once and pass sets | removes ~15+ min of suite time the uncommitted M3.10A would add | **SAFE** (required) | A defect in uncommitted code, not an optimization of the committed suite; the guards' logic is unchanged. |
| 2 | Adopt tiers 1–3 for phase commits; the full suite at milestones and pushes | ~13 min per phase commit | **SAFE** (process) | No code changes. The project's memory rule "run the suite after committing" becomes a Tier 4 rule at push time. |
| 3 | Don't edit the tree during a run; run Tier 4 on a quiet machine | variable (the 43-minute run) | **SAFE** (process) | Uses the cache as designed. |
| 4 | Memoize the model guards' `git show` and table reads within one suite (`historical_m2_scope`: `_lines`, `read_table` of provenance) | ~5–20 s per guard-heavy suite | **NEEDS DESIGN** | Many suites call two or three guards that each re-read the same five large files at the same baseline. A per-process cache is safe only if no check mutates the rows. |
| 5 | `test-m36c`: compare the in-process build (t05) with the committed audit, and keep a single subprocess `--check` | ~30 s | **NEEDS DESIGN** | t12 proves a second run is byte-identical; dropping it changes what the test proves. A determinism proof could reuse t05's bytes against one subprocess run. |
| 6 | Persist expensive deterministic checks across runs (`migrate.py --check`, the M3.6A rerun), keyed by a content hash of their inputs | 1–4 min per run | **NEEDS DESIGN** | The cache is per run by design, and keyed by mtimes, not content. A cross-run cache needs an exact input list per check, or it can hide a regression. |
| 7 | Move phase-local suites (`test-m36d` to `test-m310a`) out of every full run into Tier 2 | ~100–300 s | **NEEDS DESIGN** | They also guard cross-phase model invariants (through `historical_m2_scope`); their protection would need to move to one guard suite first. |
| 8 | Condition waits for the remaining fixed sleeps in the browser suites (Phase 6.6 §14) | ~8–10 s | **SAFE** | Phase 6.6 identified it; the same pattern as O3. |
| 9 | Memoize committed-model reads within `test-phase4` (Phase 6.6 §14) | ~6–8 s | **NEEDS DESIGN** | Needs care that no check mutates the shared rows. |
| 10 | Share one browser, or one capture, across the browser suites | ~33 s | **NOT WORTH RISK** | Rejected in Phase 6.6: suites must stay independent, and a shared Chrome profile or service worker carries state between them. |
| 11 | Stored fixtures for the frozen applications (`c775ea7`, `c15b421`) | ~45 s | **NOT WORTH RISK** | Rejected in Phase 6.6 (O5-A): the live control proves more than a stored one. |
| 12 | 3 or 4 workers | 5–28 s | **NOT WORTH RISK** | Rejected in Phase 6.6: unstable times, too little free memory. |
| 13 | PyMuPDF's unconditional layout import (~1.7 s per process) | ~44 s | **NOT WORTH RISK** now | Blocked by the reader fingerprint (Phase 6.6 §14). |
| 14 | Group the browser suites' captures within one suite (e.g. `test-phase5`'s three) | — | **NOT WORTH RISK** | Each capture is of a different site (current app, rollback copy, back on the model); there is nothing duplicated to remove. |

## What this audit did not do

It changed no test, cache, schedule, baseline or production code. It did not run the full suite. It did
not decide any tier: section C is a proposal. The working tree's uncommitted M3.10A changes are untouched
and not part of this audit.
