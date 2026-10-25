# Phase 6.6C — Test suite performance optimization

Gate: **SAFE — PHASE 6.6C TEST PERFORMANCE OPTIMIZED — HISTORICAL CONTROLS RETAINED**

The suite runs **19 % faster one suite at a time, and 38 % faster with the new runner's default of
two workers.** No test was removed or skipped, no assertion was weakened, and the checks stay at 25
suites and 708. The historical controls stay live: O5 was analysed and rejected (O5-A).

**No application, model, data or evidence file changed.** Seven tool files changed, one of them new.
Production crawler behaviour is unchanged, which was measured (section 5). The reader fingerprint
(`sheetreader.py`, `read-fiches.py`) is untouched.

## 1. Baseline

| | |
|---|---|
| Baseline commit | `f8deed8` (Phase 6.6B; the suite as at `d3643d4`) |
| Suites, checks | 25, 708 |
| Sequential | **354.8 s** (6.6B). This session's own sequential run, in Part A, took 373.1 s, so run-to-run and machine-load variance is about 5 %. |
| Peak memory | 1,443 MB (test-phase5 with Chrome) |
| Machine | 16 GB; 4.0–5.4 GB free when idle (other applications hold the rest) |

## 2. Worker benchmark (Part A)

The suites were unchanged, each in its own process, with the longest started first. Memory is the
peak sum over all suite processes and their children, Chrome included.

| Workers | Wall time | Checks | Pass/fail | Peak memory | Lowest free memory | Contention |
|---:|---:|---:|---|---:|---:|---|
| 1 | 373.1 s | 708 | 25/25 pass | 1,470 MB | 1,488 MB | — |
| 2 | 253.3 s, 251.7 s | 708 | 25/25, 25/25 | 2,697 / 2,763 MB | 1,324 / 1,590 MB | suites ×1.16–1.81 slower; total work ×1.35 |
| 3 | 225.2 s, 248.5 s | 708 | 25/25, 25/25 | 3,815 / 3,658 MB | 592 / 855 MB | ×1.34–2.66; total work ×1.81; **23 s apart between runs** |
| 4 | 219.7 s | 708 | 25/25 | 4,112 MB | **8 MB** | ×1.63–3.63; total work ×2.34; the machine nearly ran out of memory, so it was not repeated |

**Choice: 2 workers.**

- **Gain:** −32 %.
- **Reproducible:** within 1.6 s.
- **Memory:** at least 1.3 GB free throughout.

The alternatives:

- **3 workers:** saved at most 28 s more, varied by 23 s between runs, and left under 1 GB free.
- **4 workers:** added 5 s for an exhausted machine.

**Where contention lands.** test-phase4 suffers most (×1.81 at 2 workers, ×3.63 at 4). Its model
builds and reads compete for memory bandwidth and the disk.

**The runner.** `tools/run-tests.py` makes this the standard invocation. Each suite still runs in its
own process, so no state is shared.

- **Default:** `--workers 2`.
- **Reference run:** `--workers 1`, one suite after another.
- **Order check:** `--reverse`.

## 3. O2: the search box is cleared only when it holds text

**What changed.** Five places in the test tooling cleared the producers' search box before opening a
drawer: `app-reference.py`'s drawer capture, test-phase61's and test-phase63's drawer readings, and
three in test-phase65. Each did so with an `input` event even when the box was already empty, and the
app re-filters and re-renders all 470 cards for that event (45 ms, measured in 6.6B). They now do so
only when the box holds text:

```js
if (box.value !== '') { box.value = ''; box.dispatchEvent(new Event('input')); }
```

**What is unchanged:**

- The box is empty before every reading, as before, so the list holds every estate.
- The search captures still type their 13 queries and clear the box after each one; that box is not
  empty, so the reset still runs.
- The benchmark's own search measurement (`benchmark-phase5.py`) is untouched.
- test-phase63 still opens all 137 drawers, in both the `c775ea7` and the current application.
- All its checks, and both captures, remain.

**Result.** The four suites that read drawers went from 172.5 s to **151.4 s (−21.1 s)**:
test-phase63 74.4 → 55.9 s, test-phase65 42.8 → 38.8 s, test-phase61 17.3 → 16.8 s. test-phase5's
+1.9 s is noise. Every result is as before; `app-reference --compare` gives the same summary
(section 10).

## 4. O3: the browser driver waits for Chrome, not for a fixed time

**What changed.** `Browser.__exit__` in `tools/benchmark-phase5.py` slept 0.5 s after Chrome's main
process exited, before removing the temporary profile directory.

**Measured first:** in 15 closes,

- the main process exited in 0.12–0.21 s;
- of its 10 child processes, one (Chrome's crash handler) outlived it, by under 1 ms;
- an immediate `rmtree` removed the profile every time;
- nothing leaked.

The driver takes no screenshots, so nothing needed persisting. The sleep was therefore not a required
synchronisation point.

**The replacement** is not a shorter sleep but the actual condition. The driver records Chrome's
child processes before closing, waits for exactly those to exit (`psutil.wait_procs`, timeout 10 s),
then removes the profile.

**Result.** The four browser suites went from 151.4 s to **147.2 s (−4.2 s)**. That is within noise
of the 7.5 s that 15 removed sleeps would give.

**Temporary directories.** No `bdx-bench-chrome-*` profile was left after any run, sequential or
parallel. During the parallel runs Chrome itself occasionally left one empty
`chrome_chrome_url_fetcher_*` directory. In probes with 2 × 15 parallel launches per batch, two
batches on each driver, neither driver (`f8deed8`'s sleep, or the new wait) added any. The next
Chrome start removes the stale one, so at most one exists at a time. This is Chrome's own housekeeping
and does not depend on O3.

## 5. O4: the crawler honours an explicit `min_delay`; production keeps its floor

**The defect (6.6B).** test-phase33 crawls its own local server with `crawl_site(...,
min_delay=0.0)`. But `Robots.delay()` contained the production floor (`max([MIN_DELAY] + ...)`, with
`MIN_DELAY = 1.5`), so the explicit 0.0 had no effect. 16 requests waited 24 s.

**The change** (`tools/discover.py`):

- **`Robots.site_delay()`, new:** the longest Crawl-delay robots.txt names for the crawler, or 0.0.
- **`Robots.delay()`:** now `max(MIN_DELAY, site_delay())`. It is the same value as before, and it is
  what the profiles and block records report, so recorded output is unchanged.
- **The crawl loop** waits `max(r.site_delay(), self.min_delay)` (it was
  `max(r.delay(), self.min_delay)`). `min_delay` defaults to `MIN_DELAY`, and every production call
  (`crawl_site(store, d)` in `main`) uses the default, so production waits exactly as before.
- **The difference is explicit** in the code and in the module's access rules: a test crawling its
  own local server may lower the floor; production never does.

**Verified (scratch probes, not committed):**

| Case | Gap between requests |
|---|---:|
| production default, no Crawl-delay | 1.50–1.52 s, unchanged |
| production default, robots `Crawl-delay: 3` | 3.00–3.02 s |
| explicit `min_delay=0.0`, robots `Crawl-delay: 3` | 3.00–3.02 s (a site's own delay is never overridden) |
| explicit `min_delay=0.0`, no Crawl-delay | 0.00–0.03 s |

**The same crawl.** test-phase33 was run once with `f8deed8`'s crawler and once with the new one, with
every `fetch()` recorded:

- **Requests:** the same 22, in the same order, with the same headers. No request was skipped.
- **Checks:** the same 34 pass. The only text difference is the print order of a Python set.
- **Sleeps:** the crawler's 16 sleeps (23.97 s) became none.

**Result.** test-phase33 went from 35.4 s to **11.2 s (−24.2 s)**.

## 6. O5: historical-control analysis (Part E)

**The controls examined:**

- test-phase63 against `c775ea7`, the application before Phase 6.3;
- test-phase65 against `c15b421`, the application before Phase 6.5.

| Question | Finding |
|---|---|
| 1. What is captured from the historical application? | `site_at(commit)` writes that commit's `index.html`, service worker, `assets/` and `data/app/` from git into a temporary site; the legacy `data/*.js` are copied from the working tree. Both are served and driven in Chrome. **test-phase63:** each of 137 estates' drawers (text without the second-wine row, the row's label and text), and an `app-reference` capture (searches, lookups, 13 drawers). **test-phase65:** the drawers' source marks for six cases, Compare tables for five estates, the website title per tag, the sparse notice, and the phone label-column width. |
| 2. What is compared with the current application? | The same readings, made the same way on the current application: drawer text equal except the row the phase changed, capture classes within the named set, Compare values equal, sheet-row links equal, the label column no wider. |
| 3. Which current code paths are exercised? | On **both** sides: the measuring code (`FACT_JS`, `DRAWER_JS`, `ROW_JS`, `CMP_JS`, `app-reference`'s capture and compare), the browser driver, and the Chrome actually installed. On the historical side: the old commit's `app.js` rendering today's legacy data. |
| 4. What would stop being tested with a stored fixture? | **The symmetry of the measurement.** The live control reads the old application with the same, current code and browser as the new one, so a change to the measuring JavaScript, the driver or Chrome applies to both sides. A stored fixture is read once, in the past. Phases 6.3 and 6.5 both changed the measuring definitions. Each time, the live controls stayed comparable without any action, while the Phase 5 stored fixture had to be re-captured. **And the old code against today's data:** the live control renders `c775ea7`'s code on the current legacy data. A fixture would fix the data at capture time. |
| 5. Could a stored fixture preserve the guarantee? | Only with a check that the fixture still equals a live render of the old commit under the current measuring code. That check is the ~45 s the fixture was meant to save. Without it, the fixture is an unverified golden file. |
| 6. Would it need a commit identifier? | Yes. The application commit, the measuring-code version, and ideally the Chrome version. Phase 6.6A found that the existing Phase 5 fixture's `commit` field already records the wrong commit (H2), which shows how easily this drifts. |
| 7. How would it be regenerated? | An explicit capture command, run whenever the measuring code changes. That is a manual step every presentation phase must remember, the same failure mode as the four allow-lists (6.6A, H3). |

## 7. O5 decision (Part F)

**O5-A: the live historical controls are kept.**

The controls prove that the current application reproduces the historical application's behaviour,
measured the same way, on the same data, in the same browser. A stored fixture cannot preserve that
without re-rendering the historical application, which removes the saving. The ~45 s is rejected,
because the live control has the higher evidentiary value.

## 8. Incremental timings (Part G)

Each optimization was timed on the suites it affects, just before and just after it was applied, in
the same conditions:

| Stage | Measured on | Before | After | Saving | Checks |
|---|---|---:|---:|---:|---:|
| Baseline | full suite, sequential | — | 354.8 s | — | 708 |
| Parallelism, unchanged suites | full suite, 2 workers | 354.8 s / 373.1 s | 253.3 s, 251.7 s | −101.5 s / −121.4 s | 708 |
| O2 | test-phase5, 61, 63, 65 | 172.5 s | 151.4 s | **−21.1 s** | 66 in those suites |
| O3 | test-phase5, 61, 63, 65 | 151.4 s | 147.2 s | **−4.2 s** | 66 |
| O4 | test-phase33 | 35.4 s | 11.2 s | **−24.2 s** | 34 |
| O5 | — | — | — | rejected (O5-A) | — |

The three stage savings sum to **−49.5 s** for a sequential run. The final sequential run (section 9)
came in at 286.9 s, 67.9 s under the 6.6B baseline. The 18 s beyond the summed savings is machine
variance: this session's own baseline ranged 354.8–373.1 s, and the idle machine had more memory
free during the final runs (5.4 GB against 4.0 GB).

## 9. Final timing

All runs were made **at the committed state** (`b418f3a`) with `tools/run-tests.py`:

| Run | Wall | Checks | Result | Peak memory |
|---|---:|---:|---|---:|
| sequential, normal order | **286.9 s** | 708 | all pass | 1,444 MB |
| sequential, reverse order | 282.6 s | 708 | all pass | 1,448 MB |
| 2 workers (recommended), run 1 | **218.3 s** | 708 | all pass | 2,557 MB |
| 2 workers, run 2 | 222.9 s | 708 | all pass | 2,662 MB |

**Against the 354.8 s baseline:**

- **sequential:** −67.9 s (**−19.1 %**);
- **2 workers:** −136.5 s (**−38.5 %**), and −30 to −34 s against the unchanged suites at 2 workers.

## 10. Check-count comparison

| | Before | After |
|---|---:|---:|
| Suites | 25 | 25 |
| Checks | 708 | 708 |
| Checks removed, skipped or loosened | — | 0 |

**test-phase65's touch check:** the only test logic that changed beyond O2's resets.

- **The failure:** in the first pre-commit run at 2 workers it failed. It read the button's position
  after a fixed 0.5 s sleep while the drawer's 0.2 s slide-in could still be running under load, so
  the tap landed where the button had been.
- **The fix:** it now waits for the conditions. The drawer's transform has finished and the target's
  position is stable before tapping, and the tap's effect (summary open or closed) is reached after
  it, each with a 10 s timeout.
- **The assertions are unchanged:** a tap that does nothing still fails.
- **Confirmed:** it passed twice alongside the three heaviest suites (four at once, harsher than two
  workers) and alone, and in all four final runs.

**The other integrity checks:**

- `build-app-data --check`: data/app is the model, byte for byte.
- `migrate --check`: the model rebuilds byte for byte.
- `phase4-baseline --check`: unchanged.
- `app-source`: model.
- `app-reference --compare`: the same summary as at Phase 6.5's committed state (10,736 identical,
  the named classes, 0 unexplained).

## 11. Memory comparison

| | Peak |
|---|---:|
| Baseline, sequential | 1,443 MB |
| Final, sequential | 1,444–1,448 MB, unchanged |
| Final, 2 workers | 2,557–2,662 MB; with about 5.4 GB free when idle, the margin stays above 1.3 GB |

## 12. Isolation results (Part H)

Every final run was checked before and after for:

- every file in the repository and `sources/` (path, size, mtime);
- `git status`;
- new entries in the temporary directory.

| Run | Files changed | git status | Temporary entries left |
|---|---:|---|---|
| sequential, normal | 0 | unchanged | none |
| sequential, reverse | 0 | unchanged | none |
| 2 workers, run 1 | 0 | unchanged | one empty `chrome_chrome_url_fetcher_*`, Chrome's own, since removed by Chrome (section 4) |
| 2 workers, run 2 | 0 | unchanged | the same kind, one |

**Order.** Normal and reverse order give the same results. Parallel execution is not hiding an order
dependence: the reverse sequential run passes, and 6.6A ran every suite alone in both orders. The one
failure parallelism did expose, the touch check's fixed sleep, was a real timing assumption, now
replaced by condition waits.

## 13. Rejected optimizations

| Optimization | Saving | Why not |
|---|---:|---|
| O5, stored historical controls | ~45 s | weakens what the control proves (sections 6 and 7) |
| 3 or 4 workers | 5–28 s more | unstable times, under 1 GB or 8 MB free |
| a shorter fixed sleep in the driver | — | O3 replaced the sleep with the actual condition |
| testing O4 through the test alone (`D.MIN_DELAY = 0` in test-phase33) | same | it would patch the unit under test; the crawler now states the distinction itself |
| everything rejected in 6.6B | | lazy PyMuPDF import (reader fingerprint), uninstalling `pymupdf_layout`, cross-suite sharing, browser reuse across checks, fewer drawers, mocking the crawl, skipping the scratch build |

## 14. Remaining performance opportunities

| Opportunity | Estimate | Note |
|---|---:|---|
| condition waits for the other fixed sleeps in the browser suites | ~8–10 s | the touch check shows the pattern, and that fixed sleeps are fragile under load |
| in-suite memoization of committed-model reads in test-phase4 | ~6–8 s | a cache of rows shared between checks; needs care that no check mutates them |
| PyMuPDF's unconditional layout import, ~1.7 s per process | ~44 s | blocked by the reader fingerprint; and whether the reader's extraction depends on that optional package should be verified in its own right |
| test-phase4 under contention (×1.81 at 2 workers) | — | memory and disk bound; would gain from fewer model re-reads |
| one shared list of post-Phase-5 additions (6.6A H3) | — | not runtime, but removes the failure mode that started 6.6A |
