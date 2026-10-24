# Phase 2.11 — Terrasses de Saint-Christophe attribution audit

**Status: `SAFE — ATTRIBUTION AUDIT COMPLETE`**

This phase was read-only. No canonical file, manifest or evidence row
changed, nothing was appended, and the reader is unchanged.

Started from `f76bd91`, 2026-10-25.

---

## 1. Executive summary

- **Documents inspected:** the 15 v5 acceptances, plus their 15
  byte-identical copies in Bellefont-Belcier's folder, and the sixteenth
  Terrasses document in each folder. In all, **16 distinct Terrasses
  documents** stored twice (32 manifest rows).
- **What they are:** sheets for **Les Terrasses de Saint Christophe**, a
  red Saint-Émilion Grand Cru of the Vignobles K group. Four of them,
  the 2016–2019 PRODUCT-SHEETs, state in their own text: **"Les
  Terrasses de Saint Christophe is the second label of Château Tour
  Saint Christophe."** No document presents it as Château Tour Saint
  Christophe itself.
- **Classification: all 15 `MISATTRIBUTED`** as Tour Saint-Christophe's
  grand vin. The documents contradict the grand-vin context. The estate
  link to Tour Saint-Christophe is explicit for 4 and inferred for 11;
  see §7.
- **Is the acceptance evidence-supported? No.** Nothing in the
  documents identifies them as the grand vin. They pass the grand-vin
  check because of the evaluation context and gaps in the canonical
  list, not because of document evidence:
  - the folder supplies the estate;
  - the group letterhead names the estate;
  - the canonical data lists **no second wine** for Tour Saint-Christophe;
  - "second label" is not a phrase `is_second_wine` reads.
- **Is it contextual attribution? Yes.** The estate comes from the
  folder. The "grand vin" comes from there being no listed alternative.
- **No canonical record is affected.** No `fiches.js`, `field-src.js`
  or `cuvee-src.js` entry cites any Terrasses document. Unattributed
  documents are not read into records.

## 2. The 15 decisions

All 15 have:

- target estate `stem-chateau-tour-saint-christophe` (folder hypothesis;
  the manifest gives no estate), target wine "Château Tour Saint
  Christophe";
- role grand, verdict `ACCEPTED`, an empty reason;
- reader `7e8cfed1c24e`, commit `fb125c8`;
- `read.path` = `fiches/stem-chateau-tour-saint-christophe/<file>`;
- two manifest rows, one per folder, with the same manifest sha1, both
  `estate: null, wine: null, role: unknown`, with no URL.

| document | vintage | `read.sha256` (first 12) | manifest sha1 (first 8) |
| --- | --- | --- | --- |
| FICHE-TECHNIQUE-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2017.pdf | 2017 | af3da1a3ea53 | 7f7041c9 |
| FICHE-TECHNIQUE-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2018.pdf | 2018 | 8e56fbbaba23 | 03aef639 |
| FICHE-TECHNIQUE-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2019.pdf | 2019 | 97d830489f5b | b2f66396 |
| FICHE-TECHNIQUE-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2020.pdf | 2020 | cfea5e051d19 | 32d6afed |
| FICHE-TECHNIQUE-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2021.pdf | 2021 | 7926e3c91859 | b9dbe35d |
| FICHE-TECHNIQUE-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2022.pdf | 2022 | 66d1f551b918 | d8f98a2f |
| FICHE-TECHNIQUE-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2023.pdf | 2023 | bd6d30cd3ed4 | a1c85c67 |
| PRODUCT-SHEET-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2016.pdf | 2016 | aa650cfc049a | aa21974e |
| PRODUCT-SHEET-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2017.pdf | 2017 | f85bbeea5f46 | fd0ff024 |
| PRODUCT-SHEET-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2018.pdf | 2018 | 92dd952dd429 | d8ae2594 |
| PRODUCT-SHEET-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2019.pdf | 2019 | 28018c02fdc3 | d926152c |
| TECHNICAL-SHEET-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2020.pdf | 2020 | 74e372f62067 | 512b450f |
| TECHNICAL-SHEET-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2021.pdf | 2021 | 535ac4d65031 | 9b48a40d |
| TECHNICAL-SHEET-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2022.pdf | 2022 | ca674954f710 | 1c40a901 |
| TECHNICAL-SHEET-LES-TERRASSES-DE-SAINT-CHRISTOPHE-2023.pdf | 2023 | a729ff715027 | d6ad7280 |

The sixteenth, `FICHE-TECHNIQUE-…-2016.pdf`, is refused as a press
document.

## 3. Document identity evidence

**Every document opens with the Vignobles K letterhead:**

> CHATEAU BELLEFONT-BELCIER - CHATEAU TOUR SAINT CHRISTOPHE - ENCLOS
> TOURMALINE - CHATEAU HAUT-BRISSON - CHATEAU LA PATACHE - ENCLOS DE
> VIAUD - CHATEAU LE REY · Saint Christophe des Bardes ·
> contact@vignoblesk.com · www.vignoblesk.com

It names seven properties. It is a group letterhead, not a statement of
whose wine the sheet is.

**Group 1: the 4 PRODUCT-SHEETs, 2016–2019.**

- **Title:** "LES TERRASSES DE SAINT CHRISTOPHE <year> – FACTS".
- **Wine:** blend 90% Merlot, 10% Cabernet Franc (2016).
- **Estate:** they name Tour Saint Christophe 4–6 times. They say
  "the minerality that is specific to Tour Saint Christophe is well
  represented here" and give Tour Saint-Christophe's history (acquired
  by Peter Kwok and his daughter Karen in 2012; the restored terraces).
- **And they say:**

  > "Les Terrasses de Saint Christophe is the **second label of Château
  > Tour Saint Christophe**. It is made from some of the younger vines
  > planted on the beautiful terrasses of the estate and has the same
  > care at every stage as the first wine. The blend and aging are
  > slightly different leading to a different style of wine that can be
  > better enjoyed at younger age." (2019)

**Wine: the second wine of Tour Saint-Christophe. Explicit.**

**Group 2: the 11 FICHE-TECHNIQUE / TECHNICAL-SHEETs, 2017–2023.**

- **Title:** "LES TERRASSES DE SAINT CHRISTOPHE <year>".
- **Text:**

  > "Créée et orchestrée par l'équipe des **Vignobles K**, la **cuvée**
  > Les Terrasses de Saint Christophe reflète le caractère des vins de
  > l'appellation. Ce Saint-Emilion Grand Cru… issus de jolis terroirs
  > de l'appellation Saint-Emilion Grand Cru."

- **Estate:** "Tour Saint Christophe" appears exactly **once**, in the
  letterhead.

**Wine: Les Terrasses de Saint Christophe, certain.** It is presented as
a group cuvée "from fine terroirs of the appellation". These sheets do
not themselves say which estate's vines it comes from.

**No document of either group presents itself as Château Tour Saint
Christophe's grand vin.** That wine has its own sheets in the same
folder (§4), named `FICHE-PRODUIT-…`, `PRODUCT-SHEET-…` and
`TECHNICAL-SHEET-CHATEAU-TOUR-SAINT-CHRISTOPHE-<year>`.

## 4. Source and site context

- **Source domain:** `vignoblesk.com`. In `data/websites.js`, both
  `stem-chateau-tour-saint-christophe` and
  `stem-chateau-bellefont-belcier` point to it. The manifest rows carry
  no URL.
- **A multi-estate site.** The group publishes one library for all seven
  properties. The Tour Saint-Christophe folder (136 manifest rows) holds
  sheets for:
  - Badine de la Patache, Château La Patache;
  - Bellefont-Belcier and Les Tours de Belcier;
  - Haut-Brisson and Haut-Brisson La Grave;
  - Le Rey (Cabernet Franc, Les Argileuses, Les Rocheuses);
  - Enclos de Viaud, Enclos Tourmaline;
  - Tour Saint-Christophe's own grand vin (2014–2023);
  - an unlisted Tour Saint-Christophe white, "ANGELA BLANC";
  - and the Terrasses.
- **The same shape as earlier shared-site cases.** This is the
  Bellefont-Belcier / Vignobles K group-footer case of Phase 2.1: one
  site, one letterhead naming every property, a crawl filing the
  library under each property it found it from. The source is recorded
  here as **multi-estate**. No profile or rule was changed.

## 5. Cross-corpus identity evidence

| question | finding |
| --- | --- |
| same filename elsewhere | every Terrasses file exists in exactly two folders: Tour Saint-Christophe's and Bellefont-Belcier's |
| same bytes | **16 of 16 pairs byte-identical** (SHA-256) |
| same manifest hash | yes, both rows of each pair |
| other folders | none |
| attributed anywhere | no: all 32 manifest rows have `estate: null` |
| Phase 2 attribution proposal | **all 32 `HIGH_CONFIDENCE`**: 16 to Tour Saint-Christophe and **16 to Bellefont-Belcier**. Both rest on "the document names the folder's estate", which for these sheets means the group letterhead. |

A document may legitimately serve several estates, but these do not.
Each pair is one document about one wine, filed twice by the crawl.

**The Phase 2 HIGH_CONFIDENCE attribution of the 16 Belcier-folder
copies to Bellefont-Belcier is contradicted by the documents.** They
name Bellefont-Belcier only in the letterhead. Applying it would file
Tour Saint-Christophe's second wine under Bellefont-Belcier.

## 6. Historical evidence

Shown as recorded; nothing was rewritten.

| version | Tour Saint-Christophe folder (16) | Bellefont-Belcier folder (16) |
| --- | --- | --- |
| v1 | `NO_ESTATE_IN_MANIFEST` (not evaluated) | `NO_ESTATE_IN_MANIFEST` |
| v2 | grand: **15 ACCEPTED**, 1 PRESS_DOCUMENT | grand: 12 WRONG_WINE, 4 TRADE_LISTING; other cuvée: 16 not evaluated |
| v3 | identical to v2 | identical to v2 |
| v4 | identical to v2 | identical to v2 |
| v5 | identical to v2 | identical to v2 |

No provenance failures occurred in any version.

**Interpretation, separate from the historical verdicts:**

- The Tour Saint-Christophe acceptances have been stable since the first
  contextual pass (v2). No reader change has touched them.
- The Bellefont-Belcier refusals are right for the wrong reason. They
  are `WRONG_WINE`, "abbreviates Les Tours de Belcier": the filename
  word "LES" begins Belcier's degenerate mark `les de belcier`. That is
  the accidental refusal documented in Phase 2.9 §8, kept deliberately.
- The 4 `TRADE_LISTING` refusals are the PRODUCT-SHEETs.

## 7. Classification

**Identity comparison:**

| evidence | Tour Saint-Christophe (grand vin) | Les Terrasses de Saint Christophe |
| --- | --- | --- |
| canonical estate exists | yes, `stem-chateau-tour-saint-christophe` | no, and none is warranted: it is a label, not an estate |
| canonical wine exists | yes, the grand vin | **no**: Tour Saint-Christophe lists `second: null, cuvees: []` |
| document names it as the estate | only in the group letterhead (all 15), and in the history section (the 4 PRODUCT-SHEETs) | n/a |
| document names it as the wine | **no** (0 of 15) | **yes** (15 of 15, in the title) |
| source URL identifies it | no URL recorded; the site is the group's | the same |
| source site associates it | as one of seven group properties | as a group cuvée (2017–2023), and as Tour Saint-Christophe's second label (2016–2019) |
| same document elsewhere | Bellefont-Belcier folder, byte-identical (a crawl duplicate) | the same |
| other corpus documents support it | Tour Saint-Christophe's grand vin has its own sheets, 2014–2023, attributed in the manifest | no other Terrasses documents exist |

**Classification by document group:**

| documents | n | classification | estate supported | wine supported |
| --- | ---: | --- | --- | --- |
| PRODUCT-SHEET 2016–2019 | 4 | **`MISATTRIBUTED`** (as the grand vin) | Tour Saint-Christophe, **explicitly** | its **second wine**, Les Terrasses de Saint Christophe |
| FICHE-TECHNIQUE 2017–2023, TECHNICAL-SHEET 2020–2023 | 11 | **`MISATTRIBUTED`** (as the grand vin) | Tour Saint-Christophe **by inference**: same wine name, the same group and folder, and for 2017–2019 the same vintages as the explicit PRODUCT-SHEETs. For 2020–2023 no document states the estate link, and the sheets frame the wine as a Vignobles K cuvée from appellation terroirs. | Les Terrasses de Saint Christophe, **certain** |

Why not the other classifications:

- **Not `TOUR_SAINT_CHRISTOPHE`:** the estate is right, but the wine the
  context asks about, the grand vin, is not what the documents are.
- **Not `TERRASSES_SAINT_CHRISTOPHE`:** no evidence makes it an estate.
- **Not `SHARED_DOCUMENT`:** each document is about one wine; the
  multi-property letterhead is group furniture.

**How the acceptance comes about** (Task 7), traced with the unchanged
reader on `TECHNICAL-SHEET-…-2020` and `PRODUCT-SHEET-…-2019`:

| source of the acceptance | contribution |
| --- | --- |
| evaluation context: the folder | supplies the target estate (`target_estate_from: folder, a hypothesis`) |
| target wine context | "grand vin", the only wine Tour Saint-Christophe has in the data |
| document evidence | `confirms_estate: named`, but through the letterhead only |
| filename / URL | names Les Terrasses; `property_in_filename` and `names_other_chateau` find no château in it |
| generic reader behaviour | `names_another_wine` has no listed other wine to look for; `is_second_wine` reads "second vin / second wine", not "second label"; the Phase 2.6 unlisted-name model runs only in second-wine mode |

**If "Les Terrasses de Saint Christophe" were Tour Saint-Christophe's
listed second wine, the unchanged reader would refuse these sheets as
the grand vin:** "the sheet names another of the estate's wines".
`test-phase211.py` asserts it.

## 8. Recommended next action (proposal only — not implemented)

1. **Canonical estate data.** Record **"Les Terrasses de Saint
   Christophe" as Château Tour Saint Christophe's second wine.**

   - *Evidence:* the four 2016–2019 PRODUCT-SHEETs say so in the estate's
     own words, and give its sourcing (younger vines on the estate's
     terraces).
   - *Uncertain:* from 2020 the group's sheets call it a Vignobles K
     cuvée from appellation terroirs, without naming its source. Whether
     it stayed a second label of Tour Saint-Christophe, or became a
     group négoce cuvée, needs a source the corpus does not hold: the
     current page on vignoblesk.com, or a merchant. If it changed, the
     record should say so by vintage rather than choose.

2. **Attribution.**
   - Attribute the 16 Tour Saint-Christophe-folder rows to Tour
     Saint-Christophe, wine "Les Terrasses de Saint Christophe", role
     second. For 2020–2023, mark the role as inferred until point 1's
     uncertainty is settled.
   - **Reject Phase 2's 16 HIGH_CONFIDENCE attributions of the
     Bellefont-Belcier-folder copies to Bellefont-Belcier.** Record them
     as byte-identical duplicates of the Tour Saint-Christophe rows.
     Their only Belcier evidence is the group letterhead.

3. **Evidence.** After point 1, a new evidence version would withdraw
   these 15 grand-vin acceptances through the **existing** rule, with no
   reader change. Second-wine mode would evaluate them as Les Terrasses
   for the first time.

4. **Reader observations, for a later reader phase** (not needed for the
   correction above):
   - "second label" is not among the second-wine phrases;
   - the grand-vin path has no unlisted-name model, so a wine missing
     from the canonical list is invisible to it. That is the gap this
     case fell through.

5. **Related, out of scope here:** Tour Saint-Christophe's white "ANGELA
   BLANC" is also unlisted, and the group library holds five other
   properties' sheets unattributed in this folder. Both are candidates
   for the same kind of audit.

No correction was made. No manifest row, file, estate definition,
`fiches.js` entry, reader rule or evidence row was changed.

## Safety verification

- `git diff` over `data/fiches.js`, `data/chateaux.js`,
  `data/cuvees.js`, `data/sources.json`, `data/field-src.js`,
  `data/cuvee-src.js` and every committed evidence file is empty.
- The evidence store holds **177,127** decisions, and the reader is
  **`7e8cfed1c24e`**.
- New in this phase: this document and `tools/test-phase211.py`.
  `test-phase211.py` (11 checks, all pass) identifies the 15
  deterministically, confirms the document evidence and the reader
  counterfactual, and checks that nothing canonical or historical moved.
