/* ===========================================================================
   Bordeaux Dashboard — Verified overrides
   ---------------------------------------------------------------------------
   Everything in this file is marked VERIFIED in the dashboard and replaces
   the modelled value for that wine and vintage.

   These are scores and notes that entered the public record and stayed there
   — overwhelmingly Wine Advocate / Robert Parker-era perfect and near-perfect
   ratings, plus a few universally reported benchmarks. They reflect published
   critical consensus at the time of writing.

   They are NOT a live feed. Critics re-rate wines on re-tasting, and the
   aggregate you see on Wine-Searcher today may differ. Use the price link on
   any wine card for the current critic average.

   Key format:  '<chateau id>|<vintage>'
   Fields:      score   reported 100-point rating
                src     attribution shown in the UI
                note    reported tasting note, where a canonical one exists
                blend   actual final blend for that vintage, if known
   =========================================================================== */

window.BDX_SCORES = {

/* ----------------------------- LAFITE ------------------------------- */
'lafite|1982':{score:100,src:'Wine Advocate',
 note:'A legend of the estate and the wine that defined the vintage for a generation. Pencil shavings, cedar, truffle and sweet cassis; still extraordinarily fresh four decades on.'},
'lafite|1986':{score:100,src:'Wine Advocate',
 note:'Built on the vintage’s huge Cabernet tannins but with Lafite’s fine grain. A wine that needed twenty-five years and rewards the wait.'},
'lafite|1996':{score:100,src:'Wine Advocate',
 note:'The great Cabernet year expressed through the most aristocratic address in Pauillac. Graphite, violets and an endless, cool finish.'},
'lafite|2003':{score:100,src:'Wine Advocate',
 note:'An improbable triumph in the heatwave year — exotic and opulent by Lafite standards, yet retaining the estate’s signature cedar and restraint.'},

/* ------------------------------ LATOUR ------------------------------ */
'latour|1982':{score:100,src:'Wine Advocate',
 note:'Monolithic even at forty years. Walnut, tobacco, iron and dark fruit over tannins that have never fully softened.'},
'latour|1990':{score:100,src:'Wine Advocate',
 note:'The great modern Latour before 2009 — sweet-fruited for the estate, with the Enclos minerality underneath.'},
'latour|2003':{score:100,src:'Wine Advocate',
 note:'One of the wines of the heatwave vintage. The deep clay of the Enclos held water when lighter soils failed; the result is dense, savoury and remarkably fresh.'},
'latour|2009':{score:100,src:'Wine Advocate'},
'latour|2010':{score:100,src:'Wine Advocate',
 note:'Possibly the most structured Latour ever made. Enormous tannin and acidity wrapped around pure cassis; a fifty-year wine.'},

/* ------------------------------ MARGAUX ----------------------------- */
'margaux|1990':{score:100,src:'Wine Advocate',
 note:'The benchmark modern Margaux — violets, crushed rock and silk, with a mid-palate of uncanny weightlessness.'},
'margaux|1996':{score:100,src:'Wine Advocate',
 note:'90% Cabernet Sauvignon in a great Cabernet year. Tight, mineral and very slow to unfold.',
 blend:{CS:90,ME:6,CF:2,PV:2}},
'margaux|2010':{score:100,src:'Wine Advocate'},
'margaux|2015':{score:100,src:'Multiple critics',
 note:'Paul Pontallier’s final vintage, and a fitting one. The August rain that fell on Margaux and spared the north gave perfume, silk and extraordinary length.'},

/* ------------------------------ MOUTON ------------------------------ */
'mouton|1982':{score:100,src:'Wine Advocate',
 note:'Exotic, sweet and almost decadent — crème de cassis, Asian spice and cigar box. The most immediately pleasurable of the 1982 First Growths.'},
'mouton|1986':{score:100,src:'Wine Advocate',
 note:'The emblem of the vintage. Massively tannic on release and dismissed by some as impenetrable; it took thirty years to prove itself and is now magnificent.'},

/* ----------------------------- HAUT-BRION --------------------------- */
'haut-brion|1989':{score:100,src:'Wine Advocate',
 note:'Widely held to be the greatest Bordeaux of the post-war era. Scorched earth, tobacco, warm brick and molten dark fruit, with a finish that runs for a full minute.'},
'haut-brion|2009':{score:100,src:'Wine Advocate'},
'haut-brion|2010':{score:100,src:'Wine Advocate'},

/* ------------------------- SECONDS & OTHERS ------------------------- */
'montrose|1990':{score:100,src:'Wine Advocate',
 note:'The wine that made modern Montrose’s reputation. Iron, graphite and black fruit of enormous density; still youthful.'},
'montrose|2009':{score:100,src:'Wine Advocate'},
'montrose|2010':{score:100,src:'Wine Advocate'},
'cos-destournel|2009':{score:100,src:'Wine Advocate',
 note:'The most exotic expression of a hedonistic vintage — sandalwood, cocoa and liqueur-like black fruit, yet with Saint-Estèphe’s structure beneath.'},
'pichon-comtesse|1982':{score:100,src:'Wine Advocate',
 note:'The apotheosis of the old, Merlot-rich Comtesse style — voluptuous, sweet and perfumed, a wine that charmed from the cradle.'},
'leoville-las-cases|1982':{score:100,src:'Wine Advocate',
 note:'A First Growth in all but classification. Austere and graphite-driven where its neighbours were sweet, and all the better for it today.'},
'pontet-canet|2009':{score:100,src:'Wine Advocate',
 note:'The biodynamic conversion vindicated in the most public way possible — a Fifth Growth scoring alongside the First Growths. Dense, mineral and dramatic.'},
'pontet-canet|2010':{score:100,src:'Wine Advocate',
 note:'Back-to-back perfection. Even more structured than the 2009, with a stony, almost crystalline core.'},
'ducru-beaucaillou|2010':{score:99,src:'Wine Advocate'},
'leoville-las-cases|2010':{score:99,src:'Wine Advocate'},
'palmer|2010':{score:98,src:'Wine Advocate',
 note:'Merlot-rich and gloriously floral even in a Cabernet vintage — the Palmer paradox in full flight.'},

/* ------------------------------ SAUTERNES --------------------------- */
'yquem|1988':{score:99,src:'Wine Advocate',
 note:'The most structured of the great 1988–89–90 trio. Searing acidity under layers of saffron, apricot and candied citrus.'},
'yquem|1990':{score:99,src:'Wine Advocate',
 note:'The most opulent of the trio — roasted pineapple, crème brûlée and botrytis spice, with decades still ahead of it.'},
'yquem|2001':{score:100,src:'Wine Advocate',
 note:'The definitive modern Yquem, from the appellation’s greatest season in living memory. Perfect botrytis, perfect acidity, effectively immortal.'},
'climens|2001':{score:100,src:'Wine Advocate',
 note:'Pure Sémillon from the limestone of Barsac, and proof that greatness in sweet wine is a matter of tension rather than sweetness.'},
'rieussec|2001':{score:98,src:'Wine Advocate'},
'suduiraut|2001':{score:98,src:'Wine Advocate'}

};

/* ---------------------------------------------------------------------------
   Years in which no grand vin was produced, or the estate declared no vintage.
   --------------------------------------------------------------------------- */
window.BDX_NOT_PRODUCED = {
  'yquem': [1992, 2012, 2018],
  'climens': [1984, 1987, 1992, 1993, 2012, 2017],
  'de-myrat': [1982,1983,1984,1985,1986,1987,1988,1989,1990]
};
