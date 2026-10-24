# Phase 2.10 — V5 evidence

**Gate: `SAFE — V5 EVIDENCE COMPLETE`**

V5 confirms the Phase 2.9 dry run decision for decision:

- **87** grand-vin acceptances withdrawn, exactly the 87 predicted, with
  identical new verdicts;
- **0** genuine grand-vin acceptances withdrawn;
- **0** second-wine changes.

v1–v4 are byte-for-byte unchanged. No canonical data changed.

---

## 1. Run identity

| | |
| --- | --- |
| starting commit | `6e4effb` (Phase 2.9), clean |
| commit that ran v5 | `fb125c85bd795f59a242151e5b5717eef7704d91`: `DECIDER_VERSION` 4 → 5 in `evidence-wines.py` and `recharacterize.py`, nothing else |
| reader fingerprint | `7e8cfed1c24e`, on every v5 row |
| state | clean: every row `git.dirty: false`, `status_hash: null`; no `--allow-dirty` |
| run | `evidence-wines.py --write` (2026-10-24 23:47–23:56), then `recharacterize.py --write` (to 23:56) |
| store preflight | on a temporary store: seven malformed v5 rows refused (no read, short hash, legacy `commit`/`observed`, no git, dirty without hash, a failure as a decision); a minimal valid v5 row accepted |

## 2. V5 totals

| | |
| --- | ---: |
| decisions | **40,772** (39,510 + 1,262), one file `decisions-v5.jsonl`, 39.3 MB |
| distinct decision identities | 40,772: no duplicates |
| grand vin | 14,134 |
| second wine | 8,189 |
| other cuvée | 18,449 (all `GUARD_HAS_NO_CUVEE_MODE`; no reader mode, none evaluated) |
| with a target vintage / without | 39,864 / 908 |
| attributed / unattributed | 39,510 / 1,262 |
| provenance failures | **123** (103 `ARTIFACT_NOT_FOUND`, 20 `ARTIFACT_NAME_MISMATCH`), the same artifacts as v4, in `provenance-failures-v5.jsonl` |
| store after v5 | 177,127 decisions: v1 13,065 · v2 41,259 · v3 41,259 · v4 40,772 · v5 40,772 |

## 3. V4 → V5 reconciliation

`tools/compare-v4.py`'s successor, `tools/compare-v5.py --write`,
writes `data/v4-v5-comparison.json`.

| | n |
| --- | ---: |
| same questions | **40,772** |
| questions only in v4 | 0 |
| questions only in v5 | 0 |
| `UNCHANGED` | 40,685 |
| `ACCEPTED_TO_REFUSED` | **87** |
| `REFUSED_TO_ACCEPTED`, `ACCEPTED_TO_UNRESOLVED`, `UNRESOLVED_TO_*`, other | 0 |
| reason-only changes | 0 |
| same verdict, different file or hash read | 0 |

v4 and v5 differ in the reader only, and every change is a verdict
change on a grand-vin question.

## 4. Grand-vin impact

| | v4 | v5 |
| --- | ---: | ---: |
| accepted | 9,467 | **9,380** |
| accepted → refused | | 87 |
| refused → accepted | | **0** |

**Against the Phase 2.9 prediction** (`data/phase29-grand-dryrun.json`):

- predicted 87, observed 87;
- identical keys and identical new verdicts: **87**;
- unpredicted: **0**;
- missed: **0**.

So V5 differs from the dry run in nothing. The dry run's
document-lookup, vintage-selection and universe were the evidence
writer's own.

**The 87, by estate:**

| estate | the wine the refusal names | withdrawn |
| --- | --- | ---: |
| Bellefont-Belcier | Les Tours de Belcier | 32 |
| Smith Haut Lafitte | Les Hauts de Smith | 15 |
| Guiraud | Le G de Château Guiraud (Blanc) | 12 |
| du Tertre | Les Hauts du Tertre | 9 |
| Smith Haut Lafitte | Le Petit Haut Lafitte | 8 |
| Laroque | Les Tours de Laroque | 7 |
| Beaumont | Les Tours de Beaumont | 2 |
| Ducru-Beaucaillou | La Croix de Beaucaillou | 2 |

Each one, with its old (empty, accepted) and new reason, is in
`data/v4-v5-comparison.json` under `grand_withdrawals`.

**Why the rule withdrew them.** Each document names, in its filename
or title, another listed wine whose only distinguishing words are
COMMON words or a single letter. The new grand-vin mark keeps those
words (Phase 2.9 §3), so `names_another_wine` now finds the wine.
Phase 2.9 §7 established by reading each document:

- all 87 are other wines' documents: 70 of Phase 2.8's 77, Smith Haut
  Lafitte's `HDS`/`PHL` sheets, a "Haut-du-Tertre" sheet;
- or restaurant menus.

The Guiraud refusals name "Le G de Château Guiraud Blanc". Both G wines
share the mark `g de guiraud`, and the grand-vin loop reports the first
it meets.

## 5. Second-wine impact

| | n |
| --- | ---: |
| same questions | 8,189 |
| unchanged | **8,189** |
| accepted (v4 / v5) | 1,115 / 1,115 |
| any change | **0** |

The Phase 2.9 rule did not touch second-wine behaviour, as predicted.

**Other cuvées:** 18,449 contexts, none evaluated (no reader mode). The
69 other-cuvée false grand-vin acceptances of Phase 2.8 appear in V5
only through their **grand-vin** questions. **63** of the 87 withdrawals
are such documents:

- Les Tours de Belcier: 32
- Le G de Guiraud: 12
- Le Petit Haut Lafitte: 8
- Les Tours de Laroque: 7
- Les Tours de Beaumont: 2
- La Croix de Beaucaillou: 2

That gives no other-cuvée verdict; those questions remain unevaluated.

## 6. Echo

From the V5 evidence, labelled by word containment as
`diagnose-second-mode.py` does:

| document | distinct | accepted for some vintage |
| --- | ---: | ---: |
| Echo | 64 | **64** |
| grand vin | 103 | **0** |
| Blanc | 52 | **0** |

**Echo contexts:** 75. 64 are accepted and 11 are `WRONG_VINTAGE`, an
Echo sheet of one year asked about another. None is refused for another
reason. This is identical to v4.

| vintage | v5 Echo documents accepted | manifest changed |
| --- | --- | --- |
| 2008 | Echo-de-Lynch-Bages-2008-EN, -CN | NO |
| 2009 | Echo-de-Lynch-Bages-2009-EN, -CN, -FR | NO |
| 2010 | Echo-de-Lynch-Bages-2010-EN, -CN, -FR | NO |
| 2015 | Echo-de-Lynch-Bages-2015-EN, -CN, -FR | NO |
| 2016 | Echo-de-Lynch-Bages-2016-EN, -CN, -FR, Echo-Lynch-Bages-2016-FT-FR-C0888 | NO |

## 7. Conflict measurement

Documents accepted for more than one target:

| relation | v4 | v5 |
| --- | ---: | ---: |
| documents | 312 | **303** |
| SEVERAL_VINTAGES | 303 | 302 |
| **GRAND_AND_SECOND** | **8** | **0** |
| GRAND_AND_OTHER | 0 | 0 (other cuvées are never accepted: no mode) |
| SEVERAL_ESTATES | 1 | 1 |

- **New conflicts in v5: 0. Gone: 9.**
- **The 8 Les Hauts du Tertre conflicts are all gone.** Their grand-vin
  acceptance was withdrawn; the second-wine acceptance stands.
  `test-phase29.py` also checks the reader on `Hauts-du-Tertre-2017-FT-FR`
  directly: refused as the grand vin, accepted as the second wine.
- The ninth was a multi-vintage document whose grand-vin acceptance was
  withdrawn.

## 8. Edge cases

- **Guiraud G.** Every `G-de-Guiraud-…` and `G-DE-GUIRAUD-…` sheet is
  now refused as the grand vin, 12 of them. The `G-de-Chateau-Guiraud`
  sheets were already refused. **`G-Guiraud-2015-FT-FR-C0789` still
  passes:** a filename without "de", the documented filename-form limit,
  not fixed here.
- **Smith Haut Lafitte.**
  - Withdrawn, as the dry run predicted: the 2017, 2018, 2020 and 2021
    `HDS-ROUGE` and the 2017–2018 `PHL-ROUGE` sheets.
  - Still accepted, also as predicted: `2019-HDS-Rouge-FR`,
    `2019-PHL-Rouge-FR/-GB`, `2020-PHL-ROUGE-…`. Those titles name the
    wine in a form the list does not hold ("Le Petit Smith Haut
    Lafitte"), the alias limit of Phase 2.9 §7.
  - The `-BLANC` files stay `WRONG_COLOUR`.
- **White-wine regressions** of Phase 2.9's draft:
  - Fieuzal Blanc 2022 (`de-fieuzal-2022-656504d6`, `-7c05e34a`) stays
    `WRONG_WINE`;
  - "DOMAINE DE CHEVALIER BLANC PRIMEUR 2014" (`…-2014-FT-FR-363`,
    `-GB-363`) stays `WRONG_WINE`.

  The red sheets beside them stay accepted.
- **Sister-estate and non-wine documents:**
  - Bellefont-Belcier's copies of `LES-TERRASSES-DE-SAINT-CHRISTOPHE`
    are refused exactly as in v4: 12 `WRONG_WINE`, 4 `TRADE_LISTING`.
  - de Malle's two wedding brochures stay `WRONG_WINE`.
  - The abbreviation logic was not changed.
  - *Observation, unchanged from v4 and unrelated to Phase 2.9:* the
    copies of the Terrasses sheets in Tour Saint-Christophe's own folder
    are unattributed, and 15 of them are accepted as Tour
    Saint-Christophe's grand vin under the folder hypothesis.

## 9. Provenance

| | |
| --- | --- |
| wrong-folder manifest rows (Phase 2.5 audit) | 917 rows = 866 distinct folder/file pairs |
| wrong-bytes rows | 48 rows = 46 distinct pairs |
| v5 decisions on the wrong-bytes files | 278 |
| … `read.sha256` equal to the audit's actual hash | **278 of 278** |
| v5 decisions on the wrong-folder files | 1,747, each read from its own folder |
| missing files | 103 `ARTIFACT_NOT_FOUND` |
| spelling mismatches | 20 `ARTIFACT_NAME_MISMATCH` |
| ambiguous files | 0 |
| changed during read | 0 |

Historical decisions were not rewritten.

## 10. Idempotence

The same two commands were run again from the same commit, with nothing
changed in between:

| | appended | already recorded |
| --- | ---: | ---: |
| `evidence-wines.py --write` | **0** | 40,037 (527 manifest duplicate rows asked twice, each written once) |
| `recharacterize.py --write` | **0** | 1,262 |

The failure file stayed at 123 rows, and `verify()` is clean.

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
| Phase 2.6 | 61 pass |
| Phase 2.7 | 16 pass |
| Phase 2.8 | 17 pass |
| Phase 2.9 | 47 pass |
| **Phase 2.10** | **23 pass** (new) |

**`test-phase210.py` checks:**

- version 5 on every row;
- one reader (`7e8cfed1c24e`) and one full commit, which git confirms
  holds that reader and writes version 5;
- clean rows;
- SHA-256 on every row, and 300 files re-hashed;
- no legacy fields;
- unique identities;
- failures carry no verdict and are v4's artifacts;
- the index agrees and `verify()` is clean;
- v1–v4 parts and v4's failure file are identical to `6e4effb`, by index
  and by `git diff`;
- every same question is classified once, and none is dropped or new;
- the changed verdicts are exactly Phase 2.9's prediction;
- 0 second-wine changes, and no grand-vin refused → accepted;
- canonical files unchanged.

The Phase 2.8 and 2.9 suites compared the *whole* evidence directory
with HEAD, which fails whenever a new version is appended. Their git
check now covers the canonical files and every *committed* evidence
file, as this phase's spec states the invariant. Their before/after
hashing of every file, which proves the tests themselves change
nothing, is unchanged.

## 12. Canonical safety

| | changed? |
| --- | --- |
| `data/fiches.js` | no |
| `data/chateaux.js` | no |
| `data/cuvees.js` | no |
| `data/sources.json`, `field-src.js`, `cuvee-src.js` (source metadata) | no |
| historical evidence (`decisions-v1…v4.jsonl`, `provenance-failures-v4.jsonl`) | no: byte-for-byte identical to `6e4effb` |

Only v5 was added (`decisions-v5.jsonl`, `provenance-failures-v5.jsonl`
and its index entry). No canonical correction was made.

## 13. Gate

**`SAFE — V5 EVIDENCE COMPLETE`**
