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

## 4. Implemented: C1, C2, C3 (chosen 2026-10-25)

You chose C1, C2 and C3; C4–C9 were not implemented. Each was measured again with
`tools/benchmark-phase5.py`. The new runs are appended to `data/performance/benchmarks.jsonl`, and each
carries its own commit.

| Measure | M0 (`b1ce39b`) | After (`c780bbb`) | Change |
|---|---:|---:|---:|
| Model rebuild, from scratch | 13.95 s | **10.08 s** | −28 % |
| Rebuild peak memory | 424 MB | 646 MB | +52 % |
| Full suite (21 suites, 641 checks), cold / warm | 215.2 / 211.1 s | **176.9 / 175.6 s** | −18 % |
| test-phase4 alone | 83.7 s | 50.9 s | −39 % |
| Full suite peak memory | 1,184 MB | 1,463 MB | +24 % |
| Raw store, physical (a linked file counted once) | 21.55 GB | **16.30 GB** | −5.25 GB |
| Free disk | 13.8 GB | 18.8 GB | +5.0 GB |
| Model output | — | byte-identical | unchanged |

**C1, parse the evidence once** (`d6156e4`, memory fix `1bfbe7f`).

- `migration_lib.evidence()` parses each evidence file once per process.
- It keeps only the fields the migration reads (artifact, ctx, read, v, code, manifest_sha1).
- Stage M4 went from 1.68 s to 0.08 s, and M6 from 1.68 s to 0.66 s.
- The first version kept whole rows and raised a build's peak to 999 MB. Keeping the fields alone
  brought it to 646 MB.
- That is the trade: 3.9 s per build for about 220 MB more peak memory.

**C2, share the builds in test-phase4** (`f016f36`, memory fix `1bfbe7f`).

- One from-scratch build, rendered at M6 and at M7 (`migrate.snapshots`), serves both the
  determinism check and the rollback check. Before, they ran five full builds between them.
- Every property is still asserted:
  - the scratch build at M7 equals `data/model/`;
  - a registry rebuild to M6 (the rollback's revert) equals the scratch build at M6;
  - reverting to M1 leaves only the manifest;
  - no protected group changes.
- A probe that altered one byte of a copy of the model was caught.
- Building in the test's own process doubled its peak (2.5 GB), so the build runs in a child, and the
  evidence cache is dropped after use.

**C3, hard links in the raw store** (`c780bbb`).

- `tools/link-duplicates.py` hashed 5,620 candidate files itself and linked 5,379 paths in 4,639
  groups. They are legacy files at several paths, and legacy files whose bytes are also a raw
  discovery blob.
- Every linked path was re-hashed against its pre-link hash: none differs.
- Each change is recorded in the local journal `sources/.link-journal.jsonl`;
  `python tools/link-duplicates.py --revert` gives each path its own copy again.
- The five write sites in `add-sheet.py`, `harvest.py` and `crawl-pages.py` used to write into
  existing files. They now remove the file first, so a write can never change a linked twin.
- A linked path now carries its keeper's timestamps.
- Found on the way, and pre-existing: two linked paths hold bytes that match no manifest version.
  - Domaine de Chevalier 2020 rouge equals what the reader hashed in v4/v5.
  - Virginie de Valandraud was never read.

**Unchanged:** canonical data, evidence, discovery data, scope, the Phase 3.4 contract, the proposal
records, the normalized model and the application (`test-phase5`, 18 checks). The startup, search and
lookup figures stand as in M0, because the application did not change.
