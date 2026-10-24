# Phase 2.3 — Reader correctness and the v3 evidence pass

**Status: complete.** Both reader defects are fixed, in general rules and
with no estate-specific exception. Every suite passes. The v3 pass is
appended beside v1 and v2, and running it again adds nothing. No
canonical data file changed. The 50 Echo manifest corrections were **not**
applied: that is the next phase.

2026-10-24. Reader fingerprint before `c2086a5a8918`, after `ba6795763d67`.

---

## A. Previous premise

Phase 2.2 was planned as "remove the Echo's double listing from the data".
Tracing the dependencies disproved that before anything was edited.
`BDX_CUVEE_WINES` defines the Echo once, correctly, as `role:'second'`. The
"double listing" was the loader merging the second wine into `cuvees` on
purpose, and the grand-vin evaluation depends on that merge. Removing the
Echo would have deleted the wine's definition, and the refusal would have
stayed, because the loader re-adds the second wine from `chateaux.js`. The
refusals came from two defects in the reader, which is where this phase
fixed them. See `docs/PHASE-2.2-ECHO-CORRECTION.md`.

## B. Reader defects

**Defect A: second-wine mode had no positive test.** Asked whether a
document was the second wine's, the reader checked only that it was not
refused, which in practice meant "not the grand vin's". Nothing asked the
document to *be* the second wine's. Observed baseline:

| the sheet is | accepted as the Echo | refused |
| --- | --- | --- |
| Echo | 0 | 69 |
| grand vin | **107** | 8 |
| Blanc | 0 | 50 |

Across the store, 4,416 of v2's 5,291 second-wine acceptances were of
documents the manifest files under no wine, at 94 estates.

**Defect B: `mark_of()` threw away "blanc".** `blanc` is in `COMMON`, so a
mark never matches "Sauvignon Blanc". That left "Blanc de Lynch-Bages"
with the mark `de lynch bages`, which "Echo **de Lynch-Bages**" also
carries, so every Echo sheet "named the Blanc". The same collision between
genuinely distinct wines occurs at 10 estates (section D).

## C. Fix

Both fixes are in `tools/sheetreader.py`. They are rules about names and
documents, and no estate is named in them.

**Sibling-aware marks (defect B).** `mark_of(other, grand, siblings=None)`
keeps its old answer when called without siblings, so no existing caller
moved. Second-wine mode passes the estate's other wines as siblings. When
a sibling's name carries the same mark, `_refine_mark` looks for the
shortest span of the wine's own words that:

- contains a word that is not an article, not common and not a house word;
- is not inside the grand vin's name;
- is carried by no sibling;
- contains a word the clashing sibling lacks.

Colour words count here, so "Blanc de Lynch-Bages" marks with `blanc` in
it. `COMMON` itself is unchanged, so a mark still never matches
"Sauvignon Blanc", and "D de Dauzac Blanc" still marks as `d de dauzac`.

**Positive second-wine identity (defect A).** `second_wine_verdict()` asks
in this order:

1. the filename names another of the estate's wines → that wine's (`WRONG_WINE`)
2. the filename names that wine *and* the second wine → `AMBIGUOUS_WINE`
3. the document calls itself the second wine → accepted
4. the filename names the second wine → accepted
5. the filename names only the grand vin → `IS_GRAND_VIN`
6. the filename names no wine: the document's **title** must name the
   second wine. This is `names_another_wine`'s existing title rule
   (letterhead off; the wine named first in the title wins). If the title
   names another cuvée instead → `WRONG_WINE`; if nothing does →
   `NOT_IDENTIFIED`.

The first version of step 6 searched a 1,500-character window of the
opening text. Read by hand, its 116 extra acceptances included a
chocolate description, price lists and vintage reports mentioning the
second wine in passing. Measured positions showed no window size
separates those from real sheets, so the reader's existing title rule
replaced it.

Two names with identical identifying words are treated as one wine
written twice. Issan lists both "Blason d'Issan" and "Blason d’Issan";
Kirwan and Yquem have similar pairs, six estates in all. Without this,
those sheets would be refused as ambiguous. The lists themselves are
left as they are.

New verdict codes in `tools/evidence.py`: `NO_SECOND_WINE`,
`AMBIGUOUS_WINE`, `IS_GRAND_VIN`, `NOT_IDENTIFIED`, and `WRONG_WINE` for
"the filename/document names another of the estate's wines". No v3 row is
`UNMAPPED_VERDICT`.

## D. Regression coverage

`tools/test-phase23.py`, 47 checks:

- **Lynch-Bages matrix.** Echo, grand vin and Blanc sheets, each asked as
  the Echo and as the grand vin. Echo is accepted only as the Echo; grand
  vin only as the grand vin; Blanc as neither.
- **The 10-estate `blanc` set**, using the estates' real names:
  Lynch-Bages (Blanc / Echo), Margaux (Pavillon Blanc / Pavillon Rouge),
  Cos d'Estournel (Pagodes de Cos Blanc / Pagodes de Cos), Guiraud,
  Olivier, Pichon Baron, Haut-Bages Libéral (La Chapelle de Haut-Bages
  Libéral / La Chapelle de Bages), Bourgeois Château Dillon (La Comtesse
  Noire / Secret de la Comtesse) and Léoville-Poyferré (Moulin Riche /
  Pavillon de Poyferré). Each name is read as itself and not as its pair.
  For Yquem, the two spellings of Y d'Yquem read as one wine. Margaux's
  2018 Pavillon Rouge, Pavillon Blanc and grand-vin sheets are also told
  apart at document level.
- **The protections `COMMON` exists for**: no mark matches "Sauvignon
  Blanc", there is no bare common-word mark, D de Dauzac is unchanged, and
  `mark_of` without siblings is unchanged.
- **Group-footer protection**: La Patache's footer naming a group property
  is refused in both modes. Bellefont-Belcier / Vignobles K remains
  covered by the Phase 2.1 suite.
- **The Echo data structure**: defined once, keeps its slug,
  `role:'second'`, colour red, `second: 'Echo de Lynch-Bages'` in
  chateaux.js, the loader merge, 13 records, and 50 sheets still filed as
  the Blanc (the corrections are not applied).

`tools/test-phase22.py`'s two KNOWN DEFECT lines are now assertions.

All suites pass: reader, data (11), Phase 2 (30), Phase 2.1 (27),
Phase 2.2 (17), Phase 2.3 (47).

Diagnosis, after the fix (`tools/diagnose-second-mode.py`, by word
containment, independent of the reader):

| the sheet is | accepted as the Echo | refused |
| --- | --- | --- |
| Echo | **70** | 1 |
| grand vin | **0** | 110 |
| Blanc | 0 | 53 |

False acceptances: 0.

## E. v3 results

41,259 v3 decisions: 39,997 from the contextual pass and 1,262 from the
re-characterisation of unattributed artifacts. That is the same contexts
as v2, one for one. 40,332 are asked for a stated vintage; 927 have no
vintage to ask.

| code | v3 |
| --- | ---: |
| GUARD_HAS_NO_CUVEE_MODE | 18,651 |
| ACCEPTED | 10,708 |
| IS_GRAND_VIN | 3,570 |
| WRONG_WINE | 3,087 |
| NOT_IDENTIFIED | 1,827 |
| WRONG_VINTAGE | 1,322 |
| PRESS_DOCUMENT | 871 |
| WRONG_COLOUR | 774 |
| WRONG_ESTATE | 364 |
| TRADE_LISTING | 71 |
| NO_VINTAGE_STATED | 14 |

**Grand-vin contexts: 14,125 unchanged, 0 changed.** The fix touched only
second-wine mode.

Second-wine contexts, v2 → v3:

| code | v2 | v3 |
| --- | ---: | ---: |
| ACCEPTED | 5,246 | 1,090 |
| IS_GRAND_VIN | — | 3,534 |
| WRONG_WINE | 1,998 | 822 |
| NOT_IDENTIFIED | — | 1,818 |
| WRONG_VINTAGE | 364 | 364 |
| WRONG_COLOUR | 334 | 335 |
| PRESS_DOCUMENT | 162 | 163 |
| WRONG_ESTATE | 68 | 46 |

The more telling change is in documents the manifest files *as* the
second wine, asked as it. v2 accepted 83 of 1,057; v3 accepts 832 of
1,044. Le Clarence de Haut-Brion's own sheets went from 27 refused to 27
accepted, and the Haut-Brion grand-vin and Blanc sheets v2 accepted as Le
Clarence (40 and 19) are now refused.

## F. The 4,416 re-characterisation

4,416 v2 rows are 4,373 distinct contexts. The other 43 are rows the
manifest holds twice (the duplicate-row defect `test-data.py` tracks).
Each context is classified by its v3 verdict in
`data/v3-recharacterization.jsonl`:

| class | n |
| --- | ---: |
| REJECTED_BY_V3 | 4,368 |
| CONFIRMED_ACCEPTANCE | 5 |
| CHANGED_TO_OTHER_VERDICT | 0 |
| NOT_RE_EVALUATED | 0 |

Leading reasons: "nothing identifies this as Le Clarence de Haut-Brion"
(201), "the filename names the grand vin, not Le Petit Mouton" (184), not
Pavillon Rouge (132), "nothing identifies this as Lagrave-Martillac"
(127), not Echo (102), not Les Hauts de Pontet-Canet (97).

The five confirmed acceptances, read by hand:

| document | asked as | read |
| --- | --- | --- |
| belgrave-2023-fc11b611.pdf | Diane de Belgrave 2023 | **correct**: "Second vin du Château Belgrave" |
| Lagrave-Martillac blanc 2020 / Lacroix-Martillac rouge 2019 | Lagrave-Martillac 2020 | plausible |
| (the same) | Lagrave-Martillac 2019 | **doubtful**: 2019 is Lacroix's year on that sheet |
| Fiche-technique-FR-MURETS-BLANCS-2023 | Les Erables de Caillou 2023 | **wrong**: Les Murets, Caillou's dry-white second, a wine not listed |
| FT-PEDESCLAUX-2025 | Fleur de Pédesclaux 2025 | **doubtful**: a map of "the first and second wine" |

**Open defect, found here and not fixed in this phase.** Step 3, "the
document calls itself the second wine", does not ask *whose* second wine
or *which* one. That explains Caillou and Pédesclaux above. It also
explains a La Mission page ("this second wine…", La Chapelle de la
Mission) filed under Haut-Brion and accepted as Le Clarence, which v2
accepted as well. It is the
unlisted-cuvée pattern again, now inside the
second-wine reader. Fixing it means changing `is_second_wine`, which the
blend reader shares, so it belongs in its own change with its own
measurement, not after this phase's gate.

## G. Echo

Echo documents at Lynch-Bages, asked as the Echo for a vintage:

| | v2 | v3 |
| --- | ---: | ---: |
| evaluations | 67 | 67 |
| ACCEPTED | 0 | **60** |
| WRONG_WINE | 60 | 0 |
| WRONG_VINTAGE | 7 | 7 |

All 7 `WRONG_VINTAGE` refusals are an Echo sheet of one year asked about
another, so the refusal is right. One example: `Echo-de-Lynch-Bages-2023-FR`
asked for 2008 says "the filename calls this the 2023 vintage". The same
7 were refused in v2. Grand-vin and Blanc sheets are refused as the Echo
(section D).

## H. Five-vintage validation

| Vintage | Echo document exists | v3 Echo result | Manifest changed |
|---|---|---|---|
| 2008 | yes: Echo-de-Lynch-Bages-2008-EN, -CN | 2 of 4 accepted; both accepted are the 2008 sheets, both refused are the 2021 and 2023 sheets | NO |
| 2009 | yes: Echo-de-Lynch-Bages-2009-EN, -CN | 3 of 4 accepted; the refused one is the 2010 sheet | NO |
| 2010 | yes: Echo-de-Lynch-Bages-2010-EN, -CN | 3 of 3 accepted | NO |
| 2015 | yes: Echo-de-Lynch-Bages-2015-EN, -CN | 3 of 3 accepted | NO |
| 2016 | yes: Echo-de-Lynch-Bages-2016-EN, Echo-Lynch-Bages-2016-FT-FR-C0888 | 4 of 4 accepted | NO |

All five vintages are recognised. In every year, the year's own Echo
sheet is accepted and no other year's sheet is.

## I. Persistence

- **Historical decisions retained.** `data/evidence-decisions.jsonl` grew
  from 54,325 to 95,584 lines. `git diff` shows 41,259 insertions and 0
  deletions. The first 54,325 lines are identical to the committed file
  (ignoring line endings): v1 13,065 rows and v2 41,259 rows.
- **v3 appended.** 41,259 rows at `v: 3`, all under reader `ba6795763d67`.
- **Idempotence.** Rerunning v3 for Lynch-Bages (1,040 decisions),
  Haut-Brion (2,460) and the unattributed Latour-Martillac artifacts (21)
  appended 0 rows.

## J. Out of scope

This phase did not:

- apply the 50 Echo manifest corrections;
- modify the five missing Echo records;
- modify the other double-listing cases;
- apply the 99 estate attributions;
- resolve the 518 review or 360 insufficient-evidence cases;
- modify scraper behaviour;
- perform normalisation;
- fix the "whose second wine" defect in section F.

Canonical safety: `git diff --name-only HEAD -- data/sources.json
data/fiches.js data/cuvees.js data/field-src.js data/cuvee-src.js` is
empty.

## Files

- `tools/sheetreader.py`: sibling-aware marks, `wset`, `named_wines`,
  `second_wine_verdict`; `names_another_wine` takes `siblings`.
- `tools/evidence.py`: verdict codes for second-wine mode.
- `tools/evidence-wines.py`, `tools/recharacterize.py`: decider version 3.
- `tools/diagnose-second-mode.py`: labels by word containment,
  independently of the reader.
- `tools/test-phase22.py`: defect lines turned into assertions.
- `tools/test-phase23.py`: new, 47 checks.
- `tools/compare-v3.py`: new, v2 against v3.
- `data/evidence-decisions.jsonl`: 41,259 v3 rows appended.
- `data/v3-recharacterization.jsonl`: new, the 4,373 contexts classified.
