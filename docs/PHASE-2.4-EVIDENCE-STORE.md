# Phase 2.4 — Evidence store, environment baseline, and the v4 gate

**Status.** The storage decision is made, implemented and proven
lossless. v1, v2 and v3 now live one file per version under
`data/evidence/`, and their bytes reproduce the old 64 MB file
exactly. **v4 is not yet safe to generate.** The store is ready for it,
but the code that writes evidence is not (section 14), and the reader
defect v4 would measure is specified but not fixed (sections 10–11). No
canonical data changed. No v4 rows were generated.

2026-10-24, from `a36b35c`.

---

## 1. Environment baseline

| | |
| --- | --- |
| commit | `a36b35c` (Phase 2.3), after `f445e96` (site fix + two estates) |
| working tree at start | clean |
| Python | 3.12.10, `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` |
| Python packages used | PyMuPDF 2.0 (`fitz` / `pymupdf`), openpyxl (`build-workbook.py` only); no requirements file |
| Node | v24.20.0, `%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_…\node-v24.20.0-win-x64\node.exe` |
| npm | 11.19.0, bundled with Node, unused |
| package manager | none; no `package.json`, lockfile, `.nvmrc`, `.node-version`, `engines` or CI configuration |
| git | `core.autocrlf=true`; no `.gitattributes` before this phase |
| documented commands | README: `python -m http.server 8000`; tests are `python tools/test-*.py` |

**Node is a validation tool, not a project dependency.** The site is
static files with no build step. Node was installed in Phase 2.3 (winget,
user scope, PATH set for new shells), and its only use is
`tools/test-data.py` running `node --check` on every script. When Node
is missing, that check prints `MISSING` and the rest of the suite still
runs. Nothing else was installed or upgraded in this phase.

Baseline before any change: all six suites passed (reader 110 ok lines;
data 11; Phase 2 30; 2.1 27; 2.2 17; 2.3 47).

## 2. The evidence architecture as it was

- **One file**, `data/evidence-decisions.jsonl`: one header line
  `{"_": …, "decider_version": 1}`, then one JSON object per line.
- **Writers** append only: `evidence.py` (v1), `evidence-wines.py` (v2,
  v3), `recharacterize.py` (v2, v3). Each reads every identity already
  in the file (`existing_keys()`) and appends rows not among them.
- **Readers**: `propose.py`, `compare-v3.py`, `test-phase2.py`,
  `test-phase21.py`, and `evidence-wines.py` (its v1 baseline).
- **Identity**: `evidence.row_key()`, an 11-tuple of artifact, folder,
  estate, wine, field, vintage, target estate, target wine, target role,
  target vintage and `v`.
- **Each row** holds `artifact` (basename), `kind` (guard or pin),
  `ctx` (the manifest's claim: estate, wine, vintage, folder, plus the
  target asked about: estate, wine, role, vintage, `evaluated_as`,
  `target_estate_from` for hypotheses), `decision`
  (ACCEPTED / REFUSED / NOT_EVALUATED), `code`, `raw` (the reader's
  sentence, verbatim), `evidence` (a list of short strings), `observed`
  (`sha1`), `points_at` (v3), `v`, `reader` (sha1 of the reader's two
  source files), `commit`, `at` (date) and `re_evaluable`.
- **Order**: versions are three contiguous blocks, 1 then 2 then 3, each
  in the order its run produced. Nothing depends on order inside a
  version.
- **Use**: a log by construction (append-only) that is read as a
  dataset (every reader loads it whole). There was no index and no
  query layer.

### What this phase found wrong with it

1. **`observed.sha1` is the manifest's hash, not the hash of what was
   read.** Writers copy `s.get('sha1')` from `sources.json`. For 204
   folder/file pairs the manifest holds two hashes (the document changed
   between downloads) and the disk holds one copy, so one row of each
   pair names bytes the reader never saw.
2. **Writers find a document by basename across every folder**
   (`disk.setdefault(f, …)`). 917 manifest rows were therefore read from
   a same-named file in another folder; for 48 of them the bytes differ.
   Those decisions were made about a different document than the one
   the row names.
3. **`commit` is the HEAD at run time, not the code that ran.** v2 rows
   say `90f7bbb` and v3 rows say `bb2d42f`, but both passes ran on
   uncommitted code. Only `reader` identifies the code: `c2086a5a8918`
   for v1 and v2, `ba6795763d67` for v3.
4. **1,228 duplicate identities** (466 exact duplicate lines). The
   writers deduplicated against the file but not within their own
   batch, and the manifest holds duplicate rows. No duplicate group
   disagrees on its verdict. 726 groups (242 per pass) differ only in
   `observed.sha1` — finding 1 again.
5. **Mixed line endings in the working copy.** With `core.autocrlf`,
   the 54,325 lines present at checkout came back CRLF; the 41,259 v3
   lines appended later are LF. Git stores LF throughout, so "byte for
   byte" meant different things on disk and in the repository.

None of these changes a recorded verdict retroactively. All five matter
for what v4 may claim.

## 3. Measurements

| | |
| --- | --- |
| size, as committed (LF) | 64,270,999 bytes (61.29 MiB) |
| lines | 95,584: 1 header + 95,583 decisions, all parseable |
| v1 | 13,065 rows, 5.77 MB, 442 bytes/row |
| v2 | 41,259 rows, 29.1 MB, 706 bytes/row |
| v3 | 41,259 rows, 29.4 MB, 712 bytes/row |
| gzip -9 / bz2 -9 / xz -6 | 2.29 MB (28×) / 1.88 MB (34×) / 1.85 MB (35×) |
| exact duplicate lines | 466 |
| duplicate identities | 1,228 surplus rows in 1,183 groups (v1 165, v2 509, v3 509) |
| full read + parse | 0.97 s |
| `existing_keys()` | 0.70 s, before every `--write` |
| reading the last 2 MB | 0.002 s |

**Where the bytes go.** `ctx` is 35% of every row. Within it,
`evaluated_as` (7.6%) restates the target fields as a sentence. `raw` is
10.8% but has only 789 distinct values; `evidence` is 7.8% with 541.
`commit`, `reader`, `at`, `kind` and `re_evaluable` together take about
14% of the file and hold 2–3 distinct values each. The repetition is
why compression reaches 35×.

**Git history.**

| commit | blob size | loose object on disk |
| --- | ---: | ---: |
| `90f7bbb` (Phase 2) | 5.8 MB | 0.27 MB |
| `effcd4e` (Phase 2.1) | 34.9 MB | 1.84 MB |
| `a36b35c` (Phase 2.3) | 64.3 MB | 3.46 MB |

All three revisions pack together, with deltas, into **2.43 MB**. Git
stores an append-only file very efficiently: each revision is the
previous one plus a tail.

## 4. Why the 61 MB file is a problem

The problem is not repository size or clone time; 2.4 MB of packed
history is nothing. It is three things:

1. **GitHub's per-file limit is on the raw file.** It warns at 50 MB
   and refuses a push containing any file over 100 MB. Each full pass
   adds about 29 MB, so v4 would take the file to about 93 MB and v5
   would be refused. Once a blob over 100 MB is in a commit, the only
   way out is rewriting history.
2. **One file for every version** makes "which reader decided this?" a
   filter over everything, and gives no place to state a version's
   provenance once.
3. **GitHub Pages publishes it.**
   `https://breth011.github.io/bordeaux-dashboard/data/evidence-decisions.jsonl`
   answers 200 with 64 MB. The site never loads it.

## 5. Options considered

| option | append-only | history byte-identical | diff / inspect | GitHub | infrastructure | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1. JSONL split by decider version | yes | yes, lines move verbatim | yes, plain text | each version about 29 MB | none | **chosen** |
| 2. JSONL split by run / phase | yes | yes | yes | yes | none | v2 and v3 were each one run, so the same files as option 1 today. A version is the meaningful unit, because a version is one reader. |
| 3. Compressed JSONL (`.jsonl.gz`) | append means rewrite | content yes, file no | no diffs; needs a tool to read | 35× smaller | none | Git already compresses (2.4 MB packed), so it saves nothing in the repository and costs inspectability |
| 4. Outside the work tree, with an index | yes | yes | yes, locally | n/a | a second place to back up | the audit trail would leave version control |
| 5. Git LFS | yes | yes | no diffs on GitHub | LFS quota and bandwidth; Pages does not serve LFS | LFS server, client on every machine | external infrastructure for a problem plain files solve |
| 6. SQLite or another database | needs discipline | no, a binary file | no diffs, no merges | binary blob | none | good to query, wrong to keep evidence in |
| 7. Hybrid: JSONL log + generated index | yes | yes | yes | yes | none | option 1 already is this: `index.json` is the small index. A generated query database stays a future, gitignored option, unneeded while a full read takes one second. |

## 6. Chosen architecture

```
data/evidence/index.json            what is stored, with hashes
data/evidence/decisions-v1.jsonl    5.8 MB
data/evidence/decisions-v2.jsonl    29.1 MB
data/evidence/decisions-v3.jsonl    29.4 MB
tools/evidence_store.py             the only code that reads or writes them
```

- **One file per decider version.** A version that outgrows 40 MB
  continues in `decisions-vN.part2.jsonl`, so no file reaches GitHub's
  50 MB warning.
- **`index.json`** records, per version: its parts with row count,
  bytes and sha256, its reader fingerprints and its commits. It also
  records `migrated_from`: the old file's path, commit, bytes, sha256,
  line count and verbatim header line.
- **`evidence_store.py`** offers `iter_rows(only=)`, `iter_lines(v)`,
  `existing_keys()`, `latest_by_context()` (highest version per
  question, as a reading — earlier rows stay), `append(rows, v)` and
  `verify()`.
- **`.gitattributes`** keeps `data/evidence/*.jsonl` and `index.json`
  LF in the working copy, so the file on disk is the bytes the hashes
  describe.

`append()` refuses:

- a row whose `v` is not the version being written;
- a row from a different `reader` than the version was opened with (a
  changed reader is a new decider version);
- from v4 on, a row without `observed.path`, `observed.sha1`, `commit`,
  `reader` and `tree_clean` (section 9).

It drops identities already stored and duplicates within one batch.

## 7. Migration

`tools/migrate-evidence-store.py` reads the file **as committed at
`a36b35c`** (`git show`), not the CRLF working copy. It moves each
line's bytes to its version's file without parsing and re-serialising
anything.

1. **Prototype.** The first 400 rows of each version, plus every
   duplicated identity, were migrated into a scratch directory and read
   back through `evidence_store`: lossless, identical bytes, `verify()`
   sound.
2. **Migration.** The full file, with the same proof.
3. **Re-proof.** `--check` concatenates header + v1 + v2 + v3 and
   compares it with `a36b35c:data/evidence-decisions.jsonl`:
   **identical**, with the same sha256 recorded in the index.

| | before | after |
| --- | ---: | ---: |
| v1 rows | 13,065 | 13,065 |
| v2 rows | 41,259 | 41,259 |
| v3 rows | 41,259 | 41,259 |
| bytes (header + versions) | 64,270,999 | 64,270,999 |
| line sha1s, in order | — | equal |
| identity multiset, duplicates included | — | equal |

The old file is removed from the working tree. It remains in history at
`a36b35c`, and the index points to it. The Phase 2–2.3 documents still
name it, because they describe what was true when they were written.

## 8. Invariants preserved

- v1, v2 and v3 are not rewritten. Every line is byte-identical, in the
  same order. The 1,228 historical duplicates are kept as written.
- Each row keeps its original `v`, `reader`, `commit`, `observed.sha1`
  and verdict.
- History is queryable: `iter_rows([1])`, `iter_rows([2, 3])`,
  `latest_by_context()`.
- A later decision supersedes an earlier one only by being a higher
  version for the same question. `latest_by_context()` is a reading of
  the store; nothing is replaced.
- A rerun is idempotent through the store: v3 for Lynch-Bages (1,040
  decisions) and the unattributed Latour-Martillac artifacts (21) both
  appended 0.

## 9. The v4 storage boundary

**Decided.** v4 rows go to `data/evidence/decisions-v4.jsonl`, through
`evidence_store.append(rows, 4)`, and nowhere else. The store enforces:

| rule | why |
| --- | --- |
| `v` must equal 4 | no row is filed under the wrong version |
| one `reader` fingerprint for all of v4 | a reader change mid-version would make "v4" mean two things |
| `observed.path` | the file actually read, not a basename (finding 2) |
| `observed.sha1` | the hash of the bytes read, not the manifest's claim (finding 1) |
| `commit` and `tree_clean` | whether that commit held the code that ran (finding 3) |
| no duplicate identity, including within the batch | finding 4 |

**Proposed, not implemented.** The writers (`evidence-wines.py`,
`recharacterize.py`) must:

- resolve a document by its folder, not its basename;
- hash the bytes they open;
- record `tree_clean` from `git status --porcelain`;
- be run from a commit that contains the reader.

Until they do, the store refuses their v4 rows. That refusal is
deliberate: a v4 written today would repeat findings 1–3.

## 10. The surviving second-wine acceptances

Each case was traced through `second_wine_verdict` on its own document
(`tools/trace-second-wine-cases.py`, run as `python -I tools/trace-second-wine-cases.py <repo>`).

| # | estate · document · asked as | why it was accepted | does the evidence identify *that* second wine? | correct? |
| --- | --- | --- | --- | --- |
| 1 | Belgrave · `belgrave-2023-fc11b611.pdf` · Diane de Belgrave 2023 | `is_second_wine`: the title opens "Second vin du Château Belgrave" | yes. The phrase is bound to this estate, the title names no other wine, and Belgrave lists one second wine. | **yes** |
| 2 | Latour-Martillac · `…lagrave-martillac-blanc-2020-lacroix-martillac-rouge-2019-min.txt` · Lagrave-Martillac 2020 | the page's URL, which the reader appends to the name, contains `lagrave-martillac` | the URL names Lagrave-Martillac, but the page is a 676-character WordPress image-attachment page with no wine content. It is also accepted as the grand vin. | **no**: not a document about any wine |
| 3 | (the same page) · Lagrave-Martillac 2019 | as 2; 2019 is in the URL | no. In the URL, 2019 belongs to `lacroix-martillac-rouge-2019`, a wine the estate's list does not contain, so `named_wines` cannot see it | **no** |
| 4 | Caillou · `Fiche-technique-FR-MURETS-BLANCS-2023…pdf` · Les Erables de Caillou 2023 | `is_second_wine`: "LES MURETS DE CAILLOU 2023 Second Vin blanc sec du Château Caillou" | no. The phrase establishes *a* second wine — the dry white's. The title names Les Murets, which is not on the list. | **no** |
| 5 | Pédesclaux · `FT-PEDESCLAUX-2025_FR_compressed.pdf` · Fleur de Pédesclaux 2025 | `is_second_wine`: "CARTOGRAPHIE DU PREMIER ET SECOND VIN - 2025" | no. The document is about both wines. `is_second_wine` already tries to exclude "premier **et** second", but compares a three-character slice with the two-letter `'et'`, so that branch can never fire. | **no** |
| — | Haut-Brion (folder `la-mission-haut-brion`) · `…la-chapelle-de-la-mission-haut-brion2019.txt` · Le Clarence 2019 (also accepted by v2) | `is_second_wine`: "…this second wine is a gateway…", 62 characters in, mid-sentence | no. It is another estate's second wine, La Chapelle de la Mission Haut-Brion | **no** |

So one of the five is correct. Two are a page about no wine, and three
are a generic "second wine" phrase standing in for a specific wine. The
blend reader is not involved in any of the acceptances; section 11 says
where it does matter.

## 11. The reader defect, specified

**Invariant.** A document may be accepted as a particular second wine
only when its evidence identifies that wine, not merely some second
wine.

**`is_second_wine` means two different things, and both are needed.**

- *Some* second wine: the grand-vin guard (`whose_sheet` when not
  `is_second`) and the blend reader (`read-sheets.py`) use it to keep a
  second wine's sheet off the grand vin. The generic phrase is exactly
  right for that: any second wine is not the grand vin.
- *This* second wine: `second_wine_verdict` step 3 uses it as identity.
  Here it is wrong in four of the six cases above.

The fix is therefore **not** to tighten `is_second_wine`, which would
weaken the grand-vin protection. Instead:

1. Keep `is_second_wine` (some second wine) for exclusion.
2. Add an identity test for second-wine mode. Accept on the phrase only
   when all of these hold:
   - it is in the title;
   - it is bound to this estate ("second vin du Château X", "second
     wine of X");
   - the title names no other wine;
   - the estate lists exactly one second wine.

   Otherwise require the expected wine's own name in the filename, URL
   or title, as steps 4 and 6 already do.
3. Fix the `'et'` slice in `is_second_wine`, but separately, and
   measured. It changes grand-vin mode as well: Pédesclaux's two-wine
   map would stop being refused as the grand vin's.
4. When a filename or URL names two wines, bind each year to its own
   wine name. A year belonging to the other wine is not this wine's year
   (case 3).
5. A page whose body has no wine content (an image-attachment page) is
   not evidence for any wine, in either mode (cases 2 and 3).

**The part the current architecture cannot express.** Cases 3, 4 and 6
all turn on a wine the estate's list does not contain: Lacroix-Martillac,
Les Murets de Caillou, La Chapelle de la Mission. `named_wines()`
matches a closed list, so a wine nobody listed is invisible to it. A
document naming one looks like a document naming nothing, and then a
generic phrase or a sibling name wins. This is the same model problem
the grand vin has (memory: an unlisted cuvée pollutes the grand vin).
A local patch would hide it.

The general rule needs a recogniser for wine-shaped names built on the
estate's name — "X de Caillou", "Lacroix-Martillac", "… de la Mission
Haut-Brion" — that are not on the list, and both modes would refuse on
it. That is a change to the reader's model, not a patch to
`second_wine_verdict`, so it is specified here and left for its own
phase, as this phase's stop conditions require.

## 12. Tests

| suite | before | after |
| --- | --- | --- |
| `test-reader.py` | all pass (110 ok) | all pass (110 ok) |
| `test-data.py` | 11 pass | 11 pass |
| `test-phase2.py` | 30 pass | 30 pass, reading through the store |
| `test-phase21.py` | 27 pass | 27 pass, reading through the store |
| `test-phase22.py` | 17 pass | 17 pass |
| `test-phase23.py` | 47 pass | 47 pass |
| `test-phase24.py` | — | **26 pass** (new) |

`test-phase24.py` has two halves.

On a temporary store built from a sample, it checks that:

- the sample migrates losslessly, and the proof catches one changed
  verdict;
- v1–v3 read back;
- a v3 row is refused in v2, and a changed reader is refused in v3;
- the same reader may add a new question, and asking it again adds
  nothing;
- a duplicate within one batch is written once;
- v4 refuses a row without provenance and accepts one with it, in its
  own file;
- a version past its size limit continues in part 2 and reads back
  whole, in order;
- appending never changed a line of v1–v3;
- `latest_by_context` gives one answer per question;
- `verify()` passes, and catches one changed byte.

On the real store, it checks that:

- every part matches its hash, with the row counts above;
- header + v1 + v2 + v3 equals the file at `a36b35c`, byte for byte and
  by hash;
- no file is over 45 MB;
- the old file is gone and no tool opens it;
- `.gitattributes` holds the LF rule;
- the canonical files are unmodified.

## 13. Canonical safety

`git diff --name-only HEAD -- data/sources.json data/fiches.js
data/cuvees.js data/field-src.js data/cuvee-src.js` is empty. The 50
Echo corrections, the Phase 2.1 dry-run corrections and the five reader
cases are untouched. `f445e96`'s two estates are untouched.

## 14. Remaining blockers before v4

| | blocker | status |
| --- | --- | --- |
| 1 | storage design settled, migrated, proven lossless | **done** |
| 2 | writers resolve documents by folder and hash the bytes read | **open**; the store refuses v4 rows until they do |
| 3 | writers record `tree_clean`; v4 runs from a commit holding its reader | **open**; same enforcement |
| 4 | the specific-second-wine identity rule (section 11, points 1–5) | **open**, a reader change, with its own measurement |
| 5 | wine-shaped names not on the list (section 11) | **open**, a model change. It also bears on the grand vin. |
| 6 | GitHub Pages publishes `data/evidence/` (64 MB, unused by the site) | optional; not a correctness issue |

**v4 safe to generate: no.** Blockers 2 and 3 would make a v4 repeat v3's
provenance faults. Blocker 4 is the change v4 exists to measure.
