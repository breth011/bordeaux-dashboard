# Evidence census

Phase 1 of the remediation. Investigation only: no record was created,
deleted or changed, no provenance overwritten, no manifest identity
reassigned, no candidate promoted. 2026-10-24, analyzer version 1,
commit 84d690f.

The three identities are kept apart throughout. **The manifest is
metadata. The documents are evidence. The dataset is a hypothesis.**

---

## 1. What changed

| file | what it is |
| --- | --- |
| `tools/census.py` | new. Reads every artifact and records manifest identity, observed identity and a conclusion, separately. Writes only the census. |
| `tools/census-compact.py` | new. Rewrites the census as one artifact per line. |
| `tools/census-conflicts.py` | new. Sorts the conflicts into kinds. Metadata only, writes nothing. |
| `tools/reconcile.py` | from the audit. Unchanged. |
| `data/artifact-census.jsonl` | new. 13,032 lines, one per artifact, 9.4 MB. An analysis, not a source of truth. |
| `tools/test-reader.py` | 23 cases added, all pure text so they run without the archive. |
| `tools/test-data.py` | new. 7 invariants over the committed data. |
| `docs/EVIDENCE-CENSUS.md` | this. |

Not touched: `data/sources.json`, `fiches.js`, `cuvees.js`,
`field-src.js`, `cuvee-src.js`.

---

## 2. Orphan census

7,591 artifacts are cited by no record. By what the document turns out
to be:

| conclusion | n | what it means |
| --- | --- | --- |
| POSSIBLE_MISSING_RECORD | 3,343 | carries wine data, nothing cites it |
| DOCUMENT_IDENTITY_CONFLICT | 1,217 | names an estate the manifest does not |
| POSSIBLE_DUPLICATE | 906 | shares its bytes with another artifact |
| NOT_A_DATA_DOCUMENT | 836 | no wine figure or passage in it |
| POSSIBLE_MULTI_WINE_DOCUMENT | 598 | names several of the estate's wines |
| LEGITIMATE_NON_RECORD | 329 | press, event, catalogue, price list |
| MANIFEST_METADATA_WRONG | 241 | the document names a different wine |
| UNRESOLVED | 121 | unreadable or absent from disk |

By document kind:

| kind | orphans | kind | orphans |
| --- | --- | --- | --- |
| DATA_SHEET | 2,706 | IMAGE_ONLY | 428 |
| PRODUCER_PROFILE | 1,446 | PRESS_DOSSIER | 367 |
| UNKNOWN | 497 | NEWS_ARTICLE | 295 |
| WEBSITE_COPY | 476 | TECHNICAL_SHEET | 459 |

**The answer to "how many of the 7,594 are candidates for wine
evidence" is 3,343, not 7,594.** The audit was right to refuse the
larger number. Of the rest, 1,165 are demonstrably not data documents
at all (NOT_A_DATA_DOCUMENT plus LEGITIMATE_NON_RECORD), 906 are
copies of something already held, and 1,217 cannot be acted on until
their identity is settled.

Across the whole archive, 11,094 of 13,032 artifacts carry at least
one wine-data signal and 1,938 carry none.

### The finding that was not in the audit

**908 artifacts have no `estate` in the manifest at all.** Every reader
iterates sheets by estate, so these are offered to nothing, however
good the document is. 904 of the 908 sit in a folder that names an
estate, and 786 of them carry wine data. Reading them identified an
estate for 360.

Concentrated: doisy-daene 287, Bellefont-Belcier 100,
Tour-Saint-Christophe 100, d'Argan 84, Moulin-du-Cadet 74, Sansonnet 74.

486 of them are POSSIBLE_MISSING_RECORD. This is the largest single
block of recoverable evidence found, and the cheapest, because the
folder already names the estate.

---

## 3. Identity conflicts

| | n | note |
| --- | --- | --- |
| wine: manifest vs filename | **56** across 5 estates | the Echo class |
| estate: document vs record | 36 filename-edges / 107 sheet-row edges | 13 pairs |
| vintage: document vs record | 19 after reclassification | see below |
| multi-wine documents | 1,465 | names more than one of the estate's wines |

Two different units are reported for the estate conflicts on purpose.
`reconcile.py` counted 107 by walking manifest rows, and a document
registered under four estates contributes four. Walking unique
filenames gives 36. Both are true; the audit's 107 was the row count.

### Is the Echo case systemic? Mostly not.

56 sheets across 5 estates, and **50 are Lynch-Bages** — 89% at one
estate. The others: Léoville-Poyferré 2, Fleur-Cardinale 2, Mouton 1,
Grand-Puy-Lacoste 1. So the class is real and the instance is
isolated.

Getting that number took two wrong answers first, and both are worth
recording because they are the shape of mistake this phase exists to
avoid. Asking "does the filename name a different listed wine" gave
**122** — including every `2010-Opalie-de-ChateauCoutet.pdf`, where the
manifest correctly says `Opalie de Château Coutet Blanc` and the
filename merely omits the word "Blanc". Requiring the two names to be
*disjoint* then gave **3**, because that discards "blanc", which is the
very word separating the Blanc from the Echo. The test that holds is
**subset**: a longer spelling of the same wine contains the shorter
one, and a different wine does not.

### Year conflicts, reclassified

19 of the 67 survive as conflicts between a filename year and a record
year. The rest were artefacts of counting rows rather than files.

| kind | n | example |
| --- | --- | --- |
| FILENAME_CODE_NOT_YEAR | 8 | `FT-Ch-de-Braude-2016-GB.pdf` cited by a 1984 record — an estate mix-up, not a year code |
| AMBIGUOUS | 7 | Moulin-Rouge: every record cites the document of the year before |
| TRUE_VINTAGE_CONFLICT | 2 | `CS_A6_Carnet_Degust_Mars_2025.pdf` on calon-segur 2024 |
| DOCUMENT_DATE_NOT_VINTAGE | 2 | `fiche-2024-...-primeur-francais.pdf` on a 2023 wine — correct: a primeur sheet is published the spring after |

My own classifier is wrong on the 8: it labelled them
FILENAME_CODE_NOT_YEAR because the gap exceeds 12 years, when the real
cause is the de Braude/Mongravey estate mix-up below. Recorded as a
defect in the classifier, not corrected, because correcting it would
mean guessing which of the two causes applies.

The Moulin-Rouge 7 are the most interesting: `...2011.pdf` cited by the
2014 record, `...2015.pdf` by 2017, `...2009.pdf` by 2011, `...2010.pdf`
by 2012. Not a constant offset, so not a simple off-by-one — this
estate's sheets appear to be mis-dated at source or mis-filed in a
pattern that wants reading.

---

## 4. Duplicate analysis

839 identical-byte groups.

| | groups |
| --- | --- |
| all members share one estate, or none | 526 |
| two or more **different named** estates | 309 |
| one named estate plus an unattributed copy | 4 |

And the 309, split by what actually causes them:

| | groups | verdict |
| --- | --- | --- |
| **one filename, registered under several estates** | **295** | legitimate group document |
| several filenames, same bytes | 14 | downloaded twice |

The 313 cross-wine groups the audit flagged as "a major diagnostic
signal" are overwhelmingly **correct behaviour**. `LR-Rapport-2023-ANG-entier.pdf`
is the Domaines Barons de Rothschild annual report and genuinely
concerns Lafite, Duhart-Milon, L'Évangile and Rieussec; the manifest
registers it once per estate, which is the specification's own
"multiple artifacts → same record is valid" case seen from the other
side. `Fiche-technique_ClarteHB_2016_EN.pdf` is La Clarté de
Haut-Brion, made jointly by Haut-Brion and La Mission, filed under
both.

The 14 are WordPress double uploads — `_EN.pdf`, `_EN1.pdf`,
`_EN-1.pdf` — of the same sheet, landing under two estates.

**Also found: 4 zero-byte artifacts.** `LR-Rapport-2023-planche.ocr.txt`
is registered four times, once per Rothschild estate, and is empty. An
OCR run produced nothing and the nothing was recorded as evidence. Its
sha1 is the hash of the empty string, which is how it surfaced.

### Text layer vs PDF

| | n |
| --- | --- |
| `.txt` artifacts | 2,616 |
| of those, `.ocr.txt` | 36 |
| stems with both a PDF and a `.txt` | 33 |
| `.txt` with no PDF of the same stem | 2,435 |
| PDF with no `.txt` of the same stem | 9,421 |

**The audit's "2,711 `.txt` duplicating PDFs" was wrong, and this
corrects it.** There are 2,616 `.txt` artifacts and only 33 have a PDF
of the same stem. The other 2,435 are crawled web pages — the only
representation of that source there is. Classifying them as duplicates
would have discarded the entire `pages/` corpus, which is 2,580
artifacts and the source of every record at Margaux, Palmer and Latour.

Reading cost confirms it independently: 11,897 distinct byte-sets
across 13,032 artifacts, so exact duplication accounts for 1,135
artifacts, not 2,711.

---

## 5. The 129 gaps

A gap here is an (estate, year) where the manifest has a document and
no record exists. Classified from the census:

| conclusion | n |
| --- | --- |
| EXISTING_RECORD_UNDER_OTHER_IDENTITY | 50 |
| POSSIBLE_MISSING_RECORD | 45 |
| REFUSED_BY_RULE | 19 |
| LEGITIMATE_NON_RECORD | 9 |
| UNRESOLVED | 6 |

Confidence: HIGH on the 50 (the Echo sheets, whose destination is
named by their own filenames); MEDIUM on the 45; LOW on the rest.

The clearest single case, reached in one command
(`reconcile.py --estate lynch-bages`):

```
lynch-bages 1990   priority HIGH
   - the same sheet family covers 26 other vintages that ARE on record
   - 1 document for 1990 that nothing cites:
       Chateau-Lynch-Bages-1989-FR.pdf
```

— and the answer is in the evidence: the document's own filename says
1989, which is why the reader refused it for 1990. Conclusion
REFUSED_BY_RULE, correctly, and no 1990 record should be made.

---

## 6. The 44 unsupported records

| | n | what it is |
| --- | --- | --- |
| cites a URL, not a filename | **37** | all Latour, 1982–2018 |
| cites a filename absent from the manifest | 6 | Biston-Brillette, Pagodes de Cos, La Mission ×2, Valandraud, Belle-Brise |
| cites no document at all | 1 | `bourgeois-chateau-poitevin\|2023` |

The 37 are not missing evidence. Latour's vintage pages were read from
the web and `src` holds
`chateau-latour.com/en/a-time-for-sharing/vintages/...` — a real and
checkable source in the wrong *shape*, because the manifest is keyed
by filename. This is a provenance-format gap, not an evidence gap, and
it is 84% of the 44.

The one record citing nothing is the only true unsupported record in
the dataset.

---

## 7. Systematic bugs, ranked

| # | affected | pattern | root-cause hypothesis | confidence |
| --- | --- | --- | --- | --- |
| 1 | 908 artifacts | no `estate` in the manifest, so no reader ever sees them | the harvester registered them before attribution and nothing went back | HIGH |
| 2 | 56 sheets | manifest `wine` names a different wine from the filename | the cuvée matcher picked the first of several wines sharing the estate's name; `Blanc` and `Echo de Lynch-Bages` both reduce to `de Lynch-Bages` | HIGH |
| 3 | 50 of those 56 | 5 Echo vintages have a document and no record | consequence of #2: offered to the Blanc, refused by the guards, never offered to the Echo | HIGH |
| 4 | 35 edges | de Braude ↔ Mongravey cross-citation | **one website, two estates.** Both are Vignobles Bernaleau; the crawl put `vignobles-bernaleau.com` PDFs in one estate's folder and the reader then assigned each by its filename. **The records are right and the manifest folder is wrong.** | HIGH |
| 5 | 10 edges | Poitevin ↔ Moulin-de-Canhaut | same shape, same owner | HIGH |
| 6 | 7 records | Moulin-Rouge cites the previous year's document, with a varying gap | unknown; needs the documents read | LOW |
| 7 | 15 edges | Haut-Brion → La Mission | La Clarté is made by both; legitimate, and the manifest's `folder` and `estate` disagree with each other | HIGH |
| 8 | 4 artifacts | empty `.ocr.txt` registered as evidence | an OCR failure recorded as a success | HIGH |
| 9 | 2 records | one year off their own document | individual, not systematic | MEDIUM |

The most important line is #4. The direction is the opposite of what
the audit feared: where the manifest and a record disagree about the
estate, **the record is usually right**, because it was assigned by
reading the document while the manifest was filled from the folder the
crawler happened to use. The manifest really is metadata, and this is
the evidence for it.

---

## 8. New persistent evidence

`data/artifact-census.jsonl` — 13,032 lines, one artifact per line,
sorted by estate and path. The header line carries
`analyzer_version`, `analyzed_at` and the git `commit`, so any line's
classification is attributable to the version that made it. Each line
holds:

```
id, path, url            the artifact
m                        MANIFEST identity (estate, wine, vintage, role)
o                        OBSERVED identity (estate, wine, vintage,
                         document type, data signals)
conf                     per-field confidence: HIGH / MEDIUM / LOW /
                         UNKNOWN
ev                       the evidence each observation rests on
status                   the CONCLUSION, one of the nine
why                      why that conclusion, in prose
dup                      byte-group and its size, where shared
recs                     the records citing it, where any do
v                        analyzer version
```

The three layers are never merged. A line can say
`m.wine = "Blanc de Lynch-Bages"`, `o.wine = ["Echo de Lynch-Bages"]`,
`status = MANIFEST_METADATA_WRONG` and change nothing.

JSON Lines rather than one array, for the reason `fiches.js` is one
record per line: a change in one artifact's classification is a
one-line diff. The cost is 9.4 MB in the repository, and a future
analyzer version will rewrite most lines; if that becomes a burden the
file belongs in `reports/` with only the header committed.

Nine conclusions are in use: MATCH, POSSIBLE_MISSING_RECORD,
DOCUMENT_IDENTITY_CONFLICT, POSSIBLE_MULTI_WINE_DOCUMENT,
POSSIBLE_DUPLICATE, NOT_A_DATA_DOCUMENT, MANIFEST_METADATA_WRONG,
LEGITIMATE_NON_RECORD, UNRESOLVED. "Missing" is never used as a
bucket.

---

## 9. Tests

| | before | after |
| --- | --- | --- |
| `tools/test-reader.py` | 30 cases, all needing `sources/` | **53** — 23 added, all pure text |
| `tools/test-data.py` | — | **7** invariants over committed data |

The 23 reader cases protect the rules written today, which until now
lived in one-off patch scripts that ran once: the unlabelled tasting
note that names its wine (7 cases, including the past-passive refusal
and the three notes carrying no tasting vocabulary at all), the
other-wine guard (5, including the comparison that must *not* fire),
the document-title cut (7, including the all-caps headline that must
survive), Margaux's `20x22` typo and the French clock times beside it
(2), and a structural check that both of `read-plantings`' label
patterns have the capture group their shared `return` statement
requires (2) — the bug that silently discarded 70 documents.

The 7 data invariants are the defects above, each pinned at the count
it was found at, asserted as "no worse than": 56 mis-filed wines, 908
unattributed artifacts, 4 empty files, 14 double downloads, 44
unsupported records, 2 off-by-one records, and that the census names
its analyzer version.

A baseline is not a target. Every one is expected to fall.

Still untested, from the specification's list: refusal persistence
(nothing persists yet), conflicting field sources (the data cannot
express a conflict), orphan→candidate and record→source (covered by
tools, not by assertions).

---

## 10. What must NOT be fixed yet

| | why not |
| --- | --- |
| The 50 Echo sheets | the destination is clear, but refiling means writing `sources.json`, which this phase forbids. It is also the test case for whether a manifest correction is safe at all. |
| de Braude ↔ Mongravey | the hypothesis is one website and two estates. It needs confirming against `vignobles-bernaleau.com` before 35 rows are touched, and the records appear already correct. |
| The 908 unattributed artifacts | the folder names an estate, which is strong but is exactly the kind of inference that produced the mis-filings in the first place. Reading identified only 360 of 908. |
| The Moulin-Rouge year pattern | 7 records cite the previous year's document with a varying gap. No hypothesis survives the evidence yet. |
| The 1,217 identity conflicts | my own year classifier is wrong on 8 of 19 cases. A classifier that is wrong 40% of the time on its smallest category does not get to drive changes. |
| The 3,343 candidates | each needs its wine and vintage settled individually. Promoting them in bulk is how 7,594 would become a fabrication. |
| Latour's 37 URL-cited records | the evidence is real; only the shape is unusual. Changing the provenance format touches every reader. |

---

## 11. Recommended Phase 2

In order, smallest and safest first.

1. **Persist refusals.** The specification's item 9, and nothing else
   can be measured honestly without it: a document refused every year
   is still indistinguishable from one that never existed. One file,
   written by the readers that already compute the reason.
2. **Attribute the 908.** Largest recoverable block, and the cheapest
   test of whether manifest corrections are safe, because the folder
   already names the estate and 360 are confirmed by reading. Propose
   per artifact, apply only where the document and the folder agree.
3. **Then the 56 mis-filed wines**, with the Echo 50 as the worked
   case, and a regression test that the count falls to 6.
4. **Confirm the two shared-site pairs** by fetching one page from
   `vignobles-bernaleau.com` and one from Poitevin, then correct the
   manifest `folder`/`estate` — not the records, which are right.
5. **A conflict representation**, so "first writer wins" stops being
   invisible. 674 records draw their fields from more than one
   document and not one disagreement is recorded, because the losing
   value was never written.

Item 5 is also the honest answer to the specification's request to
quantify "first writer wins": it cannot be quantified from the data as
stored. 674 records draw on several documents; whether any of them
disagreed is information that was discarded at merge time and would
have to be recomputed by re-reading every document.

Do not start Phase 2 without saying which of these to take.
