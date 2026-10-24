# Château Lagrange — third growth, Saint-Julien

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

## What it holds

| | the grand vin | Les Fiefs de Lagrange (second, red) |
|---|---|---|
| records | 14 | 12 |
| span | 1983–2025 | 2013–2025 |
| blend | 14 (100%) | 10 (83%) |
| alcohol | — | 1 (8%) |
| pH | 1 (7%) | 1 (8%) |
| yield | 2 (14%) | — |
| in barrel | 12 (86%) | 12 (100%) |
| new oak | 12 (86%) | 12 (100%) |
| picking dates | 12 (86%) | 12 (100%) |
| harvest, in words | 3 (21%) | — |
| season note | 10 (71%) | 9 (75%) |
| tasting note | 10 (71%) | 7 (58%) |
| links to its source | 4 of 14 | |

## The documents

108 in the manifest — 104 PDF, 4 crawled page, 65 with an address on record.

By role: unknown 49, second 27, grand 13, other 12, skip 4, page 3.

## What the audit still says

- no address — 20
- note is word for word lagrange|les-fiefs-de-lagrange|YYYY’s — 3
- note is word for word lagrange|YYYY’s — 1

## Findings
**Four vintages of Les Fiefs de Lagrange hold the same season note, from
four different source files, and it is not a season note at all:**

> Influencé par les deux masses d'eau que sont d'une part la Gironde et
> d'autre part la proximité de l'Océan Atlantique. 111 hectares de vigne
> rouge. **LE MILLESIME : LES FIEFS DE LAGRANGE 2014** Après un
> débourrement précoce de la vigne…

The estate's standing description of its terroir, printed on every sheet
under a section headed `Climat`, and then the vintage's own text after
`LE MILLESIME`. Both are valid note labels and `Climat` comes first in
the document, so it wins.

I added the bare capitals `MILLESIME` to `LABEL_NOTE`, which was missing
— it only knew "millésime 2014", the word with a year after it — and that
alone does not fix this, because the first acceptable candidate wins and
`Climat` is first.

**The fix is to prefer a label followed by this record's own year**, which
`LE MILLESIME : LES FIEFS DE LAGRANGE 2014` is and `Climat` is not. That
is the right discriminator and `read_prose` is not given the year, so it
cannot apply it yet. Recorded rather than rushed: four records at one
wine, fully diagnosed.

The same shape as Grand-Puy-Ducasse's standing history, with one
difference that makes it fixable — here the estate marks where the
vintage begins.

## Not recoverable here

The grand vin's 2025 note is its 2024's, the same way.
