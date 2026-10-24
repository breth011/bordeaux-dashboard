# The four memories

An audit of this repository against a specification for a persistent
ingestion system: source memory, document memory, dataset memory and
quality memory. Written because the specification asked for an
inspection first, and because the honest answer is that three of the
four already exist in some form and the fourth is the one doing the
least work.

Dated 2026-10-24. Counts are from that day's data.

---

## The ten questions, answered

**1. Where are records stored?**

`data/fiches.js` — the grand vin, keyed `estate|year`, 2,725 records.
`data/cuvees.js` — every other wine, keyed `estate|slug|year`, with
`BDX_CUVEE_WINES` listing which wines each estate makes. Both are
JavaScript object literals, one record per line, loaded by the browser
as `window.BDX_FICHES` and `window.BDX_CUVEES`. There is no database;
the file *is* the store, and one record per line is what makes it
diffable, which is how most of this year's defects were found.

**2. How are vintages represented?**

As part of the key, and as an integer year only. `data/vintages.js`
holds one row per year 1982–2026 with the region's weather, report and
indicative drinking window. Records exist from 1900, and anything
before 1982 is shown separately because the regional rows do not reach
back that far.

**3. How is château identity represented?**

A slug id — `lynch-bages`, `cos-destournel` — assigned in
`data/chateaux.js` and the five other estate files that concatenate
into `BDX_CHATEAUX` (batch2, batch3, graves, libournais, sauternes).
468 estates, of which 61 are the 1855 classified growths. The id is
the only identity; names are display strings, and `sheetreader.says()`
does the fuzzy matching from a document's text or filename back to an
id.

There is no entity-resolution record: no `raw_name -> canonical_entity`
table with confidence and provenance. The matching happens at read
time and is not retained.

**4. How will fiche families be represented?**

Today, badly. `tools/audit-consistency.py` derives a family from the
filename with its digits removed —

    Chateau-Lynch-Bages-2008-EN.pdf  ->  chateau-lynch-bages-####-en
    Lynch-Bages-2012-FT-GB-122.pdf   ->  lynch-bages-####-ft-gb-#

— which is enough to separate an estate's own sheet from a negociant's,
and that separation already earned its keep: alcohol on 10 of
Lynch-Bages' 31 vintages looks like a reading fault until the families
are counted apart, whereupon it is simply the years a negociant sheet
exists.

But a filename is not a structure. It breaks on any estate that renames
its files, it cannot see that two differently-named documents share a
layout, and it says nothing about what the layout *is*. There is no
stored structural signature, no section or label ordering, no record of
where in the document a field sits.

`data/sheet-expectations.json` (written by `--freeze`) is the one piece
of real family knowledge: per family, which fields it is known to yield
and on how many records. That is a yields contract, not a schema.

**5. How are source documents represented?**

`data/sources.json` — 13,032 sheets, each with `file`, `folder`,
`estate`, `estateName`, `wine`, `role`, `colour`, `year`, `url`,
`bytes`, `sha1`, and often `how`, `note`, `slug`.

This is better than the specification assumed: **the content hash and
the byte count are already there, on every sheet.** What is missing
beside them is the retrieval timestamp, the HTTP metadata, and the
scraper version that fetched it. So change detection is possible today
and provenance-in-time is not.

The one wine per sheet is a real limitation, and it is how the Blanc de
Lynch-Bages note reached the grand vin: a negociant sheet covering
three wines is correctly attributed to one of them and still wrong
about the other two. `tools/audit-multiwine.py` now counts these.

**6. How is provenance stored?**

Well, and at the right grain. `data/field-src.js` and
`data/cuvee-src.js` hold **one filename per field per record** — so
`lynch-bages|2012` says its alcohol came from
`Lynch-Bages-2012-FT-GB-122.pdf` and its blend from
`Chateau-Lynch-Bages-2012-EN-paraphe.pdf`. Every figure on screen can
be traced to the document it was read from, and
`data/fiches-url.js` turns that into a link the reader can open.

This is the strongest part of the existing architecture and the
specification's point 10 is already satisfied.

**7. Where does validation currently happen?**

In four places, which is three more than anyone would guess:

- *Inside the reader*, as a guard chain: `whose_sheet()` refuses a
  document before anything is read from it, and the refusal reasons are
  counted and printed per run ("the filename calls this the 2010
  vintage", "the name spells another of the estate's wines in full").
- *At merge time*, as gates in `read-fiches.py`, plus a `REFUSED` pin
  list of specific `(record, field)` pairs that must never be written.
- *After the fact*, as standalone reports: `check-data.py` (every gate
  over everything), `check-language.py` (staleness and Dutch),
  `audit-sources.py` (every record against its sheet),
  `audit-estate.py` (one estate, per vintage), `audit-consistency.py`,
  `audit-multiwine.py`.
- *As a regression suite*: `tools/test-reader.py`, thirty documents
  that have each caused a bug, run before any change to the reader.

What is missing is not validation. It is that none of it is
longitudinal: every check asks "is this record sound?" and none asks
"does this record make sense beside 2019 and 2021?"

**8. How are missing values represented?**

By the absence of the key. `'lynch-bages|2008':{blend:{...},pick:{...}}`
has no `alc` and says nothing about why. The eight kinds of
missingness the specification distinguishes — NOT_PUBLISHED,
NOT_EXTRACTED, EXTRACTION_FAILED and so on — all look identical.

Some of that information exists but is thrown away: the reader knows
whether it refused a document, failed to match a label, or never saw a
document at all, and prints it to a report that nobody keeps.

**9. Is there an error/logging system?**

Per-run reports, not a log. `reports/proposed.txt`,
`reports/fiches-read.txt`, `reports/audit-sources.txt` are each
overwritten by the next run. `progress-history.tsv` is the one
persistent series — one row per day with coverage per field — and it
has four rows.

So there is no ingestion-run record: no "what happened when we imported
2026", no expected-versus-found counts, no comparison with last year's
totals.

**10. Where can an anomaly model go without duplicating what exists?**

Three seams, all already load-bearing:

- `REFUSED` in `read-fiches.py` is a resolved-anomaly store with
  written reasons. It is keyed exactly as the specification asks
  (`record`, `field`) and it survives re-reads, which is the whole
  point. It is in Python rather than in data, so nothing else can
  query it.
- The refusal counters already classify *why* a document was not read.
  They are printed and discarded.
- `reports/estates/*.md` carry a hand-written `## Findings` section per
  estate — 61 of them — which is quality memory in prose, now
  protected by a fingerprint so it cannot silently go stale.

An anomaly model belongs *beside* these, taking the first two out of
code and into data, not replacing them.

---

## What exists, by layer

| layer | exists | where | gap |
| --- | --- | --- | --- |
| **Source** | partly | `data/site-recipes.json`, 10 of 61 estates | not executable; no versions; no failed-attempt memory; no expected counts |
| **Document** | barely | filename families, `sheet-expectations.json` | no structural signature; no stored schema or field positions |
| **Dataset** | yes | `fiches.js`, `cuvees.js`, `field-src.js` | typed missingness |
| **Quality** | partly | `REFUSED`, report `## Findings`, 6 audit tools | nothing longitudinal; no persistent anomaly records; no resolutions in data |

The single most important finding: **`site-recipes.json` is read by no
tool.** `grep -rl site-recipes tools/` returns nothing. Ten estates'
scraping strategies — sitemaps, `{year}` URL patterns, the year range
the site answers for, which wine each pattern belongs to — are written
down in exactly the shape the specification asks for, and
`harvest.py` ignores them and rediscovers each site generically every
time. The knowledge is captured and unused.

---

## The smallest coherent architecture

Four stores and one runner. Everything below already has most of its
inputs in the repo.

### 1. `data/sources-profiles.json` — source memory, made executable

Promote `site-recipes.json` from notes to configuration, keyed by
**domain** rather than by estate, since one negociant site serves many
estates. Add what is missing: `version` with `valid_from`, an
`expected` block (how many documents this source yielded last run), and
`failures` (URL pattern, date, HTTP status) so the same dead pattern is
not retried for a decade.

Then make `harvest.py` read it, and fall back to generic discovery only
where no profile exists. That is the change that turns a year's
investigation into a command.

### 2. `data/fiche-families.json` — document memory, structural

Replace the filename family with a signature built from the document
itself: the ordered sequence of recognised labels, the page count, the
length class. Store per family its members, that label order, the
fields it yields, and — the part that pays for itself immediately —
**anchors for unlabelled content**: Lynch-Bages' tasting note sits
between `Production:` and `Appellation` in all 26 of its sheets, which
is why 640 records archive-wide have no tasting note while their
documents carry one.

### 3. `data/anomalies.json` — quality memory, longitudinal

One record per anomaly: `kind`, `severity`, `estate`, `year`, `field`,
`why` in prose, `evidence`, and a `resolution` a person can set
(`CONFIRMED_ERROR`, `CONFIRMED_VALID`, `NOT_PUBLISHED`,
`KNOWN_EXCEPTION`). `REFUSED` migrates into it and keeps its reasons.
Resolutions persist, so nothing is flagged twice.

### 4. `reports/ingestion/<year>.json` — the run record

Expected versus found, per source and per estate, with the previous
year's numbers beside them. This is what makes a silently halved
dataset impossible to miss.

### The runner

`tools/ingest.py --year 2026`, which is the sequence
`docs/ADDING-A-VINTAGE.md` already documents as seven commands, with
the longitudinal checks added between extraction and commit, and the
run record written at the end.

---

## Build order

Smallest increments that each stand alone and each find real defects.

1. **The longitudinal matrix.** Per estate, per field, per vintage:
   present, absent, or absent-with-neighbours-present. This is the
   specification's points 2, 4, 5, 6 and 23 at once, it needs no new
   data model, and its inputs are all in `fiches.js` and
   `sheet-expectations.json` today. It is also the check that would
   have found the Lynch-Bages gap without being told to look.
2. **`data/anomalies.json`,** populated by that matrix, with `REFUSED`
   migrated in and resolutions honoured.
3. **Structural fiche families,** replacing the filename proxy, with
   anchors — which then recovers the unlabelled prose that the
   name-and-vintage rule cannot reach (3,860 documents).
4. **Executable source profiles,** and `harvest.py` reading them.
5. **The run record and `tools/ingest.py`.**

Steps 1 and 2 are a day's work on existing data. Steps 3 and 4 are the
ones that make next year cheap.

---

## What this audit does not recommend

**Typed missingness on every field.** Eight states per field would be
a rewrite of the data files, the reader, the app and the workbook, and
the longitudinal matrix infers what matters — a gap with neighbours
either side — from presence alone. Revisit it if the matrix proves
insufficient, not before.

**A database.** One record per line in a JavaScript file is how a
defect becomes a diff, and the browser loads the store directly with no
build step. Both are load-bearing.

**Merging the six audit tools into one.** The specification warns
against "a collection of one-off validation scripts", and that warning
is fair — `audit-consistency.py` and `audit-multiwine.py` were both
written this week. But they are capabilities with distinct questions,
and the fix is that the runner calls them and the anomaly store
receives them, not that they become one file with five flags.
