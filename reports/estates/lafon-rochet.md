# Château Lafon-Rochet — fourth growth, Saint-Estèphe

<!-- fingerprint 04a42ccef5c4fac6 over 24 record(s); rebuild with tools/estate-report.py --estate lafon-rochet --out -->

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

<!-- numbers rebuilt 2026-10-24 -->

## What it holds

| | the grand vin | Les Pèlerins de Lafon-Rochet (second, red) |
|---|---|---|
| records | 16 | 8 |
| span | 2007–2023 | 2010–2022 |
| blend | 16 (100%) | 1 (12%) |
| alcohol | 4 (25%) | 2 (25%) |
| pH | 5 (31%) | 8 (100%) |
| yield | 2 (12%) | 2 (25%) |
| in barrel | 15 (94%) | 8 (100%) |
| new oak | 3 (19%) | 1 (12%) |
| picking dates | 15 (94%) | 5 (62%) |
| harvest, in words | 2 (12%) | — |
| season note | 1 (6%) | — |
| tasting note | 13 (81%) | 1 (12%) |
| links to its source | 15 of 16 | |

## The documents

77 in the manifest — 44 PDF, 33 crawled page, 36 with an address on record.

By role: page 33, grand 29, second 11, unknown 4.

## What the audit still says

- no address — 9

## Findings

The audit raises nothing else: every field it checked is the right kind of thing in the right place, and the figures are inside their plausibility bands.

**9 records cannot link to their source.** 9 of its cited documents have no address on record, and it has 24 pages of its own whose address we do hold.

So `find-doc-urls.py` has something to read: it fetches those pages and matches a document by the last segment of the link. It was run across the sixteen estates with the most to gain and filled none here, which means those pages do not link these files — but a deeper crawl of the estate’s own vintage pages might.

## Not recoverable here

Its 24 records already carry what its documents state; `unread.py` finds no field a document states that no record holds.
