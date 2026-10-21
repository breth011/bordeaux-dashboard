/* ===========================================================================
   Bordeaux Dashboard — Château master data (red 1855 classification)
   Classification officielle des vins de Bordeaux de 1855 (as amended 1973)
   61 classified red estates: Médoc + Château Haut-Brion (Graves)
   ---------------------------------------------------------------------------
   FIELD PROVENANCE
     name, growth, appellation, commune ... VERIFIED (1855 classification)
     blend ................................ VERIFIED — the estate's typical
                                            published encépagement for the
                                            grand vin. Vintage-by-vintage
                                            variation is MODELLED in app.js.
     ha, second, owner .................... VERIFIED to best knowledge;
                                            ownership and plantings drift.
     lat, lng ............................. APPROXIMATE, commune-level
                                            accuracy (roughly ±400 m).
     perf ................................. MODELLED. Points added to the
                                            growth baseline to reflect the
                                            estate's modern critical standing
                                            relative to its 1855 rank.
                                            NOT a critic score.
   Grape keys: CS Cabernet Sauvignon · ME Merlot · CF Cabernet Franc
               PV Petit Verdot · CA Carménère · MA Malbec
   =========================================================================== */

window.BDX_CHATEAUX = (window.BDX_CHATEAUX || []).concat([

/* ============================ PREMIERS CRUS ============================ */
{id:'lafite', name:'Château Lafite Rothschild', growth:1, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2383, lng:-0.7503, ha:112,
 second:'Carruades de Lafite', owner:'Domaines Barons de Rothschild (Lafite)',
 blend:{CS:70,ME:25,CF:3,PV:2}, perf:0,
 style:'The most ethereal of the First Growths. Cedar, graphite and violets over a silk-textured frame; built for very long ageing and rarely showy young.'},

{id:'latour', name:'Château Latour', growth:1, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.1716, lng:-0.7446, ha:92,
 second:'Les Forts de Latour', owner:'Groupe Artémis (François Pinault)',
 blend:{CS:80,ME:17,CF:2,PV:1}, perf:0.5,
 style:'The benchmark for power and structure in Pauillac. Dense, mineral and almost unyielding in youth; the riverside Enclos gives remarkable consistency even in weak vintages. Sold only on release-when-ready since 2012.'},

{id:'margaux', name:'Château Margaux', growth:1, cat:'red',
 appellation:'Margaux', commune:'Margaux', lat:45.0430, lng:-0.6700, ha:99,
 second:'Pavillon Rouge du Château Margaux', owner:'Corinne Mentzelopoulos',
 blend:{CS:87,ME:8,CF:3,PV:2}, perf:0.5,
 style:'Perfume and poise — rose petal, cassis and crushed stone over a weightless mid-palate. The most overtly aromatic of the First Growths.'},

{id:'haut-brion', name:'Château Haut-Brion', growth:1, cat:'red',
 appellation:'Pessac-Léognan', commune:'Pessac', lat:44.8030, lng:-0.6080, ha:51,
 second:'Le Clarence de Haut-Brion', owner:'Domaine Clarence Dillon',
 blend:{CS:45,ME:42,CF:13}, perf:0.5,
 style:'The only non-Médoc estate in the 1855 red classification. Smoky, earthy, tobacco-and-warm-brick, from gravel mounds now surrounded by suburban Bordeaux; the most Merlot-led of the Firsts.'},

{id:'mouton', name:'Château Mouton Rothschild', growth:1, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2274, lng:-0.7524, ha:90,
 second:'Le Petit Mouton de Mouton Rothschild', owner:'Baron Philippe de Rothschild SA',
 blend:{CS:83,ME:14,CF:2,PV:1}, perf:0,
 style:'Promoted from Second to First Growth in 1973 — the only revision ever made to the 1855 list. Flamboyant and exotic, crème de cassis and Asian spice, with a commissioned artist label every year since 1945.'},

/* ============================ DEUXIÈMES CRUS =========================== */
{id:'rauzan-segla', name:'Château Rauzan-Ségla', growth:2, cat:'red',
 appellation:'Margaux', commune:'Margaux', lat:45.0400, lng:-0.6730, ha:66,
 second:'Ségla', owner:'Chanel (Wertheimer family)',
 blend:{CS:62,ME:35,PV:2,CF:1}, perf:0.5,
 style:'Transformed since the Chanel purchase in 1994 — firm, dark-fruited and classically Margaux-perfumed, now a dependable overachiever.'},

{id:'rauzan-gassies', name:'Château Rauzan-Gassies', growth:2, cat:'red',
 appellation:'Margaux', commune:'Margaux', lat:45.0395, lng:-0.6740, ha:30,
 second:'—', owner:'Quié family',
 blend:{CS:65,ME:25,CF:5,PV:5}, perf:-1.5,
 style:'Long considered the clearest underperformer among the Seconds; rustic and firm, with gradual improvement over the last decade.'},

{id:'leoville-las-cases', name:'Château Léoville-Las Cases', growth:2, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1620, lng:-0.7430, ha:97,
 second:'Le Petit Lion (Clos du Marquis is a separate cuvée)', owner:'Delon family',
 blend:{CS:75,ME:15,CF:10}, perf:1.5,
 style:'Widely regarded as a First Growth in all but name. The walled Grand Enclos abuts Latour; austere, graphite-driven and exceptionally long-lived.'},

{id:'leoville-poyferre', name:'Château Léoville-Poyferré', growth:2, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1590, lng:-0.7460, ha:80,
 second:'Pavillon de Poyferré (also Château Moulin Riche)', owner:'Cuvelier family',
 blend:{CS:65,ME:30,PV:3,CF:2}, perf:0.5,
 style:'The plushest of the three Léovilles — opulent, sweet-fruited and polished, a Michel Rolland-era success story.'},

{id:'leoville-barton', name:'Château Léoville-Barton', growth:2, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1580, lng:-0.7470, ha:50,
 second:'La Réserve de Léoville-Barton', owner:'Barton family',
 blend:{CS:75,ME:20,CF:5}, perf:0.5,
 style:'Traditionalist and famously fairly priced for its quality. Cedar, tobacco leaf and a firm Cabernet spine; vinified at Langoa next door.'},

{id:'durfort-vivens', name:'Château Durfort-Vivens', growth:2, cat:'red',
 appellation:'Margaux', commune:'Margaux', lat:45.0410, lng:-0.6750, ha:65,
 second:'Vivens', owner:'Gonzague Lurton',
 blend:{CS:75,ME:20,CF:5}, perf:-0.5,
 style:'Fully biodynamic (certified 2016), one of the largest such estates in the Médoc. Lean, high-Cabernet and structured; polarising in cool years.'},

{id:'gruaud-larose', name:'Château Gruaud-Larose', growth:2, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1430, lng:-0.7560, ha:82,
 second:'Sarget de Gruaud-Larose', owner:'Merlaut family (Taillan group)',
 blend:{CS:65,ME:28,CF:4,PV:3}, perf:0,
 style:'"Le roi des vins" by its own motto. Big-boned, savoury and sometimes gamey; the 1982 and 1990 are legends of the estate.'},

{id:'lascombes', name:'Château Lascombes', growth:2, cat:'red',
 appellation:'Margaux', commune:'Margaux', lat:45.0390, lng:-0.6790, ha:120,
 second:'Chevalier de Lascombes', owner:'Lawrence family / Carlton McCoy (since 2022)',
 blend:{ME:50,CS:45,PV:5}, perf:-0.5,
 style:'Merlot-dominant and deliberately modern and extracted through the 2000s; a stylistic reset is under way with new ownership.'},

{id:'brane-cantenac', name:'Château Brane-Cantenac', growth:2, cat:'red',
 appellation:'Margaux', commune:'Cantenac', lat:45.0230, lng:-0.6720, ha:75,
 second:'Baron de Brane', owner:'Henri Lurton',
 blend:{CS:70,ME:25,CF:4.5,CA:0.5}, perf:0,
 style:'Grown on the fine gravel plateau of Brane; silky, floral and medium-bodied rather than powerful. Retains a trace of Carménère.'},

{id:'pichon-baron', name:'Château Pichon-Longueville Baron', growth:2, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.1760, lng:-0.7490, ha:73,
 second:'Les Tourelles de Longueville', owner:'AXA Millésimes',
 blend:{CS:70,ME:28,CF:2}, perf:0.5,
 style:'Muscular, dark and emphatically Pauillac, from gravel directly across the road from Latour. The fairy-tale château is the appellation’s most photographed building.'},

{id:'pichon-comtesse', name:'Château Pichon Longueville Comtesse de Lalande', growth:2, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.1740, lng:-0.7510, ha:89,
 second:'Réserve de la Comtesse', owner:'Louis Roederer (Rouzaud family)',
 blend:{CS:70,ME:25,CF:3,PV:2}, perf:1,
 style:'The most seductive wine in Pauillac — historically Merlot-rich and velvety, now increasingly Cabernet-led and precise under Nicolas Glumineau.'},

{id:'ducru-beaucaillou', name:'Château Ducru-Beaucaillou', growth:2, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1530, lng:-0.7380, ha:75,
 second:'La Croix Ducru-Beaucaillou', owner:'Borie family (Bruno Borie)',
 blend:{CS:80,ME:20}, perf:1,
 style:'Named for the "beautiful pebbles" of its riverside gravel. Refined, cassis-and-cedar, aristocratic; a model of consistency since the mid-1990s.'},

{id:'cos-destournel', name:'Château Cos d’Estournel', growth:2, cat:'red',
 appellation:'Saint-Estèphe', commune:'Saint-Estèphe', lat:45.2460, lng:-0.7560, ha:91,
 second:'Les Pagodes de Cos', owner:'Michel Reybier',
 blend:{CS:65,ME:33,CF:2}, perf:1,
 style:'The pagoda-topped chai looks East, and so does the wine — spice, sandalwood and lush dark fruit, the most exotic wine of the northern Médoc.'},

{id:'montrose', name:'Château Montrose', growth:2, cat:'red',
 appellation:'Saint-Estèphe', commune:'Saint-Estèphe', lat:45.2490, lng:-0.7340, ha:95,
 second:'La Dame de Montrose', owner:'Martin and Olivier Bouygues',
 blend:{CS:65,ME:30,CF:3,PV:2}, perf:1,
 style:'Saint-Estèphe’s iron fist — tightly wound, mineral and famously slow to open. The 1990, 2009 and 2010 rank among the Médoc’s greatest modern wines.'},

/* =========================== TROISIÈMES CRUS =========================== */
{id:'kirwan', name:'Château Kirwan', growth:3, cat:'red',
 appellation:'Margaux', commune:'Cantenac', lat:45.0250, lng:-0.6760, ha:37,
 second:'Charmes de Kirwan', owner:'Schÿler family',
 blend:{CS:55,ME:35,CF:7,PV:3}, perf:0,
 style:'Floral and juicy, built for mid-term drinking; a new gravity-fed cellar in 2015 brought noticeably greater precision.'},

{id:'issan', name:'Château d’Issan', growth:3, cat:'red',
 appellation:'Margaux', commune:'Cantenac', lat:45.0310, lng:-0.6650, ha:53,
 second:'Blason d’Issan', owner:'Cruse family and Jacky Lorenzetti',
 blend:{CS:60,ME:40}, perf:0.5,
 style:'A moated 17th-century château and one of Margaux’s prettiest wines — violets, red cherry and fine chalky tannin.'},

{id:'lagrange', name:'Château Lagrange', growth:3, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1360, lng:-0.7700, ha:118,
 second:'Les Fiefs de Lagrange', owner:'Suntory',
 blend:{CS:70,ME:25,PV:5}, perf:0.5,
 style:'Rescued from decline by Suntory in 1983 and impeccably run since. Dark, polished and dependable, with a sizeable Petit Verdot component.'},

{id:'langoa-barton', name:'Château Langoa-Barton', growth:3, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1560, lng:-0.7480, ha:20,
 second:'La Réserve de Léoville-Barton', owner:'Barton family',
 blend:{CS:70,ME:25,CF:5}, perf:0.5,
 style:'Léoville-Barton’s slightly lighter sibling, made in the same cellar — charming, cedary and almost always good value.'},

{id:'giscours', name:'Château Giscours', growth:3, cat:'red',
 appellation:'Margaux', commune:'Labarde', lat:45.0080, lng:-0.6680, ha:92,
 second:'La Sirène de Giscours', owner:'Albada Jelgersma estate',
 blend:{CS:60,ME:35,CF:3,PV:2}, perf:0.5,
 style:'The largest classified Margaux estate. Broad-shouldered and earthy rather than ethereal; strongly revived since the late 1990s.'},

{id:'malescot', name:'Château Malescot St. Exupéry', growth:3, cat:'red',
 appellation:'Margaux', commune:'Margaux', lat:45.0420, lng:-0.6770, ha:28,
 second:'La Dame de Malescot', owner:'Zuger family',
 blend:{CS:55,ME:35,CF:5,PV:5}, perf:0.5,
 style:'Intensely perfumed and firmly tannic — one of the most consistently exciting mid-tier Margaux since 1990.'},

{id:'boyd-cantenac', name:'Château Boyd-Cantenac', growth:3, cat:'red',
 appellation:'Margaux', commune:'Cantenac', lat:45.0260, lng:-0.6730, ha:17,
 second:'Jacques Boyd', owner:'Guillemet family',
 blend:{CS:65,ME:25,CF:5,PV:5}, perf:-0.5,
 style:'Tiny, traditional and old-school tannic; shares a winemaking team with neighbouring Pouget.'},

{id:'cantenac-brown', name:'Château Cantenac-Brown', growth:3, cat:'red',
 appellation:'Margaux', commune:'Cantenac', lat:45.0270, lng:-0.6780, ha:48,
 second:'BriO de Cantenac Brown', owner:'Le Lous family',
 blend:{CS:65,ME:32,CF:3}, perf:0.5,
 style:'A Tudor-style folly of a château. Once burly, now distinctly more refined, with a rammed-earth gravity cellar opened in 2023.'},

{id:'palmer', name:'Château Palmer', growth:3, cat:'red',
 appellation:'Margaux', commune:'Cantenac', lat:45.0330, lng:-0.6660, ha:66,
 second:'Alter Ego de Palmer', owner:'Mähler-Besse and Sichel families',
 blend:{CS:50,ME:45,PV:5}, perf:3,
 style:'The great overachiever of the 1855 list — routinely priced and scored at First Growth level. Unusually Merlot-rich for the Médoc, silky and intensely floral. Biodynamic since 2014.'},

{id:'la-lagune', name:'Château La Lagune', growth:3, cat:'red',
 appellation:'Haut-Médoc', commune:'Ludon-Médoc', lat:44.9600, lng:-0.6350, ha:80,
 second:'Moulin de La Lagune', owner:'Jean-Jacques Frey family',
 blend:{CS:60,ME:30,PV:10}, perf:0.5,
 style:'The southernmost classified estate, the first you meet driving out of Bordeaux. Elegant and spicy, with a notably high Petit Verdot share; biodynamic under Caroline Frey.'},

{id:'desmirail', name:'Château Desmirail', growth:3, cat:'red',
 appellation:'Margaux', commune:'Cantenac', lat:45.0280, lng:-0.6750, ha:40,
 second:'Initial de Desmirail', owner:'Denis Lurton',
 blend:{CS:60,ME:35,CF:5}, perf:-1,
 style:'Dismembered and reassembled over the 20th century; light, fresh and early-drinking, among the least ambitious of the Thirds.'},

{id:'calon-segur', name:'Château Calon-Ségur', growth:3, cat:'red',
 appellation:'Saint-Estèphe', commune:'Saint-Estèphe', lat:45.2740, lng:-0.7640, ha:55,
 second:'Le Marquis de Calon-Ségur', owner:'Suravenir Assurances',
 blend:{CS:65,ME:25,CF:8,PV:2}, perf:1,
 style:'The heart on the label recalls the Marquis de Ségur’s line about leaving his heart at Calon. Sweet-fruited and velvety for Saint-Estèphe; a marked quality leap since 2012.'},

{id:'ferriere', name:'Château Ferrière', growth:3, cat:'red',
 appellation:'Margaux', commune:'Margaux', lat:45.0405, lng:-0.6780, ha:24,
 second:'Les Remparts de Ferrière', owner:'Claire Villars Lurton',
 blend:{CS:70,ME:25,PV:5}, perf:0,
 style:'The smallest classified Margaux, biodynamic-certified. Fine-boned, mineral and increasingly well regarded.'},

{id:'marquis-dalesme', name:'Château Marquis d’Alesme', growth:3, cat:'red',
 appellation:'Margaux', commune:'Margaux', lat:45.0415, lng:-0.6765, ha:17,
 second:'—', owner:'Perrodo family',
 blend:{CS:55,ME:30,PV:10,CF:5}, perf:0,
 style:'Formerly Marquis d’Alesme Becker. A lavish new chai in 2012 and a heavy Petit Verdot hand have given the wine fresh ambition and a dark, spicy profile.'},

/* =========================== QUATRIÈMES CRUS =========================== */
{id:'saint-pierre', name:'Château Saint-Pierre', growth:4, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1470, lng:-0.7500, ha:17,
 second:'—', owner:'Triaud family',
 blend:{CS:75,ME:15,CF:10}, perf:0.5,
 style:'Small, rarely seen and consistently generous — rich, sweet-fruited Saint-Julien from old vines, made alongside Château Gloria.'},

{id:'talbot', name:'Château Talbot', growth:4, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1480, lng:-0.7600, ha:110,
 second:'Connétable Talbot', owner:'Bignon-Cordier family',
 blend:{CS:66,ME:26,PV:5,CF:3}, perf:0.5,
 style:'Large, inland and reliably sturdy; a touch rustic beside its neighbours but ages well. Also makes the white Caillou Blanc.'},

{id:'branaire-ducru', name:'Château Branaire-Ducru', growth:4, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1500, lng:-0.7400, ha:60,
 second:'Duluc de Branaire-Ducru', owner:'Maroteaux family',
 blend:{CS:65,ME:28,CF:4,PV:3}, perf:1,
 style:'Pure, chocolatey and immaculately balanced; one of the Médoc’s best quality-to-price propositions since the early 1990s.'},

{id:'duhart-milon', name:'Château Duhart-Milon', growth:4, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2340, lng:-0.7600, ha:76,
 second:'Moulin de Duhart', owner:'Domaines Barons de Rothschild (Lafite)',
 blend:{CS:70,ME:30}, perf:1,
 style:'Lafite’s neighbour and stablemate, and often a Lafite in miniature — graphite, cedar and restraint at a fraction of the price.'},

{id:'pouget', name:'Château Pouget', growth:4, cat:'red',
 appellation:'Margaux', commune:'Cantenac', lat:45.0255, lng:-0.6745, ha:10,
 second:'—', owner:'Guillemet family',
 blend:{CS:60,ME:30,CF:10}, perf:-1,
 style:'The smallest and least known of the classified Margaux; firm, old-fashioned and made together with Boyd-Cantenac.'},

{id:'la-tour-carnet', name:'Château La Tour Carnet', growth:4, cat:'red',
 appellation:'Haut-Médoc', commune:'Saint-Laurent-Médoc', lat:45.1180, lng:-0.8150, ha:119,
 second:'Les Douves de Carnet', owner:'Bernard Magrez',
 blend:{ME:62,CS:35,PV:2,CF:1}, perf:0,
 style:'A genuine moated medieval fortress, parts of it 12th-century. Modern, ripe and oak-framed under Magrez ownership.'},

{id:'lafon-rochet', name:'Château Lafon-Rochet', growth:4, cat:'red',
 appellation:'Saint-Estèphe', commune:'Saint-Estèphe', lat:45.2500, lng:-0.7620, ha:41,
 second:'Les Pèlerins de Lafon-Rochet', owner:'Lorenzetti family (since 2021)',
 blend:{CS:62,ME:33,CF:3,PV:2}, perf:0.5,
 style:'Unmistakable for its canary-yellow château. Sturdy, earthy Saint-Estèphe that has grown steadily more supple and polished.'},

{id:'beychevelle', name:'Château Beychevelle', growth:4, cat:'red',
 appellation:'Saint-Julien', commune:'Saint-Julien-Beychevelle', lat:45.1450, lng:-0.7390, ha:90,
 second:'Amiral de Beychevelle', owner:'Castel and Suntory',
 blend:{CS:62,ME:31,CF:5,PV:2}, perf:1,
 style:'The "dragon boat" label made it a phenomenon in Asia and prices run well ahead of its rank. Charming, rounded and gently cedary.'},

{id:'prieure-lichine', name:'Château Prieuré-Lichine', growth:4, cat:'red',
 appellation:'Margaux', commune:'Cantenac', lat:45.0240, lng:-0.6700, ha:70,
 second:'Confidences de Prieuré-Lichine', owner:'Ballande family',
 blend:{CS:55,ME:40,PV:5}, perf:0,
 style:'A former priory assembled plot by plot by Alexis Lichine. Supple, approachable Margaux spread across many small parcels.'},

{id:'marquis-de-terme', name:'Château Marquis de Terme', growth:4, cat:'red',
 appellation:'Margaux', commune:'Margaux', lat:45.0400, lng:-0.6800, ha:40,
 second:'Les Gondats de Marquis de Terme', owner:'Sénéclauze family',
 blend:{CS:55,ME:35,PV:7,CF:3}, perf:0,
 style:'Historically tough and tannic, considerably more refined and fruit-forward since around 2010.'},

/* =========================== CINQUIÈMES CRUS =========================== */
{id:'pontet-canet', name:'Château Pontet-Canet', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2225, lng:-0.7560, ha:81,
 second:'Les Hauts de Pontet-Canet', owner:'Tesseron family',
 blend:{CS:65,ME:30,CF:4,PV:1}, perf:2.5,
 style:'The most celebrated upgrade story in the Médoc — biodynamic since 2010, horse-ploughed, part-aged in amphora, and scoring at First Growth level. Dense, mineral and dramatic.'},

{id:'batailley', name:'Château Batailley', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.1920, lng:-0.7690, ha:57,
 second:'—', owner:'Castéja family (Borie-Manoux)',
 blend:{CS:70,ME:25,CF:3,PV:2}, perf:0.5,
 style:'Unfashionable, classical and consistently good value; pure cassis and pencil shavings with no modern makeup.'},

{id:'haut-batailley', name:'Château Haut-Batailley', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.1900, lng:-0.7700, ha:40,
 second:'Verso', owner:'Cazes family (since 2017)',
 blend:{CS:70,ME:25,CF:5}, perf:0.5,
 style:'Split from Batailley in 1942. Finer and more aromatic than its sibling; substantially replanted and re-equipped since the Cazes purchase.'},

{id:'grand-puy-lacoste', name:'Château Grand-Puy-Lacoste', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.1960, lng:-0.7720, ha:62,
 second:'Lacoste-Borie', owner:'Borie family',
 blend:{CS:75,ME:25}, perf:1.5,
 style:'Quintessential Pauillac and a connoisseur’s favourite — pure cassis, graphite and firm structure, built to age two decades without fuss.'},

{id:'grand-puy-ducasse', name:'Château Grand-Puy-Ducasse', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2030, lng:-0.7420, ha:40,
 second:'Prélude à Grand-Puy-Ducasse', owner:'Advini',
 blend:{CS:60,ME:40}, perf:0,
 style:'Scattered parcels and a chai on the Pauillac quayside. Medium-weight and straightforward, improving with recent investment.'},

{id:'lynch-bages', name:'Château Lynch-Bages', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2010, lng:-0.7560, ha:100,
 second:'Echo de Lynch-Bages', owner:'Cazes family',
 blend:{CS:75,ME:15,CF:8,PV:2}, perf:2,
 style:'Nicknamed the "poor man’s Mouton" for its exuberance. Rich, minty-cassis and crowd-pleasing, from a striking new cellar opened in 2020.'},

{id:'lynch-moussas', name:'Château Lynch-Moussas', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.1880, lng:-0.7900, ha:62,
 second:'—', owner:'Castéja family (Borie-Manoux)',
 blend:{CS:75,ME:25}, perf:-0.5,
 style:'Inland, wooded and quiet; lighter and leaner than most Pauillac, though steadily better since the 2000s.'},

{id:'dauzac', name:'Château Dauzac', growth:5, cat:'red',
 appellation:'Margaux', commune:'Labarde', lat:45.0000, lng:-0.6600, ha:49,
 second:'La Bastide Dauzac', owner:'Christian Roulleau',
 blend:{CS:60,ME:40}, perf:0,
 style:'Where Bordeaux mixture was invented in the 1880s. Solid, dark and fairly firm, with a clear lift in form over the last decade.'},

{id:'darmailhac', name:'Château d’Armailhac', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2230, lng:-0.7520, ha:70,
 second:'—', owner:'Baron Philippe de Rothschild SA',
 blend:{CS:55,ME:35,CF:8,PV:2}, perf:0.5,
 style:'Mouton’s neighbour and stablemate. Supple, red-fruited and comparatively forward, with unusually high Cabernet Franc.'},

{id:'du-tertre', name:'Château du Tertre', growth:5, cat:'red',
 appellation:'Margaux', commune:'Arsac', lat:45.0100, lng:-0.6900, ha:52,
 second:'Les Hauts du Tertre', owner:'Albada Jelgersma estate',
 blend:{CS:60,ME:20,CF:10,PV:10}, perf:0,
 style:'On a gravel knoll at Arsac, away from the river. Spicy and exotic, with a distinctive fifth of Cabernet Franc and Petit Verdot.'},

{id:'haut-bages-liberal', name:'Château Haut-Bages Libéral', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.1780, lng:-0.7480, ha:30,
 second:'La Chapelle de Bages', owner:'Claire Villars Lurton',
 blend:{CS:80,ME:20}, perf:0.5,
 style:'Parcels right beside Latour and Pichon Baron. Biodynamic, very high Cabernet, increasingly pure and energetic — a quiet bargain.'},

{id:'pedesclaux', name:'Château Pédesclaux', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2240, lng:-0.7480, ha:50,
 second:'Fleur de Pédesclaux', owner:'Jacky Lorenzetti',
 blend:{CS:55,ME:40,CF:3,PV:2}, perf:0.5,
 style:'Transformed since 2009 by a dramatic glass-clad rebuild and vineyard expansion; modern, deep and generously oaked.'},

{id:'belgrave', name:'Château Belgrave', growth:5, cat:'red',
 appellation:'Haut-Médoc', commune:'Saint-Laurent-Médoc', lat:45.1230, lng:-0.7900, ha:61,
 second:'Diane de Belgrave', owner:'Dourthe (CVBG)',
 blend:{CS:55,ME:40,CF:3,PV:2}, perf:0,
 style:'Just across the boundary from Saint-Julien, which it often resembles at a lower price. Clean, modern and fruit-driven.'},

{id:'de-camensac', name:'Château de Camensac', growth:5, cat:'red',
 appellation:'Haut-Médoc', commune:'Saint-Laurent-Médoc', lat:45.1200, lng:-0.7930, ha:75,
 second:'La Closerie de Camensac', owner:'Merlaut family',
 blend:{CS:60,ME:40}, perf:-0.5,
 style:'Sandy-gravel soils inland; medium-bodied, uncomplicated and among the most affordable of the classified growths.'},

{id:'cos-labory', name:'Château Cos Labory', growth:5, cat:'red',
 appellation:'Saint-Estèphe', commune:'Saint-Estèphe', lat:45.2450, lng:-0.7580, ha:18,
 second:'Le Charme Labory', owner:'Audoy family',
 blend:{CS:55,ME:35,CF:10}, perf:-0.5,
 style:'Cos d’Estournel’s small, traditional neighbour. Honest, firm, red-fruited Saint-Estèphe with no modern gloss.'},

{id:'clerc-milon', name:'Château Clerc Milon', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2320, lng:-0.7420, ha:41,
 second:'Pastourelle de Clerc Milon', owner:'Baron Philippe de Rothschild SA',
 blend:{CS:55,ME:35,CF:8,CA:1,PV:1}, perf:1,
 style:'The other Mouton stablemate, and the more serious of the two. Dense, spicy and mineral, with a rare dash of Carménère.'},

{id:'croizet-bages', name:'Château Croizet-Bages', growth:5, cat:'red',
 appellation:'Pauillac', commune:'Pauillac', lat:45.2000, lng:-0.7530, ha:30,
 second:'—', owner:'Quié family',
 blend:{CS:60,ME:35,CF:5}, perf:-1,
 style:'No château building and a long-standing reputation as the weakest classified Pauillac; light and simple, though slowly improving.'},

{id:'cantemerle', name:'Château Cantemerle', growth:5, cat:'red',
 appellation:'Haut-Médoc', commune:'Macau', lat:44.9430, lng:-0.6400, ha:92,
 second:'Les Allées de Cantemerle', owner:'SMABTP',
 blend:{CS:60,ME:30,CF:5,PV:5}, perf:0.5,
 style:'Added to the 1855 list only after the original printing. A wooded park, a cool site, and a fine, fragrant, often underrated wine.'}

]);
