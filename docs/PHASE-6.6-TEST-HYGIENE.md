# Phase 6.6A — Test hygiene and baseline audit

Gate: **SAFE — PHASE 6.6A TEST HYGIENE VERIFIED — PERFORMANCE BASELINE ESTABLISHED**

This phase is an audit of the 25-suite test system before any performance work. No application code,
model, canonical data, evidence, provenance or generated data was changed. Four small test-hygiene
corrections were made (section 8). Each makes a test run what it claims to run, or clean up what it
creates; none weakens, skips or deletes a check.

## 1. Initial repository state

| | |
|---|---|
| Commit | `2db48a6` (Phase 6.5), equal to `origin/main` |
| Working tree | clean |
| Python | 3.12.10 (psutil 7.2.2) |
| Node | v24 (WinGet install, **not on PATH**: see 7.1) |
| Browser | headless Chrome through the DevTools protocol (`tools/benchmark-phase5.py`) |
| Suites | 25 (`tools/test-*.py`) |
| Checks, as reported at Phase 6.5 | 707 |
| Full-suite runtime | about 8 minutes (Phase 6.5 run, not separately timed) |

The 707 was **not reproducible at `2db48a6`**. test-phase65 failed one check once committed (section 3).

## 2. The Phase 5 anomaly

**The observation.** During Phase 6.5, `tools/test-phase5.py` reported
`switch_rollback_restores_the_legacy_source` (and `switch_outputs_agree_with_the_control`) failing,
with a summary naming Phase 6.5's classes.

**What the checks are.**

- **Where they live:** both are in `tools/test-phase5.py` (Phase 5 switch, commits `7db543e`/`0e7a2b0`).
- **What they load:** `tools/app-reference.py` (capture and compare), `tools/app-source.py` (the
  data-source switch), and the control fixture `tools/fixtures/app-reference.json`.
- **`switch_outputs_agree_with_the_control`** captures the running application and compares it with
  the control.
- **`switch_rollback_restores_the_legacy_source`** copies the **current** `index.html`, service worker
  and `assets/`, plus `data/` and `data/app/`, into a temporary site. It switches that copy to the
  legacy data source, compares with the control, switches back to the model, and compares again. A
  data-source rollback reverts the data, not the code, so running the current application code is
  what the check intends.
- **The control** is the application at `8b13cb0` (Phase 6.0) on the legacy source.
- **What may differ:** every presentation change made after Phase 5 is a legitimate difference
  between the current application and that control. Each must be named in the allow-list `PHASE61`
  in `test-phase5.py`.

**History.** The allow-list was extended by Phase 6.1 (`5ec94ff`), Phase 6.3 (`0f91279`) and Phase
6.5 (`2db48a6`), each adding its own classes. The 6.5 failure happened mid-phase: the new classes were
already produced by `app-reference.py` but not yet named in test-phase5's list. Naming them, in the
same commit, made both checks pass. That is the pattern the earlier phases used.

**Root cause.** It was not contamination. The checks deliberately compare current code against a
frozen control through an allow-list that every later phase must extend. The Phase 5 test is coupled
to later phases by design, and the 6.5 implementation had not yet extended it when the full suite
first ran. No Phase 6.5 class is imported: the classes are strings `app-reference.py` produces. The
legacy implementation the rollback needs still exists (`data/*.js`, `app-source.py --legacy`), and
the check exercises it.

**Order and isolation.** The anomaly is not order-dependent:

- `test-phase5` passes alone (43 s) at `2db48a6`;
- it passes in normal order and in reverse order, run after every other suite;
- each suite runs in its own process, so no module or global state is shared.

**Verdict.** Not a defect in the test or the control. It is a maintenance coupling, kept as finding
H3 with a recommendation (section 10).

## 3. Standalone suite results

Method:

- **One process per suite**, under a runner that records exit code, check count, wall time and the
  peak resident memory of the suite's whole process tree, Chrome included (polled every 100 ms).
- **Side effects** are recorded before and after each suite:
  - every file in the repository and in `sources/` (path, size, mtime; `.git` and `__pycache__`
    excluded);
  - `git status`;
  - new entries in the system temporary directory.

**First pass at `2db48a6`, before any correction:**

| Suite | Result | Wall (s) | Checks | Leaves behind | Depends on another suite? |
|---|---|---:|---:|---|---|
| test-data | pass | 3.8 | **10** (one check skipped, 7.1) | — | no |
| test-phase2 | pass | 6.3 | 30 | — | no |
| test-phase21 | pass | 5.5 | 27 | — | no |
| test-phase210 | pass | 6.3 | 23 | — | no |
| test-phase211 | pass | 4.9 | 11 | — | no |
| test-phase212 | pass | 4.8 | 14 | — | no |
| test-phase22 | pass | 2.6 | 17 | — | no |
| test-phase23 | pass | 2.9 | 47 | — | no |
| test-phase24 | pass | 6.9 | 26 | — | no |
| test-phase25 | pass | 8.3 | 48 | a `prov-*` temporary directory (7.3) | no |
| test-phase26 | pass | 2.8 | 61 | — | no |
| test-phase27 | pass | 4.3 | 16 | — | no |
| test-phase28 | pass | 5.4 | 17 | — | no |
| test-phase29 | pass | 2.8 | 47 | a `p29-*` temporary directory (7.3) | no |
| test-phase30 | pass | 5.9 | 26 | — | no |
| test-phase31 | pass | 5.1 | 29 | — | no |
| test-phase32 | pass | 4.6 | 45 | — | no |
| test-phase33 | pass | 35.7 | 34 | — | no |
| test-phase34 | pass | 3.8 | 46 | — | no |
| test-phase4 | pass | 52.7 | 66 | — | no |
| test-phase5 | pass | 42.5 | 25 | — | no |
| test-phase61 | pass | 18.2 | 10 | — | no |
| test-phase63 | pass | 74.7 | 11 | — | no |
| test-phase65 | **FAIL** | 40.1 | 20 (1 fail) | — | no (fails alone and in either order) |
| test-reader | pass | 3.9 | (1) | — | no |

**The test-phase65 failure (H1).** The failing check was `other_generated_files_byte_identical_and_deterministic`.

- **What it asserted:** `git diff --name-only c15b421 -- data/app` lists nothing.
- **Why it passed in Phase 6.5:** the suite ran before the commit. At that point
  `data/app/source-facts.js` was untracked, and `git diff` does not list untracked files.
- **Why it fails at `2db48a6`:** the committed file is listed as added, so the check fails.

The suite was therefore green only in the uncommitted working tree; at `2db48a6` the 25-suite run was
not green. This is a defect introduced by Phase 6.5. It is corrected in section 8 without weakening
the check.

**No suite depends on another.** None writes a file in the repository or in `sources/`, none changes
`git status`, and none needs another to have run first. Each is a separate process: environment
variables, the working directory and module state cannot leak between suites. The browser suites use
a fresh temporary profile each time. The runner did see one change during the reverse run: the edit
to `test-phase65.py` described in section 8, made while test-phase63 was running. It is not a side
effect of any suite.

## 4. Order independence

| Order | Total (s) | Pass | Fail | Differences from the other order |
|---|---:|---:|---:|---|
| normal (alphabetical) | 462.2 | 24 | 1 (test-phase65, H1) | — |
| reverse | 444.3 | 24 | 1 (test-phase65, H1) | none: same suites pass, same check fails with the same message, same check counts, same temporary leftovers |

Order does not change any result. Runtime varies by under 5 %.

## 5. Cross-phase dependencies

**What each suite claims as its baseline:**

- **Earlier phases:** test-phase212 (`2072abe`), 30 (`8964131`), 31 (`e100b25`), 32 (`a842bb7`),
  33 (`a112623`) and 34 (`b278121`) each name their own commit. They check that later commits did
  not touch their protected paths. None of them references anything later than its baseline.
- **Phase 4 onwards:** test-phase5 (`b1ce39b`), 63 (`c775ea7`) and 65 (`c15b421`) name theirs.

**The four suites that name later phases' work.** test-phase4, test-phase5, test-phase61 and
test-phase63 each carry lists of what later phases added:

| Suite | What it names from later phases | Why |
|---|---|---|
| test-phase4 (M12 boundary) | `figure-sources.js`, `second-status.js`, `source-facts.js` excluded from the 23 contract files | the M12 contract is 23 projected files; later generated files sit beside them |
| test-phase5 (`application_unchanged`, switch checks) | the same three files stripped from `index.html`/service worker; the `PHASE61` allow-list of 6.1/6.3/6.5 comparison classes | its checks compare the current application with the Phase 5 control |
| test-phase61 | the later files and classes | its value check compares with the same long-lived control |
| test-phase63 | `source-facts.js`, 6.5's classes | its checks compare with `c775ea7` |

**H3, a maintenance coupling.** These lists are not contamination:

- each names the specific later addition and nothing else;
- every unnamed difference still fails as UNEXPLAINED;
- no test's control is computed from current code.

But every phase that changes presentation must edit four files in step. Missing one is exactly how
the Phase 6.5 anomaly arose.

**No dynamic import of later implementation into a control.** The suites that build an older
application take it from git at a fixed commit (`git show <commit>:…` into a temporary site):

- test-phase63 (`c775ea7`);
- test-phase65 (`c15b421`);
- the control re-capture (`8b13cb0`).

## 6. Control fixtures

The repository has one explicit equivalence fixture, `tools/fixtures/app-reference.json`.

| Question | Finding |
|---|---|
| What it represents | the application at `8b13cb0` on the legacy data source |
| Is it frozen? | **In content, yes.** It was re-captured in Phases 6.1, 6.3 and 6.5. Each time the application files came from `8b13cb0` via git and the legacy data from the working tree (unchanged since Phase 4, which test-phase5 asserts). Across the three captures, the 260 raw outputs they share are identical: page texts, years, opened rows, globals, searches, lookups, data requests and health. Only the derived texts differ (`values`, `keep_*`), whose definitions each phase extended. |
| Does the test load the fixture, or current code? | The fixture is loaded as data. The comparison runs the current application against it, which is the intended direction. The capture code (`app-reference.py`) is current tooling, so a re-capture always uses the current definitions on the old application. |
| Can later files overwrite or shadow it? | Only an explicit `app-reference.py --capture`. No test writes it. |
| **H2, metadata** | The fixture's `commit` field records the repository HEAD at capture time (now `c15b421`), not the application captured (`8b13cb0`). The `_` note says "under the legacy source" but not which commit. This does not affect any result, but someone reading the fixture would be misled. Left unchanged: correcting it would mean editing the control (section 10). |

The other baselines are committed JSON, not equivalence fixtures:

- `data/model/baseline.json` (protected group digests);
- `data/model/checks/*.json` (Phase 4 reports).

The suites that use them read them only; test-phase4 builds its comparison models in temporary
directories and removes them.

## 7. File-system and isolation findings

### 7.1 A skipped check (H4)

test-data asks Node to parse every data and asset script. Node was looked up only on PATH
(`shutil.which`). Here Node is installed by WinGet and is not on PATH. The project's own tools find
it there (`tools/migration_lib.py` `node()`), but test-data printed `MISSING node not on PATH - the
full JavaScript parse is skipped` and reported **10 checks, all pass**.

The suite's coverage, and the 707, therefore depended on the shell's PATH, not on whether Node was
installed. Corrected in section 8.

### 7.2 What the suites write

| Suite | Writes | Where | Removed? |
|---|---|---|---|
| test-phase24 | an evidence store, a corrupted copy | temporary directory | yes |
| test-phase25 | a git repository, provenance runs | temporary directory | **no: `.git` left behind** (7.3) |
| test-phase26 | crawled pages | temporary directory | yes |
| test-phase29 | a copy of the old sheet reader from git | temporary directory | **no: never removed** (7.3) |
| test-phase33 | a local site, crawl store, extraction output | temporary directory | yes |
| test-phase4 | scratch model builds (child process); two model copies for rollback | temporary directories | yes |
| test-phase5 | a copy of the site switched to legacy and back | temporary directory | yes |
| test-phase63, test-phase65 | the application at an older commit | temporary directory | yes |
| browser suites | Chrome profiles | temporary directory | yes |

**Checked and found clean:**

- No suite writes to `data/app/`, `data/model/`, `data/`, `sources/`, fixtures or the service
  worker.
- No suite switches the repository's own data source; `app-source.py` is always given a temporary
  root.
- No suite sets environment variables for itself. `BDX_MODEL_DIR` is set only in the environment of
  a child process, pointing at a temporary model.
- Git is read, never written, except inside test-phase25's own temporary repository.
- The model rebuilds run with `--check`, or into temporary directories.

### 7.3 Temporary leftovers (H5)

**test-phase25:** its `rmtree(..., ignore_errors=True)` silently failed on git's read-only object
files on Windows.

**test-phase29:** never removed its directory.

Neither affects another suite, since the names are unique per run. They accumulate: 133 `prov-*` and
`p29-*` directories from earlier runs sit in the user's temporary directory. Corrected in section 8.
The existing leftovers are outside the repository and were not deleted.

## 8. Corrections made

Each correction was rerun alone and then within the full suite:

| # | File | Defect | Correction | Effect |
|---|---|---|---|---|
| H1 | `tools/test-phase65.py` | the "no existing generated file changed" check depended on whether its own new file was committed: it passed uncommitted and failed at `2db48a6` | compare with `--name-status`; the only allowed difference against `c15b421` is `data/app/source-facts.js` with status `A` (added); any other path, or that file modified, fails. Every existing file is still required byte-identical, and the generated output deterministic and equal to the model. | passes committed and uncommitted; no weaker |
| H4 | `tools/test-data.py` | the JavaScript parse check was skipped where Node is installed by WinGet | fall back to the WinGet location, as `migration_lib.node()` does | the check runs: "JavaScript files Node cannot parse: 0"; **11** checks (was 10) |
| H5 | `tools/test-phase25.py` | `.git` left in a temporary directory on every run | make read-only files writable before deleting (an `onerror` handler) | nothing left |
| H5 | `tools/test-phase29.py` | its temporary copy never removed | remove it after the last check that reads it (`inspect.getsource`) | nothing left |

No other file changed: application, model, data, fixtures and the other 21 suites are untouched.

## 9. Final clean baseline (Phase 6.6 performance baseline)

**Run conditions:**

- the corrections above in place, all other files at `2db48a6`;
- normal order, one process per suite;
- the same machine and runner as sections 3 and 4.

| Suite | Wall (s) | Peak tree memory (MB) | Checks |
|---|---:|---:|---:|
| test-data | 5.9 | 183 | 11 |
| test-phase2 | 4.8 | 827 | 30 |
| test-phase21 | 5.0 | 818 | 27 |
| test-phase210 | 5.0 | 374 | 23 |
| test-phase211 | 4.0 | 130 | 11 |
| test-phase212 | 4.2 | 299 | 14 |
| test-phase22 | 2.4 | 129 | 17 |
| test-phase23 | 2.4 | 151 | 47 |
| test-phase24 | 6.0 | 322 | 26 |
| test-phase25 | 7.6 | 163 | 48 |
| test-phase26 | 2.7 | 133 | 61 |
| test-phase27 | 4.6 | 344 | 16 |
| test-phase28 | 6.0 | 315 | 17 |
| test-phase29 | 3.0 | 172 | 47 |
| test-phase30 | 6.1 | 261 | 26 |
| test-phase31 | 5.1 | 167 | 29 |
| test-phase32 | 4.9 | 165 | 45 |
| test-phase33 | 35.8 | 291 | 34 |
| test-phase34 | 3.7 | 215 | 46 |
| test-phase4 | 52.8 | 1,331 | 66 |
| test-phase5 | 43.1 | 1,443 | 25 |
| test-phase61 | 17.9 | 1,381 | 10 |
| test-phase63 | 80.1 | 1,391 | 11 |
| test-phase65 | 43.4 | 1,301 | 20 |
| test-reader | 4.0 | 132 | 1 |
| **Total** | **360.5 s in suites** | **1,443 peak** | **708** |

**Wall clock.** The full run took 460.6 s. About 100 s of that is the runner's own before/after scans
of the repository and `sources/` (37,000 files, twice per suite). The suites themselves take 360.5 s.
A plain sequential run, without the scans, is about 6 minutes.

**Where the time goes:**

| Part | Seconds | Share of suite time | Note |
|---|---:|---:|---|
| browser suites (test-phase5, 61, 63, 65) | 184.5 | 51 % | headless Chrome sessions; test-phase63 alone opens all 137 drawers twice (old and current application) |
| test-phase4 | 52.8 | 15 % | model builds in a child process (scratch M0–M7, rollback rebuilds); a full `migrate.py --check` alone takes **18.6 s** |
| test-phase33 | 35.8 | 10 % | a crawl and extraction against a local server, with a 120 s budget |
| the other 20 suites | 87.4 | 24 % | 2.4–7.6 s each, mostly loading the legacy data and evidence |

**Building blocks, timed alone:**

| Step | Seconds |
|---|---:|
| `build-app-data.py --check` (generated-data preparation) | 2.4 |
| `migrate.py --check` (model rebuild) | 18.6 |
| `phase4-baseline.py --check` | 1.0 |

**Subprocess time:** the browser suites are dominated by the Chrome child processes, and test-phase4
by its build child. The runner does not separate a child's CPU time from its parent's.

**Memory:** the highest peak is test-phase5, 1,443 MB including Chrome. The data-loading suites
(test-phase2, test-phase21) peak around 820 MB without a browser.

## 10. Recommendation for Phase 6.6B (performance profiling)

The baseline is trustworthy:

- all 25 suites pass alone and in either order;
- none leaves state behind;
- none depends on another;
- the only control fixture is frozen in content.

**Profile in this order, by share of time:**

1. **The browser suites (51 %).**
   - Several start their own Chrome and load the app more than once. test-phase63 opens all 137
     drawers in both the `c775ea7` and the current application, and test-phase65 starts six
     separate browsers.
   - Measure page loads and drawer openings per suite before changing anything.
   - Any reuse of captures across suites would be a cache, and must preserve the property shown here:
     each suite independent and order-free.
2. **test-phase4's model builds (15 %).** Measure how many full builds it performs and whether
   Phase 5 C2's shared build still covers all of them.
3. **test-phase33 (10 %).** Its crawl has a fixed budget; measure how much of it is waiting.
4. **The 20 small suites (24 %).** Most re-parse the same legacy data; a per-process profile would
   show the parse share.

**Hygiene items to carry, not to fix in 6.6B:**

- **H3, coupled allow-lists.** test-phase4, 5, 61 and 63 must each be extended when presentation
  changes. A single named list of post-Phase-5 additions, in `app-reference.py` and imported by the
  four suites, would remove the failure mode behind the Phase 5 anomaly. That is a test-structure
  change, for a decision.
- **H2, the fixture's `commit` field.** It should name the captured application (`8b13cb0`), not the
  capture-time HEAD. This needs a one-line change in `app-reference.py --capture` and a re-capture.
- **Leftover directories.** The 133 directories from earlier runs can be deleted by hand; they are not
  in the repository.
- **Process lesson from H1.** A phase's suites must be run again **after** its commit. A check that
  reads git state can pass on an uncommitted tree and fail on the committed one.
