# Phase 2.8 — Grand-vin reader audit across all estates

**Gate: `SAFE — AUDIT COMPLETE, READER DEFECTS FOUND`**

This phase was an audit only. No reader code, canonical data, manifest,
`chateaux.js`, `cuvees.js` or evidence changed, and no evidence was
written.

- Tool: `tools/audit-grand-marks.py`
- Inventory: `data/phase28-grand-audit.jsonl` (analysis, not evidence)
- Tests: `tools/test-phase28.py`

Started from `faf3acd`, 2026-10-24.

---

## 1. Executive summary

| | |
| --- | ---: |
| estates audited (the reader's whole universe, `sr.estates()`) | **468** |
| grand vins | 468 |
| estates listing at least one other wine | 124 |
| other wines and cuvées audited | **195** |
| **A** safe distinction | 144 |
| **B** exact normalized collision (no word beyond the grand vin's) | **4** |
| **C** partial match, distinctive word survives, name still passes | 0 |
| **D** common-word loss (only COMMON words beyond the grand vin's) | **45** |
| … **D1** not caught by any grand-vin name test | **12** |
| … **D2** caught by another test (weakened, not lost) | 33 |
| **F** runtime-dependent (written forms disagree) | **2** |
| **E** alias or mark collision between two *other* wines | 18 pairs |
| marks made only of articles, house words and the estate's own words | 26 |

**The 468 estates by collection:**

| collection | estates |
| --- | ---: |
| 1855 | 61 |
| Sauternes | 27 |
| Graves | 15 |
| Saint-Émilion | 85 |
| Pomerol | 40 |
| Libournais | 15 |
| Côtes | 12 |
| Graves & Entre-Deux-Mers | 9 |
| Crus Bourgeois | 170 |
| Crus Artisans | 34 |

**In v4**, the defect categories (B, C, D1, F) implicate **140 grand-vin
decisions on 138 documents**: **77 accepted** as the grand vin and 63
refused. **8** of them are also accepted as the second wine for the
same vintage: the Les Hauts du Tertre sheets.

Les Hauts du Tertre is not alone. It is one of 12 D1 wines and the
first observed member of a class: **a wine whose only words beyond the
grand vin's are COMMON words, or a single letter, gets a mark made of
articles and the estate's name, which no filename or title writes.**

## 2. Normalization rules, as implemented

In grand-vin mode, `whose_sheet()` (with `is_second=False`) judges the
estate's other wines in four places. All of them use
**`mark_of(other, grand)` without siblings**. The sibling-aware marks of
Phase 2.3 are used only in second-wine mode.

| test | what it compares |
| --- | --- |
| `naming_spells_cuvee(named, grand, others, second)` | the other wine's letters (`bare_name`: lower case, no accents, separators and leading articles gone), only when they are **longer** than the grand vin's and **contain** them, found inside the file name's letters |
| `abbreviates_other_wine(named, grand, others)` | a file-name word of 3+ letters that **begins** the other wine's mark |
| `is_second_wine(path)` | the generic "second vin / second wine" phrase in the opening; refuses for any second wine |
| `names_another_wine(path, filename, grand, nm)`, for the second wine and every cuvée | (1) the mark in the filename (`says_in_name`: whole words in order, or the packed letters); (2) the one-letter-initial rule (`Y d'Yquem` filed `Y2022_…`), only when the **listed name begins** with the letter; (3) the title (letterhead off): the mark must appear, and must come before the grand vin's name if both appear |

**How `_mark_of(other, grand)` builds a mark.** `g = packed(grand)`.
First it removes any parenthetical, then tries each rule in order:

1. **The first single word** that has 4+ letters, is **not** inside `g`,
   is **not** in `COMMON`, and contains 3 letters.
2. **Else the first adjacent pair** in which neither word is an article,
   the second word is not in `COMMON`, the pair has 8+ letters, and it
   is not inside `g`.
3. **Else the name's non-COMMON words**, if their packed form is not
   inside `g`.
4. **Else the whole name**, if not inside `g`.
5. **Else no mark.** `_base_mark` also returns no mark when it has no
   run of 3 letters.

**What is discarded.**

| set | words |
| --- | --- |
| `COMMON` (48 words) | petit/petite/petits/petites, grand/grande/grands/grandes, haut/haute/hauts/hautes, clos, vieux/vieille/vieilles, cuvee, reserve, prestige, chateau, domaine, blanc, blanche, rouge, rose, selection, tradition, the grape names, cote/cotes/coteaux, terrasses, bas, fleur/fleurs, tour/tours, croix, mont/monts |
| `ARTICLES` | le la les l d de du des et en au aux |
| `HOUSE_WORDS` | chateau clos domaine (used by `wset`, not by `_mark_of`) |
| by length | a single word under 4 letters cannot be a mark on its own: "G", "Y", "II", "D" |
| by containment | any word inside the grand vin's packed name |

**Scope of discarding.** It is global: `COMMON` is one set used by
every caller. But only `_mark_of` uses it to build identities; `wset`
keeps colour words.

**Matching** is by ordered whole words (`says`) or packed letters
(`says_in_name`). There is no stemming and no alias table. The grand-vin
path receives the estate's full listed wine list (the loader merges the
second wine into `cuvees`). It cannot know an unlisted wine; Phase
2.6's unlisted-name model exists only in second-wine mode.

**What it can tell apart.**

- Second wine and cuvées: yes, by mark.
- Third wines: only if listed.
- Dry white and rosé: by mark, and separately by `wrong_colour`
  (colour words in the file name, the estate's category, the blend).
- Unlisted wines: no.

## 3. Collision inventory

Every wine not in category A. **Normalized grand vin** is the grand
vin's identifying words (`wset`). **Normalized other wine** is the mark
the grand-vin check builds for it. **v4** is the status of v4 grand-vin
decisions on documents whose filename carries the wine's own words
(word containment; likely, not proven, to be that wine's).

| estate | grand vin | other wine | cat. | token(s) lost | normalized grand vin | normalized other wine (mark) | v4 evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| durfort-vivens | Château Durfort-Vivens | Vivens | B | none beyond the grand vin | `durfort vivens` | `None` | no relevant evidence |
| margaux | Château Margaux | Margaux du Château Margaux | B | none beyond the grand vin | `margaux` | `margaux du margaux` | no relevant evidence |
| rauzan-segla | Château Rauzan-Ségla | Ségla | B | none beyond the grand vin | `rauzan segla` | `None` | no relevant evidence |
| troplong-mondot | Château Troplong Mondot | Mondot | B | none beyond the grand vin | `mondot troplong` | `None` | no relevant evidence |
| stem-chateau-bellefont-belcier | Château Bellefont-Belcier | Les Tours de Belcier | D1 | tours | `belcier bellefont` | `les de belcier` | **accepted as the grand vin: 32** |
| smith-haut-lafitte | Château Smith Haut Lafitte | Le Petit Haut Lafitte | D1 | petit | `haut lafitte smith` | `le lafitte` | **accepted as the grand vin: 9** |
| du-tertre | Château du Tertre | Les Hauts du Tertre | D1 | hauts | `tertre` | `les du tertre` | **multi-target: 8 accepted as grand vin, 8 also as second** |
| stem-chateau-laroque | Château Laroque | Les Tours de Laroque | D1 | tours | `laroque` | `les de laroque` | **accepted as the grand vin: 7** |
| ducru-beaucaillou | Château Ducru-Beaucaillou | La Croix de Beaucaillou | D1 | croix | `beaucaillou ducru` | `la de beaucaillou` | **accepted as the grand vin: 3** |
| smith-haut-lafitte | Château Smith Haut Lafitte | Les Hauts de Smith | D1 | hauts | `haut lafitte smith` | `les de smith` | **accepted as the grand vin: 3** |
| bourgeois-chateau-beaumont | Château Beaumont | Les Tours de Beaumont | D1 | tours | `beaumont` | `les de beaumont` | **accepted as the grand vin: 2** |
| de-malle | Château de Malle | Les Fleurs de Malle | D1 | fleurs | `malle` | `les de malle` | no relevant evidence |
| lynch-moussas | Château Lynch-Moussas | Les Hauts de Lynch-Moussas | D1 | hauts | `lynch moussas` | `les de lynch moussas` | refused as the grand vin |
| pontet-canet | Château Pontet-Canet | Les Hauts de Pontet-Canet | D1 | hauts | `canet pontet` | `les de pontet canet` | no relevant evidence |
| smith-haut-lafitte | Château Smith Haut Lafitte | Le Petit Haut Lafitte Blanc | D1 | blanc, petit | `haut lafitte smith` | `le lafitte` | refused as the grand vin |
| smith-haut-lafitte | Château Smith Haut Lafitte | Les Hauts de Smith Blanc | D1 | blanc, hauts | `haut lafitte smith` | `les de smith` | refused as the grand vin |
| guiraud | Château Guiraud | Le G de Château Guiraud | F | g | `guiraud` | `le g de guiraud` | **accepted as the grand vin: 13** |
| guiraud | Château Guiraud | Le G de Château Guiraud Blanc | F | blanc, g | `guiraud` | `le g de guiraud` | no relevant evidence |
| ducru-beaucaillou | Château Ducru-Beaucaillou | La Croix Ducru-Beaucaillou | D2 | croix | `beaucaillou ducru` | `croix ducru` | accepted as the grand vin: 3 (the same documents as La Croix de Beaucaillou above) |
| domaine-de-chevalier | Domaine de Chevalier | Domaine de Chevalier Blanc | D2 | blanc | `chevalier` | `domaine de chevalier blanc` | accepted as the grand vin: 1 (a two-wine document, not this defect) |
| beausejour-duffau | Château Beauséjour (Héritiers Duffau-Lagarrosse) | Croix de Beauséjour | D2 | croix | `beausejour` | `de beauséjour` | no relevant evidence |
| bourgeois-chateau-de-malleret | Château de Malleret | Château de Malleret Blanc | D2 | blanc | `malleret` | `château de malleret blanc` | refused as the grand vin |
| bourgeois-chateau-paveil-de-luze | Château Paveil de Luze | Le Petit Paveil | D2 | petit | `luze paveil` | `petit paveil` | refused as the grand vin |
| canon | Château Canon | Croix Canon | D2 | croix | `canon` | `croix canon` | no relevant evidence |
| carbonnieux | Château Carbonnieux | La Croix de Carbonnieux | D2 | croix | `carbonnieux` | `la de carbonnieux` | no relevant evidence |
| clinet | Château Clinet | Fleur de Clinet | D2 | fleur | `clinet` | `de clinet` | no relevant evidence |
| cos-destournel | Château Cos d'Estournel | Cos d'Estournel Blanc | D2 | blanc | `cos estournel` | `cos d estournel blanc` | refused as the grand vin |
| dauzac | Château Dauzac | D de Dauzac Blanc | D2 | blanc | `dauzac` | `d de dauzac` | refused as the grand vin |
| de-carles | Château de Carles | Haut-Carles (prestige cuvée) | D2 | haut | `carles` | `haut carles` | refused as the grand vin |
| de-fieuzal | Château de Fieuzal | Château de Fieuzal Blanc | D2 | blanc | `fieuzal` | `château de fieuzal blanc` | no relevant evidence |
| doisy-vedrines | Château Doisy-Védrines | Petit Védrines | D2 | petit | `doisy vedrines` | `petit védrines` | no relevant evidence |
| domaine-de-chevalier | Domaine de Chevalier | Rosé de Chevalier | D2 | rose | `chevalier` | `rosé de chevalier` | refused as the grand vin |
| ducru-beaucaillou | Château Ducru-Beaucaillou | Le Petit Ducru de Ducru-Beaucaillou | D2 | petit | `beaucaillou ducru` | `petit ducru` | refused as the grand vin |
| duhart-milon | Château Duhart-Milon | Le Blanc de Duhart-Milon | D2 | blanc | `duhart milon` | `le de duhart milon` | refused as the grand vin |
| figeac | Château Figeac | Petit-Figeac | D2 | petit | `figeac` | `petit figeac` | no relevant evidence |
| guiraud | Château Guiraud | Petit Guiraud | D2 | petit | `guiraud` | `petit guiraud` | refused as the grand vin |
| guiraud | Château Guiraud | Petit Guiraud Blanc | D2 | blanc, petit | `guiraud` | `petit guiraud` | no relevant evidence |
| haut-brion | Château Haut-Brion | Château Haut-Brion Blanc | D2 | blanc | `brion haut` | `château haut brion blanc` | refused as the grand vin |
| kirwan | Château Kirwan | Château Kirwan Blanc | D2 | blanc | `kirwan` | `château kirwan blanc` | refused as the grand vin |
| la-mission-haut-brion | Château La Mission Haut-Brion | La Mission Haut-Brion Blanc | D2 | blanc | `brion haut mission` | `la mission brion` | refused as the grand vin |
| leglise-clinet | Château L'Église-Clinet | La Petite Église | D2 | petite | `clinet eglise` | `petite église` | no relevant evidence |
| leoville-barton | Château Léoville-Barton | La Réserve de Léoville-Barton | D2 | reserve | `barton leoville` | `la de léoville barton` | no relevant evidence |
| lynch-bages | Château Lynch-Bages | Blanc de Lynch-Bages | D2 | blanc | `bages lynch` | `de lynch bages` | refused as the grand vin |
| mouton | Château Mouton Rothschild | Le Petit Mouton de Mouton Rothschild | D2 | petit | `mouton rothschild` | `petit mouton` | refused as the grand vin |
| olivier | Château Olivier | Château Olivier Blanc | D2 | blanc | `olivier` | `château olivier blanc` | refused as the grand vin |
| pedesclaux | Château Pédesclaux | Fleur de Pédesclaux | D2 | fleur | `pedesclaux` | `de pédesclaux` | refused as the grand vin |
| pichon-comtesse | Château Pichon Longueville Comtesse de Lalande | Réserve de la Comtesse | D2 | reserve | `comtesse lalande longueville pichon` | `de la comtesse` | no relevant evidence |
| smith-haut-lafitte | Château Smith Haut Lafitte | Château Smith Haut Lafitte Blanc | D2 | blanc | `haut lafitte smith` | `smith lafitte` | refused as the grand vin |
| stem-chateau-badette | Château Badette | La Fleur de Badette | D2 | fleur | `badette` | `la de badette` | refused as the grand vin |
| stem-chateau-fleur-cardinale | Château Fleur Cardinale | Fleur Cardinale Blanc | D2 | blanc | `cardinale fleur` | `fleur cardinale blanc` | refused as the grand vin |
| stem-chateau-ripeau | Château Ripeau | Tour de Ripeau | D2 | tour | `ripeau` | `de ripeau` | refused as the grand vin |

**What the categories mean.**

- **B, exact collision.** The wine has no identifying word beyond the
  grand vin's. Vivens, Ségla and Mondot are each part of the grand vin's
  own name, and no mark can exist. Margaux du Château Margaux is still
  caught, by the spelled-out containment test (`naming_spells_cuvee`).
- **D1 and D2 are the same static loss.** They differ only in whether
  another test still catches the wine by name. D2 holds by:
  - a colour word in the filename (`wrong_colour`);
  - a distinctive pair: `petit mouton`, `petit figeac`, `croix canon`;
  - a degenerate mark that happens to sit inside the written name:
    `de clinet` in "Fleur-de-Clinet".
- **F, Guiraud's G.** "G" is under 4 letters, so the mark falls back to
  the whole non-COMMON name, `le g de guiraud`. That holds for a file
  named `Le-G-de-Chateau-Guiraud` and fails for `G-de-Guiraud` and
  `G-DE-GUIRAUD`, which is how the estate files it. The one-letter-
  initial rule would catch `G-…`, but it fires only when the *listed*
  name begins with the letter, and this one begins with "Le".
- **E, 18 pairs between two other wines:**
  - 9 spelling variants with the same identifying words (Blason
    d'Issan with `'` and `’`, Les Charmes / Charmes de Kirwan, BRIO /
    BriO);
  - 9 pairs sharing one mark, all a colour variant or the same wine
    twice: Pagodes de Cos / Pagodes de Cos Blanc → `pagodes`; Pavillon
    Rouge / Pavillon Blanc → `pavillon`; Les Hauts de Smith / its Blanc
    → `les de smith`; Le Petit Haut Lafitte / its Blanc → `le lafitte`;
    and others.

  For the grand-vin question, E does no harm: both sides are refused as
  "another wine". It matters for telling those two wines apart, which is
  the second-wine path's job and already sibling-aware there.

## 4. Common-word impact

Every ignored token that occurs in a real listed wine name:

| token | set | estates | wines | collisions (B/D1) | weakened (D2) | partial (C/F) | only distinguishing token | examples |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| hauts | COMMON | 4 | 5 | **5** | 0 | 0 | 4 | Les Hauts du Tertre, Les Hauts de Lynch-Moussas, Les Hauts de Pontet-Canet |
| tours | COMMON | 3 | 3 | **3** | 0 | 0 | 3 | Les Tours de Beaumont, de Belcier, de Laroque |
| blanc | COMMON | 18 | 26 | 2 | 14 | 1 | 13 | Château de Malleret Blanc, Cos d'Estournel Blanc |
| petit | COMMON | 8 | 10 | 2 | 7 | 0 | 7 | Le Petit Paveil, Petit Védrines, Le Petit Ducru |
| croix | COMMON | 4 | 5 | 1 | 4 | 0 | 5 | Croix de Beauséjour, Croix Canon, La Croix de Carbonnieux |
| fleurs | COMMON | 1 | 1 | **1** | 0 | 0 | 1 | Les Fleurs de Malle |
| fleur | COMMON | 5 | 7 | 0 | 3 | 0 | 3 | Fleur de Clinet, Fleur de Pédesclaux |
| reserve | COMMON | 3 | 3 | 0 | 2 | 0 | 2 | La Réserve de Léoville-Barton, Réserve de la Comtesse |
| haut | COMMON | 10 | 17 | 0 | 1 | 0 | 1 | Haut-Carles |
| petite | COMMON | 1 | 1 | 0 | 1 | 0 | 1 | La Petite Église |
| tour | COMMON | 2 | 2 | 0 | 1 | 0 | 1 | Tour de Ripeau |
| rose | COMMON | 1 | 1 | 0 | 1 | 0 | 1 | Rosé de Chevalier |
| grand, cuvee, chateau, domaine, franc, rouge, blanche, cote, vieille, vieilles | COMMON | 1–11 each | | 0 | 0 | 0 | 0 | present, never the only distinguishing word |
| de, la, les, le, d, du, l | ARTICLES | up to 99 | up to 135 | 0 | 0 | 0 | 0 | articles never distinguish on their own; they **remain inside** degenerate marks |
| *(length < 4)* | single-word rule | 2 | 3 | 0 | 0 | 2 | 2 | G (Guiraud: 2 wines), II (Haut-Bailly II) |

The tokens that look generic and are not, in wine names: **hauts,
tours, petit/petite, croix, fleur/fleurs, reserve, blanc, rose**. Each
is the only word separating a real wine from its grand vin somewhere.
Nothing is decided here about which should stay in `COMMON`. `COMMON`
exists so that a mark never matches "Petit Verdot", "Sauvignon Blanc"
or "Grand Cru", and that purpose is real (Phase 2.3 §C).

## 5. V4 impact

Measured on the v4 evidence only. No reader pass was run, and nothing
was appended.

| | wines | v4 grand-vin decisions | documents |
| --- | ---: | ---: | ---: |
| **collision potential** (B, C, D1, F) | 18 | 140 implicated | 138 |
| **observed v4 false acceptance**: accepted as the grand vin | 8 | **77** | 77 |
| **observed v4 multi-target acceptance**: grand vin and second, same vintage | 1 | **8** (part of the 77) | 8 |
| refused as the grand vin (another test caught them) | | 63 | |
| no relevant evidence (no document in v4 named for the wine) | 7 | | |

The 77, by wine:

| wine | accepted as grand vin |
| --- | ---: |
| Les Tours de Belcier | 32 |
| Le G de Château Guiraud | 13 |
| Le Petit Haut Lafitte | 9 |
| Les Hauts du Tertre | 8 |
| Les Tours de Laroque | 7 |
| La Croix de Beaucaillou | 3 |
| Les Hauts de Smith | 3 |
| Les Tours de Beaumont | 2 |

**Not this defect, and kept apart:**

- Domaine de Chevalier's `Chevalier-Rouge-et-Blanc_2015` (a two-wine
  document);
- Haut-Bailly's `fiche-technique-hb-ii-2020` (an abbreviation, `hb`,
  which no name rule reads).

With those, the total of v4 grand-vin acceptances on documents named for
another listed wine is 79.

Only Les Hauts du Tertre shows up as multi-target, because only second
wines have a second-wine mode. The other seven are cuvées
(`GUARD_HAS_NO_CUVEE_MODE`), so their false grand-vin acceptance has no
competing acceptance to collide with. It is just as wrong, but invisible
to a conflict count. Phase 2.7's 8 GRAND_AND_SECOND conflicts are the
visible tenth of a 77-decision problem.

## 6. Les Hauts du Tertre regression

`python tools/audit-grand-marks.py --trace du-tertre "Les Hauts du Tertre"`:

```
grand vin: Château du Tertre   packed: chateaudutertre
wine:      Les Hauts du Tertre   tokens: ['Les', 'Hauts', 'du', 'Tertre']
   word     Les              rejected: shorter than 4 letters
   word     Hauts            rejected: in COMMON
   word     du               rejected: shorter than 4 letters, inside the grand vin's name, not a word
   word     Tertre           rejected: inside the grand vin's name "chateaudutertre"
   pair     Les Hauts        rejected: contains an article
   pair     Hauts du         rejected: contains an article
   pair     du Tertre        rejected: contains an article
   fallback Les Hauts du Tertre   COMMON words dropped: Hauts -> "les du tertre"
mark: 'les du tertre'   (mark_of says 'les du tertre')
```

1. **The grand vin** is "Château du Tertre": identifying words `tertre`,
   packed `chateaudutertre`.
2. **The second wine** is "Les Hauts du Tertre", tokens `Les Hauts du
   Tertre`.
3. **"hauts" disappears in two places:**
   - as a single word, rejected for being in `COMMON`;
   - at the fallback, which keeps only non-COMMON words.

   The only pair that could hold it, `Hauts Tertre`, is not adjacent:
   "du" sits between them.
4. **The comparison.** The mark is `les du tertre`. `says()` needs
   those words whole and in order. The filename `Hauts-du-Tertre-2017-
   FT-FR.pdf` has no "les", and a title saying "Les Hauts du Tertre" has
   "hauts" between "les" and "du". Neither matches.
5. **Why the grand vin accepts it.** No other test catches the name:
   - `naming_spells_cuvee` needs the full letters `leshautsdutertre`,
     which the file name lacks without "les";
   - the abbreviation rule needs a word that begins `lesdutertre`;
   - the sheet does not call itself a second wine.

   With nothing refusing it, the check finds the estate's own name
   "Tertre" and accepts. In v4, 8 such sheets were accepted as the grand
   vin and as the second wine for the same vintage.

`test-phase28.py` asserts the mark, the lost token, the category (D1)
and the trace.

## 7. Broader patterns

Patterns by category (a wine can carry several):

| pattern | A | B | D1 | D2 | F |
| --- | ---: | ---: | ---: | ---: | ---: |
| the grand vin's name plus a modifier | 100 | | 6 | 29 | 2 |
| "X de <estate>", other | 37 | | | 1 | |
| colour word (blanc, rouge, rosé) | 11 | | 2 | 15 | 1 |
| "petit X" | 1 | | 2 | 8 | |
| "Les Hauts de X" | | | **5** | | |
| "Les Tours de X" | | | **3** | 1 | |
| "Croix de X" | | | 1 | 2 | |
| one-letter name (Y, G, D, R) | 4 | | | 1 | |
| numbered (II) | 1 | | | | |
| **inside the grand vin's name** (Vivens, Ségla, Mondot) | | **4** | | | |

What the audit demonstrates:

1. **"Les Hauts de X" and "Les Tours de X" fail every time.** All 8
   wines of these two patterns are D1. The only distinguishing word is
   COMMON, and an article sits between it and the estate.
2. **"Petit X", "Croix X" and colour wines mostly survive (D2).**
   - Without an article, the pair rule keeps them: `petit mouton`,
     `croix canon`.
   - Colour wines are caught by `wrong_colour`.
   - They fail when an article separates the word from the estate:
     "Le Petit Haut Lafitte", "La Croix de Beaucaillou".
3. **The article is half of the mechanism.** In 25 of the 26 degenerate
   marks, an article both blocks the pair rule and survives into the
   fallback mark.
4. **A second wine named as part of the grand vin** (Vivens, Ségla,
   Mondot) cannot be distinguished by name at all, by construction.
   This is not a normalization artefact; only the document can tell.
5. **Single-letter wines** (Y, G, D, R) depend on a separate rule that
   reads the listed name's first letter. It fails when the listed name
   puts an article first ("Le G de Château Guiraud").
6. **Alternate names:** La Croix de Beaucaillou and La Croix
   Ducru-Beaucaillou are one wine under its old and new names, listed as
   two wines. They share documents, which are filed in the `caillou`
   folder.
7. **Degenerate marks cut both ways.** 26 marks consist of articles and
   the estate's own words: `de clinet`, `de pédesclaux`, `la de
   badette`, `de la comtesse`. They catch the other wine's filename only
   when that filename happens to carry those words in order. And they
   can match the grand vin's **own** text ("propriété de Clinet"),
   refusing a grand-vin sheet as the other wine's. This audit did not
   measure that second effect. It is a risk the shape demonstrates, not
   an observed error.

## 8. Recommendations (proposals only — nothing implemented)

1. **Give the grand-vin path the sibling-aware, word-preserving
   identity that second-wine mode already has.** Phase 2.3's
   `_refine_mark` keeps a COMMON word when it is the one that separates
   two wines ("blanc de lynch"). The same principle applied against the
   *grand vin* would keep "hauts", "tours", "petit" and "croix" exactly
   where they are the only difference, and nowhere else. A mark would
   then never consist of articles plus the estate's own words.
2. **Treat a mark made only of articles, house words and the grand
   vin's own words as no mark.** Fall through to a name-level identity
   instead: for example, the wine's full word set minus articles,
   matched as a set rather than an ordered phrase. A degenerate mark
   should never match the grand vin's own text.
3. **Make the one-letter rule read the identifying letter, not the
   listed name's first character**, so "Le G de Château Guiraud" is
   recognised in `G-de-Guiraud` and `G-DE-GUIRAUD`.
4. **For second wines contained in the grand vin's name** (Vivens,
   Ségla, Mondot), name matching cannot decide, and should not pretend
   to. The question belongs to document-level identity: the Phase 2.6
   claim and title rules, applied in grand-vin mode.
5. **Keep `COMMON`'s purpose.** A mark must never match "Petit Verdot"
   or "Sauvignon Blanc". The fix is to stop *discarding* a COMMON word
   when it is a wine's only identity, not to remove it from `COMMON`.
6. **Measure before and after with the same tools.** This audit and a
   v4-style dry run on the 138 implicated documents give the baseline:
   77 false acceptances, 63 refusals. Fixing it is a reader change, so
   it means a new decider version.
7. **Separately, for data:** La Croix de Beaucaillou / La Croix
   Ducru-Beaucaillou, and the 9 spelling-variant pairs, are duplicate
   listings, a canonical-data proposal for later.

## 9. Tests

`tools/test-phase28.py`, 17 checks, all pass:

- every estate of the reader's universe is covered (468), and each is
  placed in a collection;
- every listed wine other than the grand vin is considered (195);
- two runs give identical rows, so the audit is deterministic;
- every row has one of the categories;
- the step-by-step explanation agrees with `mark_of()` for all 195
  wines;
- Les Hauts du Tertre: its mark, its lost token, its category (D1) and
  its trace;
- the class beyond it: Les Tours de Belcier is D1, Blanc de Lynch-Bages
  is D2, Echo de Lynch-Bages is A;
- running the audit changes no canonical or evidence file (hashed
  before and after), and they match HEAD;
- the committed inventory equals a fresh run.

All earlier suites still pass (reader, data, 2, 2.1–2.7). See §10.

## 10. Phase 2.8 gate

**Canonical, data and evidence safety:**

- `git diff` over `data/fiches.js`, `data/chateaux.js`,
  `data/cuvees.js`, `data/sources.json`, `data/field-src.js`,
  `data/cuvee-src.js` and `data/evidence/` is empty.
- The evidence store still holds v1–v4 with 136,355 decisions, and
  `verify()` is clean. No evidence was written.
- The audit's only output is `data/phase28-grand-audit.jsonl`, an
  analysis file outside the canonical and evidence paths. A temporary
  `reports/grand-marks.json` from the first draft was deleted.

**`SAFE — AUDIT COMPLETE, READER DEFECTS FOUND`**

The grand-vin reader systematically loses identity for every wine whose
only distinguishing words are COMMON words or a single letter, whenever
an article separates them from the estate's name. The measured result:
12 wines not distinguishable by name, 77 v4 false grand-vin acceptances,
8 of them visible as multi-target conflicts.
