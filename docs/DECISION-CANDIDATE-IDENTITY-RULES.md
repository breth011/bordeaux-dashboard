# Decision: candidate identity rules (R1–R4, G1) and the five held claims

Documentation only. Nothing was implemented or wired, and no data changed.

This record decides from evidence already collected:
- the M3.12 rule audit (scratchpad `VERDICT-DIFF.md` / `verdict-diff.jsonl`, 74 distinct claims across six audit layers);
- `tools/identity_rules_candidate.py`;
- [INTEGRATION-CONTRACT.md](INTEGRATION-CONTRACT.md);
- the dry run (`data/audit/integration-dryrun.jsonl`, [PHASE-INTEGRATION-DRYRUN.md](PHASE-INTEGRATION-DRYRUN.md));
- the identity refusal audit (`data/audit/m3.12-identity-refusal-audit.jsonl`);
- the held text of the five held claims, read through M3.4A's own `document_text`.

No new research was done.

**Counting.** "Changed" and "newly accepted" for a rule alone are the rule audit's own figures (each rule switched on by itself, all layers). "Dry run" counts claims of the integration corpus (187 P1 rows and 7 boundary claims) whose candidate identity the rule takes part in.

## 1. The rules, one at a time

### R1 — name form

**Problem.** The text writes the wine's own name with other separators than the model's: a hyphen, space, apostrophe or line break. Examples:
- "Château Calon Ségur 2018" (the model writes Calon-Ségur);
- "le Château-Figeac 2022";
- Grand Mayne's title split over lines ("chateau\ngrand mayne");
- Haut-Brion 2006's name on two lines;
- Brane-Cantenac's "chateau / brane-cantenac".

**Counts.**
- Rule audit: 12 claims changed, 7 newly accepted.
- Dry run: R1 alone settles Grand Mayne 1955 and 2008. It takes part in 17 settled claims: 11 with R2+R3, and 4 with R3 (Calon-Ségur 2018 blend, Figeac 2022 pH, Grand Mayne 1995 and 2009).

**Evidence.** The trace records each rewrite, for example `chateau calon segur` → `chateau calon-segur`, and `chateau-figeac` → `chateau figeac`. In every case the words are the model's name, word for word.

**False-positive protection.**
- Only separators change, never words.
- The rewrite keeps the text's length.
- It never applies inside a web or email address (`www.chateau-latour.com`, `/chateau-corbin/`).
- A model name longer than the text's form is skipped (`R1_SKIPPED_LONGER`), not stretched.
- `decide` then runs unchanged, with all its guards (siblings, colour, vintage).

**Limitations.**
- It does not fix spelling or abbreviation.
- It recovers a name but says nothing about the document type. Brane-Cantenac's score sheets reach SAFE_TO_MAP through R1; the rule is right about the name, and the documents are refused on other grounds (§3).

**Is it safe as a general rule?** Yes. It recovers the same explicit wine identity despite PDF and text normalisation; no inference is added.

**Decision: ADOPT.**

### R1b — the estate's short name

**Problem.** A grand vin whose name is the estate's is written by its core name beside the year: "Issan 2008", "2012 Issan".

**Counts.**
- Rule audit: 3 changed, 2 newly accepted.
- Dry run: R1b with R3 settles Issan 2008: `gs_c20b109c0b1a` alc, `gs_ee18a38f44d1` blend, `gs_dc7cc333faab` pH, `gs_168c78916435` yld.
- R1b also matches Issan 2012 ("2012 issan"), and G1 withdraws it (the sheet says "second wine").

**Guards in the code, verified.**
- **Multiple wines required.** R1b is never tried for an estate the model lists with one wine. The note "one wine decides nothing (M3.9)" keeps all four identity negative controls refused: Biston-Brillette 2021, Biston-Brillette 2023, Jean Faure 2025 and Mangot 2022.
- **Only for the estate-named wine.** It applies only where the wine's name is the estate's (`distinct_name` is empty). A second wine with a name of its own is never reached.
- **Not part of a longer name.** An article or preposition before the core ("d'", "l'", "de ", "du ") skips the match, unless it is "château d'…". So does a sibling's distinctive word within 30 characters before it. "Blason d'Issan 2012" therefore does not count as "Issan 2012".
- **Core name length.** The core name (without château, clos, domaine or articles) must be at least 4 characters.

**Limitation.** R1b only shows that the estate's name stands beside the year. A sheet for another cuvée of the estate can say the same. Issan 2012 is exactly that case, and G1 is what refuses it.

**Is it safe as a general rule?** Yes, but only with its guards and with G1 always applied to the acceptances it creates.

**Decision: ADOPT WITH GUARD.** The guard is the multiple-wines condition, the longer-name skip, and G1.

### R2 — late heading

**Problem.** A document's own title is extracted after the 600-character opening `decide` reads. The Grand Mayne sheets are the clear case: their title block "Château / Grand Mayne / Grand Cru Classé / 1988" is extracted last, at line 49 of 53.

**Counts.**
- Rule audit: 14 changed, 12 newly accepted.
- R2's 15 uses across the audit come in three forms:

| form | uses | claims | outcome |
|---|---:|---|---|
| `NAMED_BLOCK`: up to four short lines (each ≤ 30 characters) that together read wine name, optional classification, year | 12 | Grand Mayne 1988–2007 | 11 safe rescues; 2005 refused by G1 |
| `NAMED`: one line (≤ 60 characters) reading wine name and year | 2 | Caillou 2014; Paloumey 2022 | Caillou refused by G1; Paloumey held |
| `BARE`: "millésime YYYY" alone, allowed only when R4 names the wine | 1 | Chapelle 1998 | held |

**Guards in the code.**
- The heading must be the whole line, or the whole block (`fullmatch`).
- Line lengths are capped.
- A heading of the same wine with another year makes it ambiguous, and nothing is added.
- R2 does nothing when the year already stands in the opening.

**Limitations.**
- **Single-line form.** A one-line "wine year" cannot be told apart from a table cell. Paloumey's "chateau paloumey 2022" sits in a column of labels and values, between "age moyen" and "50 000" (§3).
- **Bare form.** It names no wine at all, so the wine identity rests entirely on R4.
- **Block form.** It is the shape of a genuine title block, and every case of it in the corpus is one.

**Is it safe as a general rule?** Yes for the block form, which recovers a genuine heading that happens to be extracted late. The other two forms do not reliably tell a heading from later text. Narrowing to the block form costs no safe rescue: every single-line and bare use in the corpus is either held or refused.

**Decision: ADOPT NARROWED to `NAMED_BLOCK`.** The single-line and bare forms are not adopted.

### R3 — non-vintage years

**Problem.** Years that are not the vintage make `decide` see a multi-vintage document, or a year other than the claimed one. These include:
- drinking windows ("best after 2007", "2008 à 2012");
- planting dates (Taillan's 1959 and 2016);
- certification dates (HVE 2018; "depuis 2021");
- an earlier season ("hiver 2017");
- comparison vintages (Figeac's bracketed "(2015 / 2018 / 2019 / 2020)");
- dated events ("mise le 19 juin 2017").

**Counts.**
- Rule audit: 17 changed, 2 newly accepted (Taillan 2025 and Figeac 2022). Most of its changes are inside combinations.
- Dry run: R3 takes part in 58 settled claims: 38 with R4, 11 with R1+R2, 4 with R1, 4 with R1b, and 1 alone (Taillan 2025, `gs_b759e729fea7`). It also takes part in the two held claims: Paloumey with R2, and Chapelle with R2+R4.

**Guards in the code.**
- R3 only masks a year (with `####`). It never writes one in, so it cannot create a vintage.
- The comparison, event and earlier-season patterns never mask the claimed year itself.
- The drinking-window range masks only a range wholly after the vintage.

**Limitations.**
- Patterns that mask every year in the match (drinking window, planting, certification) could mask the claimed year itself. That can only refuse a claim, never accept one.
- R3 can make a multi-year compilation look single-year. Corbin's 2003 press review lost its review dates this way (§3). The existing reader's `PRESS_DOCUMENT` veto still refuses it, so R3 depends on the document-type checks staying in place.

**Is it safe as a general rule?** Yes. It improves year recognition without changing what the document says, provided the existing press and document-type vetoes stay.

**Decision: ADOPT.** The guard is masks only, never the claimed year in the comparison and event patterns, and the reader's document-type vetoes unchanged.

### R4 — reviewed file series

**Not a text rule.** R4 does not read the document. It reads the estate's own site: a page reviewed as one wine's page links the file.

**Problem.** Some sheets name only the estate. Desmirail's `FT-DM` sheets name "Château Desmirail", which is the estate's name as well as the grand vin's, beside Initial, Iris Pourpre and La Perle de Desmirail. Issan's `CHATEAU_ISSAN_` sheets are the same.

**Counts.**
- Rule audit: 33 changed, 33 newly accepted.
- Dry run: R4 takes part in 40 settled claims: 38 with R3 (Desmirail 2005–2019 and 2023, and Issan 2004 and 2010) and 2 alone (Desmirail 2022 alc and blend). It also takes part in Chapelle 1998 with R2+R3, which is held.

**How the mapping is made.**
- The mapping is `FILE_SERIES_PAGES`: 31 (host, path prefix) entries, each the site's own page for one wine.
- A file is mapped to a wine only when every reviewed page linking it is that wine's.
- A file linked from two wines' pages establishes nothing. That covers Issan's sheets from 2016, which the Blason page links too, and La Clarté, filed under both the haut-brion.com and mission-haut-brion.com wine ids.
- A file the listing gives another wine vetoes an acceptance (`R4_VETO`). This includes the unlisted Rosé de Desmirail, so Rosé de Desmirail can never pass as the grand vin.

**Is it safe as a general rule?** Only in this form:

> R4 can establish identity only when the file-to-wine mapping has been independently reviewed.

The mapping is never inferred from a filename prefix (`FT-DM`, `FT-IDM`, `CHATEAU_`, `BLASON_`, `MOULIN_`). It comes from the site linking the file from a page whose own path names the wine.

**Review status of the list.** The current 31 entries were reviewed in the M3.12 rule audit by reading each page's URL and held page text. That was the agent's review, not the user's. Each entry, and any entry added later, should be signed off as reviewed before R4 runs on it in production.

**Decision: ADOPT WITH GUARD.** The guard is the reviewed listing only, `R4_VETO`, and no prefix inference.

**Left open.** Whether an identity resting on R4 can be recorded by the acceptance runner, which counts identity not from a text rule as blocked, is a recording-policy question. It is not decided here.

## 2. G1, on its own

**What it does.** An acceptance a rule created, resting on the grand vin's name, is withdrawn when the text anywhere speaks of another wine of the estate. It is not applied where R4 says whose document it is.

**Every G1 hit in the rule audit:**

| claim | match | reading |
|---|---|---|
| Doisy-Daëne 2015 | "grand vin sec" | right: the estate makes a dry white of that name |
| Doisy-Daëne 2017 | "grand vin sec" | right |
| Doisy-Daëne 2023 | "bordeaux blanc" | right: a sweet wine's estate speaking of a dry white |
| Caillou 2014 | "bordeaux blanc" | right, same reason |
| Issan 2012 (`gs_7d6ebe9220f6`, `gs_59c7bc4f8cbd`, `gs_8ef443db52d6`, `gs_b462e5fe8a11`) | "second wine" | right: R1b alone cannot tell this sheet from the second wine's |
| Grand Mayne 2005 (`gs_b1e4a29592a5`) | "cuvee tends" | **false**: a quoted review, "This cuvee tends to be made in a dense, chewy style", where the cuvée is the grand vin |

That is six hits and one known false refusal.

**Option A (G1 unchanged).** It refuses one sheet whose yield, 35 hl/ha by C6, stays unread.

**Option B (ignore quoted critic prose).** `decide` reads plain folded text. No existing parser marks quotation or review prose in a PDF, and building one is outside this decision.

**Option C (a narrower evidence region).** The only boundary seen is a layout one. In the C6 audit, Grand Mayne's critic notes sit 218–319 pt below the table, but that is page geometry `decide` never sees. No existing structure separates technical-sheet content from quotations across the corpus.

**Decision: Option A, G1 unchanged.** Grand Mayne 2005 stays refused, as a known and accepted cost. One case does not justify weakening a guard that is right in five of its six hits.

## 3. The five held claims

### Paloumey 2022 — `gs_29eb6d397c97` (yld), `ar_004783`, sha `ff3f74b8517d…`

- **Document.** "FT-Chateau-Paloumey-2022-fr-1.pdf" on chateaupaloumey.com, a two-page sheet: a technical page and a press page.
- **Wine.** The text names "Château Paloumey", which is the estate's and the grand vin's name. The sibling Plume de Paloumey is not named.
- **Vintage.** The line R2 uses, "chateau paloumey 2022" (line 50 of 92), stands in the label and value column between "age moyen" and "50 000" (the bottles produced). It may be a table label rather than the title. The second page is headed "revue de presse - chateau paloumey 2022", but no rule reads that form. The year also stands in the filename and in a quote ("2022 est dans la même lignée que 2020").
- **The requested field, yld.** The sheet prints the label "rendement (hl/ha)" with no figure beside it. An unlabelled "24" further down the column may be its value by position, but nothing states it. The only stated words are prose: "des rendements très faibles". The sheet also prints two different blends: "assemblage" 53/44/1/2 and "encépagement" 50/44/3/3.
- **Decision: HOLD_FOR_MORE_EVIDENCE.** The identity is probable, but the adopted rules have no evidence path to it: narrowed R2 no longer reads the single line. Whatever the identity, the yield is labelled, not stated. Reading a value from its position in the table is a capability that does not exist, the same deferral as Figeac's primeur pH.

### Chapelle 1998 — `gs_ac9e56dfd0d4` (blend), `ar_009165`, sha `1c74d87a4ddc…`

- **Document.** "Fiche-technique_ChapelleMissionHB_1998_FR.pdf". The held record has only its local path.
- **Wine.** The text never names a wine. "La Mission Haut-Brion" appears only as an example of an early-ripening terroir ("tels que la mission haut-brion"). The identity rests on R4 (the site's La Chapelle 1998 page links the file) and on the filename.
- **Vintage.** A bare "millesime 1998" on the last line (`BARE`), and the filename.
- **The requested field, blend.** It is stated ("assemblage merlot noir : 21 % ; cabernet sauvignon : 79 %"), but the fiche reader refuses to take it for an unestablished wine. That the blend is readable is not evidence of whose blend it is.
- **Decision: HOLD_FOR_MORE_EVIDENCE.** With R2 narrowed, the bare year is not adopted. Even with it, wine and vintage would rest on the listing and a filename alone, with nothing in the text. The claim needs text evidence of the wine, for example an edition that names it.

### Brane-Cantenac 2023, #1 — `ar_001538`, sha `a9dd99ecfc89…`, "Critics-Review_Primeurs-2023_Chateau-Brane-Cantenac.pdf"

- **Document.** A primeur critics' score sheet in English: "wine critics review. / chateau / brane-cantenac / vintage 2023".
- **Wine and vintage.** R1 reads the split "chateau / brane-cantenac", correctly.
- **But the document holds two score blocks.** Lines 4–66 give 96, 97+, 98 and so on. Lines 67–109 give a second, lower block (91–92, 92+, 89–91 …) under no wine name. Only "chateau brane-cantenac" follows, as a footer. The second block is another wine, unnamed.
- **The requested field.** None: this is a document-to-vintage link from the M3.4A mapping layer. The document states no technical field, and critics' sheets are a deferred admissibility question.
- **Decision: REFUSE.** The identity holds only for part of the document. The document carries an unattributed second wine and no technical datum.

### Brane-Cantenac 2023, #2 — `ar_002431`, sha `6ee0816c5813…`, "Revue-Critiques_Primeurs-2023_Chateau-Brane-Cantenac.pdf"

Decided separately, from its own text.

- **Document.** The French edition: "revue des critiques de vin. / chateau / brane-cantenac / millesime 2023".
- **Its own structure.** The same two blocks: lines 4–66, then lines 67–109 with no wine named, then the footer.
- **The requested field.** None. It states no technical field.
- **Decision: REFUSE**, for the same reasons, found in its own text.

### Corbin 2003 — `ar_005011`, sha `f59854e5d18e…`, "notes_presse_corbin_2003.pdf"

- **Document.** The estate's press compilation: "Château Corbin … / 2003 / revue de presse". The reviews are dated April 2013, 16 September 2009, July 2008, December 2007 and 27 July 2007, with drinking windows "2008 à 2012" and "drink 2008-12".
- **Wine and vintage.** The 2003 Château Corbin is plausible. R3 masks the review dates and drinking windows, so the document no longer looks multi-vintage. This is R3's known limitation (§1).
- **The requested field.** None technical, only critic notes. In M3.6A the existing reader still refuses it (`PRESS_DOCUMENT`: the filename says "presse"), and the rules do not override that.
- **Decision: REFUSE.** It is a press compilation, not a vintage document. The reader's veto stands, and press admissibility is deferred.

## 4. Deferred, not decided here

- La Clarté's double identity (the haut-brion.com and mission-haut-brion.com wine ids). R4 rightly finds those listings ambiguous.
- The Figeac primeur pH: the model has no stage dimension.
- C5: Issan's "Alcool (en % vol.)".
- Multi-estate brochures: identity refuses them, and no blend list is attributed.
- Taillan's partial blend (67 + 23 = 90).
- Press and critic source admissibility.
- Source admissibility outside the P1 review.
- Value reading by table position (Paloumey's "24", Figeac).
- Recording policy for R4-based identity and for C6's layout-derived unit.

## 5. Decision matrix

| Rule/claim | Evidence basis | Decision | Required guard | Reason |
|---|---|---|---|---|
| R1 | 12 changed / 7 accepted alone; the trace shows only separators changed (Calon-Ségur, Figeac, Grand Mayne, Haut-Brion 2006) | ADOPT | separators only; length kept; not inside URLs or emails; no stretching | recovers the same explicit name despite normalisation |
| R1b | 3 changed / 2 accepted; Issan 2008 ×4 settled; Issan 2012 caught by G1; the 4 identity negative controls (single-wine estates) not reached | ADOPT WITH GUARD | multiple wines required; estate-named wine only; no article, preposition or sibling word before; core of at least 4 characters; G1 always applied | the short name names the grand vin only with these guards; Issan 2012 shows it needs G1 |
| R2 | 15 uses: 12 `NAMED_BLOCK` (Grand Mayne, all sound), 2 `NAMED` (Caillou refused, Paloumey held), 1 `BARE` (Chapelle held) | ADOPT NARROWED to `NAMED_BLOCK` | whole-block match, line caps, no competing heading; single-line and bare forms not adopted | a multi-line title block is a genuine heading; a single line can be a table cell, and a bare year names no wine |
| R3 | 17 changed / 2 accepted alone; in 58 settled claims of the dry run | ADOPT | masks only; never the claimed year in comparison and event patterns; press and type vetoes kept | removes typed non-vintage years without adding any |
| R4 | 33 changed / 33 accepted alone (Desmirail, Issan 2004 and 2010); ambiguous listings give nothing; `R4_VETO` on another wine's file | ADOPT WITH GUARD | reviewed `FILE_SERIES_PAGES` only, each entry signed off; one wine's pages only; `R4_VETO`; never from a filename prefix | the site itself files the document under one wine; recording policy left open |
| G1 | 6 hits: 5 right (Doisy-Daëne ×3, Caillou 2014, Issan 2012), 1 false (Grand Mayne 2005, quoted critic prose) | KEEP UNCHANGED (Option A) | applies to every rule-created grand-vin acceptance not made by R4 | no existing structure separates quotations; one false refusal does not justify weakening it |
| Paloumey 2022 — `gs_29eb6d397c97`, `ar_004783` | the R2 line sits in a table column; a page-2 heading no rule reads; yld labelled "rendement (hl/ha)" with no figure | HOLD_FOR_MORE_EVIDENCE | not settled by the adopted rules (R2 narrowed) | identity probable but has no adopted evidence path; the value is not stated |
| Chapelle 1998 — `gs_ac9e56dfd0d4`, `ar_009165` | text names no wine; R4 listing plus filename; bare "millesime 1998"; blend stated but reader-refused | HOLD_FOR_MORE_EVIDENCE | bare-heading R2 not adopted; needs text evidence of the wine | a readable blend is not wine identity |
| Brane-Cantenac 2023 #1 — `ar_001538` | "chateau / brane-cantenac / vintage 2023" over the first of two score blocks; the second block is unnamed; no technical field | REFUSE | stays on the refusal list | the identity covers part of the document; it states no technical datum |
| Brane-Cantenac 2023 #2 — `ar_002431` | the French edition, its own text: the same two blocks, no technical field | REFUSE | stays on the refusal list | the same, found in its own text |
| Corbin 2003 — `ar_005011` | "2003 / revue de presse": a press compilation; R3 masks the review dates; reader `PRESS_DOCUMENT` veto | REFUSE | reader document-type veto kept | a press compilation, not a vintage document |

## 6. Production architecture

```
existing M3.4A decide            (fingerprinted, unchanged, called as it is)
        ↓
candidate-rule evaluation        (identity_rules_candidate.evaluate: R3, R1, R2-block, R1b, R4, then G1)
        ↓
explicit candidate identity result   (disposition, rules fired, trace, notes, file-series mapping)
```

1. **No patching of `decide`.** The adopted rules must sit beside `decide`, not inside it. Today the dry run swaps `decide` inside a `with` block and restores it afterwards. That is fine for a dry run, but production should not depend on patching a module.

   The production shape is a function that receives `decide` and its arguments. It calls `decide` on the rewritten text through `document_text`, the same injection seam M3.9's `text_hook` already uses, and returns its own result with the rule trace.

   If production integration turns out to require changing `decide` itself, stop and design that migration on its own: the file's hash is recorded in the M3.5–M3.12 evidence.
2. **Implementation changes the adoption needs, each to be tested on its own:**
   - R2 limited to `NAMED_BLOCK`;
   - `REVIEW_HOLD` replaced by an explicit, reasoned list: the two holds and the three refusals;
   - the R4 listing entries each marked as reviewed.
3. **Provenance.** The rules must stay deterministic (R1's tie-break is already fixed) and testable with no network or model data change. Every adopted identity must carry the rule trace into whatever records it, so that provenance can later say why the identity was decided.

## 7. The acceptance threshold, rule by rule

| criterion | R1 | R1b | R2 (block) | R3 | R4 |
|---|---|---|---|---|---|
| 1. explicit evidence path | rewrite trace | match and core trace | heading text and line | masked years and pattern | listing pages |
| 2. negative controls stay refused | yes | yes (single-wine guard) | yes | yes | yes |
| 3. ambiguous wines stay refused | yes | yes, with G1 | yes (competing heading) | yes | yes (ambiguous listing, veto) |
| 4. semantic basis | the wine's name | the grand-vin naming convention | the document's own title | typed non-vintage contexts | the site's own filing |
| 5. explicit guard | §1 | §1 | §1 | §1 | §1 |
| 6. provenance can explain it | trace | trace | trace | trace | pages |
| 7. no wider source admissibility | text only | text only | text only | text only | first-party pages; applied after the tier gate |

Applying the threshold, R2 is narrowed and not adopted whole; every other rule meets all seven criteria with its guard.

## 8. Conclusion

CANDIDATE IDENTITY RULES APPROVED FOR CONTROLLED INTEGRATION

Approved, exactly:

- **R1**, as implemented.
- **R1b**, with these guards:
  - the estate has more than one wine in the model;
  - it applies only to the estate-named wine;
  - no article, preposition or sibling word stands before the match;
  - the core name is at least 4 characters;
  - G1 is applied to every acceptance R1b creates.
- **R2, narrowed to the `NAMED_BLOCK` form.** The single-line `NAMED` and bare `BARE` forms are not approved.
- **R3**, as implemented. The existing press and document-type vetoes must stay.
- **R4**, with these guards:
  - only entries of the reviewed `FILE_SERIES_PAGES`, each signed off as reviewed;
  - one wine's pages only;
  - `R4_VETO`;
  - no filename-prefix inference.

  Whether R4 identities can be recorded is a separate policy decision.
- **G1, unchanged.**
- **The claim list:**
  - Paloumey 2022 (`gs_29eb6d397c97`) and Chapelle 1998 (`gs_ac9e56dfd0d4`) are HOLD_FOR_MORE_EVIDENCE;
  - Brane-Cantenac 2023 `ar_001538` and `ar_002431`, and Corbin 2003 `ar_005011`, are REFUSE.

This approval is limited to the identity rules. A controlled integration still needs:
- the implementation changes in §6 (narrowing R2, the reasoned claim list, signing off the R4 entries), each tested on its own;
- a wrapper that does not patch `decide`.

Recording R4 identities and C6 values needs the separate recording-policy decisions.

Effect on the dry run, derived and not re-run: none of the 57 candidates rests on R2's single-line or bare forms. All 11 R2-dependent candidates are Grand Mayne title blocks. With R2 narrowed, Paloumey 2022 and Chapelle 1998 stop being settled at all instead of being held. The candidate count stays 57.

- No production data changed.
- No evidence changed.
- No source registry changed.
- No fingerprinted file changed.
- No production wiring added.
- Nothing pushed.

DECISION PHASE COMPLETE — NO PRODUCTION MUTATION
