/* ===========================================================================
   Bordeaux Dashboard — research batch 3
   ---------------------------------------------------------------------------
   Depth for the appellations that batch 2 left with one or two estates. Same
   bar: an estate appears only where a source covers BOTH its history and its
   terroir, and conflicts between sources are recorded rather than resolved.

   Sources: The Wine Cellar Insider, The Wine Doctor, Decanter, Denis
   Dubourdieu Domaines, Dourthe, Grand Enclos du Château de Cérons, Grand
   Cercle des Vins de Bordeaux, the Syndicat des Côtes de Bourg, Wine Anorak,
   Château Turcaud, Château de Fontenille, Sommeliers International,
   Cazebonne, the Fronsadais tourist office, André Lurton and vins-saint-
   emilion.com.
   =========================================================================== */

window.BDX_CHATEAUX = (window.BDX_CHATEAUX || []).concat([

/* ================================ GRAVES =============================== */
{id:'clos-floridene', name:'Clos Floridène', cls:'graves-doux', growth:1, cat:'red',
 appellation:'Graves', commune:'Pujols-sur-Ciron', lat:44.570, lng:-0.400, ha:40,
 owner:'Denis Dubourdieu Domaines', blend:null,
 history:'Assembled from 1982 by Denis and Florence Dubourdieu, who named it by running their first names together. It began as two hectares of old Sémillon and Muscadelle and was enlarged decisively in 1991 by absorbing the neighbouring thirteen-hectare Château Montalivet. Their sons Jean-Jacques and Fabrice run it now.',
 terroir:'Mostly the limestone plateau of Pujols-sur-Ciron, close to Barsac, with further parcels on the pebbly terraces of Illats. Sources give the estate as 31, 40 or 41 hectares. Converting to organic, with HVE level 3.',
 sources:'Denis Dubourdieu Domaines; Wine Folly; Fareham Wine Cellar',
 style:'The red and white that showed what southern Graves limestone could do.'},

{id:'rahoul', name:'Château Rahoul', cls:'graves-doux', growth:1, cat:'red',
 appellation:'Graves', commune:'Portets', lat:44.612, lng:-0.478, ha:35,
 owner:'Dourthe', blend:null,
 history:'The chartreuse — the low country house that gives the estate its face — was built in the seventeenth century by the Chevalier Guillaume Rahoul, who gave it his name. Dourthe has managed the property since 2007.',
 terroir:'Sandy gravel and clay-gravel at Portets, thirty-one hectares in red and four in white.',
 sources:'Dourthe',
 style:'A long-standing Graves name, in both colours.'},

{id:'grand-enclos-cerons', name:'Grand Enclos du Château de Cérons', cls:'graves-doux', growth:1, cat:'red',
 appellation:'Graves', commune:'Cérons', lat:44.648, lng:-0.470, ha:30,
 owner:'Giorgio Cavanna', blend:null,
 history:'What is now the Grand Enclos was part of the Marquis de Calvimont’s estate until the national road from Bordeaux to Spain was driven through it and split the property in two. The Directoire residence dates from 1875. Giorgio Cavanna, formerly co-owner of Castello di Ama in Tuscany, has backed the estate since 2000.',
 terroir:'Pebbles, gravel and sandy deposits over limestone, both inside the walled enclos and on the Podensac plateau. Sources give the split as 9 hectares within the walls and 12 outside, or 10 and 20; the total is around thirty.',
 sources:'Grand Enclos du Château de Cérons; Grand Cercle des Vins de Bordeaux',
 style:'A walled vineyard, which in Bordeaux is rarer than it sounds.'},

/* =========================== ENTRE-DEUX-MERS =========================== */
{id:'turcaud', name:'Château Turcaud', cls:'graves-doux', growth:3, cat:'white',
 appellation:'Entre-Deux-Mers', commune:'La Sauve-Majeure', lat:44.770, lng:-0.250, ha:50,
 owner:'Robert family', blend:null,
 history:'Founded in 1973 by Maurice Robert and his wife Simone, and still in the family — one of the estates that gave Entre-Deux-Mers its reputation for dry white worth buying.',
 terroir:'Gentle slopes at about a hundred metres on silico-gravelly and clay soils, often loamy and frequently carrying gravel. Sources give 45 or 50 hectares.',
 sources:'Cazebonne; Château Turcaud',
 style:'Sauvignon-led white, and the benchmark for the appellation’s style.'},

{id:'marjosse', name:'Château Marjosse', cls:'graves-doux', growth:3, cat:'white',
 appellation:'Entre-Deux-Mers', commune:'Tizac-de-Curton', lat:44.800, lng:-0.230, ha:60,
 owner:'Pierre Lurton', blend:null,
 history:'Pierre Lurton — who also runs Château Cheval Blanc and Château d’Yquem — took over the management of Marjosse in 1990 and has made it his own estate ever since.',
 terroir:'Silty-clay ground known locally as boulbène, developed on ancient alluvium, with sand over clay and limestone on the slopes. Sources give 50 or 65 hectares.',
 sources:'The Wine Cellar Insider; Sommeliers International',
 style:'The private estate of the man who runs two of Bordeaux’s most famous.'},

{id:'fontenille', name:'Château de Fontenille', cls:'graves-doux', growth:3, cat:'white',
 appellation:'Entre-Deux-Mers', commune:'La Sauve-Majeure', lat:44.740, lng:-0.270, ha:63,
 owner:'Stéphane Defraine', blend:null,
 history:'The land belonged to the Benedictine Abbaye de la Sauve-Majeure, whose monks worked these vines for centuries before the estate passed into private hands.',
 terroir:'Sixty-seven separate plots across sixty-three hectares, on the silty, pebbly and clayey gravels typical of the Entre-Deux-Mers.',
 sources:'Château de Fontenille; Winebow',
 style:'Sixty-seven plots is not tidiness — it is what this country gives you.'},

/* ================================ CASTILLON ============================ */
{id:'daiguilhe', name:'Château d’Aiguilhe', cls:'cotes', growth:3, cat:'red',
 appellation:'Castillon Côtes de Bordeaux', commune:'Saint-Philippe-d’Aiguilhe', lat:44.862, lng:-0.040, ha:90,
 owner:'Comte Stephan von Neipperg', blend:null,
 history:'A thirteenth-century château bought by Stephan von Neipperg of Canon La Gaffelière, who turned it into the standard-setter for Castillon. The estate’s own account dates the purchase to late 1998; one guide says 1989.',
 terroir:'A hundred and forty hectares of which ninety are planted, entirely on the plateau: a thin layer of meagre clay-limestone topsoil over a limestone substratum, facing south and draining freely.',
 sources:'Neipperg estates; The Wine Cellar Insider; Wine Spectator',
 style:'The wine that proved Castillon’s limestone is Saint-Émilion’s limestone.'},

{id:'montlandrie', name:'Château Montlandrie', cls:'cotes', growth:3, cat:'red',
 appellation:'Castillon Côtes de Bordeaux', commune:'Saint-Magne-de-Castillon', lat:44.850, lng:-0.050, ha:15,
 owner:'Durantou family', blend:null,
 history:'Founded in the late 1800s by an Italian family, and bought in 2009 by Denis Durantou of Château L’Église-Clinet in Pomerol — the second of his projects outside the appellation that made him, alongside Les Cruzelles.',
 terroir:'Clay and limestone on the Castillon plateau.',
 sources:'The Wine Cellar Insider',
 style:'Durantou’s hand, on ground that costs a fraction of Pomerol.'},

{id:'clos-puy-arnaud', name:'Clos Puy Arnaud', cls:'cotes', growth:3, cat:'red',
 appellation:'Castillon Côtes de Bordeaux', commune:'Belvès-de-Castillon', lat:44.840, lng:-0.042, ha:12,
 owner:'Thierry Valette', blend:null,
 history:'Thierry Valette has been proprietor, grower and winemaker since 2000, and took the estate to biodynamics early — sources date the conversion to Demeter certification in 2005 or to fully biodynamic farming from 2008.',
 terroir:'About eighty-five per cent of the estate sits on the plateau, on a thin layer of the hardest limestone in the district, the calcaire à astéries.',
 sources:'The Wine Doctor; The Wine Cellar Insider',
 style:'Among the most serious biodynamic estates on the Right Bank.'},

/* ============================ CÔTES DE BOURG =========================== */
{id:'falfas', name:'Château Falfas', cls:'cotes', growth:1, cat:'red',
 appellation:'Côtes de Bourg', commune:'Bayon-sur-Gironde', lat:45.060, lng:-0.540, ha:22,
 owner:'Cochran-Bouchet family', blend:null,
 history:'Rebuilt in 1612 on foundations going back to the Hundred Years’ War. One of Bordeaux’s biodynamic pioneers — sources date the conversion to 1988 or 1989 — guided by François Bouchet, father of the late owner and one of the movement’s founding figures in France.',
 terroir:'Clay and silica over a deep limestone bedrock, on the right bank of the Gironde.',
 sources:'Wine Anorak; Beaune Imports',
 style:'Biodynamic in Bourg two decades before it was fashionable anywhere.'},

{id:'fougas', name:'Château Fougas', cls:'cotes', growth:1, cat:'red',
 appellation:'Côtes de Bourg', commune:'Lansac', lat:45.030, lng:-0.520, ha:16,
 owner:'Béchet family', blend:null,
 history:'The estate dates from 1778; its modern life began in 1976 when Yves and Michèle Béchet bought it. Farmed biodynamically since 2010 and certified in 2013. Its top wine is called Maldoror.',
 terroir:'A mix of sand, gravel and clay carrying iron deposits.',
 sources:'The Wine Cellar Insider',
 style:'Maldoror is the cuvée that put Fougas on lists outside France.'},

{id:'brulesecaille', name:'Château Brûlesécaille', cls:'cotes', growth:1, cat:'red',
 appellation:'Côtes de Bourg', commune:'Tauriac', lat:45.050, lng:-0.530, ha:28,
 owner:'Rodet-Récapet family', blend:null,
 history:'In the same family since 1924. Its old vines came through the frosts of 1945 and 1956, which killed so much of Bordeaux, and the estate has kept them.',
 terroir:'Twenty-eight hectares in a single unbroken block of clay-limestone and clay-gravel, ground the estate considers made for Merlot.',
 sources:'Syndicat des Côtes de Bourg',
 style:'One block, one family, a century.'},

/* ================================= BLAYE =============================== */
{id:'cailleteau-bergeron', name:'Château Cailleteau Bergeron', cls:'cotes', growth:2, cat:'red',
 appellation:'Blaye Côtes de Bordeaux', commune:'Mazion', lat:45.200, lng:-0.580, ha:35,
 owner:'Dartier family', blend:null,
 history:'Founded in 1933 by the Dartier family; the siblings Marie-Pierre and Pierre-Charles Dartier took it over in 1992.',
 terroir:'Limestone and sandy soils, close enough to the estuary for its breezes to matter. Merlot-led, with Cabernet Sauvignon, Malbec and Carménère, and Sauvignon for the whites.',
 sources:'Château Cailleteau Bergeron; Vinexposium',
 style:'Carménère in Blaye is a rarity worth noting.'},

{id:'haut-bertinerie', name:'Château Haut-Bertinerie', cls:'cotes', growth:2, cat:'red',
 appellation:'Blaye Côtes de Bordeaux', commune:'Cubnezais', lat:45.170, lng:-0.560, ha:78,
 owner:'Bantegnies family', blend:null,
 history:'The Bertinerie property has been in the same family for close to two centuries; Daniel Bantegnies took it on in 1961 and Eric and Frantz Bantegnies run it now. The estate planted Lyre-trained vines in 1987 — a divided canopy that opens the fruit to more light, which the family credits with riper, rounder tannins.',
 terroir:'Seventy-eight hectares on the clay-limestone and gravel of Blaye’s south-facing slopes.',
 sources:'Grand Cercle des Vins de Bordeaux; D.B. Wine Selection',
 style:'The Lyre trellis is the estate’s signature and is visible from the road.'},

{id:'les-jonqueyres', name:'Château Les Jonqueyres', cls:'cotes', growth:2, cat:'red',
 appellation:'Blaye Côtes de Bordeaux', commune:'Saint-Paul-de-Blaye', lat:45.230, lng:-0.600, ha:15,
 owner:'Montaut family', blend:null,
 history:'Pascal Montaut inherited five hectares of the family holding in 1982 and built it up to fifteen, making it one of the names that gave Blaye a reputation beyond bulk wine.',
 terroir:'Clay-limestone on the Blaye slopes, planted to ninety per cent Merlot.',
 sources:'Decanter; Wikipedia (Blaye)',
 style:'Small, Merlot-dominated, and built by one person.'},

/* ======================= LUSSAC-SAINT-ÉMILION ========================== */
/* ====================== MONTAGNE-SAINT-ÉMILION ========================= */
/* ============================= CANON-FRONSAC =========================== */
{id:'du-gaby', name:'Château du Gaby', cls:'libournais', growth:2, cat:'red',
 appellation:'Canon-Fronsac', commune:'Fronsac', lat:44.945, lng:-0.306, ha:16,
 owner:'Private ownership', blend:null,
 history:'Vines were first planted on Gaby’s hill in the 1600s and sources date the estate itself to 1660, though the building is eighteenth-century. It was called La Roche Gaby until 1999, and has been certified organic since 2018.',
 terroir:'Sixteen hectares of clay-limestone on steep hillsides rising to about seventy-five metres — the elevated limestone that separates the best Canon-Fronsac sites from the alluvial ground by the river.',
 sources:'The Wine Cellar Insider; vins-fronsac.com; Fronsadais tourist office',
 style:'One of the most striking vineyard sites on the Right Bank.'},

{id:'mazeris', name:'Château Mazeris', cls:'libournais', growth:2, cat:'red',
 appellation:'Canon-Fronsac', commune:'Saint-Michel-de-Fronsac', lat:44.952, lng:-0.302, ha:23,
 owner:'de Cournuaud family', blend:null,
 history:'A family estate passed down through ten generations at Saint-Michel-de-Fronsac.',
 terroir:'Most of the vineyard lies on the limestone plateau that defines Canon-Fronsac, on clay and limestone over the Eocene and Oligocene geology — calcaire à astéries and the molasses du Fronsadais.',
 sources:'Fronsadais tourist office',
 style:'Ten generations on the plateau.'}

]);
