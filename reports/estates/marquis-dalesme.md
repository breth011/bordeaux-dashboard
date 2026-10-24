# Château Marquis d’Alesme — third growth, Margaux

<!-- fingerprint 3794f71084ac8966 over 13 record(s); rebuild with tools/estate-report.py --estate marquis-dalesme --out -->

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

<!-- numbers rebuilt 2026-10-24 -->

## What it holds

| | the grand vin |
|---|---|
| records | 13 |
| span | 2009–2022 |
| blend | 13 (100%) |
| alcohol | 5 (38%) |
| pH | 3 (23%) |
| yield | 1 (8%) |
| in barrel | 10 (77%) |
| new oak | 13 (100%) |
| picking dates | 12 (92%) |
| season note | 2 (15%) |
| press scores | 11 (85%) |
| links to its source | 0 of 13 |

## The documents

31 in the manifest — 31 PDF, 0 crawled page, 0 with an address on record.

By role: unknown 18, grand 13.

## What the audit still says

- no address — 13
- blend is exactly the planting, which is a different claim — 1

## Findings
**Seven records held three months in barrel**, which no Bordeaux grand
vin spends in wood. Its sheets say:

> Élevage Barriques de chêne français 60% de bois neuf 40% barriques d'un
> vin **élevage sur lies 3 mois Durée : 15 mois**

Two figures: three months on the lees, and fifteen all told. `RX_MONTHS`
anchors on "élevage" and takes the first number within forty non-digit
characters, so it took the three. Fixed two ways — a pattern for the
duration stated outright, tried first, and "sur lies" excluded from the
anchor's reach, because time on the lees is a different fact from time in
barrel.

Corrected from their own documents: **2010–2013 → 15, 2014 → 16, 2015 →
20, 2016 → 16.** None was credited to the reader, so no re-read could
have reached them. The audit's plausibility band is what raised it.

## Not recoverable here

Its planting and one vintage's blend are identical, which may mean either
that the blend is the planting or that the planting entry is a vintage's
blend. The test is whether its `encépagement` label states one figure on
every sheet or a different one each year; I wrote a check for that and its
variety-to-figure matching is not reliable enough to act on, so the data
is untouched.
