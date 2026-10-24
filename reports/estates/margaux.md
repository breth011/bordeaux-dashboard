# Château Margaux — first growth, Margaux

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

## What it holds

| | the grand vin | Margaux du Château Margaux (other, red) | Pavillon Blanc du Château Margaux (other, white) | Pavillon Rouge du Château Margaux (second, red) |
|---|---|---|---|---|
| records | 118 | 9 | 48 | 48 |
| span | 1900–2025 | 2009–2019 | 1978–2025 | 1978–2025 |
| blend | 19 (16%) | 2 (22%) | — | 15 (31%) |
| alcohol | 3 (3%) | — | 2 (4%) | 1 (2%) |
| pH | — | — | — | 1 (2%) |
| yield | 4 (3%) | — | 5 (10%) | 2 (4%) |
| picking dates | 104 (88%) | 7 (78%) | 41 (85%) | 40 (83%) |
| season note | 93 (79%) | 9 (100%) | 47 (98%) | 46 (96%) |
| tasting note | 34 (29%) | 3 (33%) | 4 (8%) | 7 (15%) |
| links to its source | 118 of 118 | | | |

## The documents

257 in the manifest — 6 PDF, 251 crawled page, 251 with an address on record.

By role: page 142, other 66, second 48, unknown 1.

## What the audit still says

- NO RECORD, 1 document(s) on disk — 8
- note reads as a tasting note (bouquet, on the palate) and there is no taste field — 2
- note reads as a tasting note (reveals a very powerful, complex nose, silky tannins, tannic structure) and there is no taste field — 1

## Findings
**Estate 1 of 61.** The site publishes 126 vintages back to 1900 and
the manifest held 76 from 1950. One sitemap fetch said so; the fifty
missing years were then fetched by pattern. They carry notes and picking
dates — *"The legendary 1900! The century began with an extraordinary
harvest both in terms of quantity and quality"* — and 42 of the 50 made a
record at once.

**Pavillon Rouge was not in `BDX_CUVEE_WINES` at all**, and 48 of its
vintage pages sat filed `page`, offered to no reader. Pavillon Blanc was
listed with 49 pages in the same state. I checked for the Aile d'Argent
defect first — whether the grand vin had been wearing them — and it had
not: zero grand-vin fields came off a Pavillon page, because the
filenames spell the wines' names in full and the guards caught them. The
documents were simply unread. **0 → 105 records across three wines.**

**Eight of the fifty older vintages made no record, and the reason was
worth the whole pass.** `PROSE_STOP` carried `\bwines\s+[A-Z]` for the
capitals heading "WINES", its own comment reading *"In capitals only"* —
but the pattern is `(?i)`, so it matched "The **wines w**ere rather
green" and cut Margaux 1925's note at 48 characters. Scoped to capitals,
a full archive re-read rewrote **1,158 records** and recovered about
78,000 characters of prose cut mid-sentence.

**2025's season note came from a news article, about another wine.**
`/en/actualites/2025-un-grand-millésime…` beat the vintage page on
filename order and gave the grand vin *"The harvest for Pavillon Blanc
2025 took place very early"*. The news feed is ranked last now — not
refused, since an article is still the best source for a field nothing
else states. The guards could not settle it: `names_another_wine` wants
the full name and the article writes "Pavillon Blanc".

**Its vintage pages set sections inline**, so one field held three
things: *"… in its youth. **Blend:** 89% cabernet sauvignon… **Climate:**
Le millésime 2025 est marqué…"*. Both now stop a passage — but only where
the label opens a sentence, because Boyd-Cantenac 2018 genuinely reads
"marked by a contrasting climate: a cool spring". With that, 2025 reads
from its own page and **`yld:22` is captured for the first time**.

All nineteen blends verified against the estate's own words. Four were
hand-entered and all four are confirmed, including 2021's, which equals
Margaux's declared house blend to the decimal — the house blend was
derived from vintages like it.

## Not recoverable here

**No assemblage before 2005.** All 76 older pages asked with probes
looser than the reader's — any variety within 80 characters of any
percentage — and 1900–2004 state none. 2005 states only two varieties,
85% cabernet sauvignon and 8% merlot, which sums to 93 and is therefore
not a blend.

**2008 is recoverable and not yet taken.** Its page states all four
— *"our best merlots, accounting for 10%… The cabernet **cauvignons**, at
87%… the 1.5% cabernet franc and 1.5% petit verdot"* — 100 exactly. The
reader misses it on a typo in the estate's own page, `cauvignons`, which
appears in exactly one file in the archive. Not worth a rule.

**No technical sheet.** No PDF in either sitemap and `/wp-json` answers
404.

**1964 and 2025** hold a season note ending on tasting language with no
`taste` field — the pages write the year's story and the wine's tasting
as one paragraph.
