# Phase 6.8 — Vintage-list heading semantics audit

Gate: **SAFE — PHASE 6.8 HEADING SEMANTICS AUDITED — DISPLAY CHANGE RECOMMENDED**

This audit is research and design only. Nothing was implemented, and no app, generated-data, model,
evidence or test file changed.

The baseline is `aaa90c6` (Phase 6.7): 26 suites and 724 checks, all passing. The cases were read in
headless Chrome, in English and Dutch, with a scratch script that has since been removed.

## 1. Current implementation semantics

The heading is built in `assets/app.js` (estate drawer, vintage-list section):

```js
var YEARS = Object.keys(V).map(Number)...        // V = window.BDX_VINTAGES
var SPAN  = YEARS[YEARS.length - 1] + '–' + YEARS[0];
...
(state.wine === 'grand' ? 'All vintages, ' + SPAN : sel.name + ', ' + SPAN)
  + '<span class="hint">' + hint + '</span>'
```

| Part | Source | What it means |
|---|---|---|
| **The span, `1982–2025`** | the keys of `BDX_VINTAGES`, the regional vintage reports (`data/vintages.js`), 44 years | **The years this reference lists.** The span is identical for every wine and every estate. |
| **The title before the span** | the grand vin: the fixed words "All vintages"; any other wine: **its current name** (`sel.name`, the CURRENT NameRecord as projected) | the subject of the list |
| **The hint** | grand vin: "N of 44 rated · M ready to drink now"; any other wine: "N of 44 with a sheet on file", counted over the 44 years only | the wine's own coverage within the listed years |
| **The rows** | one per year in `YEARS`, always 44 | — |

What the span is **not**, by the code:

| Question | Answer |
|---|---|
| Does the first year mean the first vintage recorded? | **No.** It is 1982 for every wine. Echo's first sheet is 2011, Lions de Batailley's 2014, and Haut-Bailly II's 2018. |
| Does the last year mean the last vintage recorded? | **No.** It is 2025 for every wine. Lions de Batailley's last sheet is 2017; five wines have a 2026 sheet. |
| Does either year represent the validity of the wine's identity or name? | **No.** No validity is read. Every NameRecord is CURRENT, from UNKNOWN. |
| Does either year represent sheet coverage? | **No.** Coverage is the hint, and since Phase 6.7 the block. |
| Are missing years possible? | Yes. Each of the 44 years has a row: "No sheet on file for this wine" (other wines), or the regional report with no estate data (grand vin). |
| Do explicitly not-made years affect the range? | **No.** They appear inside the list as rows reading "No grand vin produced — the estate declared no vintage." (for example Yquem 1992, 2012, 2018). |
| Is the heading generated from vintage rows, the wine's identity or something else? | From the **regional vintage file**. The title comes from the wine's current name, and the hint from the rows. |

**Years outside the span.** For grand vins only, an "Earlier vintages, YYYY–YYYY" section follows with
the pre-1982 sheets (`earlyYears`). No section exists for other wines' early years or for any wine's
years after 2025.

## 2. Representative-case audit

Measured at `aaa90c6`:

| Case | Heading (English) | Hint | Phase 6.7 block: sheets on file | What the heading invites a reader to infer |
|---|---|---|---|---|
| Lynch-Bages, grand vin | All vintages, 1982–2025 | 21 of 44 rated · 18 ready to drink now | 31 vintages, 1988–2025 | "all of this wine's vintages are 1982–2025": roughly right, since the estate produced throughout; the span itself is the reference's |
| Echo de Lynch-Bages | **Echo de Lynch-Bages, 1982–2025** | 13 of 44 with a sheet on file | 13 vintages, 2011–2025 | **that a wine called Echo de Lynch-Bages spans 1982–2025.** The evidence (Phase 3.4 P7, unreconciled) says it was Haut-Bages Averous until 2007. The block, directly below, says the name's adoption is not recorded. |
| Haut-Bailly II | **Haut-Bailly II, 1982–2025** | 7 of 44 with a sheet on file | 7 vintages, 2018–2025 | **that Haut-Bailly II spans 1982–2025.** The evidence (P11) says La Parde until 2017, and the estate's second-wine fact says "Not established". |
| Lions de Batailley | **Lions de Batailley, 1982–2025** | 4 of 44 with a sheet on file | 4 vintages, 2014–2017 | **a continuous wine 1982–2025**, under a fact that reads "Conflicting records" |
| Yquem, grand vin | All vintages, 1982–2025 | 10 of 44 rated · 20 ready to drink now | 2 vintages, 2021–2023; not made 1992, 2012, 2018 | correct: the not-made years sit in the list as such |
| Climens, grand vin | All vintages, 1982–2025 | 8 of 44 rated · 18 ready to drink now | 15 vintages, 2005–2023; not made in six years | correct, as for Yquem |
| Corbin, grand vin | All vintages, 1982–2025 | 0 of 44 rated · 22 ready to drink now | 16 vintages, 2002–2025 | nothing about rank; the fact grid's "Grand Cru Classé · 2022" and the block carry that |
| Haut-Bailly, grand vin | All vintages, 1982–2025 | 21 of 44 rated | **28 vintages, 1998–2026** | the block counts a 2026 sheet that has no row in a list ending at 2025 |

**In Dutch** the grand-vin heading is translated ("Alle jaargangen, 1982–2025", "21 van 44 beoordeeld
· 18 nu te drinken"). The other wines' hint is **not**: it reads "13 of 44 with a sheet on file" in an
otherwise Dutch page, because `assets/i18n.js` has no entry for it. This defect predates Phase 6.7.

**Coverage outside the listed years**, across all 593 wines:

| Group | Count |
|---|---:|
| wines with a sheet before 1982 or after 2025 | 19 |
| — grand vins with pre-1982 sheets, shown in "Earlier vintages" | 12 |
| — grand vins with a 2026 sheet, which has no row (Haut-Bailly, La Tour Blanche, Langoa-Barton, Léoville-Barton, Lynch-Moussas) | 5 |
| — other wines with pre-1982 sheets, which have no row (Pavillon Rouge and Pavillon Blanc du Château Margaux: 48 sheets, 1978–2025, against "44 of 44" listable) | 2 |
| wines with exactly one sheet | 43 |
| wines with none | 253 |

## 3. User interpretation risk

**For the grand vin: A, correct and sufficiently qualified.**

- "All vintages, 1982–2025" describes the list, and the grand vin is the estate's continuing wine.
- The one overreach is "All": an estate with pre-1982 sheets gets a second "Earlier vintages" section,
  and one with a 2026 sheet gets none.
- That is minor, and not about identity.

**For every other wine: B, technically correct but misleading.**

- The rows really do run 1982–2025, so nothing in the heading is false.
- But the heading puts the wine's **current name** in front of the **reference's** span. The natural
  reading of "Echo de Lynch-Bages, 1982–2025" is "this wine, under this name, across these years". Three
  things contradict that reading:
  - the data: Echo's sheets start in 2011;
  - the unreconciled evidence: Haut-Bages Averous until 2007;
  - Phase 6.7's own block, one line below: "When it was adopted, and any earlier names, are not
    recorded."
- The same holds for Haut-Bailly II, whose identity is unresolved, and Lions de Batailley, whose
  records conflict.

**It is not C.** The span is the list's, and no value is wrong. **Nor is it manufactured by incomplete
history:** the heading makes an identity-over-time suggestion the model does not support, whether or
not history is ever recorded. If dated names arrive later, a single current name over a 44-year span
becomes visibly wrong, not just unqualified.

## 4. Alternative headings

The span is the same for every wine, so a correct heading describes the **list**, not the wine. The
wine's name is already in the "Which wine" selector directly above, and in the block's Name line
directly below.

| Heading | Factual accuracy | Readability and compactness | One vintage / gaps / no sheet | Implies identity continuity? |
|---|---|---|---|---|
| `Echo de Lynch-Bages, 1982–2025` (current, other wines) | the span is right; its pairing with the name is unsupported | compact | unchanged in all three: the span stays 1982–2025 | **yes** |
| `All vintages, 1982–2025` (current, grand vin) | right for the list; "All" overclaims where earlier or later sheets exist | compact | same | weakly, for the grand vin only |
| `Vintages, 1982–2025` | right; still reads as "this wine's vintages" under a selected wine | compact | same | **weakly**: the subject is still implied to be the wine |
| `Vintages with sheets on file, 1982–2025` | **false**: the list includes years without sheets (31 of Echo's 44), and the span is not sheet coverage (Echo's is 2011–2025) | longer | wrong in all three | no, but it misstates coverage |
| `Echo de Lynch-Bages, sheets 2011–2025` (the wine's own span) | true, but it drops the 44-row list's actual span and duplicates the block | medium | one vintage: "2018"; no sheet: no span at all, while the list still has 44 rows | **yes**, more strongly: it implies the wine began in 2011 |
| **`Vintages 1982–2025 in this reference`** | **true for every wine**: it names whose span it is | short | **unaffected**: the span is the reference's; the hint and block carry the wine's coverage | **no**: no wine name, no "all" |

Only the last states what the span is and nothing it is not. It applies identically to the grand vin
and every other wine, and it does not change when a wine has one sheet, gaps, or none.

## 5. English and Dutch

| | English | Dutch |
|---|---|---|
| Recommended heading | Vintages 1982–2025 in this reference | Jaargangen 1982–2025 in dit naslagwerk |
| i18n form | a regular expression, like the existing `^All vintages, (\d+)–(\d+)$` | `'Jaargangen $1–$2 in dit naslagwerk'` |
| Hint, grand vin | unchanged | unchanged: already translated |
| Hint, other wines | unchanged ("N of 44 with a sheet on file") | **missing today**; needs `^(\d+) of (\d+) with a sheet on file$` → `'$1 van $2 met een fiche in het archief'`, the archive wording Phase 6.5 and 6.7 already use |

**"Naslagwerk" (reference work) is a new term.** `assets/i18n.js` does not use it yet, so the
implementation should confirm it against how the Dutch interface names the app elsewhere, or choose a
plainer "in deze gids". The span stays numeric in both languages, so nothing depends on word order
beyond the two regular expressions.

## 6. Interaction with Phase 6.7

**The block does not resolve the heading problem on its own.** It sits *below* the heading and
qualifies the wine's facts:

- the name is current and its adoption is not recorded;
- the rank, classification and appellation are current;
- it gives the sheets on file and the not-made years.

It never says that the heading's span is the reference's years, not the wine's. So a reader meets
"Echo de Lynch-Bages, 1982–2025" first, then a block that partly contradicts it.

**Coverage differs between the block and the list for 7 wines.** The block counts every sheet in the
model (Phase 6.7's choice, which is correct for the data), while the list and its hint stop at
1982–2025:

- **the 5 grand vins with a 2026 sheet:** the block reads "28 vintages, 1998–2026" with no 2026 row;
- **Margaux's two Pavillons:** "48 vintages, 1978–2025" against a 44-row list with no earlier
  section.

The 12 grand vins with pre-1982 sheets are covered by "Earlier vintages".

## 7. Recommendation: CHANGE

A small, display-only change, made **before** historical-data work. Once dated names exist, a heading
pairing one current name with the whole span would be visibly wrong; a heading about the list stays
right.

**The semantic requirements**, not yet implemented:

1. **R1.** The vintage-list heading names its span as **the years this reference lists**, for every
   wine alike. Recommended: "Vintages 1982–2025 in this reference" / "Jaargangen 1982–2025 in dit
   naslagwerk", with the span still computed from `BDX_VINTAGES` as today.
2. **R2.** The heading carries **no wine name**. The selector above and the block below already name
   the wine.
3. **R3.** The grand vin uses the same heading. "All vintages" is dropped, because the list is not
   always all of them ("Earlier vintages", 2026).
4. **R4.** The hints keep their meaning. The other wines' hint gets its **missing Dutch translation**.
5. **R5.** Where the block's sheets on file include years outside the listed span, the block says so
   in its sheets line. Examples: "48 vintages, 1978–2025, 4 of them before the years listed below";
   "28 vintages, 1998–2026, 1 after". This affects 7 wines. The count stays the model's, and nothing is
   hidden.

**What implementing it will touch:**

- `assets/app.js` (the heading, and R5 in `wineEstablished`);
- `assets/i18n.js` (two regular expressions);
- the cache name.

Equivalence will need one new named presentation in `tools/app-reference.py` (the heading text), as
6.1–6.7 did, because the heading appears in every captured drawer. Tests should:

- assert R1–R5 on the cases above;
- assert that no heading contains a wine name;
- check the Dutch hint;
- confirm the 7 out-of-span wines say so.

## 8. Model or data change required

**None.** Every input exists:

- the span (`BDX_VINTAGES`);
- the hint counts (the rows);
- the block's coverage (`wine-established.js`, Phase 6.7);
- the listed years, to compute R5's "before" and "after" in the page.

No generated file needs to change, no historical date is involved, and no identity is resolved: Echo,
Haut-Bailly II and Lions de Batailley stay exactly as the model and Phase 6.3 hold them.
