# Château Ducru-Beaucaillou — second growth, Saint-Julien

<!-- fingerprint b11d5f2de1db1841 over 22 record(s); rebuild with tools/estate-report.py --estate ducru-beaucaillou --out -->

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

<!-- numbers rebuilt 2026-10-24 -->

## What it holds

| | the grand vin | La Croix de Beaucaillou (second, red) | Le Petit Ducru de Ducru-Beaucaillou (other, red) | Madame de Beaucaillou (other, red) |
|---|---|---|---|---|
| records | 8 | 8 | 2 | 4 |
| span | 2011–2024 | 2011–2024 | 2018–2022 | 2020–2024 |
| blend | 6 (75%) | 8 (100%) | 2 (100%) | 4 (100%) |
| pH | 3 (38%) | 5 (62%) | 1 (50%) | 3 (75%) |
| yield | 3 (38%) | — | — | — |
| in barrel | 6 (75%) | 5 (62%) | 1 (50%) | 2 (50%) |
| new oak | 2 (25%) | 1 (12%) | — | — |
| picking dates | 4 (50%) | 1 (12%) | 2 (100%) | 2 (50%) |
| season note | 3 (38%) | — | 1 (50%) | — |
| tasting note | 2 (25%) | 1 (12%) | — | 1 (25%) |
| press scores | — | 1 (12%) | — | — |
| serving temperature | — | — | 1 (50%) | — |
| links to its source | 2 of 8 | | | |

## The documents

66 in the manifest — 52 PDF, 14 crawled page, 16 with an address on record.

By role: second 21, other 15, grand 14, page 14, skip 1, unknown 1.

## What the audit still says

- no address — 20
- NO RECORD, 2 document(s) on disk — 1
- note reads as a tasting note (bouquet, on the palate) and there is no taste field — 1

## Findings
Estate 36 of 61, brought forward with the other second wines.

**A duplicate I made myself, caught before it did harm.** `chateaux.js`
calls the second wine "La Croix Ducru-Beaucaillou" and
`BDX_CUVEE_WINES` already listed it as "La Croix de Beaucaillou", with
8 records. Adding the first name created a second entry for one wine —
which would have shown the estate the same wine twice in the drawer and
split its vintages across two keys. The entry with the records stays;
mine came off.

That is the same defect as the four Giscours and Smith Haut Lafitte
duplicates found yesterday, arriving by a different route: there, two
generations of slug rule; here, two files spelling one wine's name
differently. The lesson is the same — the wine list is the authority and
a name has to be matched against it before anything is added, which is
why `add-wine.py` refuses a name it already holds.

## Not recoverable here

Only 8 records on the grand vin, against 15 documents for La Croix. The
estate's own site is the next thing to ask.
