/* ===========================================================================
   Bordeaux Dashboard — Classement de Saint-Émilion 2022
   85 estates: 2 Premiers Grands Crus Classés A, 12 Premiers Grands Crus
   Classés B, 71 Grands Crus Classés. Approved by the INAO on 8 September
   2022 and valid through the 2031 harvest.
   ---------------------------------------------------------------------------
   The 14 top estates carry full records. The 71 Grands Crus Classés carry
   verified name and rank; their blends fall back to the Saint-Émilion
   appellation norm and their map positions are scattered within the commune,
   both of which the dashboard flags.
   =========================================================================== */

/* ------------------ PREMIERS GRANDS CRUS CLASSÉS A (2) ------------------ */
window.BDX_CHATEAUX = (window.BDX_CHATEAUX || []).concat([

{id:'pavie', name:'Château Pavie', cls:'stem', growth:1, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8885, lng:-0.1480, ha:37,
 second:'Arômes de Pavie', owner:'Gérard and Chantal Perse',
 blend:{ME:60,CF:30,CS:10}, perf:0,
 style:'A south-facing amphitheatre of limestone and clay on the côte. Bought by Gérard Perse in 1998 and made in a deliberately powerful, concentrated style that divided critics for a decade; time has largely vindicated it, and promotion to the top rank followed in 2012.'},

{id:'figeac', name:'Château Figeac', cls:'stem', growth:1, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.9000, lng:-0.1900, ha:54,
 second:'Petit-Figeac', owner:'Manoncourt family',
 blend:{CS:35,CF:35,ME:30}, perf:0,
 style:'The great outlier of the Right Bank — three gravel rises give it a third Cabernet Sauvignon, far more than any neighbour, and a cool, cedary, almost Médocain profile. Promoted to Premier Grand Cru Classé A in 2022 after decades of campaigning.'},

/* ------------------ PREMIERS GRANDS CRUS CLASSÉS B (12) ----------------- */
{id:'beau-sejour-becot', name:'Château Beau-Séjour Bécot', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8955, lng:-0.1620, ha:16.5,
 second:'Tournelle de Beau-Séjour Bécot', owner:'Bécot family',
 blend:{ME:70,CF:24,CS:6}, perf:0,
 style:'On the limestone plateau west of the town, with cellars quarried out of the rock beneath. Demoted in 1986 and restored in 1996; polished, generous and reliably fine since.'},

{id:'beausejour-duffau', name:'Château Beauséjour (Héritiers Duffau-Lagarrosse)', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8950, lng:-0.1635, ha:6.8,
 second:'Croix de Beauséjour', owner:'Joséphine Duffau-Lagarrosse and Groupe Pichet',
 blend:{ME:70,CF:30}, perf:0.5,
 style:'Tiny, steeply sloped and held by one family from 1847 until 2021. The 1990 is among the legendary bottles of the appellation. Nicolas Thienpont’s long stewardship gave it precision rather than weight.'},

{id:'belair-monange', name:'Château Bélair-Monange', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8930, lng:-0.1615, ha:23.5,
 second:'—', owner:'Établissements Jean-Pierre Moueix',
 blend:{ME:90,CF:10}, perf:1,
 style:'Bought by Moueix in 2008, renamed, and transformed. Pure limestone-plateau Merlot of great finesse — chalky, floral and increasingly regarded as among the very best wines in Saint-Émilion.'},

{id:'canon', name:'Château Canon', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8940, lng:-0.1600, ha:34,
 second:'Croix Canon', owner:'Chanel (Wertheimer family)',
 blend:{ME:70,CF:30}, perf:1.5,
 style:'A walled vineyard on the plateau with vast underground quarries. Chanel bought it in 1996 and spent two decades replanting; under Nicolas Audebert it now makes some of the most elegant, chalk-driven wine on the Right Bank.'},

{id:'canon-la-gaffeliere', name:'Château Canon La Gaffelière', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8880, lng:-0.1555, ha:19.5,
 second:'Côte Mignon-La Gaffelière', owner:'Comte Stephan von Neipperg',
 blend:{ME:55,CF:40,CS:5}, perf:1,
 style:'At the foot of the côte on sandy clay, farmed organically since 2014. An unusually high Cabernet Franc share gives lift and spice against ripe Merlot flesh.'},

{id:'larcis-ducasse', name:'Château Larcis Ducasse', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Laurent-des-Combes', lat:44.8855, lng:-0.1390, ha:11,
 second:'Murmure de Larcis Ducasse', owner:'Gratiot-Alphandéry family',
 blend:{ME:78,CF:22}, perf:0.5,
 style:'The direct eastern continuation of the Pavie slope, and long underperforming it. Nicolas Thienpont and Stéphane Derenoncourt took over in 2002 and the wine has been transformed — mineral, tense and finely drawn.'},

{id:'pavie-macquin', name:'Château Pavie Macquin', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8905, lng:-0.1470, ha:15,
 second:'Les Chênes de Macquin', owner:'Corre-Macquin family',
 blend:{ME:80,CF:18,CS:2}, perf:1,
 style:'Named for Albert Macquin, who pioneered grafting onto American rootstock after phylloxera. On the plateau edge above Pavie; firm, structured and distinctly mineral.'},

{id:'troplong-mondot', name:'Château Troplong Mondot', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8880, lng:-0.1430, ha:33,
 second:'Mondot', owner:'SCOR',
 blend:{ME:85,CS:10,CF:5}, perf:0.5,
 style:'The highest point in Saint-Émilion, crowned by a restaurant with a view over the whole Libournais. Once opulent and high in alcohol, markedly fresher and more restrained since 2017.'},

{id:'trotte-vieille', name:'Château Trotte Vieille', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8955, lng:-0.1420, ha:10,
 second:'La Vieille Dame de Trottevieille', owner:'Castéja family (Borie-Manoux)',
 blend:{ME:50,CF:45,CS:5}, perf:0,
 style:'Holds a parcel of ungrafted, pre-phylloxera Cabernet Franc — a genuine rarity in Bordeaux. On the eastern plateau; aromatic and increasingly fine since a sharp upturn in the mid-2000s.'},

{id:'valandraud', name:'Château Valandraud', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8985, lng:-0.1300, ha:9,
 second:'Virginie de Valandraud', owner:'Jean-Luc Thunevin and Murielle Andraud',
 blend:{ME:70,CF:25,CS:5}, perf:0.5,
 style:'The original garage wine. Made from 1991 in a lock-up from unregarded parcels, priced beyond the First Growths, and a scandal for a decade — then classified Premier Grand Cru Classé B in 2012. Dense, lavish and extremely well made.'},

{id:'clos-fourtet', name:'Clos Fourtet', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Émilion', lat:44.8955, lng:-0.1585, ha:17,
 second:'La Closerie de Fourtet', owner:'Cuvelier family',
 blend:{ME:85,CF:10,CS:5}, perf:0.5,
 style:'Directly facing the church at the gates of the town, above 13 hectares of quarried cellars. Pure limestone-plateau fruit — chalky, fine-boned and long.'},

{id:'la-mondotte', name:'La Mondotte', cls:'stem', growth:2, cat:'red',
 appellation:'Saint-Émilion', commune:'Saint-Laurent-des-Combes', lat:44.8895, lng:-0.1440, ha:4.5,
 second:'—', owner:'Comte Stephan von Neipperg',
 blend:{ME:75,CF:25}, perf:1,
 style:'Refused permission to be folded into Canon La Gaffelière in 1996, so von Neipperg bottled it separately out of spite — and made one of the most concentrated wines in Bordeaux. Classified in its own right in 2012.'}

]);

/* ---------------------- GRANDS CRUS CLASSÉS (71) ----------------------- */
/* Verified names and rank from the 2022 classification. Blends fall back to
   the appellation norm; positions are scattered within the commune.        */
window.BDX_STEM_GCC = [
'Château Badette','Château Balestard La Tonnelle','Château Barde-Haut',
'Château Bellefont-Belcier','Château Bellevue','Château Berliquet',
'Château Boutisse','Château Cadet-Bon','Château Cap de Mourlin',
'Château Chauvin','Clos Badon Thunevin','Clos de Sarpe','Clos des Jacobins',
'Clos Dubreuil','Clos de l’Oratoire','Clos Saint-Julien','Clos Saint-Martin',
'Château Corbin','Château Corbin Michotte','Château Côte de Baleau',
'Couvent des Jacobins','Château Croix de Labrie','Château Dassault',
'Château de Ferrand','Château de Pressac','Château Destieux',
'Château Faugères','Château Fleur Cardinale','Château Fombrauge',
'Château Fonplégade','Château Fonroque','Château Franc Mayne',
'Château Grand Corbin','Château Grand Corbin-Despagne','Château Grand Mayne',
'Château Guadet','Château Haut-Sarpe','Château Jean Faure',
'Château La Commanderie','Château La Confession','Château La Couspaude',
'Château La Croizille','Château La Dominique','Château La Fleur Morange',
'Château La Marzelle','Château La Serre','Château La Tour Figeac',
'Château Laniote','Château Larmande','Château Laroque','Château Laroze',
'Château Lassègue','Château Le Châtelet','Château Le Prieuré',
'Château Mangot','Château Monbousquet','Château Montlabert',
'Château Montlisse','Château Moulin du Cadet','Château Peby Faugères',
'Château Petit Faurie de Soutard','Château Ripeau','Château Rochebelle',
'Château Rol Valentin','Château Saint-Georges Côte Pavie','Château Sansonnet',
'Château Soutard','Château Tour Baladoz','Château Tour Saint Christophe',
'Château Villemaurine','Château Yon-Figeac'
];
