# The classified growths, estate by estate

A systematic pass over all 61 classified growths: every vintage of the
grand vin and of each other wine, checked for what the record holds
that is the wrong thing, and for what the documents and the estate's
own website state that no record holds.

Run per estate:

    python tools/audit-estate.py --estate <id> --wines        what is held
    python tools/unread.py --estate <id> --show 3             what is missed
    python tools/datapoints.py --estate <id> --sheets         what is printed
    python tools/find-vintages.py --estate <id>               what the site has

The finished report for each lands in `reports/estates/<id>.md`, and the
instructions for repeating its scrape next year in
`data/site-recipes.json` under the estate's id.

**Order is worst-first**, by how much of blend, tasting note and growing
season is absent across the estate's records — the same ranking
`tools/progress.py` prints. The two estates with no records at all are
last, because there is nothing to audit until a source is found.

Dutch is deliberately out of scope for this pass.

## Status

| # | estate | gc | recs | done | report |
|---|---|---|---|---|---|
| 1 | margaux | 1 | 76 -> 118 | 2026-10-24 | [margaux.md](margaux.md) |
| 2 | latour | 1 | 74 | 2026-10-24 | [latour.md](latour.md) |
| 3 | grand-puy-ducasse | 5 | 40 | 2026-10-24 | [grand-puy-ducasse.md](grand-puy-ducasse.md) |
| 4 | palmer | 3 | 56 | 2026-10-24 | [palmer.md](palmer.md) |
| 5 | lynch-bages | 5 | 31 | 2026-10-24 | [lynch-bages.md](lynch-bages.md) |
| 6 | lafite | 1 | 50 | 2026-10-24 | [lafite.md](lafite.md) |
| 7 | pouget | 4 | 30 | 2026-10-24 | [pouget.md](pouget.md) |
| 8 | langoa-barton | 3 | 32 | 2026-10-24 | [langoa-barton.md](langoa-barton.md) |
| 9 | gruaud-larose | 2 | 38 | 2026-10-24 | [gruaud-larose.md](gruaud-larose.md) |
| 10 | malescot | 3 | 26 | 2026-10-24 | [malescot.md](malescot.md) |
| 11 | leoville-barton | 2 | 32 | 2026-10-24 | [leoville-barton.md](leoville-barton.md) |
| 12 | lascombes | 2 | 25 | 2026-10-24 | [lascombes.md](lascombes.md) |
| 13 | cos-destournel | 2 | 37 | 2026-10-24 | [cos-destournel.md](cos-destournel.md) |
| 14 | talbot | 4 | 21 | 2026-10-24 | [talbot.md](talbot.md) |
| 15 | leoville-poyferre | 2 | 22 | 2026-10-24 | [leoville-poyferre.md](leoville-poyferre.md) |
| 16 | duhart-milon | 4 | 33 | 2026-10-24 | [duhart-milon.md](duhart-milon.md) |
| 17 | grand-puy-lacoste | 5 | 28 | 2026-10-24 | [grand-puy-lacoste.md](grand-puy-lacoste.md) |
| 18 | batailley | 5 | 22 | 2026-10-24 | [batailley.md](batailley.md) |
| 19 | prieure-lichine | 4 | 26 | 2026-10-24 | [prieure-lichine.md](prieure-lichine.md) |
| 20 | calon-segur | 3 | 12 | 2026-10-24 | [calon-segur.md](calon-segur.md) |
| 21 | de-camensac | 5 | 25 | 2026-10-24 | [de-camensac.md](de-camensac.md) |
| 22 | marquis-dalesme | 3 | 13 | 2026-10-24 | [marquis-dalesme.md](marquis-dalesme.md) |
| 23 | la-tour-carnet | 4 | 14 | 2026-10-24 | [la-tour-carnet.md](la-tour-carnet.md) |
| 24 | pichon-baron | 2 | 24 | 2026-10-24 | [pichon-baron.md](pichon-baron.md) |
| 25 | beychevelle | 4 | 23 | 2026-10-24 | [beychevelle.md](beychevelle.md) |
| 26 | issan | 3 | 13 | 2026-10-24 | [issan.md](issan.md) |
| 27 | cantemerle | 5 | 15 | 2026-10-24 | [cantemerle.md](cantemerle.md) |
| 28 | giscours | 3 | 12 | 2026-10-24 | [giscours.md](giscours.md) |
| 29 | clerc-milon | 5 | 30 | 2026-10-24 | [clerc-milon.md](clerc-milon.md) |
| 30 | lafon-rochet | 4 | 16 | 2026-10-24 | [lafon-rochet.md](lafon-rochet.md) |
| 31 | ferriere | 3 | 12 | 2026-10-24 | [ferriere.md](ferriere.md) |
| 32 | haut-bages-liberal | 5 | 10 | 2026-10-24 | [haut-bages-liberal.md](haut-bages-liberal.md) |
| 33 | pedesclaux | 5 | 12 | 2026-10-24 | [pedesclaux.md](pedesclaux.md) |
| 34 | cantenac-brown | 3 | 20 | 2026-10-24 | [cantenac-brown.md](cantenac-brown.md) |
| 35 | darmailhac | 5 | 14 | 2026-10-24 | [darmailhac.md](darmailhac.md) |
| 36 | ducru-beaucaillou | 2 | 8 | 2026-10-24 | [ducru-beaucaillou.md](ducru-beaucaillou.md) |
| 37 | haut-batailley | 5 | 10 | 2026-10-24 | [haut-batailley.md](haut-batailley.md) |
| 38 | brane-cantenac | 2 | 6 | 2026-10-24 | [brane-cantenac.md](brane-cantenac.md) |
| 39 | la-lagune | 3 | 10 | 2026-10-24 | [la-lagune.md](la-lagune.md) |
| 40 | lynch-moussas | 5 | 8 | 2026-10-24 | [lynch-moussas.md](lynch-moussas.md) |
| 41 | desmirail | 3 | 6 | 2026-10-24 | [desmirail.md](desmirail.md) |
| 42 | leoville-las-cases | 2 | 6 | 2026-10-24 | [leoville-las-cases.md](leoville-las-cases.md) |
| 43 | montrose | 2 | 16 | 2026-10-24 | [montrose.md](montrose.md) |
| 44 | belgrave | 5 | 8 | 2026-10-24 | [belgrave.md](belgrave.md) |
| 45 | kirwan | 3 | 8 | 2026-10-24 | [kirwan.md](kirwan.md) |
| 46 | boyd-cantenac | 3 | 9 | 2026-10-24 | [boyd-cantenac.md](boyd-cantenac.md) |
| 47 | lagrange | 3 | 14 | 2026-10-24 | [lagrange.md](lagrange.md) |
| 48 | rauzan-segla | 2 | 11 | 2026-10-24 | [rauzan-segla.md](rauzan-segla.md) |
| 49 | du-tertre | 5 | 4 | 2026-10-24 | [du-tertre.md](du-tertre.md) |
| 50 | marquis-de-terme | 4 | 11 | 2026-10-24 | [marquis-de-terme.md](marquis-de-terme.md) |
| 51 | mouton | 1 | 42 | 2026-10-24 | [mouton.md](mouton.md) |
| 52 | branaire-ducru | 4 | 20 | 2026-10-24 | [branaire-ducru.md](branaire-ducru.md) |
| 53 | durfort-vivens | 2 | 2 | 2026-10-24 | [durfort-vivens.md](durfort-vivens.md) |
| 54 | cos-labory | 5 | 2 | 2026-10-24 | [cos-labory.md](cos-labory.md) |
| 55 | dauzac | 5 | 26 | 2026-10-24 | [dauzac.md](dauzac.md) |
| 56 | pichon-comtesse | 2 | 4 | 2026-10-24 | [pichon-comtesse.md](pichon-comtesse.md) |
| 57 | saint-pierre | 4 | 5 | 2026-10-24 | [saint-pierre.md](saint-pierre.md) |
| 58 | pontet-canet | 5 | 26 | 2026-10-24 | [pontet-canet.md](pontet-canet.md) |
| 59 | haut-brion | 1 | 37 | 2026-10-24 | [haut-brion.md](haut-brion.md) |
| 60 | croizet-bages | 5 | 0 | 2026-10-24 | [croizet-bages.md](croizet-bages.md) |
| 61 | rauzan-gassies | 2 | 0 | 2026-10-24 | [rauzan-gassies.md](rauzan-gassies.md) |

## Found before the pass began

Four wines in `BDX_CUVEE_WINES` carried a colour that was not their own,
which matters because `whose_sheet` calls `wrong_colour` with it before
anything is read — a white filed as red has its own sheets refused for
saying Blanc, which cost three estates 69 documents the day before.

| estate | wine | was | is |
|---|---|---|---|
| talbot | Caillou Blanc du Château Talbot | red | white |
| pichon-baron | Les Griffons de Pichon Baron Blanc | red | white |
| stem-chateau-fleur-cardinale | Fleur Cardinale Blanc | red | white |
| domaine-de-chevalier | Rosé de Chevalier | red | rosé |

Checked against two witnesses each: the wine's own name, and the grape
varieties on its own records. Caillou Blanc's twelve records are
Sauvignon Blanc and Sémillon on every one.
