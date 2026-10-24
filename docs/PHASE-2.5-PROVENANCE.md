# Phase 2.5 — Evidence provenance repair and v4 readiness

**Status: complete. V4 gate: `SAFE`** on the conditions this phase
defines (section 9). No v4 was generated. No canonical data changed.
v1, v2 and v3 are byte-for-byte unchanged.

2026-10-24, from `09edeab`.

---

## Environment

| | |
| --- | --- |
| HEAD at start | `09edeab149cee9fc8489cd9e34e7e3a81337e3ce`, clean tree |
| Python | 3.12.10; PyMuPDF 2.0 and openpyxl as before |
| Node | v24.20.0 at `%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_…\node-v24.20.0-win-x64\node.exe`; a validation tool only (`node --check` in `test-data.py`) |
| project tooling | still no `package.json`, lockfile, CI, engines setting or build step |
| installed this phase | nothing |
| tests | `python tools/test-*.py`, run from the repository root |

## The provenance path, as it was

Traced through `evidence-wines.py` (v2, v3), `recharacterize.py` (v2,
v3 for unattributed artifacts) and `evidence.py` (v1). Every value in a
decision row came from one of these places:

| value | where it came from | sound? |
| --- | --- | --- |
| artifact filename | `sources.json` row, `file` | yes |
| artifact path | `disk.get(file)`: a dict built by walking all of `sources/` and keeping the **first** path seen for each basename | **no**: any folder could win |
| artifact identity | `row_key`: artifact name, the manifest's folder, estate, wine, field, vintage, target estate/wine/role/vintage, `v` | yes; no path or hash in it |
| artifact hash (`observed.sha1`) | `sources.json` row, `sha1`, copied | **no**: the manifest's claim, never computed |
| document bytes | whatever `disk.get` returned, opened by the reader itself (`pymupdf.open(path)`, or page text) | **no**: see path |
| reader version (`reader`) | `evidence.reader_fingerprint()`: SHA-1 of the working-copy bytes of `sheetreader.py` and `read-fiches.py`, first 12 hex | yes; it hashes the code that ran |
| source-list state | not recorded | — |
| git commit (`commit`) | `git rev-parse --short HEAD` at run time | **no**: HEAD, whether or not the code that ran was committed |
| working-tree state | not recorded | **no** |
| decision identity | `evidence.row_key` | yes |

The reader opens only the path it is given, plus the project's own
`data/*.js`, which are code-like configuration under git. It caches
extracted text per process, keyed by path.

## Current provenance defects (from Phase 2.4)

1. **Hash copied, not computed.** `observed.sha1` is `sources.json`'s
   value. Measured here, the manifest's sha1 matches the bytes at the
   row's own path for 12,669 of 12,909 resolvable rows, so 240 are
   stale.
2. **Lookup by basename.** 917 rows were read from another folder's
   file of the same name; for 48 of them the bytes differ.
3. **Commit predating the code.** v2 rows say `90f7bbb` and v3 rows say
   `bb2d42f`, while both passes ran uncommitted code. Only `reader`
   identifies what decided.

The trace found a fourth, smaller one:

4. **Missing files were skipped silently or recorded as a verdict.**
   v2 and v3 `continue` past a file they cannot find, leaving no trace.
   v1 recorded it as a decision, `NOT_EVALUATED / NOT_ON_DISK`.

## Artifact identity

`tools/provenance.py`, `resolve(folder, file)`. A manifest row names a
folder and a file. The folder is a fiche library,
`sources/fiches/<folder>/`, or a crawled site, `sources/pages/<estate>/`
(written in the manifest as `pages/<estate>`). Both candidate paths are
built from the row, and then:

| finding | result |
| --- | --- |
| the exact name is listed in exactly one candidate directory | that file |
| in none | `ARTIFACT_NOT_FOUND` |
| in both | `ARTIFACT_AMBIGUOUS` |
| only a differently written name exists (letter case, a trailing dot) | `ARTIFACT_NAME_MISMATCH`, naming the near-miss |
| the folder or name climbs out of `sources/` | `ARTIFACT_OUTSIDE_SOURCES` |

There is no basename search and no first match.

"Listed" means the directory listing contains the exact name. On
Windows, `isfile()` accepts any letter case and drops trailing dots. A
first version of this phase used it, and the audit caught 20 rows such
as `domaine-de-chevalier-blanc-2025-primeur-francais.pdf` opening
`Domaine-de-Chevalier-Blanc-2025-Primeur-Francais.pdf`, which on Linux
opens nothing. A resolution that depends on the operating system is not
an identity.

## Hash semantics

| field | versions | meaning |
| --- | --- | --- |
| `observed.sha1` | v2, v3 (and any row appended to them) | **the manifest's sha1 for the row, copied.** Not a hash of anything read. Unchanged. |
| `read.path` | v4+ | the file the reader was given, relative to `sources/` |
| `read.sha256` | v4+ | **SHA-256 of the bytes at `read.path`**, taken immediately before the reader ran and confirmed equal immediately after it returned |
| `read.bytes` | v4+ | the size of those bytes |
| `manifest_sha1` | v4+ | the manifest's sha1, kept beside the real hash and named as the claim it is |

The reader opens the file itself, so the hash cannot be taken from the
same buffer. It is bracketed instead: the file is hashed before the
reader is called and again after it returns. If the two differ, the
reader may have seen other bytes; its answers for that artifact are
dropped and `ARTIFACT_CHANGED_DURING_READ` is recorded. A file that
cannot be opened is `ARTIFACT_UNREADABLE`.

v4 rows may not carry `observed` at all. The store refuses them, so the
v2/v3 meaning of `observed.sha1` can never be mistaken for a computed
hash.

## Git provenance

Taken once at the start of a run, and again before anything is written.

| field | meaning |
| --- | --- |
| `git.commit` | the full 40-character HEAD sha when the run started |
| `git.dirty` | `true` if `git status --porcelain --untracked-files=all` listed anything: a modified, added, deleted or untracked-and-unignored file |
| `git.status_hash` | when dirty, SHA-256 of that status output, `git diff HEAD --binary`, and the bytes of every untracked file. When clean, `null`. |

- **Clean (`dirty: false`)**: the code at `git.commit` produced the
  decision.
- **Dirty (`dirty: true`)**: `git.commit` plus the uncommitted state
  named by `status_hash`. Equal hashes mean the same uncommitted code;
  the state itself cannot be recovered from the repository.

The writers refuse a dirty v4 run unless `--allow-dirty` is given, and
then record it as dirty. If the state changes between the start of a run
and its write — code edited mid-run — nothing is written.

`reader` is unchanged: SHA-1 of `sheetreader.py` and `read-fiches.py`. It
remains the version lock (a version is one reader). `git.commit` and
`status_hash` cover everything else that ran, including the runners
themselves and `data/*.js`.

v1–v3 rows, and any row appended to them, keep `commit` as the
abbreviated HEAD, as before. v4 rows may not carry `commit` at all.

## Provenance failures

A failure is not a verdict. `provenance.Run` records it as
`kind: provenance_failure`, with a code from the list below, the
artifact, its context and the run's `git`. It has **no `decision`
field**. Failure codes:

- `ARTIFACT_NOT_FOUND`
- `ARTIFACT_AMBIGUOUS`
- `ARTIFACT_NAME_MISMATCH`
- `ARTIFACT_UNREADABLE`
- `ARTIFACT_CHANGED_DURING_READ`
- `ARTIFACT_OUTSIDE_SOURCES`

None of them is a reader code, and the tests assert the two lists do
not overlap.

Failures go to `data/evidence/provenance-failures-vN.jsonl` through
`evidence_store.append_failures()`. Its hash is kept in the index, and
`iter_rows()` never reads it. The store refuses a failure passed to
`append()`, and refuses a "failure" that carries a `decision`. Below v4,
failures are counted and printed but not written. Those versions' files
stay exactly as they are.

## Historical evidence

v1, v2 and v3 are not rewritten. Their provenance fields are what those
runs recorded. That `observed.sha1` was the manifest's claim, and that
`commit` was HEAD rather than the code, are facts about how they were
recorded, now documented here and in `evidence_store.py`. They are not
errors to correct after the fact. Rewriting them would claim provenance
those runs never had.

Three layers are kept apart:

| layer | where |
| --- | --- |
| historical provenance, as recorded | `data/evidence/decisions-v1..3.jsonl`, unchanged; verified by hash |
| corrected understanding of it | `data/provenance-audit.jsonl` (below): which file each row really read, and what its bytes hash to |
| new, trustworthy provenance | v4+ rows: `read`, `git`, `manifest_sha1` |

## Same-name audit

`tools/audit-provenance.py --write` compares, for all 13,032 manifest
rows, the old resolution (basename, first match) with the new one (the
row's own folder). It writes the 1,040 rows that differ to
`data/provenance-audit.jsonl`. Each row gives the old path, new path,
manifest sha1, old and actual sha1/sha256, whether the bytes differ,
whether the row is a manifest duplicate, whether its identity changes,
and how many v1–v3 decisions were made from the old path.

| | rows |
| --- | ---: |
| same file under both resolutions | 11,992 |
| **old read another folder's file** | **917** |
| … identical bytes | 869 |
| … **different bytes** | **48** |
| … rows that are manifest duplicates | 98 |
| new: `ARTIFACT_NOT_FOUND` (old read nothing either) | 103 |
| new: `ARTIFACT_NAME_MISMATCH` (old read nothing either) | 20 |
| **new: ambiguous** | **0** |
| decision identities that change | 0 |

- **All 917 resolve uniquely once the folder is used.** None needs
  another identity field.
- **4,885 v1–v3 decisions** were made from a wrong-folder file. **544**
  of those were made from different bytes, so they are decisions about
  a document other than the one their row names.
- **The 123 unresolvable rows:** v1 recorded them as `NOT_ON_DISK`
  decisions, and v2 and v3 skipped them silently. From v4 on they are
  provenance failures.

The 48 different-bytes cases, by where they were filed and where they
were read from:

| filed under | read from | rows |
| --- | --- | ---: |
| `pages/la-mission-haut-brion` | haut-brion | 28 |
| `de-malleret` | bourgeois-chateau-de-malleret | 7 |
| `laville-haut-brion` | la-tour-haut-brion | 3 |
| `pages/haut-bailly` | figeac | 2 |
| `pages/lascombes` | haut-bailly | 2 |
| `pages/la-tour-figeac` | haut-bailly | 1 |
| `pages/lafon-rochet` | haut-bailly | 1 |
| `pages/latour-martillac` | ducru-beaucaillou | 1 |
| `laville-haut-brion` | la-mission-haut-brion | 1 |
| `lynch-moussas` | batailley | 1 |
| `talbot` | caillou | 1 |

The largest group explains part of Phase 2.4's La Mission finding:
crawled pages with generic names (`2019__…`) exist on several estates'
sites, and La Mission's rows were read from Haut-Brion's copies.

No canonical record was changed on the strength of this audit.

## Decision identity

`evidence.row_key` is unchanged, and the audit confirms that no row's
identity differs between the two resolutions. Path, hash, commit,
status hash and date are not in it. The same question asked twice —
same artifact name, folder, estate, wine, vintage and target — is the
same decision, whatever code state or bytes produced it. A rerun stays
idempotent. Tests 26–27 append a row whose commit, hash and date all
differ, and nothing is written.

That is the existing design, and it is kept. A consequence: if a
document's bytes change between two runs of the same version, the
second run's answer is not appended. A changed document is a question
for the next version, which records `read.sha256` and can be compared
with the last.

## Tests

| suite | result |
| --- | --- |
| `test-reader.py` | all pass (110 ok) |
| `test-data.py` | 11 pass |
| `test-phase2.py` | 30 pass |
| `test-phase21.py` | 27 pass |
| `test-phase22.py` | 17 pass |
| `test-phase23.py` | 47 pass |
| `test-phase24.py` | 26 pass; its v4 cases moved to the Phase 2.5 fields |
| `test-phase25.py` | **46 pass** (new) |

`test-phase25.py` runs on fixtures: a synthetic `sources/` tree, a
throwaway git repository and a temporary store.

- **Resolution (1–10)**: exact folder; same name in another folder;
  same name with different bytes; same name with same bytes; a
  crawled page; an ambiguous name; a name found only elsewhere (not
  found, never borrowed); letter case and trailing dot as
  `NAME_MISMATCH`; escaping `sources/`.
- **Hash (11–16)**: the recorded hash is the bytes'; a stale manifest
  hash does not override it; v4 carries no `observed`/`commit`; the
  v1–v3 stamp is unchanged below v4; bytes changed under the reader are
  caught and nothing kept.
- **Git (17–23)**: clean; modified; different and identical uncommitted
  code; untracked files; a new commit; never the parent.
- **Store (24–38)**: a clean v4 write; identity ignores commit, hash
  and date; v1–v3 fields refused at v4; failures carry no verdict, are
  refused as decisions, go to their own file, are never read as rows
  and are not duplicated; a dirty run is refused, then recorded as
  dirty with `--allow-dirty`; code changed mid-run means nothing is
  written.
- **History (39–41)**: v1–v3 match their hashes; `data/evidence/` is
  unchanged from HEAD; no v4 exists.
- **Real cases (42–45)**: all 48 different-bytes cases now read their
  own bytes; all 869 same-bytes cases resolve to their own folder; none
  is ambiguous; no identity changes. These checks print `MISSING`
  without `sources/`.

## Canonical safety

`git diff --name-only HEAD -- data/sources.json data/fiches.js
data/cuvees.js data/field-src.js data/cuvee-src.js` is empty. The 50
Echo entries, the two estates from `f445e96` and the second-wine reader
are untouched. `data/evidence/` is unchanged.

## V4 gate

| condition | |
| --- | --- |
| the writer resolves the intended artifact without filename-only ambiguity | yes: folder + exact name; ambiguity is a failure (0 cases) |
| the exact bytes read are hashed | yes: SHA-256, bracketing the reader |
| the recorded hash matches those bytes | yes: `read.sha256`; tests 11, 12, 25, 42 |
| commit provenance represents the code executed | yes: full HEAD sha, and the run is refused if the code changes mid-run |
| dirty-tree execution is explicitly represented | yes: `git.dirty` + `status_hash`; refused unless `--allow-dirty` |
| provenance failures cannot masquerade as verdicts | yes: separate kind, codes and file; refused by `append()` |
| decision identity remains stable | yes: `row_key` unchanged; 0 identity changes in the audit |
| v1/v2/v3 unchanged | yes: hashes verified; `data/evidence/` clean against HEAD |
| the store accepts the new provenance fields | yes: test 24 |
| all test suites pass | yes: eight suites |

**`SAFE`**: v4 can now be tied to exact artifact bytes, exact reader
code and exact execution state.

This answers the provenance question only. Whether v4 should be
generated *before* the second-wine identity fix specified in Phase 2.4
(section 11 there) is a separate decision. A v4 run today would measure
the v3 reader with trustworthy provenance, which has value of its own:
it would show how the 544 wrong-bytes decisions change. But it would not
be the v4 that measures the reader fix. To generate it, the runners'
`DECIDER_VERSION` goes to 4 and the run is made from a clean tree.
Neither was done here.

## Files

- `tools/provenance.py`: new. Resolution, hashing, git state,
  `Run`, `write`.
- `tools/evidence_store.py`: v4 field rules, `append_failures`,
  `iter_failures`, failures in `verify()`.
- `tools/evidence-wines.py`, `tools/recharacterize.py`,
  `tools/evidence.py`: resolve through `provenance`; stamp through
  `Run.stamp`; write through `provenance.write`; `--allow-dirty`.
- `tools/audit-provenance.py`: new. The same-name audit.
- `data/provenance-audit.jsonl`: new. The 1,040 rows that resolve
  differently.
- `tools/test-phase24.py`: v4 cases on the new fields.
- `tools/test-phase25.py`: new, 46 checks.
