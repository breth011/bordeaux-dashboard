/* ===========================================================================
   Bordeaux Dashboard — Crus Classés de Graves (1953, finalised 1959)
   16 estates, all now within the Pessac-Léognan appellation created in 1987.
   ---------------------------------------------------------------------------
   The list has no internal hierarchy: an estate is classified for its red,
   for its white, or for both. `wine` records which.
   Château Haut-Brion appears here as well as in the 1855 classification —
   the only estate in Bordeaux classified under two separate systems. It is
   carried once, under 1855, and cross-referenced here.
   =========================================================================== */

window.BDX_CHATEAUX = (window.BDX_CHATEAUX || []).concat([

{id:'la-mission-haut-brion', name:'Château La Mission Haut-Brion', cls:'graves', growth:1, cat:'red',
 wine:'red', appellation:'Pessac-Léognan', commune:'Talence', lat:44.8010, lng:-0.6050, ha:29,
 second:'La Chapelle de La Mission Haut-Brion', owner:'Domaine Clarence Dillon',
 blend:{ME:45,CS:45,CF:10}, perf:2.5,
 style:'Haut-Brion’s neighbour across the road, and its historic rival — in many vintages the darker, smokier, more powerful of the two. Under the same ownership since 1983.'},

{id:'pape-clement', name:'Château Pape Clément', cls:'graves', growth:1, cat:'red',
 wine:'red and white', appellation:'Pessac-Léognan', commune:'Pessac', lat:44.8085, lng:-0.6330, ha:60,
 second:'Le Clémentin de Pape Clément', owner:'Bernard Magrez',
 blend:{CS:50,ME:45,CF:3,PV:2}, perf:1,
 style:'Planted in 1300 by Bertrand de Goth, later Pope Clement V — among the oldest continuously worked vineyards in Bordeaux, now surrounded by Pessac suburbia. Opulent and heavily oaked under Magrez.'},

{id:'haut-bailly', name:'Château Haut-Bailly', cls:'graves', growth:1, cat:'red',
 wine:'red', appellation:'Pessac-Léognan', commune:'Léognan', lat:44.7290, lng:-0.5790, ha:33,
 second:'La Parde de Haut-Bailly', owner:'Robert G. Wilmers family',
 blend:{CS:60,ME:35,CF:5}, perf:2,
 style:'A four-hectare parcel of ungrafted, pre-phylloxera mixed old vines sits at its heart. The most elegant and consistently fine red in Pessac-Léognan after the Haut-Brion pair — silky, restrained and ageless.'},

{id:'smith-haut-lafitte', name:'Château Smith Haut Lafitte', cls:'graves', growth:1, cat:'red',
 wine:'red and white', appellation:'Pessac-Léognan', commune:'Martillac', lat:44.7180, lng:-0.5660, ha:78,
 second:'Les Hauts de Smith', owner:'Daniel and Florence Cathiard',
 blend:{CS:60,ME:34,CF:4,PV:2}, perf:1.5,
 style:'Transformed since 1990 by the Cathiards, with its own cooperage, a vinothérapie spa and Les Sources de Caudalie next door. The red is dense and polished; the white is among the finest in Bordeaux.'},

{id:'domaine-de-chevalier', name:'Domaine de Chevalier', cls:'graves', growth:1, cat:'red',
 wine:'red and white', appellation:'Pessac-Léognan', commune:'Léognan', lat:44.6980, lng:-0.6080, ha:65,
 second:'L’Esprit de Chevalier', owner:'Bernard family',
 blend:{CS:65,ME:30,CF:3,PV:2}, perf:1.5,
 style:'A clearing in the pine forest, cool and frost-prone, which gives a red of unusual freshness and length. The white — barely 5 hectares of it — is one of the half-dozen greatest dry whites in France.'},

{id:'de-fieuzal', name:'Château de Fieuzal', cls:'graves', growth:1, cat:'red',
 wine:'red', appellation:'Pessac-Léognan', commune:'Léognan', lat:44.7120, lng:-0.5920, ha:80,
 second:'L’Abeille de Fieuzal', owner:'Lochlann Quinn',
 blend:{CS:55,ME:40,CF:3,PV:2}, perf:0.5,
 style:'Classified for its red, though its unclassified white has long been the more admired wine. Substantial investment since the Quinn purchase in 2001.'},

{id:'malartic-lagraviere', name:'Château Malartic-Lagravière', cls:'graves', growth:1, cat:'red',
 wine:'red and white', appellation:'Pessac-Léognan', commune:'Léognan', lat:44.7050, lng:-0.5970, ha:53,
 second:'Le Sillage de Malartic', owner:'Bonnie family',
 blend:{CS:50,ME:43,CF:4,PV:3}, perf:1,
 style:'Rebuilt from the ground up by the Bonnie family after 1997. Precise, mineral and modern in both colours; the white is nearly pure Sauvignon Blanc.'},

{id:'carbonnieux', name:'Château Carbonnieux', cls:'graves', growth:1, cat:'red',
 wine:'red and white', appellation:'Pessac-Léognan', commune:'Léognan', lat:44.7250, lng:-0.5880, ha:92,
 second:'La Croix de Carbonnieux', owner:'Perrin family',
 blend:{CS:60,ME:30,CF:7,PV:3}, perf:0,
 style:'One of the largest estates in the appellation, monastic in origin. Reliable rather than thrilling in red; the white, half Sauvignon and half Sémillon, is the better-known wine.'},

{id:'olivier', name:'Château Olivier', cls:'graves', growth:1, cat:'red',
 wine:'red and white', appellation:'Pessac-Léognan', commune:'Léognan', lat:44.7210, lng:-0.5930, ha:62,
 second:'La Seigneurie d’Olivier', owner:'de Bethmann family',
 blend:{CS:50,ME:45,CF:3,PV:2}, perf:0,
 style:'A moated medieval castle in a wooded park. Long an underperformer, markedly better since a thorough replanting and a new cellar after 2010.'},

{id:'bouscaut', name:'Château Bouscaut', cls:'graves', growth:1, cat:'red',
 wine:'red and white', appellation:'Pessac-Léognan', commune:'Cadaujac', lat:44.7450, lng:-0.5750, ha:50,
 second:'Les Chênes de Bouscaut', owner:'Lurton family (Sophie Lurton)',
 blend:{ME:55,CS:40,PV:5}, perf:-0.5,
 style:'Unusually Merlot-led for the appellation, on heavier clay-gravel soils. Solid and supple; the Sémillon-dominated white is the more distinctive wine.'},

{id:'latour-martillac', name:'Château Latour-Martillac', cls:'graves', growth:1, cat:'red',
 wine:'red and white', appellation:'Pessac-Léognan', commune:'Martillac', lat:44.7020, lng:-0.5520, ha:45,
 second:'Lagrave-Martillac', owner:'Kressmann family',
 blend:{CS:55,ME:40,PV:5}, perf:0.5,
 style:'The southernmost classified growth, named for a tower built from the ruins of a 12th-century fort. Quietly consistent and among the better-value classed Graves.'},

{id:'couhins', name:'Château Couhins', cls:'graves', growth:1, cat:'white',
 wine:'white', appellation:'Pessac-Léognan', commune:'Villenave-d’Ornon', lat:44.7390, lng:-0.5820, ha:25,
 second:'—', owner:'INRAE (French agricultural research institute)',
 blend:{SB:100}, perf:0,
 style:'Classified for its white alone and owned by the national agricultural research institute, which uses it as an experimental estate. Pure Sauvignon Blanc, crisp and varietal.'},

{id:'couhins-lurton', name:'Château Couhins-Lurton', cls:'graves', growth:1, cat:'white',
 wine:'white', appellation:'Pessac-Léognan', commune:'Villenave-d’Ornon', lat:44.7380, lng:-0.5830, ha:26,
 second:'—', owner:'Jacques Lurton',
 blend:{SB:100}, perf:0.5,
 style:'Split from Couhins in 1967 and classified separately for white. Barrel-fermented pure Sauvignon Blanc of real concentration and ageing capacity.'},

{id:'laville-haut-brion', name:'Château Laville Haut-Brion', cls:'graves', growth:1, cat:'white',
 wine:'white', appellation:'Pessac-Léognan', commune:'Talence', lat:44.8012, lng:-0.6048, ha:3.7,
 second:'—', owner:'Domaine Clarence Dillon',
 blend:{SEM:70,SB:30}, perf:1.5,
 style:'For decades one of the greatest white wines in the world — Sémillon-dominated, waxy and extraordinarily long-lived. From the 2009 vintage the wine has been sold as the white of La Mission Haut-Brion, so the Laville label is now historic.'},

{id:'la-tour-haut-brion', name:'Château La Tour Haut-Brion', cls:'graves', growth:1, cat:'red',
 wine:'red', appellation:'Pessac-Léognan', commune:'Talence', lat:44.8000, lng:-0.6040, ha:4.9,
 second:'—', owner:'Domaine Clarence Dillon',
 blend:{CS:45,ME:40,CF:15}, perf:0,
 style:'Historically the second wine of La Mission and then a classified growth in its own right — dark, tannic and austere. The last vintage was 2005; the parcels were absorbed into La Mission Haut-Brion, so the label is now historic.'}

]);

/* Château Haut-Brion is classified in BOTH the 1855 list and the 1959 Graves
   list (red 1953, white added 1960). It is stored once under '1855'; app.js
   cross-lists it into the Graves collection so neither list is incomplete. */
window.BDX_GRAVES_CROSSLIST = ['haut-brion'];
