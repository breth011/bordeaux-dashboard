/* ===========================================================================
   Bordeaux Dashboard — Château master data (Sauternes & Barsac 1855)
   27 classified estates: 1 Premier Cru Supérieur, 11 Premiers Crus,
   15 Deuxièmes Crus.
   ---------------------------------------------------------------------------
   growth 0 = Premier Cru Supérieur (Château d'Yquem, a rank of its own)
   Same field provenance rules as chateaux.js.
   Grape keys: SEM Sémillon · SB Sauvignon Blanc · MU Muscadelle
   =========================================================================== */

window.BDX_CHATEAUX = (window.BDX_CHATEAUX || []).concat([

/* ====================== PREMIER CRU SUPÉRIEUR ====================== */
{id:'yquem', name:'Château d’Yquem', growth:0, cat:'sweet',
 appellation:'Sauternes', commune:'Sauternes', lat:44.5330, lng:-0.3270, ha:113,
 second:'Y d’Yquem (a dry white, not a second wine)', owner:'LVMH',
 blend:{SEM:75,SB:25}, perf:0,
 style:'In a class of its own in 1855 and ever since. Pickers pass through the vines up to a dozen times taking individual botrytised berries; yields are around a glass per vine. Saffron, apricot, orange marmalade and a searing acid line that carries it a century. No wine is released in years judged unworthy — 1992, 2012 and 2018 among them.'},

/* ============================ PREMIERS CRUS ============================ */
{id:'la-tour-blanche', name:'Château La Tour Blanche', growth:1, cat:'sweet',
 appellation:'Sauternes', commune:'Bommes', lat:44.5480, lng:-0.3330, ha:40,
 second:'Les Charmilles de Tour Blanche', owner:'French Ministry of Agriculture',
 blend:{SEM:83,SB:12,MU:5}, perf:0.5,
 style:'Listed first among the Premiers Crus in 1855 and run as a working wine school since 1909. Rich, oaky and pineapple-scented, with real concentration in top years.'},

{id:'lafaurie-peyraguey', name:'Château Lafaurie-Peyraguey', growth:1, cat:'sweet',
 appellation:'Sauternes', commune:'Bommes', lat:44.5430, lng:-0.3290, ha:36,
 second:'La Chapelle de Lafaurie-Peyraguey', owner:'Silvio Denz',
 blend:{SEM:93,SB:6,MU:1}, perf:1,
 style:'A fortified medieval courtyard now housing a Lalande-furnished hotel. Pure, tightly wound and citrus-driven, among the most precise wines of the appellation.'},

{id:'clos-haut-peyraguey', name:'Clos Haut-Peyraguey', growth:1, cat:'sweet',
 appellation:'Sauternes', commune:'Bommes', lat:44.5420, lng:-0.3300, ha:15,
 second:'Symphonie de Haut-Peyraguey', owner:'Bernard Magrez',
 blend:{SEM:90,SB:10}, perf:0.5,
 style:'Split from Lafaurie-Peyraguey in 1879. Small, delicate and floral rather than massive, with lemon curd and acacia.'},

{id:'rayne-vigneau', name:'Château de Rayne Vigneau', growth:1, cat:'sweet',
 appellation:'Sauternes', commune:'Bommes', lat:44.5410, lng:-0.3320, ha:84,
 second:'Madame de Rayne', owner:'Trésor du Patrimoine (Crédit Agricole)',
 blend:{SEM:74,SB:24,MU:2}, perf:0,
 style:'A gravel rise famously studded with semi-precious stones. Large production, bright and marmalade-toned, more exuberant than profound.'},

{id:'suduiraut', name:'Château Suduiraut', growth:1, cat:'sweet',
 appellation:'Sauternes', commune:'Preignac', lat:44.5560, lng:-0.3080, ha:92,
 second:'Castelnau de Suduiraut', owner:'AXA Millésimes',
 blend:{SEM:90,SB:10}, perf:1.5,
 style:'Le Nôtre gardens and the richest, most unctuous wine in Sauternes after Yquem — honeyed apricot and roasted pineapple with great viscosity.'},

{id:'coutet', name:'Château Coutet', growth:1, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5680, lng:-0.3080, ha:38.5,
 second:'La Chartreuse de Coutet', owner:'Baly family',
 blend:{SEM:75,SB:23,MU:2}, perf:1,
 style:'The quintessential Barsac — lighter, brisker and more citrus-edged than Sauternes proper, on limestone rather than gravel. The rare Cuvée Madame is made only in exceptional years.'},

{id:'climens', name:'Château Climens', growth:1, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5630, lng:-0.3200, ha:30,
 second:'Les Cyprès de Climens', owner:'Moulin family (since 2022)',
 blend:{SEM:100}, perf:2,
 style:'"Le seigneur de Barsac" — 100% Sémillon, biodynamic, and for many the finest sweet wine in Bordeaux after Yquem. Crystalline, tense and endlessly fine rather than heavy.'},

{id:'guiraud', name:'Château Guiraud', growth:1, cat:'sweet',
 appellation:'Sauternes', commune:'Sauternes', lat:44.5300, lng:-0.3130, ha:103,
 second:'Petit Guiraud', owner:'Peugeot, Neipperg, Planty and Bernard families',
 blend:{SEM:65,SB:35}, perf:0.5,
 style:'The first classified growth in Bordeaux to gain organic certification (2011), with a conservatory of old vine material. Unusually high Sauvignon gives a zesty, grapefruit-tinged lift.'},

{id:'rieussec', name:'Château Rieussec', growth:1, cat:'sweet',
 appellation:'Sauternes', commune:'Fargues', lat:44.5400, lng:-0.2990, ha:92,
 second:'Carmes de Rieussec', owner:'Domaines Barons de Rothschild (Lafite)',
 blend:{SEM:90,SB:7,MU:3}, perf:1,
 style:'The highest point in the appellation after Yquem, which it adjoins. Dark-toned, powerful and spicy, with barley sugar and candied orange.'},

{id:'rabaud-promis', name:'Château Rabaud-Promis', growth:1, cat:'sweet',
 appellation:'Sauternes', commune:'Bommes', lat:44.5450, lng:-0.3350, ha:33,
 second:'—', owner:'Déjean family',
 blend:{SEM:80,SB:18,MU:2}, perf:0,
 style:'The larger half of the divided Rabaud estate. Honeyed and broad, workmanlike rather than thrilling, and usually keenly priced.'},

{id:'sigalas-rabaud', name:'Château Sigalas-Rabaud', growth:1, cat:'sweet',
 appellation:'Sauternes', commune:'Bommes', lat:44.5460, lng:-0.3340, ha:14,
 second:'Lieutenant de Sigalas', owner:'Lanneluc / de Lambert des Granges family',
 blend:{SEM:85,SB:15}, perf:0.5,
 style:'The smaller and finer half of the Rabaud split. Elegant, lemony and comparatively restrained, with notably clean botrytis.'},

/* ============================ DEUXIÈMES CRUS =========================== */
{id:'de-myrat', name:'Château de Myrat', growth:2, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5700, lng:-0.3170, ha:22,
 second:'—', owner:'de Pontac family',
 blend:{SEM:88,SB:8,MU:4}, perf:-0.5,
 style:'The vines were grubbed up entirely in 1976 and replanted in 1988; production resumed in 1991. Light, fresh, honest Barsac.'},

{id:'doisy-daene', name:'Château Doisy-Daëne', growth:2, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5640, lng:-0.3150, ha:17,
 second:'—', owner:'Dubourdieu family',
 blend:{SEM:85,SB:15}, perf:1.5,
 style:'Made by the Dubourdieus, Bordeaux’s most influential white-wine family. Pure, precise and vibrant; the L’Extravagant cuvée is one of the most concentrated wines in Bordeaux.'},

{id:'doisy-dubroca', name:'Château Doisy-Dubroca', growth:2, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5635, lng:-0.3160, ha:9,
 second:'—', owner:'Gonzague Lurton',
 blend:{SEM:100}, perf:0.5,
 style:'The smallest of the three Doisy estates, long farmed alongside Climens and all Sémillon. Delicate and floral.'},

{id:'doisy-vedrines', name:'Château Doisy-Védrines', growth:2, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5660, lng:-0.3140, ha:28,
 second:'Petit Védrines', owner:'Castéja family',
 blend:{SEM:80,SB:15,MU:5}, perf:1,
 style:'The richest and most structured of the Doisy trio — fuller-bodied, oak-aged and closer to a Sauternes in weight.'},

{id:'darche', name:'Château d’Arche', growth:2, cat:'sweet',
 appellation:'Sauternes', commune:'Sauternes', lat:44.5350, lng:-0.3230, ha:43,
 second:'Prieuré d’Arche', owner:'Perromat family / investors',
 blend:{SEM:90,SB:10}, perf:0,
 style:'On the hill above Sauternes village, with a small hotel in the château. Sweet, straightforward and attractively priced.'},

{id:'filhot', name:'Château Filhot', growth:2, cat:'sweet',
 appellation:'Sauternes', commune:'Sauternes', lat:44.5150, lng:-0.3250, ha:62,
 second:'—', owner:'de Vaucelles family',
 blend:{SEM:60,SB:36,MU:4}, perf:0,
 style:'A vast neoclassical château in an English park. Deliberately lighter and less sweet than its neighbours, with high Sauvignon and brisk acidity.'},

{id:'broustet', name:'Château Broustet', growth:2, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5690, lng:-0.3100, ha:16,
 second:'Les Charmes de Broustet', owner:'Laulan Ducos family',
 blend:{SEM:63,SB:37}, perf:0,
 style:'Small Barsac property with an unusually high Sauvignon share; crisp, lemony and quick to charm.'},

{id:'nairac', name:'Château Nairac', growth:2, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5750, lng:-0.3060, ha:16,
 second:'Esquisse de Nairac', owner:'Tari-Heeter family',
 blend:{SEM:90,SB:6,MU:4}, perf:0.5,
 style:'A listed 18th-century château at the entrance to Barsac. Heavily oaked and long-lived, made with uncompromising severity of selection.'},

{id:'caillou', name:'Château Caillou', growth:2, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5600, lng:-0.3230, ha:13,
 second:'Les Erables de Caillou', owner:'Bravo family (since 2016)',
 blend:{SEM:90,SB:10}, perf:0,
 style:'A white turreted château on limestone. Clean, lightly honeyed and fresh, in a restrained Barsac register.'},

{id:'suau', name:'Château Suau', growth:2, cat:'sweet',
 appellation:'Barsac', commune:'Barsac', lat:44.5720, lng:-0.2980, ha:7,
 second:'—', owner:'Biarnès family',
 blend:{SEM:80,SB:10,MU:10}, perf:-0.5,
 style:'One of the smallest and most obscure classified estates, with no château of its own in use. Simple and lightly sweet.'},

{id:'de-malle', name:'Château de Malle', growth:2, cat:'sweet',
 appellation:'Sauternes', commune:'Preignac', lat:44.5620, lng:-0.2880, ha:27,
 second:'Les Fleurs de Malle', owner:'de Bournazel family',
 blend:{SEM:69,SB:28,MU:3}, perf:0.5,
 style:'A listed 17th-century château with celebrated Italianate gardens, straddling the Sauternes and Graves boundary. Light, floral and graceful.'},

{id:'romer', name:'Château Romer', growth:2, cat:'sweet',
 appellation:'Sauternes', commune:'Fargues', lat:44.5450, lng:-0.2950, ha:5,
 second:'—', owner:'Farges family',
 blend:{SEM:70,SB:25,MU:5}, perf:-0.5,
 style:'The smaller fragment of the Romer estate, divided in 1881 and rarely seen outside France.'},

{id:'romer-du-hayot', name:'Château Romer du Hayot', growth:2, cat:'sweet',
 appellation:'Sauternes', commune:'Fargues', lat:44.5440, lng:-0.2960, ha:15,
 second:'—', owner:'du Hayot family',
 blend:{SEM:70,SB:25,MU:5}, perf:-0.5,
 style:'The larger Romer fragment; the château itself was lost to the A62 motorway. Straightforward, grapey and inexpensive.'},

{id:'lamothe', name:'Château Lamothe', growth:2, cat:'sweet',
 appellation:'Sauternes', commune:'Sauternes', lat:44.5250, lng:-0.3200, ha:8,
 second:'—', owner:'Despujols family',
 blend:{SEM:85,SB:10,MU:5}, perf:-0.5,
 style:'The smaller half of the divided Lamothe estate. Modest, caramel-toned and early-drinking.'},

{id:'lamothe-guignard', name:'Château Lamothe-Guignard', growth:2, cat:'sweet',
 appellation:'Sauternes', commune:'Sauternes', lat:44.5255, lng:-0.3210, ha:17,
 second:'—', owner:'Guignard family',
 blend:{SEM:90,SB:5,MU:5}, perf:0.5,
 style:'The larger and distinctly better half of the Lamothe split since 1981 — richer, better balanced and reliably good value.'}

]);
