# Phase 2.7 — V4 evidence

**V4: COMPLETE.** 40,772 decisions and 123 typed provenance failures.
Every decision is tied to the bytes it read, the reader that decided and
a clean commit. An exact rerun added 0. v1–v3 are unchanged, and no
canonical file was touched.

2026-10-24.

---

## The v4 run

| | |
| --- | --- |
| reader fingerprint | `c12eb3102b45`: the Phase 2.6 reader, from `evidence.reader_fingerprint()` (SHA-1 of `sheetreader.py` + `read-fiches.py`) |
| decider version | 4: `DECIDER_VERSION` in `evidence-wines.py` and `recharacterize.py` (commit `e64184b`) |
| commit | `61f17e990ee57c9679f695563ceb689c0a72a7e9`, recorded in every row as `git.commit`, with `git.dirty: false` |
| run | `evidence-wines.py --write`, then `recharacterize.py --write`; no `--allow-dirty` |
| decisions | **40,772** (39,510 + 1,262); one file, `decisions-v4.jsonl`, 39.3 MB |
| provenance failures | **123** in `provenance-failures-v4.jsonl`: 103 `ARTIFACT_NOT_FOUND`, 20 `ARTIFACT_NAME_MISMATCH`; no ambiguity, no unreadable file, no read race |
| store after v4 | 136,355 decisions: v1 13,065 · v2 41,259 · v3 41,259 · v4 40,772 |

**By target role:**

| role | decisions |
| --- | ---: |
| grand vin | 14,134 |
| second wine | 8,189 |
| other cuvée | 18,449 (no reader mode: `GUARD_HAS_NO_CUVEE_MODE`) |

**Coverage:**

- 39,864 decisions with a target vintage, 908 without;
- 39,510 on attributed artifacts, 1,262 on unattributed ones (folder
  estate as a hypothesis).

### Getting to a clean run

v4 needed two commits before it could run from a clean tree:

1. **`e64184b`: the version bump.** v3 → v4 in the two runners and
   nothing else, committed so the commit that ran holds the code that
   decided.
2. **`61f17e9`: a provenance fix found by the first attempt.** The
   evidence store lives inside the repository, so once `evidence-wines`
   had written, `recharacterize` saw a dirty tree and refused to run.
   No exact rerun could have started clean either.

   `git_state()` now leaves `data/evidence/` out of the dirty check. It
   is a run's output, and no verdict reads it. Two regression checks
   were added to `test-phase25.py`.

   The partial output of that first attempt was never committed and was
   discarded, so all of v4 comes from one commit.

## Idempotence

The same two commands were run again from the same commit, with nothing
changed in between:

| | appended | already recorded |
| --- | ---: | ---: |
| `evidence-wines.py --write` | **0** | 40,037 |
| `recharacterize.py --write` | **0** | 1,262 |

The failure file stayed at 123 rows, and `verify()` is clean.

40,037 is more than the 39,510 written, because 527 questions in the
first run were asked twice: the manifest holds duplicate rows. The
store wrote each identity once, within the batch as well. v4 has 0
duplicate identities, where v3 has 527.

## V3 → V4

v4 changes two things at once: the reader (Phase 2.6) and file
resolution (Phase 2.5). They are separated using Phase 2.6's dry run,
which ran the *old* reader on the *right* files:

- old reader, right file: the provenance effect alone;
- new reader, right file: the reader effect.

`tools/compare-v4.py --write` writes `data/v3-v4-comparison.jsonl`.

| contexts | n | share |
| --- | ---: | ---: |
| same context in v3 and v4 | 40,726 | |
| … unchanged verdict | 40,594 | 99.7% |
| … changed verdict | 132 | 0.3% |
| … reason-only change | 0 | |
| in v3 only (no longer asked) | 6 | |
| in v4 only (newly asked) | 46 | |

Every one of the 132 changes is a **reader** effect. **The provenance
correction changed no verdict.** It did change *which questions were
asked*. The 6 + 46 contexts that exist in only one version are all on
the wrong-folder pages: La Mission's crawled pages, which v3 read from
Haut-Brion's same-named copies, plus one each at La Tour Figeac and
Haut-Bailly. Candidate vintages come from a document's text, so reading
the right file asks about different years.

| transition | n |
| --- | ---: |
| REFUSED → a different refusal | 70 |
| REFUSED → ACCEPTED | 31 |
| UNRESOLVED → REFUSED | 25 |
| ACCEPTED → REFUSED | 4 |
| ACCEPTED → UNRESOLVED | 2 |

## Grand vin

**14,123 contexts in both versions, 0 changed.** This matches Phase
2.6's dry run (13,999 contexts there, counted before the 123
provenance failures and duplicate rows were removed). The `"et"` bug in
`is_second_wine` is still present on purpose, and v4 reflects it.

## Second wines

| | v3 | v4 |
| --- | ---: | ---: |
| contexts | 8,181 | 8,189 |
| accepted | 1,090 | **1,115** |
| unresolved (NOT_IDENTIFIED, AMBIGUOUS) | | 1,795 |
| UNLISTED_WINE | — | 97 |

Same contexts:

| | n |
| --- | ---: |
| acceptances withdrawn | 6 |
| acceptances added | 31 |
| refusal → other refusal | 95 |
| refusals unchanged | 6,964 |

**The six withdrawn.** All five known bad cases are here, and Haut-Bailly
II is refused:

| estate | asked as | vintage | document | v4 | why |
| --- | --- | --- | --- | --- | --- |
| Latour-Martillac | Lagrave-Martillac | 2020 | `2020__agrave-martillac-blanc-2020-lacroix-martillac-rouge-2019-min.txt` | AMBIGUOUS_WINE | the address names Lacroix-Martillac as well as the second wine |
| Latour-Martillac | Lagrave-Martillac | 2019 | the same page | AMBIGUOUS_WINE | the same |
| Caillou | Les Erables de Caillou | 2023 | `Fiche-technique-FR-MURETS-BLANCS-2023-…pdf` | UNLISTED_WINE | the title names LES MURETS DE CAILLOU, a wine the list does not hold |
| Pédesclaux | Fleur de Pédesclaux | 2025 | `FT-PEDESCLAUX-2025_FR_compressed.pdf` | IS_GRAND_VIN | "premier et second vin" is not a claim to be the second wine; the filename names the grand vin |
| Haut-Brion | Le Clarence de Haut-Brion | 2019 | `2019__…la-chapelle-de-la-mission-haut-brion2019.txt` | UNLISTED_WINE | the address names La Mission Haut-Brion |
| Haut-Bailly | La Parde de Haut-Bailly | 2019 | `fiche-technique-hb-ii-2019.pdf` | WRONG_WINE | the document is Haut-Bailly II's, which the data lists apart from La Parde |

In v3 every one of them was accepted on the generic "second vin" phrase,
or on a URL naming the second wine. That told v3 only that the document
concerned some second wine, not which one.

**The 31 added** are second-wine sheets v3 refused as the grand vin's:

- Les Hauts du Tertre: 17;
- La Bastide Dauzac: 13, filed as `LABASTIDE-DAUZAC`;
- Haut de Carles: 1.

## Echo

From the v4 evidence itself: Lynch-Bages documents asked as the Echo,
labelled by word containment exactly as `diagnose-second-mode.py`
labels them.

| document | distinct documents | accepted for some vintage |
| --- | ---: | ---: |
| Echo | 64 | **64** |
| grand vin | 103 | **0** |
| Blanc | 52 | **0** |

- **Echo contexts:** 75. 64 are accepted; 11 are WRONG_VINTAGE, an Echo
  sheet of one year asked about another.
- **Why Phase 2.6 said 71 / 110 / 53.** Its diagnosis counted manifest
  *rows*, and these include duplicate rows. The distinct documents are
  64 / 103 / 52.

**The five missing vintages:**

| vintage | v4 Echo result | manifest changed |
| --- | --- | --- |
| 2008 | accepted: Echo-de-Lynch-Bages-2008-EN, -CN | NO |
| 2009 | accepted: Echo-de-Lynch-Bages-2009-EN, -CN, -FR | NO |
| 2010 | accepted: Echo-de-Lynch-Bages-2010-EN, -CN, -FR | NO |
| 2015 | accepted: Echo-de-Lynch-Bages-2015-EN, -CN, -FR | NO |
| 2016 | accepted: Echo-de-Lynch-Bages-2016-EN, -CN, -FR, Echo-Lynch-Bages-2016-FT-FR-C0888 | NO |

In each year the year's own Echo sheets are accepted. The other
contexts in those years are other years' sheets, refused for the wrong
vintage. The 50 Echo corrections were not applied.

## Provenance

| | |
| --- | --- |
| manifest rows read from another folder by v1–v3 | 917 (869 same bytes, 48 different) |
| v4 contexts on the 48 different-bytes artifacts | 278 |
| … `read.sha256` equal to the actual hash in the Phase 2.5 audit | 278 of 278 |
| … verdict changed from v3 | **0** |
| missing files | 103 `ARTIFACT_NOT_FOUND` |
| case-only / trailing-dot name mismatches | 20 `ARTIFACT_NAME_MISMATCH` |
| ambiguous files | 0 |
| read/hash races | 0 |
| stale manifest hashes (manifest sha1 ≠ bytes at the right path) | 240 of 12,909 (Phase 2.5 audit). v4 keeps the claim as `manifest_sha1`, beside `read.sha256` |

Per-artifact paths and hashes (old path and hash, v4 path and hash) are
in `data/provenance-audit.jsonl`. Each v4 row carries its own `read`.

Even read from the wrong folder, the reader came to the same verdict.
The same-named crawled pages are usually the same kind of page from a
sister site. What the correction changed is which vintages were asked
about (above). Until v4, nobody could have known that it changed
nothing else, because v1–v3 recorded the manifest's hash and not the
bytes.

## Attribution

`tools/attribute.py` rerun without `--write`. The result is **identical**
to the committed `data/attribution-candidates.jsonl`:

| state | n |
| --- | ---: |
| CANDIDATE | 444 |
| HIGH_CONFIDENCE | 244 |
| CONFLICT | 95 |
| REJECTED | 76 |
| UNRESOLVED | 49 |
| **unattributed artifacts** | **908** |

Attributed artifacts: 12,124 manifest rows carry an estate. None of
these is a canonical change, and the 908 remain an evidence/corpus
problem.

## Conflicts

**The established field-conflict model could not be run.** It needs
`--apply`, which writes canonical data. `conflicts.py` is fed by
`read-fiches.py`, and `read-fiches.py` calls `conflicts.note()` only
after its dry run has returned (lines 717 and 848, after the return at
line 634). The comment at line 634 says the opposite. A full dry run in
this phase confirmed it: nothing canonical was written, and
`data/field-conflicts.jsonl` was not created, because nothing had been
collected. So Phase 2's claim that field conflicts are recorded without
`--apply` was wrong. It is recorded here as a defect, not fixed:
`read-fiches.py` is not evidence tooling.

**Conflicts in the v4 evidence itself** come from
`tools/conflicts-v4.py --write`, which writes
`data/v4-identity-conflicts.jsonl`. A conflict is one document accepted
for more than one target. Every accepted target is kept; none is chosen.

| relation | v4 | v3 |
| --- | ---: | ---: |
| documents in conflict | **312** | 304 |
| SEVERAL_VINTAGES (accepted for more than one vintage of a wine) | 303 | 303 |
| GRAND_AND_SECOND (accepted as both, same vintage) | **8** | 1 |
| SEVERAL_ESTATES | 1 | 1 |

**By estate:**

| estate | documents in conflict |
| --- | ---: |
| bourgeois-chateau-de-braude | 50 |
| bourgeois-chateau-mongravey | 42 |
| stem-chateau-de-ferrand | 18 |
| palmer | 12 |
| la-mission-haut-brion | 11 |
| haut-brion | 9 |
| de-pressac | 9 |
| du-tertre | 8 |
| latour-martillac | 8 |
| malartic-lagraviere | 8 |

The de Braude and Mongravey documents are the crawler pattern Phase 1
found. By wine, the leaders are the same estates' grand vins.

**By vintage:** mostly 2010s (265) and 2020s (233), with a tail back to
the 1900s, mostly on multi-vintage history documents.

- **New in v4: 8 documents. Gone: 0.** None of the new conflicts is on
  a document v3 read from another folder. **The corrected provenance
  caused no new conflict.**
- **All 8 new conflicts are Les Hauts du Tertre sheets**, now accepted
  as Château du Tertre's second wine, and still accepted, as in v3, as
  its **grand vin**. The cause is a grand-vin guard defect that v4
  exposes rather than introduces. Without siblings, `mark_of("Les Hauts
  du Tertre", "Château du Tertre")` drops "hauts" as a common word and
  leaves `les du tertre`. Those words never appear in that order, so
  the grand-vin guard cannot see the second wine. It is the Phase 2.3
  defect B class; its sibling-aware fix is used only in second-wine
  mode. `whose_sheet(Hauts-du-Tertre-2017-FT-FR.pdf, year=2017)` as the
  grand vin returns None (accepted). Not fixed here: no reader changes
  in this phase.

## Decision-history integrity

- **v1, v2, v3 unchanged.** Their parts in `index.json` are identical to
  `ddf5d19` (hash, rows, bytes), and `verify()` re-hashes every file.
- **v4 appended separately**, as `decisions-v4.jsonl`. No historical row
  was deleted and no historical verdict rewritten.
- **v4 uses the new schema:** `read`, `git`, `manifest_sha1`; none of
  the v1–v3 fields `observed` and `commit`.
- **v4 can be queried alone:** `evidence_store.iter_rows([4])`.

## Tests

| suite | result |
| --- | --- |
| reader | all pass (110 ok) |
| data | 11 pass |
| Phase 2 | 30 pass |
| Phase 2.1 | 27 pass |
| Phase 2.2 | 17 pass |
| Phase 2.3 | 47 pass |
| Phase 2.4 | 26 pass |
| Phase 2.5 | 48 pass (two checks added: evidence output does not make a run dirty, code does) |
| Phase 2.6 | 62 pass |
| **Phase 2.7** | **16 pass** (new) |

`test-phase27.py` checks:

1. every v4 row is version 4;
2. one reader fingerprint, the Phase 2.6 one;
3. every row carries a SHA-256, and re-hashing 300 sampled files gives
   the recorded bytes;
4. one full commit, `61f17e9`. Git confirms that commit holds exactly
   reader `c12eb3102b45`, and that its runner writes version 4;
5. no dirty row, and no v1–v3 field on a v4 row;
6. the 123 failures carry no verdict;
7. every identity is unique;
8. the index matches the rows, and `verify()` is clean;
9. v1–v3 parts are identical to `ddf5d19`;
10. canonical files are unchanged since `ddf5d19`.

Two earlier checks asserted that the *whole* evidence directory matched
HEAD, which cannot hold while a new version sits uncommitted beside the
old ones. `test-phase25` #40 and the `test-phase26` safety check now
assert what they were protecting: the v1–v3 files are unchanged.
`test-phase25` #41 ("no v4 exists", true only during Phase 2.5) now
asserts v1–v3 are identical to Phase 2.5's index.

## Canonical safety

`git diff --name-only ddf5d19` over `data/sources.json`,
`data/fiches.js`, `data/cuvees.js`, `data/field-src.js` and
`data/cuvee-src.js` is empty.

None of the following was applied:

- the 50 Echo corrections;
- the 149 Phase 2.1 proposals, 518 reviews and 360
  insufficient-evidence cases;
- any wine-list additions.

## Notes for the next phase

- **Grand-vin guard: Les Hauts du Tertre.** See Conflicts. The
  grand-vin path computes second-wine marks without siblings, so a
  second wine whose distinctive word is a COMMON word ("hauts") is
  invisible to it. v3 and v4 both accept 8 Les Hauts du Tertre sheets
  as Château du Tertre's grand vin. The same check is worth running for
  every estate.
- **The field-conflict model needs a non-canonical dry-run path.** It
  currently records only under `--apply`; see Conflicts.
- **`read-fiches.py`** still falls back to a basename search when a
  file is not in its own folder. That is the gap Phase 2.5 closed for
  the evidence writers. It was left alone here, because it is not an
  evidence writer.
- **A v4 run takes about 9–11 minutes, single-threaded.** Running
  estates in parallel would cut that, but as its own measured change.
- **`decisions-v4.jsonl` is 39.3 MB.** Any further v4 rows will start
  `decisions-v4.part2.jsonl`, as designed.
