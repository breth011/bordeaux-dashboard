# Château Cos Labory — fifth growth, Saint-Estèphe

<!-- fingerprint 7391e1b417adbf70 over 2 record(s); rebuild with tools/estate-report.py --estate cos-labory --out -->

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

<!-- numbers rebuilt 2026-10-24 -->

## What it holds

| | the grand vin | Le Charme Labory (second, red) |
|---|---|---|
| records | 2 | 0 |
| span | 2024–2025 | — |
| blend | 2 (100%) | — |
| tasting note | 1 (50%) | — |
| links to its source | 0 of 2 | |

## The documents

6 in the manifest — 6 PDF, 0 crawled page, 4 with an address on record.

By role: grand 2, second 2, unknown 2.

## What the audit still says

- no address — 2

## Findings

The audit raises nothing else: every field it checked is the right kind of thing in the right place, and the figures are inside their plausibility bands.

**2 records cannot link to their source.** 2 of its cited documents have no address on record, and it has 0 pages of its own whose address we do hold.

Neither route can reach them. `recover-urls.py` needs a media library that names the file; `find-doc-urls.py` reads a document’s address off the page that links to it, and there is no such page here. These addresses need the documents re-fetched with `harvest.py`, which records the address at fetch time.

## Not recoverable here

Its 2 records already carry what its documents state; `unread.py` finds no field a document states that no record holds.
