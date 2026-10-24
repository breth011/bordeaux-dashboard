# Château Grand-Puy-Lacoste — fifth growth, Pauillac

<!-- fingerprint c8c67fa016c7d91a over 29 record(s); rebuild with tools/estate-report.py --estate grand-puy-lacoste --out -->

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

<!-- numbers rebuilt 2026-10-24 -->

## What it holds

| | the grand vin | Lacoste-Borie (second, red) |
|---|---|---|
| records | 28 | 1 |
| span | 1995–2024 | 2024–2024 |
| blend | 27 (96%) | — |
| yield | 1 (4%) | 1 (100%) |
| in barrel | 20 (71%) | — |
| new oak | 27 (96%) | — |
| picking dates | 26 (93%) | 1 (100%) |
| season note | 5 (18%) | — |
| tasting note | 21 (75%) | — |
| links to its source | 23 of 28 | |

## The documents

112 in the manifest — 18 PDF, 94 crawled page, 94 with an address on record.

By role: page 94, grand 10, unknown 6, combined 1, second 1.

## What the audit still says

- no address — 6

## Findings

The audit raises nothing else: every field it checked is the right kind of thing in the right place, and the figures are inside their plausibility bands.

**6 records cannot link to their source.** 12 of its cited documents have no address on record, and it has 94 pages of its own whose address we do hold.

So `find-doc-urls.py` has something to read: it fetches those pages and matches a document by the last segment of the link. It was run across the sixteen estates with the most to gain and filled none here, which means those pages do not link these files — but a deeper crawl of the estate’s own vintage pages might.

## Not recoverable here

Its 29 records already carry what its documents state; `unread.py` finds no field a document states that no record holds.
