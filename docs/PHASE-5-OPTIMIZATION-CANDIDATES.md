# Phase 5 — Optimization candidates from the M0 baseline

**A decision document. Nothing here has been implemented.**

M0 (`docs/PHASE-5-BASELINE-BENCHMARK.md`, commit `e564eff`) measured the system. This document
turns those measurements into candidate optimizations: what each would gain, what it would touch,
and whether it is worth doing.

- **Gains:** a gain is an estimate derived from the measurements, labelled as such. No candidate was
  tried.
- **Extra measurements:** three questions needed figures the baseline did not have. They were measured
  read-only and are given in section 1.

## 1. Where the measured costs come from

| Cost (M0) | Breakdown (measured for this document) |
|---|---|
| Full suite 215 s; test-phase4 alone ≈ 84–104 s | `model_rebuilds_byte_for_byte_deterministic` 38.4 s (37 %) and `t31_migration_rolls_back_stage_by_stage` 33.6 s (32 %): together 69 % of test-phase4, five full model builds. The other 64 checks take 31.5 s. |
| Model rebuild 13.95 s; M2 6.3 s | M2 `documents()` 4.95 s (reads v4/v5 evidence, the 123 failures, 35,776 discovery locations, 29,517 discovery artifacts). M2 `legacy_estate_uses()` 2.29 s (reads all five evidence versions, 177,127 rows). One full parse of the evidence costs 2.0 s. It is parsed again in M4 (display names: all five versions) and M6 (evidence links: v4/v5): **the evidence is parsed about four times per build**. |
| App cold data loading 292 ms, 3.67 MB in 36 scripts | `fiches.js` 1.55 MB (40 %), `cuvees.js` 0.72 MB (18 %), `fiches-nl.js` 0.41 MB (10 %), `ratings.js` 0.20 MB, `app.js` 0.20 MB. **68 % of the startup bytes are vintage records** that are read only when an estate's drawer or a comparison opens. |
| Search 19–40 ms per keystroke | 19 ms even with **no** match (`zzqxv`): the floor is the redraw of the list and the map on every input event, not the matching. |
| Raw store 21.46 GB | 4.33 GB held both in the legacy folders and the blob store; 1.07 GB legacy files at several paths. |

## 2. Candidates

The ordering is by measured benefit over risk. "Invariant" names what a candidate would touch among
the things Phase 4 protects.

| # | Candidate | Expected gain (estimate) | Touches | Risk | Reversible | Recommendation |
|---|---|---|---|---|---|---|
| C1 | **Parse the evidence once per migration run** (one shared in-memory read for M2, M4, M6) | about 4–5 s of the 14 s rebuild (≈ 30 %); test-phase4 shortened accordingly, since it rebuilds five times | migration code only. Output must stay byte-identical, which `migrate.py --check` proves. | low | yes (a code revert) | **worth doing** |
| C2 | **Run each of test-phase4's two rebuild checks on fewer builds.** The determinism check builds twice (from scratch and from the registry). The rollback check builds three times. They could share one from-scratch build in a temporary directory. | ≈ 30–40 s of the 215 s suite | test code. Each property stays checked: determinism (scratch against committed bytes), registry reuse, rollback. | low–medium: this restructures a test, and the brief says "do not weaken tests". Each property must remain asserted. | yes | **worth doing, if you accept restructuring the test** |
| C3 | **Hard-link duplicate raw files** in the gitignored `sources/`. Identical bytes at two paths become one file with two names: the legacy copies of the 4,526 blobs where both are raw, and the 971 extra legacy copies. Every path and every byte stays readable. | up to ≈ 5.4 GB of disk (4.33 + 1.07). Blobs stored gzipped are not linkable to raw copies, so the real figure is lower and must be measured. | the raw store's physical layout (not its content or paths). `raw_store.locate` and every digest stay valid. | medium: a later write to one path would change both. The legacy crawlers write by replacing files, not in place, which must be confirmed first. | yes (copy back) | **worth considering**, given the 5.5 GB low point in Phase 4 |
| C4 | **Lazy-load the vintage records** (`fiches`, `cuvees`, `fiches-nl`): fetched when a drawer or comparison first needs them, not at startup | ≈ 2.7 MB less per cold start; data loading 292 → est. 100–120 ms, app ready 655 → est. 450–500 ms cold. Warm is already 148 ms from the service-worker cache. | the application's startup path and its offline behaviour; the service worker must still cache the files | medium: the app's code changes, and offline use must keep working | yes | **later**: this belongs with the D7 switch, when the page's data files are regenerated anyway |
| C5 | **Debounce the search input** (e.g. 100–150 ms), or redraw the map only when the result set changes | removes the 19–40 ms redraw from all but the last keystroke | the application's search behaviour | low, but a visible change | yes | **optional**: the cost is within a frame budget on this machine |
| C6 | Index estates by id in the app (`chateauById` is a linear scan) | microseconds to sub-microseconds | app code | low | yes | **not worth it**: every lookup is already ≤ 2 µs |
| C7 | Drop or compress repeated evidence (v5 repeats v4's verdict on 99.8 % of rows) | ≈ 39 MB in git | the evidence store | **forbidden**: append-only by design, and V1–V5 are protected | — | **do not** |
| C8 | Shrink the model's representation (fiche values 10.6× `fiches.js`; evidence links 20.7 MB of keys) | tens of MB in git; ≈ 0.2 s per full read | the Phase 3.4 contract and its identities | medium–high, for no measured runtime problem | — | **not worth it now** |
| C9 | Pack the 29,517 small extracted-text files | ≈ 65 MB lost to cluster rounding | local, gitignored discovery cache | low | yes | **not worth it**: 0.3 % of the raw store |

## 3. Recommendation

Do **C1** first. It is code-only and invisible in the output, and `migrate.py --check` and
`test-phase4` already prove it changes nothing. It also shortens every later rebuild and test run.

Then **C2**, on the condition that every property test-phase4 checks today is still asserted, one for
one. This is a restructuring of the test, not a weakening.

**C3** is a disk decision, not a performance one. It matters only if free disk becomes a constraint
again; it fell to 5.5 GB once. It needs a measurement of how many of the duplicates can actually be
linked, and a check that nothing writes into `sources/` in place.

**C4 and C5** change the application. They belong with the D7 switch, which already regenerates the
page's data files.

**C6–C9** are not worth doing on these measurements, and C7 is ruled out by the evidence invariants.

Each implemented candidate would be measured again with `tools/benchmark-phase5.py --only <family>`
against the M0 records.
