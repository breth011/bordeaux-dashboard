# Phase 6.2 — Second-wine status & contradiction audit

Audit only, measured at `5ec94ff`. The only file this phase adds is this document. Line references
are to `assets/app.js`. "The harvest" is the Phase 3.3 discovery corpus: `data/discovery/`, with
extracted text in the local store. Its statements are attached to estates here only for reading,
through the Phase 3.3 target list's `canonical_ids`. The model does not hold those attachments.

## 1. Executive summary

The second-wine fact and the wine list come from **two different legacy statements**. Both are
carried faithfully through the model into the application, which shows them side by side and
reconciles neither. The model knows more than the UI shows: it records each estate-file
second-wine string as resolved, ambiguous or "no second wine" (a RankAbsence), with findings where
the two legacy statements disagree. None of that reaches the page.

- **There is no single bug.** There is no "first wine after the grand vin" rule and no stale data
  (`data/app/` is the model, byte for byte). The fact row prints the estate file's string verbatim
  (`if (ch.second) fx.push(['Second wine', ch.second])`, 2948). The wine list prints `cuvees.js`'s
  list (`winesOf` 3712, `wineSwitcher` 3854). Neither consults the other or the model's resolution.
- **Batailley:** two conflicting dataset statements. The estate file says "—" (no second wine), while
  `cuvees.js` lists Lions de Batailley as the second, with vintages 2014–2017 in the model. A
  first-party statement in the harvest calls Lions de Batailley "the Château's second wine" and
  Pauillac de Batailley "the third wine" (3.4 fixture P1). The model holds both dataset claims
  undated, with a CONFLICT finding. Whether "no second wine" was ever true, for example before 2014,
  is not established.
- **Haut-Bailly:** the model leaves *La Parde de Haut-Bailly* against *Haut-Bailly II* unresolved
  (identity map AMBIGUOUS). The estate's own site, in the harvest, states the rename: "2018 La Parde
  de Haut-Bailly, né en 1967, se voit renommer … Haut-Bailly.II" (fixture P11). The model holds
  Haut-Bailly II vintages from 2018 only. The rename is evidenced and dated, but not in the model.
- **The 34 "—" estates:** the model records "no second wine" for each as a DATASET claim with no
  source (RankAbsence, provenance LEGACY_UNSOURCED). The UI prints a bare "—".
  - **2** contradict the dataset's own wine list (Batailley, Lynch-Moussas).
  - **4** are contradicted by first-party material in the harvest that the model does not hold:
    Rauzan-Gassies, Croizet-Bages, Belair-Monange (a second label from 2014) and Pouget.
  - **13** were harvested and say nothing either way.
  - **15** were never harvested.

**Answer: B — partly.** A presentation-only correction is safe for every case:

- show the model's second-wine state (resolved, no second wine as recorded, conflicting, identity
  not established, or a note that is not a name) instead of the raw string;
- never pick a winner.

Resolving the conflicts (Batailley, Lynch-Moussas), applying the Haut-Bailly rename, or accepting the
harvest's contrary evidence each needs a decision. No model change is needed: everything found is
representable (§8).

## 2. Baseline

| | |
|---|---|
| HEAD | `5ec94ff` (Phase 6.1), equal to `origin/main`; working tree clean |
| Application source | `model`: the contract files come from `data/app/` |
| Tests | all 23 suites pass (verified again at the end, §15) |
| Read | PHASE-6.0 audit, PHASE-6.1, PHASE-3.4-DOMAIN-MODEL and its REVIEW, BACKLOG; `docs/phase34-fixtures.json` (P1, P11) |

## 3. Current second-wine representation

| Layer | What holds the second wine |
|---|---|
| Legacy | **two independent statements.** The estate files' `second` string (137 estates: a name, `'—'`, or a name with commentary) and `cuvees.js` `BDX_CUVEE_WINES` (80 estates; each wine has `role` `second` or `other`). |
| Model (Phase 4 M4) | Estate-file strings live in the identity map, namespace `second-by-name`, one entry each: **86 ACTIVE** (45 listed wines, 3 by typography; 41 minted where the estate lists none), **17 AMBIGUOUS** (11 another name than the listed wines, 4 commentary, 2 claimed by two estates), **34 RETIRED** with a RankAbsence SECOND (DATASET, LEGACY_UNSOURCED). `cuvees.js` wines carry a RankAssertion SECOND (163 in all) or UNKNOWN (`other`, 58). Findings: CONFLICT (2), IDENTITY_UNCERTAIN (13), AMBIGUOUS_SEMANTICS (4 strings, plus the two-seconds cases). |
| Generated data | `model_reader.project` rebuilds the legacy shapes: each estate record gets `second` = the identity map's legacy string, verbatim, and `BDX_CUVEE_WINES` comes back as listed. The identity map's status, the RankAbsence and the findings are **not** projected. |
| UI | Fact row "Second wine: <string>" (2948), including `'—'` literally. The "Which wine" list shows the grand vin plus listed wines with `ROLE_LABEL` "second wine" or "another cuvée" (3736). Search matches the string (560). |

**How the UI reads each concept today:**

| Concept | Model | UI |
|---|---|---|
| second wine | a RankAssertion SECOND on a wine | the string, or "second wine" in the list |
| no second wine | a RankAbsence SECOND (claimant DATASET) | "Second wine —" |
| unknown second-wine status | no assertion and no absence | no fact row |
| second-wine name differs from the list | identity map AMBIGUOUS with candidates, plus a finding | both shown as facts |
| another cuvée | RankAssertion UNKNOWN, legacy term `other` | "another cuvée" |
| third wine | representable (THIRD, fixture P1); 0 in the model | none |
| prestige or superior wine | representable as a wine with no rank, plus a descriptor; 0 descriptors | Haut-Carles shown as "Second wine" |

**Conflations in the UI:**

1. **"No second wine" against "unknown":** the UI separates them only by "—" against an absent row,
   which a reader cannot tell apart from "not filled in".
2. **A note against a name:** commentary is shown as the second wine's name (Yquem, De Carles).
3. **A disputed name against an established one:** both lists are shown as facts.

## 4. Batailley

| Layer | Evidence |
|---|---|
| Estate file (`chateaux.js`) | `second: '—'` |
| Model, estate | RankAbsence SECOND, claimant DATASET, provenance LEGACY_UNSOURCED, validity UNKNOWN to OPEN; identity map `second-by-name` `batailley\|—` RETIRED |
| Model, wines | grand vin; *Lions de Batailley*, PRODUCED_BY with a RankAssertion SECOND (legacy `second`, `cuvees.js`) |
| Model, vintages | Lions de Batailley: 4 (2014–2017), from the estate's own sheets (e.g. `lionsdebatailley2014-web_fr.ocr.txt`) |
| Model, findings | CONFLICT: "data/chateaux.js says the estate has no second wine ('—'); cuvees.js lists Lions de Batailley as its second" |
| Harvest (first party, batailley.com) | "Lions de Batailley, the Château's second wine; and Pauillac de Batailley, the Château's third wine … made using the youngest vines" (artifact `0aea93df…`, fixture P1). 35 further "second wine" or "second vin" statements on the site, some naming *Les Lions de Batailley*. |
| Generated data | estate `second: "—"`; `BDX_CUVEE_WINES.batailley` = Lions de Batailley (second) |
| UI | "Second wine —", and "Which wine": *Lions de Batailley — second wine · 4 vintages on file* |

**Conclusion.** Lions de Batailley is a separate wine of Batailley, and the current first-party
statement calls it the second wine. The "—" is a dataset statement with no source, contradicted by
the dataset's own wine list and by the estate.

Two things are **not established**: whether "—" was true for some earlier period (the model holds
Lions vintages from 2014 only, and neither claim is dated), and the third wine, *Pauillac de
Batailley*, which is absent from the model.

Classification: **CONFLICTING_STATEMENTS**. The UI presents both as facts.

## 5. Haut-Bailly

| Layer | Evidence |
|---|---|
| Estate file (`graves.js`) | `second: 'La Parde de Haut-Bailly'` |
| Model | identity map `haut-bailly\|La Parde de Haut-Bailly` AMBIGUOUS, candidate *Haut-Bailly II*; finding IDENTITY_UNCERTAIN; no wine minted for La Parde |
| Model, wines | *Haut-Bailly II*, a RankAssertion SECOND (`cuvees.js`); vintages 2018–2025 (7) |
| Harvest (first party, haut-bailly.com) | "2018 La Parde de Haut-Bailly, né en 1967, se voit renommer après 50 années d'existence. Modèle de second vin, le nom s'est imposé spontanément : Haut-Bailly.II." (artifact `0227ded4…`, fixture P11). 53 further second-wine statements on the site. |
| Generated data | estate `second: "La Parde de Haut-Bailly"`; wine list *Haut-Bailly II* (second) |
| UI | "Second wine: La Parde de Haut-Bailly", and "Which wine": *Haut-Bailly II — second wine* |

**Conclusion.** One wine, renamed, is what the estate states: the name changed with the 2018
vintage, and the wine began in 1967. The model's own vintage data fits this (Haut-Bailly II from
2018). It is a rename, not a succession of two wines ("se voit renommer").

The **model does not hold it.** The identity stays AMBIGUOUS, and applying the rename means
recording the first-party statement as NameRecords (FORMER La Parde to vintage 2017, CURRENT
Haut-Bailly II from 2018), which fixture P11 shows is representable. That is the same kind of
step as D2 (Echo) and D8 (the Graves whites): applying first-party identity evidence, which needs a
decision.

Classification: **IDENTITY_UNRESOLVED** in the model, with a dated rename **evidenced** in the
harvest.

## 6. The 34 "no second wine" estates

For every one:

- **Model:** RankAbsence SECOND, claimant DATASET, LEGACY_UNSOURCED, undated.
- **Generated data:** `second: "—"`.
- **UI:** "Second wine —".
- **Estate statement:** none of the 34 has an estate statement of "no second wine" in the model.

| Estate | Wine list (model) | Harvest (read here, not in the model) | Classification |
|---|---|---|---|
| Batailley | Lions de Batailley, SECOND (2014–2017) | "the Château's second wine" (P1) | CONFLICTING_STATEMENTS |
| Lynch-Moussas | Les Hauts de Lynch-Moussas, SECOND | "second wine … Les Hauts de Lynch-Moussas" | CONFLICTING_STATEMENTS |
| Rauzan-Gassies | — | group site domaines-quie.com, under Château Rauzan-Gassies' production: "Second vin – Gassies", "L'Orme de Rauzan-Gassies" | CONFLICTING_STATEMENTS (harvest) |
| Croizet-Bages | — | "Alias Croizet-Bages, Second vin de Château Croizet-Bages Pauillac" (FR, EN, CN) | CONFLICTING_STATEMENTS (harvest) |
| Belair-Monange | — | press quoted on its own site: 2014 "the first official vintage where the grand vin was joined by second label Annonce de Bélair-Monange" | CONFLICTING_STATEMENTS (harvest), temporal |
| Pouget | — | its own site has a section "The second wines" / "Les seconds vins"; no name in context | CONFLICTING_STATEMENTS (harvest, weak) |
| Doisy-Daëne | — | shared site denisdubourdieu.com; the statements concern Clos Floridène | UNKNOWN |
| Doisy-Dubroca | — | same site, same statements | UNKNOWN |
| La Mondotte | — | shared site neipperg.com; the statements concern Château d'Aiguilhe | UNKNOWN |
| Couhins-Lurton | — | harvested (373 documents), silent | UNKNOWN |
| Couhins | — | harvested (120), silent | UNKNOWN |
| d'Armailhac | — | harvested (199), silent | UNKNOWN |
| de Myrat | — | harvested (120; 24 refused by robots), silent | UNKNOWN |
| Filhot | — | harvested (24), silent | UNKNOWN |
| Lamothe-Guignard | — | harvested (113), silent | UNKNOWN |
| Lamothe | — | harvested (32), silent | UNKNOWN |
| Marquis d'Alesme | — | harvested (120), silent | UNKNOWN |
| Romer du Hayot | — | harvested (51), silent | UNKNOWN |
| Rabaud-Promis | — | 3 documents, 18 HTTP errors | UNKNOWN |
| Saint-Pierre | — | not harvested (timeouts) | UNKNOWN |
| Suau | — | not harvested (site-wide robots refusal) | UNKNOWN |
| Romer | — | no known site | UNKNOWN |
| Pétrus | — | not a harvest target (editorial Pomerol) | UNKNOWN |
| Le Pin | — | not a target | UNKNOWN |
| Trotanoy | — | not a target | UNKNOWN |
| Hosanna | — | not a target | UNKNOWN |
| La Fleur-Pétrus | — | not a target | UNKNOWN |
| Certan de May | — | not a target | UNKNOWN |
| Clos l'Église | — | not a target | UNKNOWN |
| La Violette | — | not a target | UNKNOWN |
| Providence | — | not a target | UNKNOWN |
| Latour à Pomerol | — | not a target | UNKNOWN |
| Laville Haut-Brion | — | not a target | UNKNOWN |
| La Tour Haut-Brion | — | not a target | UNKNOWN |

"UNKNOWN" means: the model's only statement is the unsourced dataset claim of "no second wine", and
nothing in the repository confirms or contradicts it. Silence from a harvested site is not
confirmation; absence of a mention is not a statement of absence.

## 7. Application and code-path analysis

| Candidate cause | Found? | Evidence |
|---|---|---|
| first wine after the grand vin taken as the second | no | `winesOf` lists the listed wines with their own roles (3712-3719) |
| missing second rendered as "—" | no; the "—" is the data's own value | `'—'` is the estate file's string, carried verbatim (`model_reader.project`, `second-by-name` key) and printed by 2948 because the string is truthy |
| the legacy field overriding the normalized relationships | **yes, by construction** | the fact row reads the projected legacy string; the model's resolution (ACTIVE / AMBIGUOUS / RankAbsence) and its findings are not projected into `data/app/` |
| an estate-level field preferred over wine relationships | **yes** | two independent displays: the estate fact (2948) and the wine list (3854); neither consults the other |
| a display-name lookup instead of stable identity | no in the UI; yes in the data | the UI never resolves the string to a wine. In the model, the M4 resolution compares names (exactly or by typography), which is why 11 differing names stay AMBIGUOUS rather than being guessed |
| stale generated data | no | `tools/build-app-data.py --check`: `data/app/` is the model, byte for byte |
| an assumption inherited from the pre-normalized model | **yes** | the projection's goal was equality with the legacy files (Phase 4 M8/M9), so it reproduces two unreconciled legacy statements exactly |

**The boundary responsible:** the generated application data carries the legacy *string*, not the
model's second-wine *state*. Everything the model learned in M4 (resolution, absence, conflict, note
against name) stops at `tools/model_reader.project`.

## 8. Model sufficiency

| Case | Representable? | How (contract) |
|---|---|---|
| a second wine with a former name | yes | NameRecord FORMER and CURRENT with Validity (fixture P11) |
| a second wine renamed over time | yes | the same, dated on the VINTAGE axis |
| two sources naming one wine differently | yes | several NameRecords (SOURCE_RENDERING, MARKET_ALIAS) on one Wine |
| two different wines both claimed as second | yes | two RankAssertions SECOND, possibly TYPE_RANGE; the quality audit flags overlaps |
| explicit "no second wine" | yes | RankAbsence (with a vintage scope where stated, e.g. Corbin 2022) |
| no information about second-wine status | yes | no assertion and no absence |
| a third wine | yes | RankAssertion THIRD (fixture P1) |
| a wine with no rank | yes | RankAssertion UNRANKED, or none |
| conflicting rank claims from different sources | yes | several RankAssertions with different claimants and provenance |

**No D0.** Every case found is representable. What is missing is data (the first-party statements are
unattached) and presentation (the state is not projected).

## 9. Historical and name-change analysis

- **Haut-Bailly:** a dated rename, evidenced first-party (1967 start; renamed with the 2018 vintage).
  The model's vintage data is consistent: Haut-Bailly II holds 2018–2025, and La Parde holds no
  vintages under its own name. The rename is not in the model.
- **Batailley and Belair-Monange:** "no second wine" may have been true earlier. Belair-Monange's
  second label is dated by press quoted on the estate's site (from 2014); Lions de Batailley appears
  in the model from 2014. Neither the "—" claims nor the wines' start dates are recorded in the
  model, so a historical "no second wine until 2013" **cannot be established** and is not asserted.
- **The 11 other differing names** stay unresolved; each is rename, succession or another wine, not
  decided. Ducru (La Croix Ducru-Beaucaillou / La Croix de Beaucaillou), Haut-Bages Libéral (La
  Chapelle de Bages / La Chapelle de Haut-Bages Libéral), Malartic (Le Sillage / Le Comte), Olivier
  (La Seigneurie / Le Dauphin) and Doisy-Védrines (Petit Védrines / Chevalier de Védrines) may be
  renames, but no dated statement is in the model. **Pichon Baron:** the harvest names *Les Tourelles
  de Longueville* among "second wines" (plural) while the list has *Les Griffons* as second. That may
  be two seconds at once, not a rename.

## 10. Case matrix

For the 34 "—" estates, see §6. Every other estate-file string that is not a resolved name:

| Estate | Model state | Wine list state | UI state | Provenance | Classification |
|---|---|---|---|---|---|
| Batailley | RankAbsence + SECOND on Lions; CONFLICT | Lions de Batailley, second | "Second wine —" + "Lions de Batailley — second wine" | both DATASET; P1 first party | CONFLICTING_STATEMENTS |
| Lynch-Moussas | RankAbsence + SECOND; CONFLICT | Les Hauts de Lynch-Moussas, second | "—" + the list | DATASET; harvest | CONFLICTING_STATEMENTS |
| Haut-Bailly | AMBIGUOUS → Haut-Bailly II | Haut-Bailly II, second (2018–) | "La Parde de Haut-Bailly" + "Haut-Bailly II" | DATASET; P11 first party | IDENTITY_UNRESOLVED (rename evidenced) |
| Cos d'Estournel | AMBIGUOUS → Pagodes de Cos | Pagodes de Cos, second (2000–2025) | "Les Pagodes de Cos" + "Pagodes de Cos" | DATASET | IDENTITY_UNRESOLVED |
| Ducru-Beaucaillou | AMBIGUOUS → La Croix de Beaucaillou | La Croix de Beaucaillou, second (2011–2024) | "La Croix Ducru-Beaucaillou" + list | DATASET | IDENTITY_UNRESOLVED |
| Haut-Bages Libéral | AMBIGUOUS → La Chapelle de Haut-Bages Libéral | that, second | "La Chapelle de Bages" + list | DATASET | IDENTITY_UNRESOLVED |
| Kirwan | AMBIGUOUS → Les Charmes de Kirwan | Les Charmes de Kirwan, second | "Charmes de Kirwan" + list | DATASET | IDENTITY_UNRESOLVED |
| Malartic-Lagravière | AMBIGUOUS → Le Comte de Malartic | Le Comte de Malartic, second (2019–) | "Le Sillage de Malartic" + list | DATASET | IDENTITY_UNRESOLVED |
| Olivier | AMBIGUOUS → Le Dauphin d'Olivier (red, white) | two seconds (red, white) | "La Seigneurie d'Olivier" + list | DATASET | IDENTITY_UNRESOLVED |
| Pichon Baron | AMBIGUOUS → Les Griffons | Les Griffons, second | "Les Tourelles de Longueville" + list | DATASET; harvest names Tourelles a second wine | CONFLICTING_STATEMENTS |
| Doisy-Védrines | AMBIGUOUS → Chevalier de Védrines | Chevalier de Védrines, second | "Petit Védrines" + list | DATASET; harvest "Second vin … Petit Védrines" | CONFLICTING_STATEMENTS |
| La Fleur de Boüard | AMBIGUOUS → Le Plus de La Fleur de Bouärd | that, **other** | "Le Plus de La Fleur de Boüard" under "Second wine" + list "another cuvée" | DATASET | CONFLICTING_STATEMENTS |
| Marquis de Terme | AMBIGUOUS → the 2 `other` wines | Cuvée 1762, Empreinte (other) | "Les Gondats de Marquis de Terme" + list | DATASET | UNKNOWN |
| Léoville Barton, Langoa Barton | AMBIGUOUS (one name, two estates) | — | both "La Réserve de Léoville-Barton" | DATASET | IDENTITY_UNRESOLVED |
| Yquem | AMBIGUOUS_SEMANTICS | Y d'Yquem, other | "Second wine: Y d'Yquem (a dry white, not a second wine)" | DATASET | PRESENTATION_BUG (label contradicts value) |
| De Carles | AMBIGUOUS_SEMANTICS | — | "Second wine: Haut-Carles (prestige cuvée)" | DATASET | PRESENTATION_BUG (a prestige cuvée shown as the second wine) |
| Léoville Las Cases | AMBIGUOUS_SEMANTICS | — | "Second wine: Le Petit Lion (Clos du Marquis is a separate cuvée)" | DATASET | PRESENTATION_BUG (a note in the name) |
| Léoville Poyferré | AMBIGUOUS_SEMANTICS → Pavillon de Poyferré | Pavillon de Poyferré, second; Moulin Riche, other | "Pavillon de Poyferré (also Château Moulin Riche)" + list | DATASET | PRESENTATION_BUG |

The 86 resolved strings (45 matching a listed wine, 41 the only wine named) display a name that the
model resolves to one wine: **CORRECT_PRESENTATION**. They could link to that wine, but are correct
as they stand.

## 11. Severity classification

| Id | Severity | Finding |
|---|---|---|
| S1 | **P1** | The second-wine fact prints the legacy string, not the model's state: "—" for 34 recorded absences, conflicts shown as two facts (Batailley, Lynch-Moussas, Pichon Baron, Doisy-Védrines, La Fleur de Boüard), and names whose identity the model leaves open shown as established (11). |
| S2 | **P1** | Notes shown as second-wine names under the label "Second wine": Yquem's "not a second wine", De Carles' "prestige cuvée", Las Cases, Poyferré. |
| S3 | **Q0** | The dataset's "—" is unsourced and contradicted for 6 of the 34: 2 by the dataset's own wine list, 4 by first-party harvest material the model does not hold. |
| S4 | **D1** | Applying first-party identity evidence: Haut-Bailly's dated rename (P11), Batailley's second and third wines (P1). The same kind of decision as D2 and D8. |
| S5 | **D1** | Accepting harvest statements into the model at all (attribution to model estates, conflict policy D5). |
| S6 | **R0** | 28 "—" estates whose status is UNKNOWN (13 harvested and silent, 15 not harvested); the 11 differing names' history; Pichon Baron's two seconds. |
| S7 | **F0** | Third wines (Pauillac de Batailley) and prestige descriptors are absent from the data. Representable, not needed for correctness now. |

No **P0** and no **D0**.

## 12. Safe implementation boundary

**Can the current second-wine UI be corrected safely, using the normalized model, without a domain
decision? B — partly.**

**Safe, presentation only.** Carry the model's second-wine state into the generated data, beside the
legacy string, and show that state:

| Model state | Estates | Show |
|---|---:|---|
| `second-by-name` ACTIVE, no finding | 86 | the name, as now |
| RankAbsence, no other record | 32 | "No second wine recorded" (the dataset's claim, unsourced) instead of "—" |
| RankAbsence + a CONFLICT finding | 2 (Batailley, Lynch-Moussas) | both statements, said to disagree: the record says none; the wine list names X as second |
| AMBIGUOUS with candidates (IDENTITY_UNCERTAIN) | 13 | the recorded name, marked as not established, with the listed wine(s) named |
| AMBIGUOUS_SEMANTICS (a note, not a name) | 4 | the text under a neutral label, not "Second wine" |

The rule, exactly: the fact row is derived from the identity map's `second-by-name` entry for the
estate (status, candidates), the estate's RankAbsence, and the findings targeting the estate's
second-wine claims, projected by `tools/build-app-data.py`. It is never derived from the wine list
alone, and never resolved toward either statement.

**Not safe without a decision** (each stays as it is under the rule above):

- choosing Lions de Batailley over "—", or the reverse (S3/S4);
- recording Haut-Bailly's rename (S4);
- using the harvest's contrary statements for Rauzan-Gassies, Croizet-Bages, Belair-Monange and
  Pouget (S5);
- deciding any of the 11 differing names, Pichon Baron's two seconds, or the shared *La Réserve*
  (S6).

## 13. Recommended next step

**Phase 6.3, presentation only:** the rule in §12, with the same pattern as Phase 6.1.

- An additive generated global carries each estate's second-wine state from the model.
- The fact row renders it.
- A test holds every one of the 137 states to the model.
- The control comparison shows "EXPECTED: …" for the changed rows only, and no value changes.

Decisions S4 and S5 can follow independently, as data decisions. Each would then flow through the
same rule without a further UI change.

## 14. Explicitly deferred

- Resolving any conflict or identity: Batailley, Lynch-Moussas, Haut-Bailly, the 11 names, *La
  Réserve*, Pichon Baron.
- Attaching or accepting harvest evidence (the 4 contrary "—" cases).
- Historical "no second wine until …" claims.
- Third wines and prestige descriptors.
- Linking resolved second-wine names to their wine in the drawer: an enhancement (P2).
- All other Phase 6.0 findings: wine colour, the unknown-rank label, search, language, history.

## 15. Phase 6.2 gate

- No canonical data, evidence, discovery data, normalized model, generated application data, raw
  source or application code was changed. The only new file is this document; the diagnostic script
  stayed in the session's scratch space and is not committed.
- All 23 existing suites pass after the audit.
- The protected hashes and the model hashes are unchanged; the pinned anomaly hashes are unchanged
  (test-phase5).
- The answer is **B**. The safe subset is defined exactly (§12), and every decision-dependent case is
  named.

**SAFE — PHASE 6.2 SECOND-WINE AUDIT COMPLETE — READY FOR IMPLEMENTATION**
(of the presentation-only subset in §12; the conflicts and identities remain decisions, S4–S6)
