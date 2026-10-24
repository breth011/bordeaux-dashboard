# Château Lafite Rothschild — first growth, Pauillac

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

## What it holds

| | the grand vin |
|---|---|
| records | 50 |
| span | 1968–2025 |
| blend | 48 (96%) |
| alcohol | 45 (90%) |
| pH | 10 (20%) |
| yield | 33 (66%) |
| in barrel | 36 (72%) |
| new oak | 1 (2%) |
| picking dates | 25 (50%) |
| season note | 3 (6%) |
| tasting note | 40 (80%) |
| total acidity | 46 (92%) |
| links to its source | 1 of 50 |

## The documents

74 in the manifest — 62 PDF, 12 crawled page, 11 with an address on record.

By role: grand 49, page 11, unknown 11, group report 3.

## What the audit still says

- no address — 49

## Findings
Estate 6 of 61.

**Two tasting notes the estate printed on the wrong sheet.**
`Chateau-Lafite-Rothschild-1976.pdf` prints, under TASTING NOTES, the
1975 note word for word — and names the year inside itself:

> On the nose the wine reveals complex and intense aromas of tobacco and
> black truffle… all finesse. **One of the most beautiful 1975!**

The same pair exists at 2007 and 2016: the 2016 sheet carries 2007's
note. This is the estate's own error in its own documents, not a
misreading — the reader did exactly what the sheet said. What found it
was two records of one wine holding the same passage, which is what the
duplicate check in `audit-estate.py` is for. Both are pinned absent.

**A yield that was the tail of a decimal.** The record held `yld 75`
where the sheet states "Yield : 38.75 hL/ha". `RX_YLD` allowed one
decimal place, so it tried 38.7, wanted the unit, found "5 hL/ha" and
failed — and `RX_YLD2`, which had no guard against starting inside a
number, then matched the two digits before the unit and stored **75**.

A yield of 75 hl/ha at a first growth is not possible; Lafite runs in
the thirties and forties, and the audit's plausibility band is what
raised it. Both patterns now take two decimal places, and the bare-number
one carries `(?<![\d,.])` — the guard `RX_ALC2` has had since it was
written.

## Not recoverable here

**49 of 49 addresses are unreachable.** Lafite, Rieussec and
Duhart-Milon share `lafite.com`, whose media library does not name their
files, and only 2 of its pages have addresses on record — neither links
the PDFs. Its documents need their addresses captured at fetch time.
