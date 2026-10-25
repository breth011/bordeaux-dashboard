# Historical model M2: document dates

*2026-10-25. Follows M1 (3b1d543). The model gains a document's own date, taken only from the
document's own words. Nothing else historical is written.*

M2 answers one question for each of the 37,067 held documents: does the text say when it was
itself published, issued, posted or updated? Where it says so once and plainly, the model gains
one `ArtifactDate` of kind `STATED_IN_TEXT` on the calendar axis. A DOCUMENT provenance quotes the
words and gives where they stand. Every other document keeps no date. The audit records why.

**Result: 79 documents dated, 37,067 decided.** M2 preferred fewer correct dates over many
questionable ones. Before the rules were tightened they accepted 136 dates. A manual review of
those 136 found press quotes, book references, cookie banners and site-wide footers among them.

## 1. What was built

| File | Role |
|---|---|
| `tools/document_dates.py` | The rules. Pure functions, no input or output, no clock. `VERSION = 'document-dates/1'`. |
| `tools/extract-document-dates.py` | Applies the rules to every artifact. Writes the audit. `--check` rebuilds and compares the audit byte for byte. `--dry-run` writes nothing and lists the rows the model would gain. |
| `data/history/document-dates.jsonl` | The audit: one row per artifact, with its category, its flags and, where a date was accepted, the date, label, quote and locus. |
| `tools/mig_m6_provenance.py` `document_dates(m)` | Copies the audit's accepted rows into the model: one `Provenance` (DOCUMENT) and one `ArtifactDate` for each. |
| `tools/historical_m2_scope.py` | Defines what M2 may change in `data/model/`. The earlier suites use it instead of asserting that nothing changed. |
| `tools/test-historical-m2.py` | 20 checks: the 16 required cases and 4 whole-model checks. |

The audit lives in `data/history/`. That directory is in no protected group, so M2 writes it
without touching anything the baseline guards. The migration reads the audit, the same way it
reads the evidence store. It never writes the audit.

## 2. Method

1. **Text already held, nothing parsed again.** Each document is read from its discovery
   extraction (`sources/discovery/extracted/<sha256>.json`, status `EXTRACTED`), in this order:
   title, headings, blocks, PDF pages, tables. A plain-text page with no extraction is read as
   its own lines. A PDF whose text was never extracted is not parsed here: it is `NO_TEXT_HELD`.
   This keeps the audit reproducible from the store alone. The cost is shown in §8.
2. **Only a labelled date counts.** The date must follow a label that names the document's own
   date:
   - French publication labels: *publié le*, *paru le*, *mis en ligne le*, *édité le*, *date de
     publication*;
   - French update labels: *dernière mise à jour*, *mis à jour le*, *mise à jour*, *révisé le*,
     *modifié le*;
   - English publication labels: *published (on)*, *posted (on)*, *issued*, *issue date*,
     *publication date*;
   - English update labels: *last updated*, *updated*, *last modified*, *revised*, *revision
     date*.

   A bare date, a year in a heading or a date in running prose is never accepted.
3. **Only where a document dates itself.** A labelled date is read only in these places:
   - on a PDF's first page;
   - on a web page, in the two blocks before its `h1` or the four after it, where a post's byline
     sits;
   - in a text file, in its first eight lines.

   A labelled date anywhere else, such as a footer, a teaser for another post or a sidebar, is
   `REJECTED_ELSEWHERE_ON_PAGE`. A page with no `h1` has no such place.
4. **Not when it dates something the text names.** A mention is external in four cases:
   - it follows a comma: *"…, par Isabelle Spaak, publié le 22/10/2021"* dates the book;
   - it is the predicate of a sentence: *"le classement … **est** publié le 20/02/2020"* dates the
     classification;
   - its sentence is about another document, such as a cookie or privacy policy, terms,
     *conditions générales* or *mentions légales*;
   - a critic's score follows it: *"Top 100 … publié le 22/11/2022 – 95"*.
5. **One date, or none.** The decision depends on how many dates remain:
   - several distinct dates are `AMBIGUOUS`;
   - a numeric date that an English label leaves unclear (03/04/2020) is `AMBIGUOUS`;
   - a labelled update next to an unlabelled first date is `AMBIGUOUS`: the page has a
     publication and a revision, and only one of them says which it is.

   Nothing is chosen between candidates.
6. **Plausible.** A date after the document's first retrieval, or before 1900, is
   `REJECTED_IMPLAUSIBLE`.
7. **Everything else names its reason.** The file name, the address, a vintage line, embedded
   metadata and the retrieval are recorded as *flags*, never as a value. When no date is accepted,
   the category is the first of these that applies:
   - an external reference;
   - a date elsewhere on the page;
   - a year in the file name;
   - a year in the URL;
   - a vintage;
   - metadata;
   - a retrieval date.

   The flags list every reason that applies. A sheet named `…-2020.pdf` that prints *Millésime
   2020* is therefore `REJECTED_FILENAME_ONLY`, with `vintage_year` among its flags.

Numeric dates: under a French label they are read day first. Under an English label they are
read only when one part is above 12 or both parts are equal. French and English month names and
their abbreviations (*avr.*, *juil.*, *oct.*) are read.

## 3. Acceptance rules, in one line each

- **A1:** the date stands in the document's own text, not in its metadata, file name, address or
  retrieval.
- **A2:** it follows a label that names the document's own publication or update.
- **A3:** it stands where the document dates itself: the first page, by the main heading, or the
  opening lines.
- **A4:** it does not date something the sentence names (appositive, predicate, another document,
  a press quote).
- **A5:** it is the only date that survives A1 to A4; otherwise the document is AMBIGUOUS.
- **A6:** it is no later than the document's first retrieval and no earlier than 1900.
- **A7:** it is written at the precision printed (DAY, MONTH or YEAR), kind EXACT, axis
  CALENDAR, with a DOCUMENT provenance as its basis.

## 4. Counts

| Category | Documents |
|---|---:|
| ACCEPTED_DOCUMENT_DATE | **79** |
| AMBIGUOUS | 11 |
| REJECTED_EXTERNAL_REFERENCE | 56 |
| REJECTED_ELSEWHERE_ON_PAGE | 32 |
| REJECTED_IMPLAUSIBLE | 0 |
| REJECTED_FILENAME_ONLY | 10,014 |
| REJECTED_URL_ONLY | 6,509 |
| REJECTED_VINTAGE_ONLY | 2,875 |
| REJECTED_METADATA_ONLY | 5,177 |
| REJECTED_RETRIEVAL_DATE | 6,462 |
| NO_DOCUMENT_DATE | 1 |
| NO_TEXT_HELD | 5,851 |
| **Total** | **37,067** |

The 79 accepted dates break down as follows:

- **Label:** 68 PUBLISHED, 11 UPDATED.
- **Precision:** 74 DAY, 5 MONTH, 0 YEAR.
- **Where they stand:** 74 by a web page's h1, 4 on a PDF's first page, 1 in a text file's
  opening lines.
- **Range:** 2012-10-04 to 2026-10-08.

The categories added beyond the brief:

- REJECTED_URL_ONLY: the brief names URLs among the rejected sources.
- REJECTED_METADATA_ONLY: PDF information, `<meta>` tags and JSON-LD dates.
- REJECTED_ELSEWHERE_ON_PAGE.
- REJECTED_IMPLAUSIBLE.
- NO_TEXT_HELD.

## 5. Coverage by document type

| Type | Documents | Accepted | Ambiguous | External / elsewhere | File name | URL | Vintage | Metadata | Retrieval | No date | No text |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HTML | 20,090 | 74 | 11 | 49 / 32 | 1,685 | 6,008 | 2,484 | 4,770 | 4,976 | 0 | 1 |
| PDF | 12,189 | 4 | 0 | 5 / 0 | 5,911 | 455 | 385 | 407 | 30 | 0 | 4,992 |
| Plain text | 2,502 | 1 | 0 | 0 / 0 | 2,396 | 1 | 0 | 0 | 0 | 1 | 103 |
| Image | 612 | 0 | 0 | 0 / 0 | 0 | 0 | 0 | 0 | 0 | 0 | 612 |
| Other | 1,674 | 0 | 0 | 2 / 0 | 22 | 45 | 6 | 0 | 1,456 | 0 | 143 |

Technical sheets, which are most of the PDFs, almost never print their own date. They print a
vintage. A web page dates itself only when it is a post (a journal entry, news, a recipe) or a
legal page (a privacy policy or terms). The 79 come from 14 sites and one text file:

- Ripeau's news pages (41);
- Pontoise Cabarrus's journal (17);
- Rollan de By's posts (5), a Caillou event post, and one post held as a text file (ar_010129);
- Bibian's terms of sale, in French and English;
- the privacy and terms pages of Lafon du Berger, Guiraud, Grand Brun, Olivier and Lamothe Bergeron.

They also include four PDFs whose first page dates them: a Sud Ouest article (Micalet), a Wine
Advocate review (Larcis Ducasse), a Figaro Vins review (Corbin), and the Boyd-Cantenac and Pouget
press book, whose cover reads "Mise à jour : 14 juillet 2020".

## 6. Ambiguity examples

All 11 AMBIGUOUS documents are Vieux Landat recipe posts (9 English, 2 French), each with an
unlabelled first date and a labelled update. Examples:

| Artifact | Candidates |
|---|---|
| ar_013494 | unlabelled "Apr 13, 2021" (b:24) · "Updated: Oct 14, 2023" (b:26) |
| ar_030798 | unlabelled "21 avr. 2020" (b:24) · "Dernière mise à jour : 14 oct. 2023" (b:26) |
| ar_024190 | unlabelled "6 févr. 2020" (b:24) · "Dernière mise à jour : 19 avr. 2021" (b:26) |

The earlier version of the rules also left this case AMBIGUOUS: an English label over 03/04/2020.
It is in the tests (c04).

## 7. Manual spot checks

| Case | Artifact | What the document shows | Decision |
|---|---|---|---|
| A printed date | ar_023367 (Sud Ouest PDF) | p:1 "Publié le 04/10/2012 à 06h00 Par Julien Lestage" | ACCEPTED 2012-10-04 DAY ✔ |
| Several dates | ar_012197 (Pontoise Cabarrus journal) | h1, then "Publié le 02/01/2023", then "Le nouveau classement des crus bourgeois **est publié le** 20/02/2020" | ACCEPTED 2023-01-02. The 2020 date is the classification's (predicate rule) ✔ |
| A vintage sheet | ar_017452, ar_017555 (Las Cases sheets) | page 1 opens "2007 TERROIR…", "2021 TERROIR…" | REJECTED_VINTAGE_ONLY ✔ |
| Filename only | ar_000619 (gruaud-larose.com/…/2021/03/…-2019-fr.pdf) | the address carries 2021/03 and 2019. The text carries phenology dates (15-mars, 24-mai) | REJECTED_FILENAME_ONLY. Neither the upload path nor the phenology is taken ✔ |
| A revised document | ar_013494 (Vieux Landat recipe) | "Apr 13, 2021" · "Updated: Oct 14, 2023" | AMBIGUOUS. The revision is not taken for the document's date ✔ |
| No date | ar_003234 (Romer page text) | years in the prose, no dating label | NO_DOCUMENT_DATE ✔ |
| Multilingual | ar_020120 / ar_027093 (Bibian terms, FR / EN) | "Dernière mise à jour : 18/04/2025" / "Last updated: 04/18/2025" | both ACCEPTED 2025-04-18. The French label reads day first. The English date is read because 18 > 12 ✔ |
| Spam terms page | ar_013303 (vignobles-lacombe.com/terms) | "Dernière mise à jour : 5 October 2026" in block 72, far from the h1 | REJECTED_ELSEWHERE_ON_PAGE ✔ |
| A book reference | ar_015765 and three more | "by Isabelle Spaak, published on 22/10/2021" | REJECTED_EXTERNAL_REFERENCE ✔ |
| A press quote | ar_000185, ar_001285, ar_009321 | p:2 "Top 100 … publié le 22/11/2022" | not page 1, so not read. REJECTED_EXTERNAL_REFERENCE ✔ |

Each of the 79 accepted rows was read in its context (the h1, the dating block and the blocks
around it). This includes the ten privacy and terms pages, whose "last updated" stands directly
under their own h1 and is their own date.

## 8. Provenance and its limits

Each date's provenance is a `Provenance` of kind DOCUMENT with these fields:

- `actor` is `tools/extract-document-dates.py`;
- `artifact` is the dated document;
- `quote` holds the dating words with about 30 characters of context;
- `code_state` holds `{extractor: 'document-dates/1', label, locus, text}`;
- it has no `at`: M2 reads no clock.

The `ArtifactDate.value.basis` is that provenance id.

Limits:

- **The locus is relative to the extraction**, not to the bytes. `b:49` is the 49th block of the
  discover-extract/1.0 reading of the page. A different extractor version may number the blocks
  differently.
- **4,992 PDFs and 612 images hold no extracted text.** They are NO_TEXT_HELD. A date they print
  is unread, not absent.
- **Quote encoding.** The quote is the extraction's text, so it carries what the extractor read,
  including its whitespace normalisation.
- **Metadata dates are not used.** Most PDFs (§ Phase 3.4: 93 %) carry an information-dictionary
  date and many pages carry `<meta>` or JSON-LD dates. They are recorded as the flag
  `metadata_date` only. ArtifactDate kinds PDF_METADATA, HTTP_LAST_MODIFIED, UPLOAD_PATH and
  RETRIEVED stay unpopulated.

## 9. What M2 did not do

M2 inferred no date of any event, name, ownership, classification or appellation. In the model:

- no Observation gained `claimed_validity`, `claimed_window` or `statement_mode`;
- no IdentityTransition was written;
- no Reconciliation gained `dispositions`;
- no name became non-CURRENT;
- no conflict was resolved, D5 was not adopted and D2 was not resolved.

Every state record is still "current, start unknown". No date came from:

- a vintage;
- a retrieval or crawl date;
- a file's mtime;
- a file name, URL or upload path;
- embedded metadata.

The application and its generated data are unchanged.

### Before and after

| Quantity | Before (3b1d543) | After |
|---|---:|---:|
| ArtifactDate rows | 0 | **79** |
| Provenance rows | 25,895 | 25,974 (+79, all DOCUMENT by the M2 actor; none changed or removed) |
| Observations with claimed_validity / claimed_window / statement_mode | 0 | 0 |
| IdentityTransitions | 0 | 0 |
| Reconciliations with dispositions | 0 | 0 |
| Names not CURRENT | 0 | 0 |
| Other model files | — | byte-identical |
| `data/app/` | — | byte-identical (`build-app-data.py --check`) |
| Protected groups | — | unchanged (`phase4-baseline.py --check`) |

## 10. Tests

`tools/test-historical-m2.py` runs 20 checks.

The 16 required cases (c01–c16):

1. explicit date;
2. year precision;
3. month and day precision;
4. several dates unresolved;
5. filename only;
6. URL only;
7. retrieval, metadata and implausible;
8. vintage;
9. referenced dates not promoted (classification, book, press, policy, cookie, event years,
   elsewhere on the page);
10. calendar axis;
11. provenance present;
12. two versions keep their own dates;
13. a missing date stays absent;
14. no historical claims;
15. no transitions;
16. no dispositions.

The four whole-model checks:

- every accepted date stands on page one or by the heading;
- the audit is reproducible (`--check`);
- the model changed only by M2's additions;
- generated data and protected groups are unchanged.

The earlier suites asserted that the model never changed: test-historical-m1 and the
model_and_protected checks of test-phase61, 63, 65, 67 and 69, and test-phase5's
normalized_model_byte_identical. They now call
`historical_m2_scope.model_changes_are_m2_only(BEFORE)`. That call names exactly M2's three
files and requires every row present before to be there byte for byte. It requires every added
row to be an M2 STATED_IN_TEXT date or its DOCUMENT provenance. It requires the manifest to
differ only in those two files and one M6 statistic. M1's `nothing_populated` now allows
ArtifactDate rows of kind STATED_IN_TEXT only, and its row count c20 adds exactly M2's rows. No
check was removed or skipped.

## 11. Regression

| Check | Result |
|---|---|
| M0 validator (`docs/schema/check_historical_m1_proposal.py`) | all pass |
| `tools/test-historical-m1.py` | 24 checks, all pass |
| `tools/test-historical-m2.py` | 20 checks, all pass |
| Full suite (`tools/run-tests.py`) | **29 suites, 784 checks, all pass** (was 28 / 764; +20) |
| `tools/migrate.py --check` | the model rebuilds byte for byte |
| `tools/phase4-baseline.py --check` | protected groups unchanged (canonical, evidence, discovery, scope, review, phase records, phase34_model) |
| `tools/build-app-data.py --check` | `data/app/` is the model, byte for byte; no application change |
| `tools/extract-document-dates.py --check` | the audit is current and reproducible |

The full run took 389 s with 2 workers, against about 300 s at M1. The difference is the new
suite (190 s), mostly `the_audit_is_reproducible`, which reruns the extractor over every document
(about 105 s).

The first full run found two older checks this section's rescoping had missed. Both were
rescoped in the same way:

- test-phase5 `normalized_model_byte_identical` diffed `data/model` against Phase 4;
- test-historical-m1 c20 counted 333,022 rows.

M2 adds 158 rows to that count: 79 dates and their 79 provenances.

## 12. Deferred

These are listed in `docs/BACKLOG.md` under "Document dates":

- extracting text from the 4,992 PDFs that never had it;
- populating the metadata kinds of ArtifactDate as clues of their own;
- detecting boilerplate dates repeated across a site.
