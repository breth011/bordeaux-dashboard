# Phase 2.6 — Specific second-wine identity

**Status: complete.**

- **Reader gate:** `SAFE`.
- **Evidence gate:** `SAFE`.
- No v4 generated, no canonical data changed, no evidence written.

2026-10-24, from `4370382`.

---

## 1. The problem

Second-wine mode asks whether a document belongs to *this* second wine.
Until now it accepted on evidence that only showed *a* second wine, and
five acceptances survived Phase 2.3 on that gap (Phase 2.4 §10):

| case | what the reader saw | what the document is |
| --- | --- | --- |
| Belgrave 2023 → Diane de Belgrave | "Second vin du Château Belgrave" | Diane: **correct** |
| Latour-Martillac page → Lagrave-Martillac 2020 | `lagrave-martillac` in the URL | an image page whose URL also names Lacroix-Martillac |
| the same page → Lagrave-Martillac 2019 | 2019 in the URL | the year of Lacroix-Martillac rouge |
| Caillou → Les Erables | "Second Vin blanc sec" | **Les Murets**, which Caillou's list does not hold |
| Pédesclaux 2025 → Fleur | "premier et second vin" | a map of both wines |
| La Mission page → Le Clarence | "this second wine" | La Chapelle de la Mission Haut-Brion |

Underneath sits one model limit. The reader's universe of wines is
closed: `sr.estates()` builds it from `chateaux.js` (`name`, `second`)
and `cuvees.js`. `named_wines()` can only report a wine from that list.
A wine nobody listed is invisible, so a document naming one looks like a
document naming nothing, and a generic phrase or a sibling's name then
decides.

## 2. The existing `is_second_wine` contract

`is_second_wine(path)` asks whether the opening of the document (first
120 characters, whitespace removed) contains "second vin", "deuxième
vin" or "second wine", not followed by ":" (a label) or "s" (plural),
and not preceded by "and"/"et". It answers **"is this some second
wine's document?"**

| caller | what it needs |
| --- | --- |
| `whose_sheet`, grand-vin mode | refuse a second wine's sheet as the grand vin: the generic meaning, and the right one |
| `read-sheets.py` (blend reader) | the same: keep a second wine's blend off the grand vin |
| `second_wine_verdict` step 3 (until now) | used as **identity**, which is the defect |
| `diagnose-second-mode.py`, `trace-second-wine-cases.py`, `test-reader.py` | diagnostics and its own tests |

Its "et" check compares a three-character slice with a two-letter word,
so it never fires. That is why Pédesclaux's two-wine map counts as a
second wine's sheet in grand-vin mode. **The function is left
unchanged**, bug included. Fixing it would change what the grand-vin
guard refuses: Pédesclaux's map would become a candidate grand-vin
sheet. That is a separate correction with its own measurement, and this
phase does not make it.

## 3. Generic against specific

| question | function | answers |
| --- | --- | --- |
| is this *some* second wine's document? | `is_second_wine` (unchanged) | true / false |
| what does its opening claim? | `second_wine_claim` (new) | `'this'` (it calls itself a second wine), `'both'` (first and second together, with "et" read correctly), `None` |
| which wines does it name, listed or not? | `wine_identity` (new) | see §4 |
| is it the requested second wine? | `second_wine_verdict` (rewritten) | `None` (accept), or a refusal with a reason |

## 4. The identity representation

`wine_identity(path, named, grand, wines, filename)` returns its parts
separately, never merged:

| part | meaning |
| --- | --- |
| `estate` | the name or the title carries the estate's own name |
| `generic` | `is_second_wine`: some second wine |
| `claim` | `second_wine_claim`: `'this'`, `'both'` or `None` |
| `name_listed` / `name_unlisted` | wines the name names (filename, or a page's URL), listed or not |
| `title_listed` / `title_unlisted` | the same for the title (letterhead off, "Second wine: X" labels off) |
| `title_first` | the first wine the title names, listed or unlisted, the estate and furniture aside |

Role ("a second wine"), wine identity ("Les Murets de Caillou"), estate
identity and canonical membership ("not on Caillou's list") are four
different answers, and none of them implies another.

## 5. Wines no list holds

`wine_shaped_names(text, grand, prose)` finds names built on the
estate's own name, which is how Bordeaux names its wines: Les Erables
*de Caillou*, Lacroix-*Martillac*, Echo *de Lynch-Bages*. It returns
each name with its position.

- **Where it looks.** Wherever the estate's name appears, it takes the
  words just in front of it: up to three, through *de*/*du*/*d'*, back
  to an article or a house word (including *Ch.*, *Cht*, and *Ch-teau*
  where an address lost its accented letter).
- **Where it stops.** At punctuation, a number, a dash with spaces round
  it, a conjunction, or document furniture (*Grand Vin*, *Fiche
  technique*, *FT*, *primeur*, *packshot*, language codes).
- **In prose**, it also stops at a lower-case word. "le nez de Duluc de
  Branaire-Ducru" gives Duluc de Branaire-Ducru; "la fois à
  Branaire-Ducru" gives nothing.
- **The shape test.** A name is kept only if it has the Bordeaux shape:
  a *de*/*du* link, or a hyphen joining it to the estate's name.
  "Château Bahans Haut-Brion", "Découvrez Giscours" and "Renommé
  Haut-Bailly" are not wine names.
- **Hyphenated estate names.** When the estate's name is a hyphenated
  pair, a hyphenated name sharing its second half counts too:
  Latour-Martillac → Lagrave-Martillac, Lacroix-Martillac.

`classify_name` then sorts each name into one of four kinds:

| kind | example |
| --- | --- |
| `estate` | only the estate's own and house words |
| `generic` | furniture and the estate's name |
| `listed` | a wine on the estate's list: the same identifying words (colour kept), the same name run together (`LABASTIDE-DAUZAC` = La Bastide Dauzac), or the listed name whole with something in front ("France Castelnau de Suduiraut", "OLIVIER BERNARD ESPRIT DE CHEVALIER") |
| `unlisted` | LES MURETS DE CAILLOU, lacroix-martillac, la-mission-haut-brion |

An unlisted wine is reported, not added. The refusal reads "the document
names a wine the estate's list does not hold: LES MURETS DE CAILLOU"
(code `UNLISTED_WINE`). The reader can now say "this document is second
wine Y, and Y is not known for this estate", which is a different
statement from "this is the target". Asked about Les Murets itself (a
hypothetical target, because it is not listed), the same sheet is
accepted. Nothing reaches `cuvees.js`.

## 6. The rule, and multi-wine documents

`second_wine_verdict` asks, in order:

1. **The name names another listed cuvée.** It is that cuvée's sheet;
   if it also names the second wine, `AMBIGUOUS_WINE`.
2. **The name names an unlisted wine.** If it also names the second
   wine, `AMBIGUOUS_WINE`; alone, `UNLISTED_WINE`.
3. **The name names the second wine.** Accept, unless the title never
   names it and opens on an **unlisted** wine. A listed sibling in the
   opening does not contradict the name: an estate's own pages carry its
   range in their menus and headers, so Pavillon Rouge's page opens on a
   menu naming Pavillon Blanc.
4. **The claim is `'this'`, but the name names nothing.** Accept,
   unless the title never names the second wine and opens on any other
   wine, listed or unlisted. A generic phrase is weak evidence, so here
   any other wine named first refuses.
5. **The name names only the grand vin.** `IS_GRAND_VIN`.
6. **The title opens on an unlisted wine.** `UNLISTED_WINE`.
7. **The title names the second wine** by `names_another_wine`'s
   existing first-named rule: accept. If it names another listed cuvée,
   it is that cuvée's sheet.
8. **Otherwise** `NOT_IDENTIFIED`.

"First-named" is the reader's own rule from `names_another_wine`: a
document is about the wine its title names first.

**Multi-wine documents.** A document naming the target and another
wine is never accepted on the strength of the target's name: steps 1,
2 and 4 refuse it. "First and second wine" is the `'both'` claim, which
step 3 does not accept. There is no new fallback: the first rule that
applies decides, in a fixed order.

## 7. URL and filename evidence

- The name of a crawled page is read from its **URL**, not its
  filename. The filename is the URL docked at the front
  (`2020__agrave-martillac…` for `lagrave-martillac…`), and a docked
  word is not a wine.
- A name naming the target is **not weakened**: steps 4 and 6 still
  accept on it. It no longer wins **against a title that never names it
  and opens on a wine no list holds** (step 3), or against **a second
  wine name in the same URL** (step 2). Years are not re-bound: case 3 is refused
  because the URL names two wines, which makes the year question moot.
- Generic role words in a URL or title ("second wine") never establish
  a specific wine.

## 8. Blend-reader and grand-vin compatibility

Proven by construction and checked by test. Comparing the reader's
source with `4370382` function by function, **the only existing
function changed is `second_wine_verdict`**, and only second-wine mode
calls it. These are byte-identical to Phase 2.5:

- `is_second_wine`
- `blend_of`
- `names_another_wine`
- `whose_sheet`
- `mark_of`
- `named_wines`

`read-sheets.py` and the grand-vin guard therefore behave exactly as
before. The dry run (§10) confirms it on every grand-vin context.

## 9. Regression matrix

On the real documents, from `tools/test-phase26.py`:

| document | asked as | expected | result |
| --- | --- | --- | --- |
| Belgrave 2023 (Diane) | Diane de Belgrave | ACCEPT | ACCEPTED |
| Belgrave 2023 (Diane) | Belgrave grand vin | REFUSE | WRONG_WINE |
| Lagrave/Lacroix image page | Lagrave-Martillac 2020 | REFUSE | AMBIGUOUS_WINE |
| Lagrave/Lacroix image page | Lagrave-Martillac 2019 | REFUSE | AMBIGUOUS_WINE |
| Caillou Les Murets | Les Erables | REFUSE | UNLISTED_WINE |
| Caillou Les Murets | Les Murets (were it listed) | accept on specific evidence | ACCEPTED |
| Pédesclaux both-wines map | Fleur de Pédesclaux | REFUSE | IS_GRAND_VIN |
| La Mission "this second wine" page | Le Clarence | REFUSE | UNLISTED_WINE |
| Lynch-Bages grand-vin sheet | Echo | REFUSE | IS_GRAND_VIN |
| Blanc de Lynch-Bages sheet | Echo | REFUSE | WRONG_WINE |
| Echo sheet | Echo | ACCEPT | ACCEPTED |
| Echo sheet | grand vin | REFUSE | WRONG_WINE |

On fixture pages:

| document | asked as | result |
| --- | --- | --- |
| generic "this second wine" naming an unlisted wine | the second wine | REFUSED, `UNLISTED_WINE` |
| URL naming the second wine, title naming another | the second wine | REFUSED, `UNLISTED_WINE` |
| URL naming the second wine and another wine | the second wine | `AMBIGUOUS_WINE` |
| URL and title both naming the second wine | the second wine | ACCEPTED |
| "premier et second vin" | the second wine | not accepted |
| grand-vin document | the second wine | refused |
| Blanc document | the second wine | refused |

Phase 2.3's own protections are untouched and still pass (47 checks),
and the Echo diagnosis is unchanged:

- Echo sheets accepted 70/71;
- grand-vin sheets accepted 0/110;
- Blanc sheets accepted 0/53;
- the ten "blanc" collision estates;
- the group-footer protection;
- the Echo data structure.

## 10. Dry-run impact

`tools/dryrun-second-identity.py --write` runs both readers on the
same bytes:

- the reader at `4370382`, loaded from git;
- the reader in this commit.

Each file is found by its own folder (Phase 2.5), so the comparison
isolates the reader change. It covers every manifest sheet, as the grand
vin and as the second wine, for each of its candidate years. Output:
`data/phase26-impact.jsonl` (analysis, not evidence, not v4).

| | contexts | unchanged | changed |
| --- | ---: | ---: | ---: |
| grand vin | 13,999 | 13,999 | **0** |
| second wine | 8,160 | 8,028 | 132 |

(123 artifacts were not asked: provenance failures, Phase 2.5.)

| v3 / base reader | new reader | n | read |
| --- | --- | ---: | --- |
| ACCEPTED | refused | **6** | the five Phase 2.4 cases (Lagrave/Lacroix ×2, Caillou, La Mission, Pédesclaux), plus Haut-Bailly's `fiche-technique-hb-ii-2019`, which names Haut-Bailly II, listed in the data as a wine apart from the second wine |
| IS_GRAND_VIN | **ACCEPTED** | **31** | second-wine sheets v3 wrongly refused: Les Hauts du Tertre (17), La Bastide Dauzac (13, filed as `LABASTIDE-DAUZAC`), Haut de Carles (1) |
| IS_GRAND_VIN / NOT_IDENTIFIED | UNLISTED_WINE | 95 | refused before and after; only the reason changes |
| — | — | 0 | accepted → unresolved |

- **Wines absent from canonical lists.** UNLISTED_WINE appears in 97
  contexts (92 documents, 25 estates). The real wines among them are
  Les Murets de Caillou, Lacroix-Martillac, Les Arums de Lagrange,
  Pagus de Lagrange, Les Divertissements de Malle, La Mission Haut-Brion
  and R de Real Caillou. They are reported, and are candidates for a
  separate canonical proposal. Nothing was added.
- **Noise.** Among the 95 refusals that only changed reason, some reason
  labels are furniture read as a name in a page address:
  `paques-latour-martillac` (an Easter page), `at-cantemerle`,
  `prix-giscours`. Those documents were refused before and are refused
  now, so no acceptance depends on the label. It is a known limit of the
  name-shape rule on addresses, and it fails safe.
- **Grand-vin decisions:** 0 changed.
- **Blend decisions:** unchanged by construction (§8). `is_second_wine`
  and `blend_of` are byte-identical.

### How the model got here

The first version of the name finder read prose as wine names, and the
dry run caught it before anything was committed. That version withdrew
134 acceptances, and reading them showed most were wrong:

- prose read as names: "la fois à Branaire-Ducru", "Le nez de Duluc…";
- listed wines with something in front: "France Castelnau de Suduiraut";
- a sibling in a page's menu outranking the page's own wine (Pavillon
  Rouge losing to "Pavillon Blanc").

Three general rules fixed it (§5, §6), and the withdrawals fell from 134
to the six above:

- the name-shape requirement, with the lower-case stop in prose;
- containment and run-together matching against listed names;
- the first-named, name-first contradiction rule.

## 11. Tests

| suite | result |
| --- | --- |
| `test-reader.py` | all pass (110 ok) |
| `test-data.py` | 11 pass |
| `test-phase2.py` | 30 pass |
| `test-phase21.py` | 27 pass |
| `test-phase22.py` | 17 pass |
| `test-phase23.py` | 47 pass |
| `test-phase24.py` | 26 pass |
| `test-phase25.py` | 46 pass |
| `test-phase26.py` | **62 pass** (new) |

`test-phase26.py` has four parts:

- **Unit checks** on names and phrases, including the six prose
  phrases the first draft misread, and the three listed-with-prefix and
  run-together cases.
- **Fixture pages** for every rule in §6.
- **Contract checks.** The only existing function changed is
  `second_wine_verdict`; six shared functions are byte-identical to
  Phase 2.5; `is_second_wine`'s callers are the known ones.
- **The real-document matrix**, plus a check that no unlisted wine
  reached `cuvees.js`.

One trap the fixtures surfaced: a second wine whose distinctive word is
"second" would be "named" by every "second vin" sentence. No listed
wine has one; the only listed name containing "second" is Yquem's
bracketed note, which `_name_words` drops.

## 12. Canonical safety

`git diff --name-only HEAD` over `sources.json`, `fiches.js`,
`cuvees.js`, `field-src.js`, `cuvee-src.js` and `data/evidence/` is
empty. Les Murets, Lacroix-Martillac and every other unlisted wine stay
out of the lists. The Echo entries and the two estates from `f445e96`
are untouched.

## 13. Is v4 ready?

**Reader gate: `SAFE`.**

- Generic and specific second-wine evidence are now separate questions.
- Wines no list holds are recognised and reported without being added.
- Multi-wine documents are refused deterministically.
- URL evidence yields to a contradicting title.
- The grand-vin and blend paths are byte-identical.
- All nine suites pass.

**Evidence gate: `SAFE`.**

- `provenance.py` and the store are unchanged.
- The reader's fingerprint moved (`ba6795763d67` → `c12eb3102b45`), so
  the store now refuses any further rows under v3. Shown by a real
  run: `RefusedAppend: v3 was written by reader ba6795763d67; these rows
  come from c12eb3102b45`.
- The next pass must therefore be v4, which is what the provenance
  rules require.

Generating v4 needs:

- the runners' `DECIDER_VERSION` set to 4;
- a commit holding this reader;
- a clean tree.

Neither gate turns these two open items into blockers:

- **`is_second_wine`'s "et" bug.** It affects grand-vin mode (§2).
- **Furniture vocabulary.** `GENERIC_NAME_WORDS` is a list. On page
  addresses, a furniture word missing from it gives a false `unlisted`
  label to a document that is refused anyway. In the dry run that never
  turned an acceptance into a refusal.
