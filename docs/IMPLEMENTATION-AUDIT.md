# Implementation audit

What is actually implemented, traced through the code and the data, on
2026-10-24.

**The short answer first.** Four specifications were given today —
fiche families, persistent source knowledge, longitudinal quality,
reconciliation. Essentially none of them is implemented. What exists is
a strong dataset-and-provenance layer that predates them and happens to
satisfy some of their requirements, plus two read-only audit tools
written today. Nothing in this audit should be read as "we built that".

Where a requirement is marked COMPLETE it is because the pre-existing
architecture already did it, not because it was built to the
specification.

---

## 1. Traceability matrix

Five states: COMPLETE (end-to-end, exercised by real data or tests),
PARTIAL, SCAFFOLDED (shape without behaviour), MISSING, UNKNOWN.

### A. Multi-vintage fiche families

| Requirement | Status | Implementation | Evidence | Gap |
|---|---|---|---|---|
| Recognise recurring structures across vintages | PARTIAL | `tools/audit-consistency.py:family()` | groups Lynch-Bages' 26 own sheets apart from its negociant sheets; that split is what showed alcohol-on-10-of-31 to be document coverage, not a reading fault | derived from the **filename**, not the document. Breaks on any rename; blind to two differently-named documents sharing a layout |
| Distinguish family from instance | MISSING | — | — | no family object exists; `family()` returns a string computed on the fly and stored nowhere |
| Reuse structural knowledge | MISSING | — | — | nothing reads a family when extracting. The reader is estate-agnostic and label-driven |
| Allow schema evolution | MISSING | — | — | no schema is stored, so no change can be classified |
| Field aliases | COMPLETE | `tools/sheetreader.py` label patterns | `RX_ALC` and friends match "Alcohol", "Alcool", "Degré", "titre alcoométrique"; `LABEL_TASTE` matches 9 forms | aliases are global, not per-source or per-family |
| Retain raw labels | PARTIAL | `read_prose` returns `how[field]` | the matched label text is returned and printed in `reports/fiches-read.txt` | discarded at merge; not stored beside the value |
| Avoid duplicate structures per vintage | N/A | — | no structures are created at all | — |
| **Yields contract per family** | PARTIAL | `data/sheet-expectations.json`, `--freeze` | written today; records which fields a family is known to yield and on how many records | **empty** — nothing frozen yet |

### B. Persistent source / scraping knowledge

| Requirement | Status | Implementation | Evidence | Gap |
|---|---|---|---|---|
| Remember how each source is scraped | SCAFFOLDED | `data/site-recipes.json` | 10 of 61 estates, with sitemaps, robots, `{year}` URL patterns, the year range the site answers, and which wine each pattern serves | **`grep -rl site-recipes tools/` returns nothing.** No tool reads it. It is documentation a human follows |
| Retain URL/discovery patterns | SCAFFOLDED | same | `"pattern": ".../grand-vin-du-chateau-margaux-{year}"`, `"years": "1900-2025"` | same — not executable |
| Source-specific field mappings | MISSING | — | — | aliases live in the reader, global across all sources |
| Scraper versions | MISSING | — | — | `checked: "2026-10-24"` is a date, not a version with validity |
| Track source changes | MISSING | — | — | — |
| Track scraping failures | MISSING | — | — | a dead URL pattern is retried indefinitely |
| Incremental annual ingestion | PARTIAL | `harvest.py --year`, `sources.json.sha1` | content hash on all 13,032 sheets, so change detection is *possible* | no tool compares hashes to skip unchanged documents |
| Ingestion history | MISSING | — | `progress-history.tsv` has 4 rows of coverage, not runs | no expected-vs-found, no per-run record |
| Scraping distinct from extraction | COMPLETE | `harvest.py` vs `sheetreader.py` | genuinely separate modules with separate entry points | — |

### C. Annual ingestion

| Requirement | Status | Implementation | Evidence | Gap |
|---|---|---|---|---|
| Add a new vintage | COMPLETE | `docs/ADDING-A-VINTAGE.md` | 7 commands, 544 lines, including the recurring-defect list | manual sequence, not one operation |
| Reuse previous knowledge | PARTIAL | `--apply` never overwrites | existing fields survive a re-read | the *source* knowledge is not reused (see B) |
| Discover new/changed documents | PARTIAL | `harvest.py` | media API, then sitemaps | rediscovers each site generically every year |
| Avoid reprocessing | MISSING | — | — | `--redo` is all-or-nothing per estate |
| Detect source changes | MISSING | — | — | — |
| Ingestion report | MISSING | — | — | per-run reports are overwritten by the next run |

### D. Longitudinal data quality

| Requirement | Status | Implementation | Evidence | Gap |
|---|---|---|---|---|
| Gaps between populated vintages | PARTIAL | `tools/reconcile.py` (today) | finds 129 such gaps, 84 ranked HIGH, e.g. `lynch-bages 1990` with a document nothing cites | only where a **document is filed for that year**; a gap with no document is invisible |
| Unexpected missing fields | PARTIAL | `tools/audit-consistency.py` | 640 records across 43 estates hold no tasting note while their documents carry one; ragged fields per family | compares within a filename family, not against a stored expectation |
| Suspicious value changes | MISSING | — | `audit-estate.py` has `BAND` plausibility ranges | fixed global ranges, not learned per estate; no vintage-to-vintage delta check |
| Identity inconsistencies | PARTIAL | `tools/reconcile.py` | 67 year conflicts, 107 estate conflicts | filename/URL vs record only; document **contents** not compared |
| Duplicate documents | PARTIAL | `tools/reconcile.py` | 839 identical-byte groups, 313 spanning different wines | by sha1 only; no normalised-text hash, so an OCR copy reads as distinct |
| Duplicate/conflicting records | PARTIAL | `check-data.py` | reports a blend appearing in none of the estate's own sheets | no conflict object; the first writer silently wins |
| Unexpected disappearance | MISSING | — | — | — |
| Unexpected appearance | MISSING | — | — | — |
| Schema changes | MISSING | — | — | requires A |
| Cross-source conflicts | MISSING | — | — | provenance records one document per field, so a second source's disagreement is never seen |
| Source failures | MISSING | — | — | — |

### E. Evidence and provenance

| Requirement | Status | Implementation | Evidence | Gap |
|---|---|---|---|---|
| Source artifact registry | COMPLETE | `data/sources.json` | 13,032 sheets with file, folder, estate, wine, role, colour, year, url, bytes, sha1 | — |
| URL / source | COMPLETE | same, `url` field | — | — |
| Retrieval information | PARTIAL | `bytes`, `sha1` | hash and size on every sheet | **no retrieval timestamp, no HTTP metadata, no scraper version** |
| Document identity | PARTIAL | `estate`, `wine`, `year`, `role` | — | one wine per sheet; a combined sheet is wrong about its other wines |
| Fiche family | MISSING | — | — | requires A |
| **Field-level provenance** | COMPLETE | `data/field-src.js`, `data/cuvee-src.js` | one filename per field per record; `lynch-bages\|2012` alcohol from the negociant sheet, blend from the estate's own | page/region not recorded |
| Extraction method | PARTIAL | `how` in the manifest; `via:'trade'` | — | not per field |
| Confidence | MISSING | — | — | every stored value is equally certain |

### F. Reconciliation

| Requirement | Status | Implementation | Evidence | Gap |
|---|---|---|---|---|
| artifact → record | COMPLETE | `tools/reconcile.py` (today) | 5,438 of 13,032 cited | — |
| record → evidence | COMPLETE | `field-src.js` + `reconcile.py` | 3,855 of 3,899 records supported by a manifest document | — |
| Orphan artifacts | COMPLETE | `tools/reconcile.py` | **7,594** cited by nothing | the count needs interpretation — see §4 |
| Incorrectly mapped | PARTIAL | `tools/reconcile.py` | 107 estate conflicts, concentrated: de Braude↔Mongravey 35, Haut-Brion→La Mission 15, Poitevin↔Moulin-de-Canhaut 10 | metadata only |
| Duplicate artifacts | PARTIAL | sha1 grouping | 839 groups | no text-level clustering |
| Genuinely missing | PARTIAL | `reconcile.py --gaps` | 129 | cannot see a gap with no document |
| Legitimate absence | MISSING | — | — | nowhere to record "this estate published nothing in 1990" |

### G. Gap investigation order

| Requirement | Status | Implementation | Evidence | Gap |
|---|---|---|---|---|
| Mapped evidence first | COMPLETE | `reconcile.py --estate X` | for `lynch-bages 1990`: names the family covering 26 other vintages and the uncited document | — |
| Orphan artifacts second | COMPLETE | same | lists 139 orphans at Lynch-Bages with the wine each is filed under | — |
| Duplicates/alternates third | PARTIAL | sha1 | — | not surfaced per gap |
| Source archive fourth | COMPLETE | `sources.json` | — | — |
| Known source strategy fifth | SCAFFOLDED | `site-recipes.json` | — | not executable |
| External last | COMPLETE | behavioural | the one web fetch today was to confirm Margaux's own `20x22` typo | not a system capability |
| Does not invent values | COMPLETE | `read-fiches.py` | every field is written with the filename it came from; no inference path exists | — |

### H. Conservative modification

| Requirement | Status | Implementation | Evidence | Gap |
|---|---|---|---|---|
| Confidence tiers | MISSING | — | — | — |
| Propose before applying | COMPLETE | `--apply` / `--dry-run` | every reader prints a report and writes nothing without `--apply`; `refile-wine.py` likewise | — |
| Audit trail of reconciliations | PARTIAL | git | every data change is a commit with its reasoning in the message | no machine-readable old→new mapping record |

### I. Quality memory

| Requirement | Status | Implementation | Evidence | Gap |
|---|---|---|---|---|
| Resolved anomalies persist | PARTIAL | `REFUSED` in `read-fiches.py` | keyed `(record, field)` with a written reason; contains `lynch-bages\|2017` taste — "not this wine: the note is the estate's white" | **in Python, not data.** No other tool can query it; a report cannot say "known exception" |
| Known exceptions persist | PARTIAL | `reports/estates/*.md` `## Findings` | 61 hand-written sections, now protected by a fingerprint so a rebuild cannot silently drop them | prose, not queryable |
| Not rediscovered yearly | PARTIAL | same | the `lynch-bages\|2017` pin worked — and I rediscovered the class anyway today, because nothing generalised it | — |

---

## 2. Real-data traces

**Example 1 — normal multi-vintage.** Lynch-Bages 2012.
`sources.json` → `Chateau-Lynch-Bages-2012-EN-paraphe.pdf` (sha1, bytes,
url) → `whose_sheet()` accepts → `fields_of()` reads blend, months, oak,
pick → `field-src.js` records which document gave each → `fiches.js`
holds the record → the drawer links back via `fiches-url.js`. Every
link works **except fiche family**, which does not exist, and **page
region**, which is not recorded.

**Example 2 — a known gap.** `reconcile.py --estate lynch-bages`
returns `lynch-bages 1990, priority HIGH`, because the sheet family
covers 26 vintages that are on record and one document filed for 1990
is cited by nothing. It names the document:
`Chateau-Lynch-Bages-1989-FR.pdf` — whose own filename says 1989, which
is why the reader refused it for 1990. So the gap is explained, in one
command, with evidence. This requirement works.

**Example 3 — orphan artifact.** `Echo-de-Lynch-Bages-2008-EN.pdf` is
on disk, in the manifest, and cited by no record. `reconcile.py` lists
it and shows it filed under **`Blanc de Lynch-Bages`** — the white. The
cause: `read-fiches.py` routes cuvée documents by the manifest's `wine`
field, so these were offered to the Blanc; `whose_sheet()` correctly
refused them; and they were never offered to the Echo. 50 Echo sheets
are affected, and 5 Echo vintages (2008, 2009, 2010, 2015, 2016) have a
document and no record. **Detected, not yet fixed.**

**Example 4 — suspicious mapping.** `bourgeois-chateau-mongravey|1984`
cites `FT-Ch-de-Braude-2022-GB.pdf` — another estate's document, and
another year. Found by `reconcile.py`, which also shows the pattern:
de Braude and Mongravey cross-cite 35 times in both directions. This is
a systematic pair, not 35 accidents.

**Example 5 — changed structure.** Not possible. No structure is
stored, so schema evolution cannot be distinguished from a new family.
UNKNOWN.

---

## 3. Silent failure modes found

Highest-priority first. Three were found today and two are fixed.

1. **`except Exception: continue` swallowing a crash.**
   `read-plantings.py` called `block()`, whose last line raised
   `IndexError` for one of its two label patterns. 70 documents across
   17 estates were discarded in silence — figures found, validated, and
   dropped. *Fixed today (commit f9e060a).*
2. **A guard refusing a document and nobody being told.** Refusal
   reasons are counted and printed, then discarded. A document refused
   every year for ten years looks identical to one that does not exist.
   *Not fixed — this is the strongest argument for the anomaly store.*
3. **`--apply` never overwrites, so the first writer wins silently.**
   Two documents disagreeing about alcohol produce no conflict and no
   note; whichever was read first stands. *Not fixed.*
4. **Prose offered from the wrong wine.** A combined sheet's labelled
   passage went to whichever wine the document was filed under.
   *Fixed today by `opens_on_another_wine()` (commit ec347bc).*
5. **`(?i)` silently disabling a case-sensitive test.** Hit three times
   this week in patterns whose own comments said "in capitals only".
   *Each fixed; the class remains possible.*

---

## 4. The dataset, statistically

| | |
|---|---|
| Source artifacts in the manifest | 13,032 |
| Present on disk | 12,909 |
| Named but absent from disk | 123 |
| Cited by at least one record | 5,438 |
| **Cited by nothing** | **7,594** |
| Identical-byte groups | 839 (313 spanning different wines) |
| Dataset records | 3,899 |
| Supported by a manifest document | 3,855 (98.9%) |
| Weakly or unsupported | 44 |
| Document-year vs record-year conflicts | 67 |
| Document-estate vs record-estate conflicts | 107 |
| Gaps with a document and no record | 129 (84 HIGH) |

**The 7,594 orphans need interpretation and I will not inflate them.**
A large share are documents the guard chain deliberately refuses and
should refuse: press dossiers, event pages, article reprints, the
other-language copies of a page already read, and the 2,711-document
`.txt` layer that duplicates PDFs. The number is not 7,594 lost
records. It is the size of the haystack that has never been sorted, and
until it is sorted nobody can say which of it matters — which is
precisely the specification's point.

The year-offset distribution is the useful part: `+1` appears 12 times,
which is the classic off-by-one worth chasing, while `+41` and `+44`
are a filename containing a code rather than a year.

---

## 5. Tests

`tools/test-reader.py` — 30 documents, each one a bug that was fixed,
all passing. It covers vintage detection, press-dossier refusal, prose
extraction and blend reading.

Coverage against the ten priorities the specification lists:

| | |
|---|---|
| identity resolution | PARTIAL — vintage and press cases only |
| fiche-family matching | NONE |
| source/document mapping | NONE |
| provenance | NONE |
| gap detection | NONE |
| duplicate detection | NONE |
| anomaly detection | NONE |
| annual ingestion | NONE |
| scraper failures | NONE |
| reconciliation | NONE |

The seven rules I added today are covered by inline case lists inside
their patch scripts, which ran once and are not part of the suite. That
is a real gap: `named_candidate` and `opens_on_another_wine` have seven
and five cases respectively and neither runs again.

---

## 6. Scorecard

```
REQUIREMENTS (54 traced)
Complete:        13
Partial:         21
Scaffolded:       3
Missing:         16
Unknown:          1

DATA INTEGRITY
Records audited:        3,899
Source-supported:        98.9%
Orphan artifacts:        7,594  (unsorted, not lost)
Suspicious mappings:       174  (67 year + 107 estate)
Unresolved gaps:           129  (84 high priority)
Duplicate byte-groups:     839

TESTS
Relevant tests:    1 suite, 30 cases, all passing
Missing coverage:  9 of 10 priority areas
```

### Highest-risk issues

1. **`site-recipes.json` is read by nothing.** The one artefact that
   would make next year cheap is inert. Highest value per hour of any
   item here.
2. **50 Echo de Lynch-Bages sheets are filed as the white**, costing 5
   vintages of the second wine. The class — manifest `wine` wrong,
   guard then refuses, data silently absent — is worth a sweep, not a
   patch.
3. **Refusals are not retained.** Every "why is X missing" question is
   re-investigated from scratch because the answer was printed and
   thrown away.
4. **No conflict representation.** The first document to state a value
   wins, permanently and silently.
5. **de Braude ↔ Mongravey and Poitevin ↔ Moulin-de-Canhaut** cross-cite
   45 times. Two estate pairs, systematic, cause unknown.

### Recommended next actions, in order

1. **Sort the orphans by kind** — one pass over 7,594 documents
   classifying them (press, duplicate language copy, text layer of a
   PDF already read, genuinely unread). Until this is done, every other
   number here is reported against an unknown denominator.
2. **Sweep the manifest `wine` field** for the Echo class: filename
   names one listed wine, manifest says another. 50 known at one
   estate; the sweep says how many elsewhere.
3. **`data/anomalies.json`**, with `REFUSED` migrated in and refusal
   reasons retained per run.
4. **Make `harvest.py` read `site-recipes.json`.**
5. **Put today's seven rules into `test-reader.py`.**

### Four questions, answered

1. *Did it understand the requirements?* Yes — and `docs/INGESTION-ARCHITECTURE.md`
   maps them to the four memory layers.
2. *Are they implemented end-to-end?* Mostly no. 13 of 54 complete, and
   the complete ones are largely pre-existing dataset and provenance
   work rather than anything built to these specifications.
3. *Is the dataset trustworthy?* The 3,899 records are 98.9%
   traceable to a document, and that is its real strength. Where it is
   not trustworthy is specific and now named: 174 identity conflicts, 44
   unsupported records, and one systematic mis-filing costing 5
   vintages.
4. *What next?* Sort the orphans. Every other number depends on it.
