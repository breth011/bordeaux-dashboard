# Phase 2.9 — Grand-vin identity fix: design, dry run and regression gate

**Recommendation: `READY FOR READER FIX`.**

- The rule is structural: no estate or wine is named in its code.
- In a dry run over the whole v4 grand-vin universe it withdraws 87
  false grand-vin acceptances, 70 of Phase 2.8's 77 plus 17 more of the
  same kind.
- It withdraws **no** genuine grand-vin acceptance and accepts nothing
  v4 refused.
- It changes **no** second-wine decision.

No canonical data or evidence changed, and no evidence was written.
The reader fingerprint moved from `c12eb3102b45` to `7e8cfed1c24e`, so
the store now refuses more v4 rows, and the next evidence pass is a new
decider version.

Started from `5778417`, 2026-10-24.

---

## 1. Problem

Phase 2.8 (`docs/PHASE-2.8-GRAND-VIN-AUDIT.md`) found that the grand-vin
check builds each other wine's mark with `mark_of(other, grand)`, without
siblings. A wine whose only words beyond the grand vin's are COMMON
words (*hauts, tours, petit, croix, fleurs*) or a single letter gets a
mark of articles plus the estate's name: `les du tertre`, `les de
belcier`, `le lafitte`, `le g de guiraud`. No filename or title writes
those, so nothing refuses the sheet.

The measurements:

- 12 wines slipped every grand-vin name test;
- 140 v4 grand-vin decisions were implicated;
- 77 of them accepted another wine's sheet as the grand vin.

## 2. The existing second-wine principle

`_refine_mark(other, grand, siblings, clash)` runs only in second-wine
mode, and only when a sibling also carries a wine's mark. It then looks
for the **shortest span of the wine's own words** that meets all of
these:

- it contains at least one word that is not an article, not COMMON and
  not a house word;
- it does not start or end on an article;
- it is not inside the grand vin's name;
- no sibling carries it;
- it contains a word the clashing sibling lacks.

How it behaves:

- **Tokens.** It works on tokens (`_name_words`, `packed`) and
  matches with `says`.
- **Kinds of word.** COMMON words, including colour words, may sit
  inside the span but never make it up alone. Articles may not start or
  end it.
- **Direction.** It is directional: this wine against its siblings.
- **Inputs.** It relies on the estate's listed wines.

**The principle:** a word that is generic in prose is kept when it is
the word that separates two wines, anchored to a real word, never on
its own. It cannot simply be copied, because it compares a wine with
its *siblings* and never fires without a clash. The grand-vin question
compares a wine with the *grand vin*.

## 3. The grand-vin rule

**Own word.** A word of the other wine that the grand vin's identifying
words (`wset`) lack. House words do not count, and neither do articles,
except a single capital letter, which is a wine's initial: the D of "D
de Dauzac Blanc", the G of "Le G de Château Guiraud", the Y of "Y
d'Yquem". **COMMON words count.**

Given the grand vin and another listed wine of the same estate, the
grand-vin path's mark is:

1. **Trim.** The ordinary mark, with articles removed from either end,
   because filenames drop a leading article.
2. **Case B, non-discriminator.** If the mark then holds an own word, it
   identifies the wine, and it is kept as it is.
3. **Case C, exact canonical collision.** If the wine has no own word,
   its name is the grand vin's (Vivens, Ségla, Mondot). The mark stays
   what it was, and no identity is invented.
4. **Case A / D, meaningful discriminator.** Otherwise the mark is
   rebuilt as the span of the name **from its first to its last own
   word**, so several common words that distinguish it together stay
   together. The span is extended to the nearest word of the estate's
   name, with no article at either end.

Examples of case A / D:

| wine | old mark | new mark |
| --- | --- | --- |
| Les Hauts du Tertre | `les du tertre` | `hauts du tertre` |
| Les Tours de Belcier | `les de belcier` | `tours de belcier` |
| Le Petit Haut Lafitte | `le lafitte` | `petit haut` |
| Le Petit Haut Lafitte Blanc | `le lafitte` | `petit haut lafitte blanc` |

## 4. Implementation

All changes are in `tools/sheetreader.py`. No other production code was
touched.

- **`mark_of(other, grand, siblings=None, against_grand=False)`.** The
  new argument defaults to off, so every existing caller gets exactly
  the mark it always got: `blend_of`, the second-wine path,
  `check-data.py`, the second-wine label stripper. When on, it returns
  `_grand_mark(...)`.
- **`_own_tokens`** and **`_grand_mark`** implement §3.
- **`names_another_wine`** passes `against_grand=True` only when it has
  no siblings, which is the grand-vin loop in `whose_sheet`. Second-wine
  mode always passes a list, even an empty one, and is untouched.
- **`abbreviates_other_wine`** was tried with the new mark and **left on
  the old one**; the reason is in §8. Only a comment was added.

Unchanged, and asserted byte-for-byte or by behaviour:

- `is_second_wine`
- `blend_of`
- `second_wine_verdict`
- `named_wines`
- `whose_sheet`
- `_mark_of`
- `wine_identity`
- every mark with siblings
- every mark without `against_grand`

## 5. Universe-wide impact

`tools/dryrun-grand-identity.py --universe` covers all 195 other wines.
For each it compares the old and new mark, and runs the grand-vin name
tests on the filename forms Phase 2.8 used, under the old reader
(`5778417`, loaded from git) and the new one. Output:
`data/phase29-grand-dryrun.json`.

| class | wines |
| --- | ---: |
| changes nothing | 165 |
| **prevents a false collision** (a name for the wine passed before, refused in every form now) | **14** |
| strengthens distinction (mark gains its real word, already caught) | 12 |
| exposes an exact canonical collision (left as is) | 4 |
| creates ambiguity (new mark carried by the grand vin's own name) | **0** |
| requires further inspection | 0 |

**Strengthened:**

| wine | old mark | new mark |
| --- | --- | --- |
| Croix de Beauséjour | `de beauséjour` | `croix de beauséjour` |
| La Croix de Carbonnieux | `la de carbonnieux` | `croix de carbonnieux` |
| Fleur de Clinet | `de clinet` | `fleur de clinet` |
| Le Blanc de Duhart-Milon | `le de duhart milon` | `blanc de duhart` |
| La Mission Haut-Brion Blanc | `la mission brion` | `brion blanc` |
| La Réserve de Léoville-Barton | `la de léoville barton` | `réserve de léoville` |
| Blanc de Lynch-Bages | `de lynch bages` | `blanc de lynch` |
| Fleur de Pédesclaux | `de pédesclaux` | `fleur de pédesclaux` |
| Réserve de la Comtesse | `de la comtesse` | `réserve de la comtesse` |
| Château Smith Haut Lafitte Blanc | `smith lafitte` | `lafitte blanc` |
| La Fleur de Badette | `la de badette` | `fleur de badette` |
| Tour de Ripeau | `de ripeau` | `tour de ripeau` |

Of Phase 2.8's 45 common-word-loss wines:

- the 12 that slipped every test are all now caught (§6);
- 12 of the 33 already caught gained their real word;
- the other 21 keep the mark they had, because it already held an own
  word: `petit mouton`, `croix canon`, `d de dauzac`, `château kirwan
  blanc`, and so on.

**Sibling overlap, not grand-vin ambiguity.** In 4 cases the new mark is
also carried by another of the estate's *other* wines:

| wine | new mark | also carried by |
| --- | --- | --- |
| Les Hauts de Smith | `hauts de smith` | Les Hauts de Smith Blanc |
| Le Petit Haut Lafitte | `petit haut` | Le Petit Haut Lafitte Blanc |
| Château Smith Haut Lafitte Blanc | `lafitte blanc` | Le Petit Haut Lafitte Blanc |
| La Mission Haut-Brion Blanc | `brion blanc` | La Clarté de Haut-Brion Blanc |

In grand-vin mode both wines are refused either way. The overlap can
only change *which* wine a refusal names, and second-wine mode, which
does tell siblings apart, does not use these marks.

## 6. The 12 previously uncaught wines (and the two G wines)

Every one is now refused by name in every written form tested (full,
without article, without house word, run together). This is asserted
in `test-phase29.py`:

| wine | Phase 2.8 | old mark | new mark | caught |
| --- | --- | --- | --- | --- |
| Les Tours de Belcier | D1 | `les de belcier` | `tours de belcier` | yes |
| Le Petit Haut Lafitte | D1 | `le lafitte` | `petit haut` | yes |
| Les Hauts du Tertre | D1 | `les du tertre` | `hauts du tertre` | yes |
| Les Tours de Laroque | D1 | `les de laroque` | `tours de laroque` | yes |
| La Croix de Beaucaillou | D1 | `la de beaucaillou` | `croix de beaucaillou` | yes |
| Les Hauts de Smith | D1 | `les de smith` | `hauts de smith` | yes |
| Les Tours de Beaumont | D1 | `les de beaumont` | `tours de beaumont` | yes |
| Les Fleurs de Malle | D1 | `les de malle` | `fleurs de malle` | yes |
| Les Hauts de Lynch-Moussas | D1 | `les de lynch moussas` | `hauts de lynch` | yes |
| Les Hauts de Pontet-Canet | D1 | `les de pontet canet` | `hauts de pontet` | yes |
| Le Petit Haut Lafitte Blanc | D1 | `le lafitte` | `petit haut lafitte blanc` | yes |
| Les Hauts de Smith Blanc | D1 | `les de smith` | `hauts de smith blanc` | yes |
| Le G de Château Guiraud | F | `le g de guiraud` | `g de guiraud` | yes |
| Le G de Château Guiraud Blanc | F | `le g de guiraud` | `g de guiraud` | yes |

**Les Hauts du Tertre, step by step.** The tokens are `Les Hauts du
Tertre`, and the own word is `Hauts`, which is in COMMON. The old mark
`les du tertre` (from Phase 2.8's trace) holds no own word, so it is
case A. The span runs from `Hauts` to the nearest estate word `Tertre`,
through `du`, giving `hauts du tertre`. The real file
`Hauts-du-Tertre-2017-FT-FR.pdf`:

- is **refused** as Château du Tertre's grand vin ("the sheet names
  another of the estate's wines: Les Hauts du Tertre");
- is still **accepted** as Les Hauts du Tertre, the second wine.

Phase 2.8's `--trace` is unchanged; it explains `mark_of` without
`against_grand`.

## 7. V4 dry-run impact

`tools/dryrun-grand-identity.py --v4` re-judged every v4 grand-vin and
second-wine decision with the new reader, on the exact file v4 read
(`read.path`). It compared each with the recorded v4 verdict, which is
the old reader's. Every changed verdict was re-judged by the old module
too: **it reproduced v4 in all 87**, so each change is the rule's, not
the harness's.

**Phase 2.8's 140 implicated decisions:**

| class | n |
| --- | ---: |
| `EXPECTED_FALSE_GRAND_VIN_WITHDRAWAL` (of the 77 accepted) | **70** |
| `UNRESOLVED`: still accepted | 7 |
| `NO_CHANGE` (the 63 already refused) | 63 |
| `POSSIBLE_REGRESSION` | **0** |

**The 70 withdrawn, by wine:**

| wine | withdrawn |
| --- | ---: |
| Les Tours de Belcier | 32 |
| Le G de Château Guiraud | 12 |
| Les Hauts du Tertre | 8 |
| Les Tours de Laroque | 7 |
| Le Petit Haut Lafitte | 4 |
| Les Hauts de Smith | 3 |
| Les Tours de Beaumont | 2 |
| La Croix de Beaucaillou | 2 |

**The 7 unresolved** are name variants the listed names do not cover.
They are an alias limit, not a normalization defect:

- `Croix-Beaucaillou-2012` and `G-Guiraud-2015` drop the "de";
- five Smith Haut Lafitte sheets name the second red "Le **Petit
  Smith** Haut Lafitte", while the list holds "Le Petit Haut Lafitte",
  and `petit haut` is correctly not found in "petit smith haut".

**17 further withdrawals outside the 140**, all other wines' documents,
caught now by the title rule:

| documents | n | read |
| --- | ---: | --- |
| `2017/2018/2020/2021-HDS-ROUGE-…` | 10 | Les Hauts de Smith sheets ("Les Hauts de Smith 2017 Pessac-Léognan…"), filed under an abbreviation |
| `2017/2018-PHL-ROUGE-…` | 4 | Le Petit Haut Lafitte sheets |
| `Haut-du-Tertre-2013-FT-GB-C1145` | 1 | "Les Hauts du Tertre – Second label – Margaux" |
| `Menus-2023-GB-H` (2 contexts), `menu-smith-haut-lafitte` | 3 | restaurant menus listing Les Hauts de Smith and Le Petit Haut Lafitte; not a grand-vin sheet |

## 8. Grand-vin regression analysis

Over all **14,134 v4 grand-vin decisions**:

| v4 → new | n |
| --- | ---: |
| accepted → accepted | 9,380 |
| **accepted → refused** | **87** |
| refused → accepted | **0** |
| refused → refused | 4,667 |

**All 87 accepted → refused decisions are documents that are not the
grand vin's.** In each, the refusal reason names the other wine, and the
document's own opening confirms it: the 70 Phase 2.8 sheets and the 17
in §7. **Genuine grand-vin acceptances withdrawn: 0.** A real grand-vin
sheet, `Chateau-Lynch-Bages-2008-EN`, is asserted still accepted.

**Second-wine decisions:** 8,189, **0 changed**.

### What the first draft of the rule did, and why it changed

The first draft was measured the same way, and failed this gate in two
ways. Both are fixed structurally:

1. **It also dropped the house word.** "Château de Fieuzal Blanc"
   became `fieuzal blanc`, and "Domaine de Chevalier Blanc" became
   `chevalier blanc`. In a title those now start *after* the grand vin's
   "de Fieuzal" / "de Chevalier". `names_another_wine`'s first-named
   rule then called the white's own sheets the grand vin's:

   - Fieuzal Blanc 2022, FR and EN;
   - "DOMAINE DE CHEVALIER BLANC PRIMEUR 2014", FR and EN.

   That was 4 refused → accepted. **Fix:** trim articles only; house
   words stay.
2. **It also switched `abbreviates_other_wine` to the new mark.** That
   test is shared by second-wine mode, and one second-wine verdict
   changed reason. With real marks it also stopped refusing documents
   it had only ever refused **by accident**. A filename word "LES"
   begins the degenerate `lesdebelcier` / `lesdemalle`, so:

   - Bellefont-Belcier's `…LES-TERRASSES-DE-SAINT-CHRISTOPHE…` sheets
     (a sister estate's wine, filed in Belcier's folder) were refused;
   - de Malle's wedding brochures were refused.

   With the accident gone, they fell through to acceptance: 13 refused
   → accepted. **Fix:** `abbreviates_other_wine` keeps the old mark.
   The accidental "les" refusals remain. They are a separate latent
   defect, and removing them needs a guard for sister-estate and
   non-wine documents first.

## 9. Exact and partial collisions

| wine | Phase 2.8 | after | kind |
| --- | --- | --- | --- |
| Vivens (Durfort-Vivens) | B | unchanged, no mark | **identity-model limitation**: the name is part of the grand vin's |
| Ségla (Rauzan-Ségla) | B | unchanged, no mark | identity-model limitation |
| Mondot (Troplong Mondot) | B | unchanged, no mark | identity-model limitation |
| Margaux du Château Margaux | B | unchanged, `margaux du margaux`, still caught by `naming_spells_cuvee` | identity-model limitation, mitigated |
| Le G de Château Guiraud | F | `g de guiraud`: caught in every tested form, and 12 v4 acceptances withdrawn | **normalization defect, fixed** for names with "de". `G-Guiraud-2015` (no "de") still passes: a filename-form limit, not a probability shift. |
| Le G de Château Guiraud Blanc | F | `g de guiraud`, caught | normalization defect, fixed |

**Normalization defects:** the 12 D1 wines and the 2 Guiraud G wines
are fixed. **Identity-model limitations** are left as they are and are
not solved by normalization:

- the 4 exact collisions;
- the alias variants (Petit Smith Haut Lafitte, Croix without "de", G
  without "de").

## 10. New risks

- **New exact or subset collisions with the grand vin:** 0. No new mark
  is carried by its grand vin's own name; asserted for all 195 wines.
- **Sibling overlaps:** 4, harmless to the grand-vin verdict (§5).
- **More specific marks.** The 12 strengthened marks are longer: `fleur
  de clinet` instead of `de clinet`. A filename that wrote only "Clinet
  2nd" would no longer be caught by the mark. But the old degenerate
  mark also matched the grand vin's own text ("propriété de Clinet").
  In v4 no decision changed for any of these 12 wines.
- **Latent, not introduced:** `abbreviates_other_wine`'s accidental
  "les"-prefix refusals (§8), and the gap they hide (sister-estate
  sheets and non-wine documents accepted once a guard lets them
  through).

## 11. Tests

| suite | result |
| --- | --- |
| reader | all pass (110 ok) |
| data | 11 pass |
| Phase 2 | 30 pass |
| Phase 2.1 | 27 pass |
| Phase 2.2 | 17 pass |
| Phase 2.3 | 47 pass |
| Phase 2.4 | 26 pass |
| Phase 2.5 | 48 pass |
| Phase 2.6 | 61 pass (two byte-identity checks on `mark_of` / `names_another_wine` replaced by one behavioural check, see below) |
| Phase 2.7 | 16 pass |
| Phase 2.8 | 17 pass |
| **Phase 2.9** | **47 pass** (new) |

**`test-phase29.py` covers:**

- the du Tertre marks, and that the default mark is unchanged;
- all 12 previously uncaught wines and both G wines, caught by name;
- six already-caught wines, still caught, including D de Dauzac, Y
  d'Yquem and Echo;
- the three name-in-grand-vin collisions (no mark) and Margaux du
  Château Margaux (unchanged);
- **grand-vin protection:**
  - no new mark is in its grand vin's name;
  - every mark without `against_grand`, and every mark with siblings,
    equals the old reader's for all 195 wines;
  - seven shared functions are byte-for-byte unchanged;
  - the rule's code names no estate or wine;
- real documents:
  - Hauts du Tertre 2017 refused as grand vin, accepted as second wine;
  - Les Tours de Belcier 2015 refused;
  - G de Guiraud 2025 refused;
  - Lynch-Bages 2008 accepted;
- determinism, and no canonical or evidence mutation.

**Why the Phase 2.6 suite changed.** It asserted that `mark_of` and
`names_another_wine` were byte-identical to Phase 2.5, guarding *its*
scope. Phase 2.9 changes them on purpose, for the grand-vin path only.
The suite now asserts what that guarded, by behaviour: every mark
second-wine mode and `blend_of` use is identical to Phase 2.5's, for
every wine, with and without siblings.

## 12. Recommendation

**`READY FOR READER FIX`.**

- The rule is structural.
- It catches every wine Phase 2.8 found slipping through.
- In the full v4 dry run it withdraws 87 false grand-vin acceptances
  and nothing genuine.
- It accepts nothing new.
- It leaves second-wine mode and the blend reader exactly as they were.

The reader change is in this commit. Using it for evidence means a new
decider version (v5), from a clean commit, which is the next phase's
decision. No canonical correction follows from this phase.

**Git and safety:**

- `git diff` over `data/fiches.js`, `data/chateaux.js`,
  `data/cuvees.js`, `data/sources.json`, `data/field-src.js`,
  `data/cuvee-src.js` and `data/evidence/` is empty.
- The evidence store is unchanged (v1–v4, 136,355 decisions;
  `verify()` clean).
- Dry-run caches live in `reports/`, which is not tracked.
