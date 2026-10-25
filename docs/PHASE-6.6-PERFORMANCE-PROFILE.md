# Phase 6.6B — Test suite performance profile

Gate: **SAFE — PHASE 6.6B PERFORMANCE PROFILE COMPLETE — READY FOR OPTIMIZATION**

This phase is measurement and diagnosis only. No test, tool, application file, model or data was
changed; the only output is this document. The profiling ran each suite in-process, unchanged, with
instrumentation wrapped around the calls it makes. The harness, cProfile output and trial runners
stayed in the session scratchpad and were removed.

Two of the proposed optimizations need a decision before Phase 6.6C (section 7): one touches the
crawler, one changes how two frozen controls are held. Neither blocks the rest of the plan.

## 1. Baseline

Reproduced at `d3643d4`, sequential, one process per suite:

| | Phase 6.6A | Phase 6.6B rerun |
|---|---:|---:|
| Suites | 25 | 25 |
| Checks | 708 | 708, all pass |
| Suite time | 360.5 s | **354.8 s** (−1.6 %, within run-to-run variance) |
| Peak memory | 1,443 MB (test-phase5, with Chrome) | — |

**Per-suite time** (6.6B rerun):

| Suite | s | Suite | s | Suite | s |
|---|---:|---|---:|---|---:|
| test-phase63 | 73.6 | test-phase25 | 7.9 | test-phase210 | 5.3 |
| test-phase4 | 49.6 | test-data | 6.4 | test-phase31 | 5.1 |
| test-phase5 | 42.8 | test-phase30 | 6.0 | test-phase2 | 4.9 |
| test-phase65 | 42.3 | test-phase24 | 5.9 | test-phase27 | 4.9 |
| test-phase33 | 35.4 | test-phase28 | 5.8 | test-phase32 | 4.8 |
| test-phase61 | 17.4 | test-phase21 | 5.4 | test-phase212 | 4.4 |
| | | test-phase211 | 4.3 | test-phase34 | 3.9 |
| | | test-reader | 3.8 | test-phase29 | 2.9 |
| | | test-phase26 | 2.8 | test-phase23 | 2.5 |
| | | test-phase22 | 2.4 | | |

**Method.** A scratch harness ran each suite in-process, unchanged, and wrapped:

- **every check:** suites built on `@check` were timed check by check;
- **the shared browser driver**, `tools/benchmark-phase5.py`, each time a suite loaded it: launches,
  start and close time, page loads, DevTools calls by method, `js` evaluations, screenshots and input
  events;
- **every `subprocess` call**, with its time;
- **every `time.sleep`**, attributed to its file and line.

A second pass ran under cProfile, used for shares only because it inflates time. Separate scripts
then timed the individual building blocks without the profiler. The instrumented total was 344.3 s,
against 354.8 s for the plain run.

## 2. Browser breakdown

The four browser suites total 177.1 s (instrumented), **51 %** of all suite time.

| Suite | Runtime (s) | Browser launches | Page loads | JS evaluations | Screenshots | Input events | Major operation |
|---|---:|---:|---:|---:|---:|---:|---|
| test-phase5 | 42.1 | 3 | 3 | 90 | 0 | 0 | three full `app-reference` captures: current app, rollback copy on legacy, rollback copy back on model |
| test-phase61 | 18.3 | 2 | 2 | 34 | 0 | 0 | one full `app-reference` capture (12.1 s) |
| test-phase63 | 75.7 | 4 | 4 | 336 | 0 | 0 | 137 drawers opened in the current app (26.1 s) and in the `c775ea7` app (25.3 s); two captures (22.8 s) |
| test-phase65 | 41.0 | 6 | 6 | 155 | 0 | 134 | two page sweeps (current and `c15b421`), two phone-width loads, one keyboard and one touch session |
| **Total** | **177.1** | **15** | **15** | **615** | **0** | **134** | |

**Where the browser time goes:**

| Component | Seconds | Share of browser time |
|---|---:|---:|
| JavaScript evaluations (`Runtime.evaluate`): rendering drawers, searches, reading text | **96.7** | 55 % |
| Fixed sleeps | 23.1 | 13 % |
| Browser close (15 × 0.62–0.77 s, of which a fixed 0.5 s each) | 12.9 | 7 % |
| Browser launch (15 × 0.58–0.67 s) | 10.5 | 6 % |
| Page loads (navigate to load event) | 11.7 | 7 % |
| Python-side work in these suites (model reads, `render`, git) | ~22 | 12 % |

The fixed sleeps break down as:

- 7.5 s in the driver's own close;
- 5.8 s after navigation and tab clicks in `app-reference`;
- 3.2 s of 64 × 50 ms between keystrokes in test-phase65;
- the rest after taps and drawer opens.

**Re-initialization.** No suite re-starts a browser for each check:

- test-phase63 and test-phase65 keep one browser per application through a page cache;
- each launch serves a different application (current, `c15b421`, `c775ea7`, a copied site) or a
  different device mode (desktop, phone with touch).

**The full capture.** `app-reference.capture()` costs about **11 s** each time: 13 searches, the
lookups, 13 estate drawers with each wine and opened vintage rows. It runs 6 times in all:

- 3 in test-phase5;
- 1 in test-phase61;
- 2 in test-phase63.

That is about 66 s. Three of the six capture the identical current application, in three different
suites.

**One drawer reading in test-phase63**, split in the browser (137 drawers in one evaluation, 13.6 s):

| Step | Per drawer | 137 drawers |
|---|---:|---:|
| clear the search box (an `input` event re-filters and re-renders all 470 cards, even when the box is already empty) | 45 ms | **6.1 s** |
| open the drawer (the app renders it) | 22 ms | 3.0 s |
| read its text (`innerText` of a clone) | 29 ms | 3.9 s |
| close | 4 ms | 0.6 s |

A DevTools round trip itself is about 1.7 ms. The cost is the page's work, not the protocol.

## 3. Phase 4 breakdown

test-phase4: 48.2 s instrumented, 66 checks, no browser.

| Part | Seconds | Note |
|---|---:|---|
| from-scratch build to M6 and M7 (child process, `migrate.snapshots`) | 12.1 | one build, shared by the determinism check and the rollback check (Phase 5 C2) |
| `migrate.py --revert M7` on a copy of the model | 9.3 | the rollback check: the registry path must equal the scratch path |
| `migrate.py --revert M2`, copying, comparing | ~2.2 | the rest of the rollback check (11.5 s total) |
| the other 63 checks | 24.2 | 0.4–3.0 s each: they read the committed model |
| `build-indexes.py --check` | 0.6 | |
| `git diff-tree` × 30 | 0.8 | |
| Node legacy and canonical dumps | 0.7 | |

**Repeated builds: none.** The two builds are different paths, a from-scratch build and a registry
rollback, and the check exists to prove they agree. The determinism check and the rollback check
already share the scratch build. `migrate.py --check` (18.6 s) is not run by the suite.

**Repeated reads within the suite.** The model is read many times over:

- `read_table` 79 calls, with no in-process cache (a full read of every model table takes **0.98 s**,
  and 1.02 s again);
- `jsonl_lines` 530 calls;
- `model_reader.project` 5 calls (**1.13 s** each, 0.87 s when warm);
- `group_hashes` 21 calls (0.90 s for all protected groups).

Re-reading the committed model across checks accounts for an estimated **6–8 s** of the 24.2 s.

**Subprocess start-up** is small: Python starts in 0.03 s. The children's cost is their work.

## 4. Phase 33 breakdown

test-phase33: 35.4 s, 34 checks.

| Part | Seconds | Note |
|---|---:|---|
| **crawler sleeps** (`discover.py:603`), 16 × 1.5 s | **24.0** | **68 % of the suite** |
| `discover_extract.py` child processes, 6 × ~1.9 s | 11.5 | of which ~1.7 s each is importing PyMuPDF (section 5) |
| requests to the local server, parsing, report, harvest checks | < 1 | |

**Why the sleeps happen.** The suite deliberately runs the real crawler, extractor and report three
times against a local crafted site (initial crawl, repeat with saved validators, replaced document).
That is a behaviour test, not a live-network test. The test asks for no politeness delay
(`crawl_site(..., min_delay=0.0)`). But `Robots.delay()` returns `max([MIN_DELAY] + robots delays)`,
with `MIN_DELAY = 1.5`. The crawler then applies `max(delay, self.min_delay)`, so the floor of 1.5 s
holds whatever the caller passes.

**The test's request has no effect.** Production calls `crawl_site(store, d)` with the default
`min_delay=MIN_DELAY`, so it never relies on the override. No test asserts the delay value or the
waiting.

## 5. Repeated immutable work

| Operation | Frequency | Total cost | Immutable? | Safe to share? |
|---|---:|---:|---|---|
| importing PyMuPDF (`import fitz`, 1.67 s, of which `pymupdf.layout` and its ONNX runtime 1.58 s, imported unconditionally by PyMuPDF 2.0) | 20 suites + 6 extractor children | **~44 s** | yes | **no**: avoiding it means changing `sheetreader.py`, whose bytes are the pinned reader fingerprint (`7e8cfed1c24e`), or uninstalling `pymupdf_layout`, which may change extraction |
| full `app-reference` capture of the current application | 3 suites (5, 61, 63) | ~33 s | within a run, yes | **no** across suites: each suite must stay independent (6.6A). Within test-phase5 the second capture is of a different site, the rollback copy. |
| re-rendering a frozen older application (`c775ea7` in test-phase63: 137 drawers and a capture; `c15b421` in test-phase65: a page sweep and a phone load) | every run | **~45 s** | yes: fixed commits, fixed legacy data | possible only as stored fixtures, which changes what the control is (section 7, decision) |
| clearing an already-empty search box before each drawer | 274 in test-phase63, ~80 in captures and test-phase65 | **~13–15 s** | n/a: pure redundant work | yes, if cleared only when not empty (the list is then the same) |
| fixed sleeps in the browser driver and tests | 15 closes, ~190 others | 23.1 s | n/a | the close sleep can become a retry; the others need condition waits |
| crawler politeness sleeps in test-phase33 | 16 | 24.0 s | n/a | yes: the test already asks for none |
| reading the committed model (`read_table`, `project`, `group_hashes`) | test-phase4, and 5, 61, 63, 65 | ~6–8 s in test-phase4, ~2–4 s elsewhere | yes, during a run | within one suite only, and only if checks cannot mutate shared rows (a cache, decision) |
| generated-data `render()` | test-phase65 ×2 (the determinism check), test-phase5 ×1 | 2.1 s each | yes | **no**: rendering twice is what the determinism check tests |
| scratch model build | test-phase4 ×1 | 12.1 s | yes | already shared (Phase 5 C2) |
| Node legacy dump | 2 per suite, ~15 suites | ~6 s | yes | low value |
| `git diff-tree` per commit | 50 in test-phase5, 30 in test-phase4 | ~2 s | yes | low value |

## 6. Ranked bottlenecks and opportunities

Ranked by expected saving, then confidence that coverage is preserved, then complexity and isolation
risk:

| Rank | Opportunity | Saving (sequential) | Coverage preserved | Complexity | Isolation risk |
|---:|---|---:|---|---|---|
| 1 | **run suites in parallel** (no test changes) | **−140.7 s** measured (354.8 → 214.1 s, 4 workers) | fully: same suites, same checks | low: a runner | low; contention slows each suite 2–3.8×, so fixed sleeps must hold under load (they did) |
| 2 | **frozen controls held as stored fixtures** (test-phase63's `c775ea7`, test-phase65's `c15b421`) | ~45 s | the comparisons stay; the old app is no longer re-rendered | medium | **decision**: a stored control drifts if the capture definitions change |
| 3 | **crawler honours `min_delay=0.0`** in test-phase33 | ~24 s | fully; production delay unchanged | low | **decision**: touches `tools/discover.py` (the crawler) |
| 4 | **clear the search box only when it is not empty** | ~13–15 s | fully: the card list is identical | low (test JS only) | none |
| 5 | **driver close without a fixed 0.5 s sleep** (retry the profile removal instead) | ~7.5 s | fully | low | none |
| 6 | condition waits instead of other fixed sleeps | ~8–10 s | fully | medium | flakiness under load |
| 7 | memoize committed-model reads within one suite | ~6–8 s (test-phase4) | fully, if rows are not mutated | medium | a cache: shared mutable state between checks |

**The smallest set with a material effect is 1, 4 and 5.** They need no decision:

| | Seconds | Change |
|---|---:|---|
| sequential, after 4 and 5 | ~333 | −6 % |
| with 3 as well, if approved | ~309 | −13 % |
| with 2 as well, if approved | ~264 | −26 % |
| run in parallel (1), on top | ~150–200 | about −45 % to −58 % (estimated) |

## 7. Proposed optimizations

### O1 — Parallel suite runner

- **Duplicated work removed:** none. It uses idle cores.
- **Why it is safe:** 6.6A showed every suite is independent and order-free:
  - no suite writes the repository or `sources/`;
  - temporary directories have unique names;
  - servers and Chrome use ephemeral ports and their own profiles;
  - each suite runs in its own process.
- **Isolation preserved:** fully. Suites still run in separate processes.
- **Still exercised:** everything; no test changes.
- **Saving:** measured 354.8 → **214.1 s** with 4 workers, all 25 suites passing, the tree clean
  afterwards. Contention made each suite 2–3.8× slower (test-phase4 182 s, test-phase63 155 s), so
  more workers will not scale linearly. A 2- and 3-worker trial should pick the setting.
- **Verification:** three parallel runs with the same per-suite results and check counts as
  sequential (708), and a clean tree after each. The sequential run stays the reference.

### O2 — Clear the search box only when it holds text

- **Duplicated work removed:** an `input` event on an already-empty box. It re-filters and
  re-renders 470 cards, 45 ms each time.
- **Where:** test-phase63's `FACT_JS`, app-reference's `DRAWER_JS` and `SEARCH_SET_JS` resets, and
  test-phase65's `ROW_JS`.
- **Why it is safe:** the reset exists so the estate's card is in the list. An empty box already
  gives the full list. Any search a check sets is still cleared.
- **Still exercised:** search itself is exercised by the 13 capture searches and the benchmark.
- **Saving:** ~12 s in test-phase63, ~1–3 s elsewhere.
- **Verification:**
  - test-phase63's 137-drawer texts byte-identical before and after;
  - `app-reference --compare` identical summary;
  - the control fixture's hashes unchanged.

### O3 — The browser driver closes without a fixed sleep

- **Duplicated work removed:** a 0.5 s sleep after Chrome exits, which gives Windows time to release
  the profile directory before `rmtree`.
- **Change:** retry the removal briefly instead.
- **Isolation preserved:** profiles are still removed.
- **Saving:** 15 × 0.5 = 7.5 s.
- **Verification:** no `bdx-bench-chrome-*` directories left after a full run (the 6.6A runner's
  temporary-directory check).

### O4 — The crawler honours the caller's `min_delay` (decision needed: crawler code)

- **Duplicated work removed:** 16 politeness sleeps against the test's own local server.
- **Why it is safe:**
  - apply the 1.5 s floor through `min_delay`, which defaults to `MIN_DELAY`, instead of inside
    `Robots.delay()`;
  - production uses the default, so its waits are unchanged;
  - a robots `Crawl-delay` above the floor is still honoured;
  - `record_block` keeps recording `r.delay()` as before, so discovery output does not change.
- **Still exercised:** the crawl, robots, validators, replaced documents and extraction are all
  unchanged.
- **Saving:** ~24 s (test-phase33: 35 → ~11 s).
- **Verification:**
  - test-phase33's 34 checks pass;
  - production default checked: `crawl_site` without `min_delay` still waits ≥ 1.5 s between requests;
  - a robots `Crawl-delay: 3` is still honoured.
- **Test-only alternative:** set `D.MIN_DELAY = 0` inside test-phase33. It would remove the floor
  only in the test, but it patches the unit under test. Rejected in favour of the crawler fix, or of
  no change.

### O5 — Frozen controls as stored fixtures (decision needed: control semantics)

- **Duplicated work removed:** re-rendering two frozen commits on every run.
  - test-phase63: `c775ea7`, 137 drawers and a capture, ~36 s;
  - test-phase65: `c15b421`, a page sweep and a phone load, ~9 s.
- **What would be stored:** like `tools/fixtures/app-reference.json`, the drawer texts, the
  capture's hashes, Compare's per-row values and the phone label-column width.
- **Trade-off:**
  - **For:** the controls are frozen by construction.
  - **Against:** a stored control must be re-captured whenever the capture definitions change. Phases
    6.3 and 6.5 both changed those definitions; a live re-render never goes stale.
- **Saving:** ~45 s.
- **Verification:** the stored fixture is generated from the same `site_at(commit)` the test uses
  today, and compared once with a live render before adoption.

### O6 and O7 — Deferred

- **O6, condition waits:** about 8–10 s, with a risk of flakiness under parallel load.
- **O7, in-suite memoization of model reads:** about 6–8 s, but it introduces a cache of mutable
  rows shared between checks.

Both are worth less than their risk at this point.

## 8. Rejected optimizations

| Optimization | Saving | Why not |
|---|---:|---|
| Lazy-import PyMuPDF in the reader | ~44 s | `sheetreader.py`'s bytes are the reader fingerprint pinned by the evidence checks; changing them changes the reader identity of every evidence decision |
| Uninstall `pymupdf_layout` | ~40 s | PyMuPDF imports it unconditionally and may use it in text extraction; removing it could change what the reader extracts. **This dependency is itself a finding:** the reader's output may depend on an optional installed package, which a later phase should verify. |
| Share captures or renders across suites (the current application captured once for test-phase5, 61 and 63) | ~33 s | a cross-suite cache: breaks the independence 6.6A established |
| Reuse one browser across test-phase65's checks | ~5 s | checks set device emulation, touch and focus; reuse would couple them |
| Sample fewer of the 137 drawers, or fewer searches | ~25 s | reduces coverage |
| Skip the scratch build, or reuse it for the rollback | ~12 s | they test different build paths; the agreement is the point |
| Mock the crawl in test-phase33 | ~30 s | it tests the real crawler end to end, by design |
| Render once in test-phase65's determinism check | ~2 s | rendering twice is the determinism test |

## 9. Expected savings

| Plan | Sequential (s) | vs 354.8 s |
|---|---:|---:|
| baseline | 354.8 | — |
| O2 + O3 (no decision needed) | ~333 | −6 % |
| + O4 (crawler decision) | ~309 | −13 % |
| + O5 (fixture decision) | ~264 | −26 % |
| O1 parallel, unchanged suites (measured) | **214.1** | **−40 %** |
| O1 + O2–O5 | ~150–170 (estimate) | about −52 % to −58 % |

## 10. Verification plan for Phase 6.6C

For every optimization:

1. **Counts:** 25 suites and 708 checks, unchanged; no check removed, skipped or loosened (diff
   review).
2. **Equal outputs:**
   - `app-reference` summaries identical before and after;
   - test-phase63's drawer texts byte-identical;
   - the control fixture's hashes unchanged;
   - test-phase33's temporary store contents equal apart from timestamps.
3. **Mutation checks still fail:** the 6.6A/6.5 practice. The page checks are run against the old
   application (`c15b421`) and must still fail where they did.
4. **Isolation:** the 6.6A runner, alone and in reverse order; no file, git or temporary-directory
   side effects.
5. **Production unchanged (O4):** crawler default delay ≥ 1.5 s, a robots `Crawl-delay` honoured,
   discovery outputs unchanged.
6. **Committed state:** all suites rerun after the commit (the 6.6A H1 lesson).
7. **Timing:** sequential and parallel wall clock reported against 354.8 s, three runs each.

**Decisions needed before 6.6C:**

- **O4:** may `tools/discover.py` apply its politeness floor through `min_delay`? Production
  behaviour is unchanged.
- **O5:** may the two frozen controls (`c775ea7` in test-phase63, `c15b421` in test-phase65) become
  stored fixtures, like the Phase 5 control?

O1, O2 and O3 need no decision.
