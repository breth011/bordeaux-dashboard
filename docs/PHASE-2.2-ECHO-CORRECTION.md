# Phase 2.2 — Echo correction: stopped at the Stage A gate

**Status: stopped before any canonical change, as the phase's own rule
requires.** No canonical file was modified. Stage B was not started.

> "If any link fails, stop at that link and diagnose it rather than
> compensating downstream."

The first link failed — not because the fix did not work, but because
the fix as planned was built on an imprecise finding of mine, and
applying it would have broken the Echo while leaving the refusal in
place. This document records the diagnosis and the decision it needs.

2026-10-24, from commit `effcd4e`.

---

## The headline

1. **The data does not double-list the Echo.** It appears once in
   `BDX_CUVEE_WINES`, correctly marked `role:'second'`. My Phase 2.1
   summary said otherwise; it was describing the *loader's* view, not
   the data.
2. **The "double listing" is the loader merging the second wine into
   `cuvees` on purpose**, which the grand-vin evaluation depends on.
3. **The refusal comes from two reader defects**, neither fixable by
   any change to Lynch-Bages' data.
4. **The current second-wine mode is already unsafe**: it accepts 107
   of Lynch-Bages' grand-vin sheets as the Echo, and the Phase 2.1
   store holds 4,416 second-wine acceptances of grand-vin-filed
   documents across 94 estates.

---

## A. The dependency chain, as it actually is

Stated before editing, as the phase asks — and stating it is what
stopped the edit.

```
chateaux.js        second: 'Echo de Lynch-Bages'
cuvees.js          'lynch-bages': [
                     {slug:'blanc-de-lynch-bages', role:'other',  white},
                     {slug:'echo-de-lynch-bages',  role:'second', red  } ]
                   -> the Echo is defined ONCE, correctly

sr.estates()       e['cuvees'] = every name: in BDX_CUVEE_WINES
                                 (the role field is ignored)
                   if e['second'] not in e['cuvees']:
                       e['cuvees'].append(e['second'])     # on purpose
                   -> cuvees = ['Blanc de Lynch-Bages',
                                'Echo de Lynch-Bages']

whose_sheet()      answers "is this the GRAND VIN's sheet?"
                   - the second wine must be in `cuvees` for a second
                     wine's sheet to be refused as the grand vin's:
                     that merge is correct and essential
```

### Why the planned Stage A edit would have been wrong

Removing the Echo from `cuvees.js` would:

- **delete the Echo's wine definition** — its slug `echo-de-lynch-bages`
  and colour, which `read-fiches --cuvees` uses to key the 13 existing
  Echo records and the app uses to display the wine; and
- **not fix the refusal**, because `sr.estates()` re-adds the second
  wine from `chateaux.js` regardless.

The phase warned against exactly this — *"do not simply delete a string
from a file because it looks duplicated"* — and the warning was right.

### What the "102 estates" were

My Phase 2.1 report said 102 estates "list their second wine twice".
They do not. That count was taken from `sr.estates()` output, where the
loader merges every second wine into `cuvees`. It is the loader's
normal behaviour at every estate with a second wine, not 102 defects.

There **is** a real data double-listing, and it is something else —
the same wine under two spellings in one estate's list:

| estate | listed as | and as |
| --- | --- | --- |
| cantenac-brown | BRIO de Cantenac Brown | BriO de Cantenac Brown |
| cos-destournel | Pagodes de Cos | Les Pagodes de Cos |
| grand-puy-ducasse | Prélude à Grand-Puy Ducasse | Prélude à Grand-Puy-Ducasse |
| issan | Blason d'Issan | Blason d’Issan |
| kirwan | Les Charmes de Kirwan | Charmes de Kirwan |
| la-fleur-de-bouard | Le Plus de La Fleur de Bouärd | Le Plus de La Fleur de Boüard |

Six estates. Lynch-Bages is not one of them.

---

## B. The two reader defects

### Defect 1 — there is no real second-wine mode

`whose_sheet()` has three guards that recognise the second wine.
`is_second=True` switches off one:

| guard | in second-wine mode |
| --- | --- |
| `naming_spells_cuvee(named, grand, others, second)` | **still runs** — refuses the Echo for being the Echo |
| `if not is_second and is_second_wine(path)` | switched off |
| `for nm in (second,) + others: names_another_wine(...)` | **still runs** — iterates the second wine itself |

And nothing requires a document to *be* the second wine's. The guards
only refuse documents that name something else. So a grand-vin sheet,
which names no other wine, is accepted as the second wine:

| evaluated as the Echo | ACCEPTED | refused |
| --- | --- | --- |
| the Echo's own sheets | **0** | 69 |
| the grand vin's sheets | **107** | 8 |
| the Blanc's sheets | 0 | 50 |

That is backwards on both counts.

### Defect 2 — `mark_of` discards the word that tells two wines apart

`mark_of(wine, grand)` returns what distinguishes a wine's name, and
`names_another_wine` looks for it. For the Blanc:

- `blanc` is in `COMMON`, so a mark never matches "Sauvignon Blanc"
- `de` is an article; `lynch`, `bages` are in the grand vin's name
- no single word or pair qualifies, so it falls back to the name less
  its common words: **`'de lynch bages'`**

which every *X* de Lynch-Bages carries — including "Echo **de
Lynch-Bages**". So every Echo sheet "names the Blanc".

This is the Phase 2 lesson — *colour words are identity, not
decoration* — found inside the reader's own `mark_of`. The same
collision occurs between genuinely distinct wines at **10 estates**:

| estate | wine | mark | found inside |
| --- | --- | --- | --- |
| lynch-bages | Blanc de Lynch-Bages | `de lynch bages` | Echo de Lynch-Bages |
| margaux | Pavillon Blanc du Château Margaux | `pavillon` | Pavillon Rouge |
| cos-destournel | Pagodes de Cos Blanc | `pagodes` | Pagodes de Cos |
| guiraud | Petit Guiraud | `petit guiraud` | Petit Guiraud Blanc |
| olivier | Le Dauphin d'Olivier | `dauphin` | Le Dauphin d'Olivier Blanc |
| haut-bages-liberal | La Chapelle de Haut-Bages Libéral | `chapelle` | La Chapelle de Bages |
| leoville-poyferre | Moulin Riche / Pavillon de Poyferré | `moulin` / `pavillon` | each other |
| bourgeois-chateau-dillon | La Comtesse Noire | `comtesse` | Secret de la Comtesse |
| yquem | Y d'Yquem | `y d yquem` | a variant of itself |

### The trap in the obvious fix

The obvious fix for Defect 1 is "leave the second wine out of the
competing set in second-wine mode". Measured, it makes things worse:

| version | Echo sheets accepted | grand-vin sheets accepted as Echo |
| --- | --- | --- |
| current | 0 / 69 | 107 / 115 |
| naive (second excluded) | **0 / 69** | **110 / 115** |
| naive + "must name the second wine" | 0 / 69 | **1 / 115** |

The naive fix accepts *more* grand-vin sheets and still no Echo sheets,
because Defect 2 then refuses them for naming the Blanc. Adding a
positive requirement fixes the false acceptances (110 → 1) — but the
Echo still cannot be accepted until Defect 2 is fixed.

So **both defects have to be fixed, together, in the reader**, and the
first must include a positive requirement or it weakens validation.

---

## C. Stage A validation gate — run before any change

| | n |
| --- | --- |
| Echo second-wine evaluations | 69 |
| accepted | **0** |
| refused, "the name spells another of the estate's wines in full: Echo de Lynch-Bages" | 61 (current) |
| refused, "the sheet names another of the estate's wines: Blanc de Lynch-Bages" | 68 (with Defect 1 fixed naively) |
| refused, a genuine vintage mismatch | 1 |
| unexpected | 0 |

**Gate: failed.** Per the phase's own instruction, Stage B was not
attempted, and nothing was compensated downstream.

---

## D. Stage B

Not started. The 50 manifest corrections remain proposals in
`data/proposals.jsonl`, status PROPOSED_CORRECTION, unapplied.

Applying them now would route the 50 sheets to the Echo, where the
reader would refuse every one (Defect 2), and the five vintages would
stay missing — a correction that looks like it failed.

---

## E. Five-vintage baseline

Taken from the reader, not assumed. No "after" column, because nothing
was changed.

| vintage | Echo record now | Echo sheet in archive | manifest says | as the Echo today |
| --- | --- | --- | --- | --- |
| 2008 | none | yes | Blanc de Lynch-Bages | refused — names "Echo" (Defect 1) |
| 2009 | none | yes | Blanc de Lynch-Bages | refused — names "Echo" (Defect 1) |
| 2010 | none | yes | Blanc de Lynch-Bages | refused — names "Echo" / one vintage mismatch |
| 2015 | none | yes | Blanc de Lynch-Bages | refused — names "Echo" (Defect 1) |
| 2016 | none | yes | Blanc de Lynch-Bages | refused — names "Echo" (Defect 1) |

15 of the 50 cases fall in these five vintages. Per-case detail in
`data/echo-baseline.jsonl`.

---

## F. The full 50

All 50 remain `MANIFEST_METADATA_WRONG`, unapplied, with their evidence:

| | n |
| --- | --- |
| refused as the Echo, naming itself (Defect 1) | 49 |
| refused, a genuine vintage mismatch | 1 |
| accepted | 0 |

`CORRECTED_AND_ACCEPTED` / `CORRECTED_BUT_REJECTED` cannot be reported:
nothing was corrected.

---

## G. Effect on the Phase 2.1 store

Defect 1 means the store's second-wine acceptances are unsafe:

| | n |
| --- | --- |
| second-wine contexts | 8,272 |
| ACCEPTED | 5,291 |
| ...of documents the manifest files as the grand vin's or no wine | **4,416**, at 94 estates |

At Lynch-Bages, where the truth is checkable, 107 of 115 such
acceptances are grand-vin sheets wrongly accepted. The store is
append-only, so these rows stay; a corrected decider version will
append the right verdicts beside them. **Until then, no `target_role:
second` ACCEPTED verdict should be used to justify a correction.**

---

## H. Tests

`tools/test-phase22.py`, 13 checks. Two jobs:

**Make the wrong fix impossible to apply quietly.** It asserts the
Echo is defined exactly once in `BDX_CUVEE_WINES`, as the second wine,
with its slug; that the Blanc is still a separate wine; that
`chateaux.js` names the Echo as second; that the loader's merge is
still there; that the 13 Echo records are untouched; that an Echo
sheet is still refused as the *grand vin*; and that the 1989/1990
vintage guard holds.

**Name the defects without failing on them.** Four `KNOWN` lines: the
mark collision, `blanc` being discarded, the Echo refused as the Echo,
and a grand-vin sheet accepted as the Echo. They do not fail the suite
because they are the documented current state; when either defect is
fixed its line flips to `fixed` and should become a real assertion.

All suites pass: reader 53, data 8, phase2 30, phase21 27, phase22 13.

---

## I. Out of scope, and untouched

- the 99 estate-attribution proposals
- the 6 estates with a wine spelled twice
- the 10 estates with a `mark_of` collision
- the 518 reviews and 360 insufficient-evidence cases
- general manifest cleanup and the 174 duplicate rows
- scraper behaviour
- any canonical file

---

## J. Files

Created, none canonical: `tools/diagnose-second-mode.py`,
`tools/echo-baseline.py`, `tools/test-phase22.py`,
`data/echo-baseline.jsonl`, this document.

**Not modified:** `data/sources.json`, `fiches.js`, `cuvees.js`,
`field-src.js`, `cuvee-src.js` — verified by `git diff`, which
`test-phase22.py` runs itself.

---

## K. The decision this needs

The correct fix is in the reader, and it is not narrow:

1. **A real second-wine mode** in `whose_sheet`: the second wine out of
   the competing set, *and* a positive requirement that the document
   identifies itself as the second wine. Measured: false acceptances
   at Lynch-Bages fall from 107 to 1.
2. **`mark_of` must not discard a colour word** when it is the only
   thing distinguishing a wine from its sibling — "Blanc de
   Lynch-Bages" should mark as `blanc de lynch bages` or similar, not
   `de lynch bages`.

Both change reader behaviour for every estate, not only Lynch-Bages.
That is not an exception for one estate — it is the reader becoming
correct — but it conflicts with this phase's constraints ("not a
reader-wide change", "do not generalise to the other estates"), so it
is your call rather than mine. The order, once agreed:

1. fix both defects together, behind `tools/test-reader.py` plus new
   cases for the 10 colliding estates;
2. re-run `tools/diagnose-second-mode.py` and confirm: Echo sheets
   accepted, grand-vin sheets refused, Blanc sheets refused;
3. re-run the contextual pass as decider version 3, so the 4,416
   unsafe acceptances are superseded rather than rewritten;
4. only then apply the 50 manifest corrections and check that 2008,
   2009, 2010, 2015 and 2016 gain Echo records.
