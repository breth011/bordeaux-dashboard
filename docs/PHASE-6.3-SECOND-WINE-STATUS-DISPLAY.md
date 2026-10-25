# Phase 6.3 — Second-wine status display

Gate: **SAFE — PHASE 6.3 SECOND-WINE STATUS DISPLAY IMPLEMENTED**

The estate drawer's second-wine fact now shows the state the normalized model records, instead of
the estate file's raw string. This is display only:

- no model, canonical, evidence or discovery data changed;
- no conflict or identity was resolved;
- the Phase 6.2 audit (`docs/PHASE-6.2-SECOND-WINE-AUDIT.md`) is unchanged and authoritative.

## 1. The data contract

**What the model holds.** Phase 4 M4 recorded each estate file's `second` string in the identity map
(namespace `second-by-name`):

- **ACTIVE:** it names one wine of the estate;
- **RETIRED with a RankAbsence:** the dataset's "—";
- **AMBIGUOUS:** with candidate wines.

M4 also wrote findings: CONFLICT where "—" meets a listed second wine, IDENTITY_UNCERTAIN, and
AMBIGUOUS_SEMANTICS where the string is a note, not a name.

**What the generated data lacked.** `model_reader.project` carried the string only. One generated file
is added to expose that state; nothing else changes:

**`data/app/second-status.js`** (5.5 KB), `BDX_SECOND_STATUS`, written by `tools/build-app-data.py`
`second_status()` from the model's records:

| Model records | State | Estates |
|---|---|---:|
| `second-by-name` ACTIVE | `resolved` | 86 |
| RETIRED, RankAbsence, no CONFLICT finding | `none` | 32 |
| RETIRED, RankAbsence, and a CONFLICT finding on the estate's second-wine claim | `conflict`, with the wines `cuvees.js` claims as SECOND | 2 |
| AMBIGUOUS, and an AMBIGUOUS_SEMANTICS finding that the string is not a plain name | `note`, with the text verbatim | 4 |
| any other AMBIGUOUS | `unestablished`, with the recorded name and the identity map's candidate wines | 13 |

The 24 existing generated files are byte-identical. There is no list of estates anywhere: the state
follows from the model's records, and a test checks that `secondFact` names no estate.

## 2. The presentation

`assets/app.js` `secondFact` renders the state in the fact grid:

| State | Label | Shown |
|---|---|---|
| resolved | Second wine | the name, exactly as before (e.g. *Carruades de Lafite*) |
| none | Second wine | **No second wine recorded** |
| conflict | Second wine | **Conflicting records**, then "one record lists none; the wine list names *Lions de Batailley*" |
| unestablished | Second wine | **Not established**, then "recorded as *La Parde de Haut-Bailly*; the wine list names *Haut-Bailly II*" (the list part only where the model has candidates) |
| note | **Recorded note** | the text verbatim, e.g. *Y d'Yquem (a dry white, not a second wine)* |

- **Style:** the explanation sits on a second, muted line, using the existing `.sitenote` class.
  There is no CSS change and no redesign.
- **Language:** Dutch entries are added to `assets/i18n.js` for the fixed words. The names stay as
  recorded.
- **Wiring:** `index.html` and the service worker load the file, with cache
  `bordeaux-classified-v171`.
- **Search:** it still reads the estate file's string, so search results are unchanged.

Nothing is decided by the display:

- **Batailley and Lynch-Moussas** show a conflict, not a winner.
- **Haut-Bailly** shows La Parde as recorded and not established; no rename is implied.
- **Pichon Baron** shows *Les Tourelles de Longueville* as recorded and *Les Griffons* as listed, with
  no choice between them.
- **Rauzan-Gassies, Croizet-Bages, Belair-Monange and Pouget** show "No second wine recorded", which is
  what the model holds. Their contrary website evidence is not in the model and is not shown.

## 3. Phase 6.1 provenance

It is untouched. The second-wine fact carries no source link, because the model's second-wine claims
are LEGACY_UNSOURCED. `test-phase61` passes (10/10).

## 4. Tests

**`tools/test-phase63.py`**, 11 checks:

| Check | What it holds |
|---|---|
| generated state is the model's | the file equals `second_status()`; 86/32/13/4/2; every state traced to its identity-map entry, RankAbsence and candidates |
| no hard-coded estates | `secondFact` contains no estate id |
| resolved | Lafite: "Carruades de Lafite", as before |
| "—" → "No second wine recorded" | Saint-Pierre (never crawled), Couhins-Lurton (crawled, nothing said) |
| conflict | Batailley, Lynch-Moussas: "Conflicting records", the listed wine named, not adopted |
| not established | Haut-Bailly, Pichon Baron: the recorded and the listed names, neither presented as the second wine, no rename; Léoville Barton's shared name with no list |
| notes | Yquem, De Carles under "Recorded note", verbatim |
| every state renders its contract | all 137 estates in the live page |
| nothing else on any drawer changed | all 137 drawers, against the application at `c775ea7`: everything but the second-wine row is identical; a resolved row identical too |
| search, lookups, values against Phase 6.2 | the control comparison against `c775ea7`'s application: 0 unexplained, no order change |
| model and protected data | the model and the other generated files unchanged since `c775ea7`; canonical, evidence, discovery, scope and proposals unchanged |

**Comparison tooling.** `tools/app-reference.py` now also records each drawer's text with only the
source marks removed, and with only the second-wine row removed. A changed page is therefore
classified by which named presentation changed:

- "PROVENANCE" (Phase 6.1);
- "SECOND-WINE STATUS" (6.3);
- both.

Anything else stays UNEXPLAINED. The long-lived control was re-captured from `8b13cb0`'s application on
the legacy source, the same baseline as Phase 6.1, with the extra texts.

**Rescoped.** The checks in `test-phase5`, `test-phase61` and `test-phase4`'s M12 that name the
application's later additions now also name `second-status.js` and the 6.3 classes.

## 5. Results

**Equivalence against Phase 6.2** (`c775ea7`'s application, model data):

| Class | Count |
|---|---:|
| IDENTICAL | 10,771 |
| EXPECTED: SECOND-WINE STATUS PRESENTATION | 2 (Yquem, Saint-Pierre: the captured pages with a non-resolved state) |
| EXPECTED: ADDED SECOND-WINE STATUS | 1 |
| UNEXPLAINED | **0** |

Beyond the capture, all 137 drawers were compared: only the second-wine row differs, and only for
the 51 non-resolved states.

**Against the long-lived control:** 10,738 identical, 22 presentation order (the switch), 8 provenance
presentation, 2 provenance and second-wine status presentation, 2 named additions, **0 unexplained**.

**Tests:**

| | Before | After |
|---|---:|---:|
| Suites | 23 | 24 |
| Checks | 676 | 687 |
| Failures | 0 | 0 |

**Browser.** In headless Chrome, screenshots of the drawer were checked for Lafite (resolved),
Saint-Pierre (none), Pichon Baron (not established), Lynch-Moussas (conflict), Yquem, De Carles,
Batailley and Haut-Bailly. The state reads first, the explanation is a muted second line, and
uncertainty is never presented as a name.

**Performance**, as a regression check (temporary output):

| | Phase 6.1 | Phase 6.3 |
|---|---|---|
| cold app ready | 497 / 654 / 631 ms | 688 / 608 ms |
| warm app ready | 122–136 ms | 139 / 148 ms |
| broadest search | 34.3 ms | 34.8 ms |

There is no material regression; cold runs vary by more than these differences.

## 6. Unchanged, and still decisions

These remain as Phase 6.2 left them (S3–S6):

- Batailley's "—" against Lions de Batailley;
- the Haut-Bailly rename;
- Lynch-Moussas;
- the contrary website evidence for Rauzan-Gassies, Croizet-Bages, Belair-Monange and Pouget;
- the 11 differing names;
- Pichon Baron's two possible seconds;
- the shared *La Réserve*.

Each would flow through `second_status()` without a further UI change once decided.
