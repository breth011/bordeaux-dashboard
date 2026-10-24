# Château Talbot — fourth growth, Saint-Julien

<!-- fingerprint 6ecd18a6de5bf754 over 49 record(s); rebuild with tools/estate-report.py --estate talbot --out -->

Checked 2026-10-24. <!-- fill in: estate N of 61 -->

<!-- numbers rebuilt 2026-10-24 -->

## What it holds

| | the grand vin | Caillou Blanc du Château Talbot (other, white) | Connétable Talbot (second, red) |
|---|---|---|---|
| records | 21 | 12 | 16 |
| span | 2005–2025 | 2011–2024 | 2008–2023 |
| blend | 21 (100%) | 7 (58%) | 16 (100%) |
| alcohol | 12 (57%) | 5 (42%) | 9 (56%) |
| yield | 19 (90%) | 8 (67%) | 16 (100%) |
| in barrel | 4 (19%) | 12 (100%) | — |
| new oak | 21 (100%) | 7 (58%) | 13 (81%) |
| picking dates | 3 (14%) | 5 (42%) | 1 (6%) |
| links to its source | 17 of 21 | | |

## The documents

71 in the manifest — 71 PDF, 0 crawled page, 44 with an address on record.

By role: other 29, grand 26, second 16.

## What the audit still says

- no address — 16

## Findings
**Caillou Blanc du Château Talbot was listed as a red.** It is Talbot's
dry white, and every one of its twelve records is Sauvignon Blanc and
Sémillon. That matters beyond tidiness: `whose_sheet` calls
`wrong_colour` with the listed colour before anything is read, so a white
filed as red has its own sheets refused for saying *Blanc* — which had
cost Blanc de Lynch-Bages, Domaine de Chevalier Blanc and Cos d'Estournel
Blanc 69 documents between them the day before.

Found by a sweep of all 132 listed wines against two witnesses each: the
wine's own name, and the grape varieties on its own records. Three others
were wrong the same way — Les Griffons de Pichon Baron Blanc, Fleur
Cardinale Blanc, and Rosé de Chevalier.

**Connétable Talbot** was added to the wine list in an earlier pass; it
was in `chateaux.js` as the second wine and not in `BDX_CUVEE_WINES`.

## Not recoverable here

Its media library cannot be read — the TLS handshake times out — and its
sitemap lists no per-vintage address, so its 4 remaining addresses are
unreachable.
