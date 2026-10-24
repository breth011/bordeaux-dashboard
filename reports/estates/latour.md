# Château Latour — first growth, Pauillac

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

## What it holds

| | the grand vin |
|---|---|
| records | 74 |
| span | 1945–2019 |
| picking dates | 66 (89%) |
| season note | 72 (97%) |
| tasting note | 67 (91%) |
| links to its source | 74 of 74 |

## The documents

75 in the manifest — 0 PDF, 75 crawled page, 75 with an address on record.

By role: page 75.

## What the audit still says

- NO RECORD, 1 document(s) on disk — 1

## Findings
**Estate 2 of 61.** All 75 of its vintage extracts are laid out the same
way:

> **Signature Wine style:** This vintage has confirmed all of its
> potential… good tannic structure. **Vineyard & harvest Weather
> conditions:** After a cold, dry winter, March was warm and wet…

Neither heading was in `LABEL_TASTE` or `LABEL_NOTE`, so both passages
were unlabelled, the season note's at-start candidate won, and **the
tasting note was being filed as the season** — 1949, 1968, 1971, 1977,
1979, 1980 and 1981 had a tasting note in `note` and no `taste` at all.
I had added `LEAD_SIGNATURE` the day before to strip that heading as
site furniture; it is the label over the tasting note. Registered as
labels: **tasting notes 44 → 67 of 74 (91%), season notes 62 → 70
(95%)**.

**Three tasting notes ended on the shop's availability line** — *"Vintage
available only for Les Forts de Latour and Pauillac de Château
Latour."* Latour left the primeurs system in 2012 and does not release a
grand vin every year, which is **not** the same as not making one, so
nothing was marked not-produced.

**Its second and third wines are deliberately not listed.** I added Les
Forts de Latour and Le Pauillac de Château Latour, then took them back
off. The site publishes no per-vintage page for either — one descriptive
page each, 2,194 and 1,408 characters, with no year anywhere in the
markup. And listing them cost five of the grand vin's own pages: Latour's
extracts never name Château Latour in their text, so
`names_another_wine`'s last rule hands the page to whichever other wine
is mentioned — 1966 says Les Forts was first made that year, 1987 says
vats were downgraded to generic Pauillac. Removing them recovered 1987
and 2019.

## Not recoverable here

**Zero blends on 74 records, and the documents do not have them.** All 75
asked with no guard and no gate: not one pairs a variety with a
percentage. All are extracts from the anchors of a single page,
`/a-time-for-sharing/vintages#1945`. No PDF in the sitemap, no media
library, and the other wines' pages carry no figures. Latour's
assemblages need a source other than its own site — it is the only one of
the 61 classified growths with no technical sheet at all.

**1966 is still refused**, because `chateaux.js` records Les Forts as
Latour's `second` independently of `cuvees.js`.
