# Château Lascombes — second growth, Margaux

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

## What it holds

| | the grand vin | Chevalier de Lascombes (second, red) | Haut-Médoc de Lascombes (other, red) |
|---|---|---|---|
| records | 25 | 8 | 6 |
| span | 2001–2025 | 2018–2025 | 2019–2025 |
| blend | 25 (100%) | 7 (88%) | 5 (83%) |
| alcohol | 13 (52%) | 7 (88%) | 4 (67%) |
| yield | 25 (100%) | 8 (100%) | 6 (100%) |
| in barrel | 1 (4%) | — | 1 (17%) |
| new oak | 5 (20%) | — | 1 (17%) |
| picking dates | 25 (100%) | 8 (100%) | 6 (100%) |
| season note | 3 (12%) | — | 1 (17%) |
| links to its source | 5 of 25 | | |

## The documents

86 in the manifest — 74 PDF, 12 crawled page, 23 with an address on record.

By role: grand 29, second 21, unknown 18, page 10, other 6, skip 2.

## What the audit still says

- no address — 32
- NO RECORD, 1 document(s) on disk — 1

## Findings
**Its 2025 season note was the whole page.** The grand vin's technical
block, then **Chevalier de Lascombes' block entire**, then the language
switcher, the age gate and a login form:

> …Alcohol content 13.5% vol. Yield 25 hl/ha Ageing In barrels, casks and
> amphoras. Technical sheet see other vintages Download PDF **Chevalier
> de Lascombes Margaux Millésime 2025 Blend 70% Merlot**… Are you of
> legal age in your home country?… Log in Username or email Password

Three stops were missing and are now there: `Alcohol content` and `Yield`
followed straight by a figure, with no colon — nothing but a data block
writes that; the age gate, whose pattern allowed no words between "legal
drinking" and "age" where this page says "legal drinking **and
purchasing** age"; and the page's own `Download PDF` / `Technical sheet`,
which sits exactly where the grand vin's block ends.

The second wine's block would be better cut at its own name, which the
guards know — but `PROSE_STOP` is one pattern for the whole archive and
carries no per-estate knowledge. The furniture stop lands in front of it,
which has the same effect here.

**3 of 35 addresses recovered.**

## Not recoverable here

32 records still cannot link to their source.
