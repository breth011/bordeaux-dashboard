# Château Palmer — third growth, Margaux

<!-- fingerprint f29595e66a9e4d5a over 56 record(s); rebuild with tools/estate-report.py --estate palmer --out -->

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

<!-- numbers rebuilt 2026-10-24 -->

## What it holds

| | the grand vin |
|---|---|
| records | 56 |
| span | 1959–2024 |
| blend | 56 (100%) |
| picking dates | 56 (100%) |
| season note | 43 (77%) |
| tasting note | 4 (7%) |
| links to its source | 56 of 56 |

## The documents

129 in the manifest — 56 PDF, 73 crawled page, 122 with an address on record.

By role: page 73, grand 56.

## What the audit still says

- note reads as a tasting note (on the palate, silky tannins, the finish) and there is no taste field — 1
- NO RECORD, 2 document(s) on disk — 1

## Findings
Estate 4 of 61.

**49 of 49 missing addresses found, from 18 pages.** Palmer's records
cite per-vintage PDFs with Webflow CDN hashes in their names —
`6708fceb328ad893ef618242_Fiche_millesime_EN_1978.pdf` — and not one
had an address, so 49 of its 56 records could not link to their source.
No media library to ask (the site is Webflow, `/wp-json` answers 404)
and no PDF in its sitemap.

But its 73 crawled pages *do* have addresses, and those pages are where
the PDFs were linked from. `tools/find-doc-urls.py` fetches the pages we
can already reach, takes every document link off them, and matches by
filename. A match means that page carries a link whose last path segment
is exactly this file — nothing is guessed. **Every one found.**

That tool exists because of Palmer, and it generalises: it works on any
site that links its own documents, whatever the site is built with,
where the media-library route needs WordPress.

## Not recoverable here

Nothing outstanding. One vintage has two documents and no record.
