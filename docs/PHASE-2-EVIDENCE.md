# Phase 2 — persistent evidence

Investigation and persistence only. No canonical dataset file was
modified: `data/sources.json`, `fiches.js`, `cuvees.js`,
`field-src.js` and `cuvee-src.js` are byte-identical to HEAD, and
`tools/test-phase2.py` asserts it on every run rather than taking my
word for it.

2026-10-24. Decider version 1, census analyzer version 1.

---

## 1. What changed

| file | what it is |
| --- | --- |
| `tools/evidence.py` | new. Runs the guard chain over every artifact and records why it was accepted or refused. Migrates the hand-written `REFUSED` pins without removing them. |
| `tools/attribute.py` | new. The 908 artifacts with no manifest estate, with folder, filename and document identity kept apart. |
| `tools/wine-identity.py` | new. The 56 wine-identity cases, with the rule that fired shown. |
| `tools/conflicts.py` | new. The conflict model: five relations, append-only store. |
| `tools/read-fiches.py` | wired to record a disagreement at the two points it used to discard one. Which value wins is unchanged. |
| `data/evidence-decisions.jsonl` | new. One decision per line. |
| `data/attribution-candidates.jsonl` | new. 908 proposals, none promoted. |
| `data/wine-identity.jsonl` | new. 56 cases with their evidence. |
| `data/field-conflicts.jsonl` | new, created on the next merge. |
| `data/site-recipes.json` | two multi-estate sites recorded. Not a canonical dataset file. |
| `tools/test-phase2.py` | new. 29 invariants. |
| `tools/test-data.py` | +1 invariant (duplicate manifest rows). |

---

## 2. The persistent refusal model

`data/evidence-decisions.jsonl`, append-only, one decision per line:

```
artifact                the filename
kind                    guard | pin
ctx                     estate, wine, vintage, folder, evaluated_as
decision                ACCEPTED | REFUSED | NOT_EVALUATED
code                    the normalised reason
raw                     the verdict verbatim
points_at               the role and wine the guard thinks it is
evidence                what the decision rests on
v, reader, commit, at   decider version, reader fingerprint, commit, date
re_evaluable            whether a newer rule could decide differently
```

The reason codes are **not invented**. Every one is mapped from a
verdict string `whose_sheet()` actually returns, and `raw` keeps that
string so the normalisation is reversible. A verdict the table does
not know becomes `UNMAPPED_VERDICT` and shows up in the tests rather
than being folded quietly into `OTHER` — which is how the next rule
change will announce itself.

### What is now recorded

| code | n | from |
| --- | --- | --- |
| ACCEPTED | 8,626 | the guards raised no objection |
| WRONG_WINE | 2,212 | the sheet or filename names another of the estate's wines |
| NO_ESTATE_IN_MANIFEST | 908 | never evaluated by anything |
| PRESS_DOCUMENT | 579 | a press dossier or a filename saying so |
| WRONG_COLOUR | 400 | the filename says the other colour |
| WRONG_ESTATE | 162 | another château, or a sibling property |
| NOT_ON_DISK | 123 | named in the manifest, absent |
| TRADE_LISTING | 22 | a merchant's listing, not an estate's sheet |
| PINNED_BY_HAND | 33 | the `REFUSED` list, migrated |

So 3,408 refusals now have a durable reason where before they had a
line of terminal output. "Why is this document not in the dataset?" is
answerable without re-deriving it.

**One honest limitation.** Each artifact was evaluated once, as its
estate's grand vin, with no target vintage. The vintage guards
therefore never fire, so `WRONG_VINTAGE` and `NO_VINTAGE_STATED` do
not appear — not because no document fails them but because this pass
never asked. A per-wine, per-vintage pass is a larger run and belongs
to Phase 3.

### Versioning

A refusal is what one version of one rule concluded on one day, not a
fact about the document. Each row carries `v` (the decider version),
`reader` (a sha1 of `sheetreader.py` + `read-fiches.py`, so a rule
change is visible even without a version bump) and `commit`. A later
version appends beside the earlier rows; nothing in the file is ever
rewritten. The tests assert that two versions can coexist and that no
row lacks its attribution.

### Idempotence, and a defect it found

Running twice at one version must add nothing. The first key —
`(artifact, estate, wine, version)` — produced **654 duplicates**, and
the test caught it. The cause was not the key alone:

- a basename occurs in more than one folder 888 times, so the folder
  belongs in the row identity; and
- **174 manifest rows duplicate another row on file, folder, estate,
  wine and year** — two rows for one physical document.

The key now includes the folder. The 174 are a manifest defect, not
corrected here, and now pinned in `tools/test-data.py`. They matter
beyond tidiness: every count taken from the manifest is inflated by
them, so 13,032 sheets are 12,858 distinct ones.

---

## 3. The 908 unattributed artifacts

`data/attribution-candidates.jsonl`. The folder is recorded as
**evidence about where the crawler put the file**, never as the
answer — the de Braude/Mongravey pattern is precisely a crawler
filing documents under the wrong estate.

| state | n | at a classified estate |
| --- | --- | --- |
| CANDIDATE | 444 | 311 |
| HIGH_CONFIDENCE | 244 | 8 |
| CONFLICT | 95 | 2 |
| REJECTED | 76 | 1 |
| UNRESOLVED | 49 | 5 |

`HIGH_CONFIDENCE` means the document itself names the folder's estate,
carries wine data and states a vintage — two independent signals
agreeing. `CANDIDATE` means the folder names an estate and the
document carries data but names no estate itself, usually because the
fiche prints a logo rather than a name. `CONFLICT` means the document
names a different estate from its folder, and those 95 are the ones
that must not be bulk-assigned.

**No proposal names a wine.** An estate is not one wine, and defaulting
to the grand vin is exactly how a second wine's sheet becomes the
first wine's data. The tests assert that `proposed.wine` is null
everywhere.

### A scope correction

I first reported that only 21 of the 908 were at classified estates.
That was wrong, and the error is worth recording: I read only
`chateaux.js`, the 61 of the 1855 Médoc, and so called Doisy-Daëne
unclassified. It is a Barsac second growth of the same 1855 list and
owns **287 of the 908**.

"Classified" is four files, not one: `chateaux.js` (61, 1855 Médoc and
Graves), `sauternes.js` (27, 1855 Sauternes and Barsac), `graves.js`
(15, Crus Classés de Graves), `saintemilion.js` (14, Saint-Émilion
grands crus classés) — 117 estates. By that definition **327 of the
908 are at a classified estate**, Doisy-Daëne dominating.

The rest sit at Cru Bourgeois and Saint-Émilion estates held in
`crubourgeois.js` and `cruartisan.js` rather than in `BDX_CHATEAUX`,
which is why the report labels them "not in BDX_CHATEAUX". They are
real estates with records; they are simply outside the classified
scope.

| folder | n | collection |
| --- | --- | --- |
| doisy-daene | 287 | 1855 Sauternes & Barsac |
| bellefont-belcier | 100 | not in BDX_CHATEAUX |
| tour-saint-christophe | 100 | not in BDX_CHATEAUX |
| d'Argan | 84 | not in BDX_CHATEAUX |
| moulin-du-cadet | 74 | not in BDX_CHATEAUX |
| sansonnet | 74 | not in BDX_CHATEAUX |
| issan | 12 | 1855 Médoc & Graves |
| malartic-lagravière | 10 | Crus Classés de Graves |

367 of the 908 are PRODUCER_PROFILE — estate history and terroir pages
rather than vintage sheets — which is why only 226 are DATA_SHEET.

---

## 4. The 56 wine-identity cases

`data/wine-identity.jsonl`.

| state | n | confidence |
| --- | --- | --- |
| MANIFEST_METADATA_WRONG | 50 | HIGH |
| FILENAME_MISLEADING | 4 | HIGH |
| MULTI_WINE_DOCUMENT | 2 | MEDIUM |

All 50 are Lynch-Bages: `Echo-de-Lynch-Bages-YYYY-*.pdf` filed under
`wine: "Blanc de Lynch-Bages"`, with both the filename and the
document text naming the Echo. The other 6 are Léoville-Poyferré 2,
Fleur-Cardinale 2, Mouton 1, Grand-Puy-Lacoste 1.

`FILENAME_MISLEADING` is the mirror case and the reason the states are
separate: the document text agrees with the manifest and only the
filename misleads. Those four need no correction at all.

### The rule, and the two that failed

The subset test, with the two rejected alternatives recorded as tests
in `tools/test-phase2.py` so neither can come back:

| filename names | manifest says | verdict | why |
| --- | --- | --- | --- |
| Château Coutet | Opalie de Château Coutet Blanc | same wine | the manifest's words contain the filename's: a longer spelling |
| Echo de Lynch-Bages | Blanc de Lynch-Bages | different | neither contains the other |
| Pavillon Rouge du Château Margaux | Pavillon Blanc du Château Margaux | different | rouge and blanc *are* the wines |

"Does the filename name a different listed wine" gives **122** cases,
66 of them false — every `Opalie-de-ChateauCoutet.pdf`, where the
manifest is right and the filename merely omits "Blanc". Requiring the
names to be **disjoint** gives **3**, missing 53 — because that
discards "blanc", the one word separating the Blanc from the Echo.
Only the house words (château, clos, domaine, articles) are stripped.
**Colour words are identity, not decoration.**

### An edge case that changed the answer

The first run classified all 50 Echo sheets as MULTI_WINE_DOCUMENT,
because each names both "Echo de Lynch-Bages" and "Château
Lynch-Bages". The second is the house in the footer — *Château
Lynch-Bages, 33250 Pauillac* — not a second wine. The estate's own
name inside a cuvée's sheet is now excluded from the wine count and
kept as `also_names_the_estate`, so the distinction survives for the
sheets that genuinely cover two wines.

---

## 5. The shared sites — confirmed

Both hypotheses hold, on one fetch each.

**vignobles-bernaleau.com** — title *"Vignobles Bernaleau, des vins
d'exception"*. Names Château de Braude 7 times, Château Galland 6,
Château Mongravey 5. **One site, three estates.** Its PDFs sit under
`/wp-content/uploads/` as `FT-Ch-de-Braude-2016-GB.pdf` and
`FT-Ch-Mongravey-2016-GB.pdf`; a crawl files them all under whichever
estate it was fetching for, and the reader then assigns each by its
own filename. That is the whole 35-edge cross-citation. **The records
are right; the manifest folder is wrong.**

**chateau-poitevin.com** — title *"Château Poitevin – Cru Bourgeois
situé sur la commune de Jau-Dignac-et-Loirac"*. Names Poitevin 14
times and Château Moulin de Canhaut once. Same shape, and it also
explains why both estates hold the identical "CARNET DE BORD DU
MILLÉSIME" season note: it is one document.

Both sites serve byte-identical `robots.txt` — the same WooCommerce
template — which is corroboration of a shared operator.

Recorded in `data/site-recipes.json` as `multi_estate: true` plus
`serves`, with the evidence and why it matters. Deliberately **not** a
rule: "shared site means ignore the manifest estate" would be as
dangerous in reverse, because the manifest is right far more often
than it is wrong.

**Found while confirming:** Château Galland is a third estate on the
Bernaleau site and appears in no conflict pair and nowhere in the
dashboard. Noted, not acted on.

---

## 6. The conflict model

`tools/conflicts.py`, writing `data/field-conflicts.jsonl`.

### A correction to Phase 1

Phase 1 said disagreement "cannot be quantified because the losing
value was never written". That is true of the history and **false
going forward**, and finding out why was the useful part: at the
moment a value is dropped, both values are in hand.

Two places in `read-fiches.py` drop one:

```python
best.setdefault(key, {}).setdefault(f, (r['got'][f], r['src']))
```

The first document in the sort order takes the field and every later
document's value for it vanishes — incumbent in `best[key][f]`,
challenger in `r['got'][f]`, both right there.

```python
if f in held:          # never overwrite
    continue
```

Here the record's existing value wins, which is what makes a re-read
safe and is not in question. The document's value was discarded with
it.

Both now call `conflicts.note()`. **Which value wins is unchanged** —
the calls sit beside a `setdefault` and a `continue` and alter
neither.

### Five relations, not one

| relation | meaning |
| --- | --- |
| AGREE | two documents, same value. Corroboration, not conflict |
| SAME_VALUE_DIFFERENT_FORM | `13.5` and `13,5`; `18` and `18.0` |
| DISAGREE | genuinely different values |
| INCUMBENT_HELD | the record's value beat the document's |
| SUPERSEDED | an earlier document had already filled the field |

`winner` records which value is on the record and `why` the rule that
put it there — "first in the sort order" or "already on the record" —
so the choice is inspectable instead of invisible.

### What is not yet measured

The store is empty, and will fill on the next merge. The dry-run path
in `read-fiches.py` returns *before* the merge is built, so no conflict
is reachable without `--apply`, which writes canonical files and this
phase forbids. The mechanism is tested by unit cases instead.

So the backlog across the 674 multi-document records remains
unmeasured, by choice rather than by limitation. Phase 3 can measure
it with one `--prose` run per estate once writing is permitted again.

---

## 7. Tests

| suite | before | after | needs the archive |
| --- | --- | --- | --- |
| `tools/test-reader.py` | 53 | 53 | mostly |
| `tools/test-data.py` | 7 | 8 | no |
| `tools/test-phase2.py` | — | 29 | no |

The 29 new ones cover: a refusal is persisted; it keeps its reason
code; no verdict is unmapped; every decision names its rule version
and reader fingerprint; the identity context survives; the original
wording survives; persistence is idempotent; two versions can coexist;
the pins came across and are still in the Python; attribution states
are from the agreed set; no proposal claims a manifest estate; no
proposal guesses a wine; a CONFLICT proposes nothing; the subset
identity rule on six cases including both failed alternatives; the
five conflict relations; the recorder deduplicates; and the canonical
files are unmodified.

The last is checked by running `git diff --name-only HEAD` against the
five protected paths, not by assertion.

---

## 8. Files deliberately not modified

`data/sources.json`, `data/fiches.js`, `data/cuvees.js`,
`data/field-src.js`, `data/cuvee-src.js` — verified clean.

`tools/read-fiches.py` was modified, to record rather than discard.
`data/site-recipes.json` was modified, because item 4 asked for the
shared-site finding to be recorded as source knowledge. Neither is a
canonical dataset file.

---

## 9. Unresolved

| | n | why it stays unresolved |
| --- | --- | --- |
| CONFLICT attributions | 95 | the document names an estate its folder does not. Reading settled only 360 of 908 estates; these 95 are where the two signals actively disagree |
| UNRESOLVED attributions | 49 | unreadable, image-only, or no estate anywhere |
| MULTI_WINE_DOCUMENT | 2 | a document covering two wines has no single right attribution |
| Vintage-based refusals | — | this pass never asked for a vintage, so `WRONG_VINTAGE` is absent from the store and its true size is unknown |
| Field conflicts | 674 records | the mechanism is in place and the backlog needs a merge run |
| The 174 duplicate manifest rows | 174 | found by a failing test, not investigated |
| Château Galland | — | a third estate on the Bernaleau site, in no pair and not in the dashboard |

---

## 10. Recommended Phase 3

1. **A per-wine, per-vintage decision pass.** The refusal store has one
   decision per artifact, taken as the grand vin with no target year.
   Until it has one per (artifact, wine, vintage), the vintage guards
   are invisible and "refused" is only two-thirds answered.
2. **Then the 50 Echo sheets**, as the first manifest correction — the
   smallest change with the clearest evidence, and the test of whether
   a manifest correction is safe at all. `test-data.py` should then
   assert the count falls from 56 to 6.
3. **Then the 244 HIGH_CONFIDENCE attributions**, where the document
   and the folder already agree.
4. **Measure the conflict backlog** with one merge run per estate, now
   that nothing is lost when it happens.
5. **The 174 duplicate manifest rows**, which are cheap and make every
   manifest count honest.

Not in Phase 3: the 444 CANDIDATE attributions, where only the folder
speaks, and the 95 CONFLICT cases. Both want the per-vintage pass
first.

Do not start Phase 3 without saying which of these to take.
