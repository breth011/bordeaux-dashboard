# Château Grand-Puy-Ducasse — fifth growth, Pauillac

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

## What it holds

| | the grand vin | Prélude à Grand-Puy Ducasse (second, red) |
|---|---|---|
| records | 40 | 15 |
| span | 1970–2024 | 2007–2021 |
| blend | 19 (48%) | 7 (47%) |
| alcohol | 30 (75%) | 15 (100%) |
| pH | 3 (8%) | — |
| yield | 9 (22%) | 14 (93%) |
| in barrel | 14 (35%) | 15 (100%) |
| new oak | — | 14 (93%) |
| picking dates | 17 (42%) | — |
| season note | 13 (32%) | 8 (53%) |
| links to its source | 35 of 40 | |

## The documents

86 in the manifest — 86 PDF, 0 crawled page, 35 with an address on record.

By role: grand 51, second 18, other 10, unknown 6, skip 1.

## What the audit still says

- no address — 20
- NO RECORD, 1 document(s) on disk — 10

## Findings
Estate 3 of 61.

**Every one of its 86 documents is a PDF, and not one had an address**,
so none of its 40 records could link to its source. Its media library
holds all 86 — but the address on file is `https://www.grandpuyducasse.fr`
and that host's certificate does not verify, while the bare host answers
normally. `recover-urls.py` now tries both forms. **35 of 40 recovered.**

**Ten documents make no record, and the reason is the standing history.**
Every sheet opens with the same 1,100 characters about the estate:

> Tout commence lorsqu'Arnaud Ducasse fait l'acquisition en 1675 d'une
> « modeste » maison en bordure du fleuve à Pauillac… menée par Anne Le
> Naour et Benjamin Cassoulet.

and only then comes the vintage, unlabelled:

> Le débourrement arriva en avance début mars mais le froid jusqu'au 25
> mars a ensuite ralenti le développement végétatif… Vêtu de rubis
> foncé, le 1975 s'annonce par un bouquet séduisant, marqué cependant de
> notes végétales.

The prose reader's unlabelled candidate starts at the beginning of the
document, gets the history, and rejects it — correctly, since the
history is the same on every sheet. It never reaches the vintage, because
there is no heading to anchor on.

That wants a reader that can walk past a standing preamble, which is a
real change needing archive-wide measurement, so it is recorded rather
than attempted here. It is the same shape at any estate whose sheet
opens with its own story.

## Not recoverable here

**The figures in the footer are the estate's, not the vintage's.** The
sheets end with a flattened two-column block:

> ASSEMBLAGE L'HISTOIRE LE MILLESIME 62 38 ALCOOL % Cab. Sauvignon %
> Merlot 13% vol

`62 38` and `13% vol` are byte-identical on the 1970, 1971 and 1975
sheets, so they are what the estate prints on every sheet and not what
it made that year. The reader refusing them is right, and a rule to
read numbers that precede their variety names would read these wrong.
