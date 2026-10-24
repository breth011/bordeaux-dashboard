# Phase 2.1 — decisions in context: estate, wine, vintage

Evaluation and proposal only. Nothing applied. `data/sources.json`,
`fiches.js`, `cuvees.js`, `field-src.js` and `cuvee-src.js` are
byte-identical to HEAD, checked by `git diff` inside the test suites
rather than asserted.

2026-10-24. Decider version 2.

---

## The headline

Supplying the vintage and the wine changed what the reader concludes,
and it found three things the no-vintage pass could not:

1. **The Lynch-Bages 1990 gap is a manifest year error.**
   `Chateau-Lynch-Bages-1989-FR.pdf` is filed under 1990. Phase 2
   accepted it as the grand vin's because nothing asked about the year.
   With `year=1990` the guard refuses it — *"the filename calls this the
   1989 vintage"* — and with `year=1989` accepts it again. A regression
   test now holds all three answers.

2. **The census's HIGH_CONFIDENCE was fooled by group footers.** Of 244
   unattributed artifacts it called certain, **88 the reader judges to
   be another estate's**. `FICHE-PRODUIT-CHATEAU-LA-PATACHE-2019.pdf` sits
   in Bellefont-Belcier's folder and prints, at its foot, *"CHÂTEAU
   BELLEFONT-BELCIER – CHÂTEAU TOUR SAINT CHRISTOPHE – ENCLOS TOURMALINE –
   CHÂTEAU HAUT-BRISSON – CHÂTEAU LA PATACHE"* and `www.vignoblesk.com`.
   The census saw the folder's estate named and called it certain; the
   reader reads the filename and says La Patache. **This refutes my own
   Phase 2 recommendation** to apply the 244 next.

3. **The reader cannot read the Echo de Lynch-Bages' own sheets, even
   asked correctly.** See §6. This changes what the next phase has to do.

---

## 1. The evaluation universe

Not every artifact against every context — that would invent meaningless
combinations. For each artifact:

| | drawn from |
| --- | --- |
| **estate** | the manifest's; for the 908 with none, the folder's, labelled as a hypothesis |
| **wines** | every wine the estate makes: the grand vin, the second, each cuvée (`sr.estates()`, i.e. `chateaux.js` + `BDX_CUVEE_WINES`) |
| **vintages** | the manifest's year, the year the document declares of itself, any year the filename spells — capped at three |

A year in a filename is evidence, not truth: Phase 1 found the year
classifier wrong in 8 of 19 cases. So every candidate year is tried and
the decisions are kept side by side rather than one being chosen.

The authoritative scope audit — which estates and which wines are in
scope — is reserved for Phase 3. This pass uses the project's accepted
data as context and copies no canonical value into a conclusion.

| | |
| --- | --- |
| artifacts evaluated | 12,124 attributed + 908 unattributed |
| estate/wine/vintage contexts | 39,997 + 1,262 = **41,259** |
| decisions with a target vintage | 39,111 (886 had no year available anywhere) |
| contexts with at least one accepted document | 5,162 |

---

## 2. How a decision is generated

`whose_sheet()` already took `year` and `is_second`; Phase 2 passed
neither. Now:

```python
sr.whose_sheet(path, file, estate_name, cuvees, second, cat,
               year=target_vintage,
               is_second=(target_role == 'second'))
```

`is_second` matters: without it the reader refuses every second wine's
sheet *for being the second wine's sheet*, which is true and useless.

### A limit of the reader, recorded rather than worked around

`whose_sheet` has exactly two wine modes — the grand vin, and the second
wine via `is_second`. **It has no mode for a named cuvée.** Asked about
the Blanc de Lynch-Bages it answers "names another of the estate's
wines", which means *not the grand vin* and says nothing about the
Blanc.

So a cuvée context is recorded as `NOT_EVALUATED` with the code
`GUARD_HAS_NO_CUVEE_MODE`. The context stays in the matrix — the
question is real and the answer is "this architecture cannot answer it".
**18,438 of 39,997 contexts (46%) are this.** That is the single largest
gap the pass revealed, and it is in the reader, not the documents.

---

## 3. Decision identity

One `row_key()` in `tools/evidence.py`, used by every writer and every
test:

```
artifact, folder, estate, wine, field, vintage,
target_estate, target_wine, target_role, target_vintage, v
```

Every part is there because leaving it out produced duplicates, and the
tests found each one:

| key | duplicates | what was missing |
| --- | --- | --- |
| artifact, estate, wine, v | 654 | a basename occurs in more than one folder 888 times |
| + folder | 255 | a record can hold a pin on two fields; a file can sit under two years |
| + field, vintage | 174 | — the manifest's own duplicate rows |
| + target_wine, target_vintage | 8,882 | **the contextual pass**: see below |
| + target_role, target_estate | 527 | — every one from a duplicate manifest row |

The fourth step was the instructive one. My first test allowed "174 ×
40" duplicates, which was a guess, and the pass returned 8,882. Tracing
them found two real faults rather than noise:

- **102 estates list their second wine among their cuvées as well**, so
  one wine was evaluated twice — as the second (a real verdict) and as a
  cuvée (`GUARD_HAS_NO_CUVEE_MODE`). Without `target_role` those
  collided, and **8,181 of the colliding pairs carried different
  verdicts**. The collision was hiding information, not de-duplicating
  it.
- `test-phase2.py` kept **its own copy** of the key tuple, which did not
  follow when `evidence.py` changed — the same drift `row_key()`'s
  docstring warns about, in my own test file. It now imports the key.

The 527 that remain all trace to a manifest row duplicating another, and
`test-phase21.py` asserts exactly that: **zero duplicates the manifest
does not itself explain**. Not a bound — an exact account.

**Idempotence, proven directly:** Lynch-Bages' 1,040 contextual
decisions re-run, 0 appended.

The no-vintage decisions (v1) and the contextual ones (v2) coexist:
`target_vintage` is absent from every v1 row, so no v2 row can collide
with one. **Store: 13,065 → 54,325 decisions** — exactly 13,065 + 39,997
+ 1,262 + the header.

---

## 4. Vintage behaviour

| | n |
| --- | --- |
| `WRONG_VINTAGE` | **1,232** — was 0, because nothing asked |
| `NO_VINTAGE_STATED` | 14 |
| accepted with a target vintage | 14,209 |

### What changed — in the comparable context only

Phase 2 asked one thing: the grand vin, at no vintage. The only fair
comparison is the grand vin **at the manifest's own year**. Comparing
Phase 2's single verdict against every new context made a 2017 sheet
judged against 2014 look like a verdict that changed, when it was a
question nobody had put — and I reported it that way at first, then
corrected the comparison.

| was | now | n | meaning |
| --- | --- | --- | --- |
| ACCEPTED | WRONG_VINTAGE | **87** | **a genuine reversal**: the manifest year is wrong |
| PRESS_DOCUMENT | WRONG_VINTAGE | 77 | guard order, not a reversal |
| WRONG_WINE | WRONG_VINTAGE | 28 | guard order |
| WRONG_ESTATE | WRONG_VINTAGE | 10 | guard order |
| ACCEPTED | NO_VINTAGE_STATED | 4 | a genuine reversal |
| ACCEPTED | WRONG_WINE | 1 | La Clarté, a genuine reversal |

Only the rows that leave ACCEPTED are reversals. The rest are **guard
order**: once a year is supplied, the vintage guard runs before the
press and wine guards and reports first. A press dossier refused as
`WRONG_VINTAGE` is still a press dossier. Reporting those 115 as changed
verdicts would overstate what the vintage did by more than half.

So **92 documents were accepted for a year they are not about.** Some
are plainly manifest misparses: `Technical-Sheet-Ch-Batailley-2023.pdf`
filed under 1991; `PDF_CHATEAU_REYNON_FR_1671462035.pdf` under **2035**,
which is the tail of a Unix timestamp in the filename.

`tools/propose.py` turns these into **143 `manifest_vintage`
proposals**, all PROPOSED_REVIEW and none with a proposed year: the
reader can say the manifest's year is wrong, not which year is right.

---

## 5. Wine identity — the 56, in context

`tools/wine-identity.py` still classifies them as 50 / 4 / 2. The
contextual pass adds what the reader concludes when asked properly:

| class | n | asked as the filename's wine | asked as the manifest's wine |
| --- | --- | --- | --- |
| MANIFEST_METADATA_WRONG | 43 | WRONG_WINE, naming the Echo | GUARD_HAS_NO_CUVEE_MODE |
| (same, vintage first) | 3 | WRONG_VINTAGE | GUARD_HAS_NO_CUVEE_MODE |
| FILENAME_MISLEADING | 4 | WRONG_WINE / WRONG_VINTAGE | GUARD_HAS_NO_CUVEE_MODE |
| MULTI_WINE_DOCUMENT | 2 | — | — |

The 4 FILENAME_MISLEADING remain NO_CHANGE, and the 2 MULTI_WINE remain
for review. No conclusion changed. What the context added is §6.

---

## 6. The Echo cannot be read as the Echo

Asked *"is this the Echo de Lynch-Bages' sheet for its year?"* — the
correct question, in second-wine mode — the reader refuses **all 61
evaluations**:

```
WRONG_WINE  the name spells another of the estate's wines in full:
            Echo de Lynch-Bages
points_at.wine = Echo de Lynch-Bages
```

Two things follow, and they pull in opposite directions.

**It confirms the manifest is wrong.** The reader's own verdict names
the document's wine as the Echo. Three independent signals now agree —
filename, document text, and the reader's identification — which is
why the 50 stay PROPOSED_CORRECTION at HIGH.

**It shows the correction will not be enough.** The refusal comes from
`naming_spells_cuvee()`, which checks `others + (second,)`. `is_second`
switches off a different guard. Lynch-Bages lists the Echo in **both**
`second` and `cuvees`, so the cuvée-spelling guard catches the second
wine's own name and refuses it.

So if the next phase sets the manifest's `wine` to the Echo and does
nothing else, `read-fiches --cuvees` will offer the 50 sheets to the
Echo and the guard will refuse every one. **The 5 missing vintages will
stay missing, and the correction will look as though it failed.** The
double-listing has to be resolved in the same step — and it is not
Lynch-Bages alone: 102 estates list their second wine twice, and Issan
lists `Blason d'Issan` twice among its cuvées, once with `'` and once
with `’`.

The 13 Echo records that *do* exist cite negociant sheets
(`Echo-de-Lynch-Bages-2011-FT-GB-C0888.pdf`) filed correctly under the
Echo. Why those pass and the estate's own sheets do not is the first
thing Phase 3 should establish.

---

## 7. Multi-wine behaviour

The footer is now understood to fool three different checks, not one:

| level | check | footer effect |
| --- | --- | --- |
| wine | `wine-identity.py` | all 50 Echo sheets looked multi-wine — fixed in Phase 2 |
| estate | the census's observed estate | 88 La Patache / Le Rey sheets looked like Tour Saint-Christophe's |
| reader | `naming_spells_cuvee` | the Echo's own name refuses the Echo — §6 |

The 2 genuine MULTI_WINE_DOCUMENT cases stay multi-wine. The 50 Echo
sheets do not regress into multi-wine: `test-phase2.py` holds that.

### A third multi-estate group

**Vignobles K** (`www.vignoblesk.com`), confirmed from the document:
Bellefont-Belcier, Tour Saint-Christophe, Enclos Tourmaline,
Haut-Brisson, La Patache, Le Rey. Its sheets were crawled into
Bellefont-Belcier's and Tour Saint-Christophe's folders. It joins
Vignobles Bernaleau and Château Poitevin from Phase 2.

The same shape appears at Doisy-Daëne's folder, which holds
`PDF_CHATEAU_REYNON_*` and `PDF_CHATEAU_HAURA_*` — Reynon and Haura are
Dubourdieu-family properties alongside Doisy-Daëne. Observed in the
filenames, not yet confirmed at the source.

---

## 8. The 908, re-characterised

Asked per wine and per vintage against their folder's estate, with
every one of the 908 rows accounted for (keying by basename merged them
into 727 in my first report; fixed):

| Phase 2 state | n | now: reader accepts | refuses as another estate | not wine evidence |
| --- | --- | --- | --- | --- |
| HIGH_CONFIDENCE | 244 | **99** | **88** | 57 (trade 25, wrong wine 14, press 10, colour 8) |
| CANDIDATE | 444 | 373 | 57 | 14 |
| CONFLICT | 95 | 67 | 17 | 11 |
| REJECTED | 76 | 66 | — | 10 |
| UNRESOLVED | 49 | 43 | — | 6 |

Read carefully, because ACCEPTED does not mean what it sounds like.
`whose_sheet` is an **identity** check. ACCEPTED means "no guard objects
to this being the estate's document for that year" — not "this carries
wine data". A producer profile with no figures in it is accepted too,
because nothing objects. That is why 66 REJECTED become ACCEPTED: the
census rejected them for having no data and the reader has no opinion
about data. Neither is wrong; they answer different questions.

The column that changes decisions is the refusal one. **88 of 244
HIGH_CONFIDENCE are another estate's** — 36%.

---

## 9. Dry-run proposals

`data/proposals.jsonl`. No code path in `tools/propose.py` writes a
canonical file.

| | Phase 2 | Phase 2.1 |
| --- | --- | --- |
| PROPOSED_CORRECTION | 294 | **149** |
| PROPOSED_REVIEW | 446 | 518 |
| INSUFFICIENT_EVIDENCE | 144 | 360 |
| NO_CHANGE | 80 | 80 |

By kind:

| kind | correction | review | insufficient | no change |
| --- | --- | --- | --- | --- |
| wine_identity | 50 | 2 | — | 4 |
| estate_attribution | 99 | 373 | 360 | 76 |
| manifest_vintage | — | 143 | — | — |

**The contextual pass withdrew 145 corrections the census would have
proposed** — the 88 group-footer cases and the 57 the reader refuses as
trade listings, press, wrong wine or wrong colour. Each withdrawn
proposal carries its reason: *"the census called this certain because
the document names X, but the reader refuses it for every wine and
vintage of that estate (WRONG_ESTATE) — a group footer names every
property, so naming the estate is not evidence of being its document."*

The 99 estate corrections that survive need **two** signals: the
document names the folder's estate, *and* the reader accepts it for one
of that estate's wines and years.

---

## 10. Missingness, kept apart

The store now distinguishes, per estate/wine/vintage:

| state | how it shows |
| --- | --- |
| no document at all | no decision row for the context |
| document refused, wrong vintage | `WRONG_VINTAGE` |
| document refused, wrong wine | `WRONG_WINE`, with `points_at` |
| document refused, wrong estate | `WRONG_ESTATE` |
| document is not a data document | `PRESS_DOCUMENT`, `TRADE_LISTING` |
| the reader cannot answer | `GUARD_HAS_NO_CUVEE_MODE` |
| no manifest estate | the folder used as a labelled hypothesis |
| accepted | `ACCEPTED` — an identity non-objection |

No new missingness taxonomy was introduced; these are the reader's own
verdicts, kept distinct.

---

## 11. Tests

| suite | before | after |
| --- | --- | --- |
| `tools/test-reader.py` | 53 | 53 |
| `tools/test-data.py` | 8 | 8 |
| `tools/test-phase2.py` | 30 | 30 — now imports the shared key, scoped to v1 |
| `tools/test-phase21.py` | — | **27** |

All four pass.

The new 27 hold: a no-vintage decision differs from a targeted one; two
target vintages are two decisions; **the 1989 sheet is accepted with no
vintage, refused at 1990 as WRONG_VINTAGE, and accepted at 1989** — the
proof that the vintage is supplied and not merely recorded; the store
holds both versions; v1 has no WRONG_VINTAGE because it never asked;
estates are evaluated against more than one wine; the cuvée gap is
recorded rather than answered; no cuvée context claims a verdict; every
contextual duplicate traces to a manifest row; proposals stay
proposals; the four FILENAME_MISLEADING are NO_CHANGE; the 50 Echo are
PROPOSED_CORRECTION; the two multi-wine are left for review; and the
canonical files are unmodified.

---

## 12. Files deliberately not modified

`data/sources.json`, `data/fiches.js`, `data/cuvees.js`,
`data/field-src.js`, `data/cuvee-src.js` — verified by `git diff`, run
inside `test-phase2.py` and `test-phase21.py`.

Modified, none canonical: `tools/evidence.py` (the key),
`tools/test-phase2.py` (the key, and `target_estate` accepted as
context), `tools/propose.py`, `data/evidence-decisions.jsonl`
(appended), `data/proposals.jsonl` (new).

---

## 13. Unresolved

| | |
| --- | --- |
| 18,438 cuvée contexts | the reader has no cuvée mode |
| 102 estates double-listing their second wine | makes the second wine's own sheets unreadable — §6 |
| Issan's `Blason d'Issan` listed twice | one with `'`, one with `’` |
| 143 manifest years the reader contradicts | the right year needs a person |
| 360 INSUFFICIENT_EVIDENCE attributions | the reader refuses them for the folder's estate |
| Why 13 Echo negociant sheets read and the estate's own do not | not yet established |
| Reynon and Haura in Doisy-Daëne's folder | a likely fourth group, unconfirmed |

---

## 14. Recommended next step

The Echo is still the right first correction — the evidence is now
three signals strong — but it is **two changes, not one**, and doing
only the first would produce a correction that silently recovers
nothing:

1. **Resolve the double-listing at Lynch-Bages**: the Echo is the second
   wine and should not also be a cuvée. Then re-run the contextual pass
   for Lynch-Bages and confirm the reader **accepts** the Echo sheets in
   second-wine mode. That is the test of the fix.
2. **Then apply the 50 manifest corrections**, and confirm the 5 missing
   vintages (2008, 2009, 2010, 2015, 2016) gain records. `test-data.py`
   should then show the mis-filed count fall from 56 to 6.
3. **Then the 99 surviving estate corrections** — not 244.
4. Then the 102 double-listings generally, which is a data change to
   `BDX_CUVEE_WINES` and `chateaux.js`, not to the manifest.
5. Then the 143 manifest years.

Not yet: the 360 INSUFFICIENT_EVIDENCE attributions, and a cuvée mode
for the reader — which is real engineering, and the largest gap here.

Do not start without saying which to take.
