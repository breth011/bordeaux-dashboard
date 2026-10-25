# Phase 5 — Optimization candidates from the M0 baseline

**A decision document.** Sections 1–3 were written before anything was implemented; section 4 records what was implemented, measured and decided.

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

## 4. Results and decision

The selected C1–C3 optimizations were implemented and measured against the Phase 5 M0 baseline. The normalized model output, protected data, and application behavior remain unchanged.

### 4.1 Storage reduction was the largest practical gain

C3 reduced the physical size of the raw document store from **21.55 GB to 16.30 GB**, a reduction of **5.25 GB**. Free disk space increased from approximately **13.8 GB to 18.8 GB**.

The reduction was achieved by hard-linking files only where their content hashes proved them byte-identical. All source paths remain present, so the operation reduced physical duplication without removing source/location provenance.

In total:

* **5,379 paths** now share storage with an identical copy;
* these represent **4,639 duplicate groups**;
* every affected path was re-hashed after linking;
* no linked file changed content;
* an explicit `--revert` operation remains available.

The writers that could previously modify files in place were also changed so that they remove an existing file before writing. This prevents a future write from unexpectedly modifying another path through a hard link. A regression test protects this invariant.

This is therefore considered a safe storage optimization rather than an information-loss operation.

Two raw files were found whose current bytes no longer match any version recorded by the source list. These pre-existing anomalies were not altered. One is Domaine de Chevalier 2020 rouge, whose bytes correspond to material previously read by the reader; the other is Virginie de Valandraud, which was never read. Both remain preserved.

### 4.2 Rebuild performance improved substantially

C1 reduced model rebuild time from **13.95 s to 10.08 s**, a **28% improvement**.

The principal change was to avoid repeatedly parsing the evidence during migration. The previous process read the evidence approximately four times per rebuild. The optimized process reads it once and retains only the six fields actually required by the migration.

The evidence itself was not changed or discarded. This is an execution optimization only.

Rebuild peak memory increased from **424 MB to 646 MB**, approximately **52%**. This is recorded as a deliberate trade-off and remains well below the memory pressure initially encountered during the first implementation of C1.

The rebuilt model remains byte-identical to the committed model.

### 4.3 Test-suite performance also improved

C2 changed test-phase4 so that its two slowest checks share one complete model build rather than performing five separate builds.

The full suite improved from:

* **215 s → 177 s**
* approximately **18% faster**

Test-phase4 itself improved from:

* **84 s → 51 s**
* approximately **39% faster**

All existing checks remain active. The rollback and deliberate-corruption checks continue to detect the conditions they were designed to detect.

The first implementation placed the shared build inside the test process and raised peak memory to approximately 2.5 GB. The final implementation runs that expensive build in a separate process and releases the cache afterward.

The resulting full-suite peak memory is **1,463 MB**, compared with **1,184 MB** at M0, an increase of approximately **24%**.

This memory increase is accepted as a measured trade-off rather than treated as an unbounded optimization target. Future performance work must not assume that additional memory is free.

### 4.4 Deferred candidates

Two candidates were investigated but not selected:

**C4 — lazy vintage loading**

The baseline does not currently establish sufficient benefit to justify introducing the additional loading complexity. No implementation was made.

**C5 — search redraw**

The application currently redraws the list and map on every search input, producing approximately **19–40 ms per keystroke** in the baseline measurement.

This is a real user-facing optimization opportunity, but it was deliberately not combined with C1–C3. The application remains unchanged, and the original measurement remains the reference point for any future search optimization.

### 4.5 Overall decision

C1–C3 are accepted.

They improve the project in three different dimensions without changing its data meaning:

| Measure                |       M0 |        C1–C3 |       Change |
| ---------------------- | -------: | -----------: | -----------: |
| Model rebuild          |  13.95 s |  **10.08 s** |     **−28%** |
| Full test suite        |    215 s |    **177 s** |     **−18%** |
| Test-phase4            |     84 s |     **51 s** |     **−39%** |
| Raw document storage   | 21.55 GB | **16.30 GB** | **−5.25 GB** |
| Rebuild peak memory    |   424 MB |   **646 MB** |     **+52%** |
| Full-suite peak memory | 1,184 MB | **1,463 MB** |     **+24%** |

The storage reduction is the most consequential result because disk capacity had previously become an operational constraint. The rebuild and test-suite improvements are substantial secondary gains.

No evidence, provenance, canonical information, discovery information, or application behavior was sacrificed to obtain these improvements.

The remaining optimization candidates are therefore deferred rather than rejected. Their baseline measurements are preserved so that they can be reconsidered later on the basis of actual user impact.

### 4.6 Phase 5 direction

The project should not continue optimizing indefinitely before using the normalized model.

The next decision should be whether the already-proven application boundary can now be switched from today's legacy-shaped files to the generated normalized-model output.

Before that switch, the following must remain true:

* the normalized model rebuilds deterministically;
* the application dual-read equivalence remains established;
* protected data remains unchanged;
* C3's hard-link safety invariant remains tested;
* the known memory increase remains documented;
* the two pre-existing raw-file anomalies remain preserved;
* C4 and C5 remain explicitly deferred unless a later decision reopens them.

The purpose of the next stage should therefore be **production transition and application-source switch**, not another general optimization cycle.

### 4.7 Implementation record

The commits behind the figures above are `d6156e4` (C1), `f016f36` (C2), `1bfbe7f` (the memory fix for C1 and C2), `c780bbb` (C3) and `7359268` (the re-measurements). Every measurement is in `data/performance/benchmarks.jsonl`, and each run carries its commit. The C3 journal is the local file `sources/.link-journal.jsonl`.
