/* ===========================================================================
   Bordeaux Dashboard — Fronsac & the Libournais satellites
   ---------------------------------------------------------------------------
   None of these appellations is classified. The groups are appellations, not
   ranks, and the dashboard says so on the collection card.

   RESEARCH BATCH 1. Every estate here was looked up, and only estates whose
   sources cover BOTH history and terroir are included. Where sources
   disagree, the entry says so rather than picking a side. Where an estate's
   encépagement was not stated, no blend is shown — an appellation average
   would not be that château's blend.

   Sources consulted for this batch: The Wine Doctor (Chris Kissack),
   Decanter regional profiles of Fronsac/Canon-Fronsac and the Saint-Émilion
   satellites, The Wine Cellar Insider appellation guides, Vinovest's
   Lalande-de-Pomerol guide, Hachette's producer entries and Skurnik's
   importer profile of La Vieille Cure.
   =========================================================================== */

window.BDX_CHATEAUX = (window.BDX_CHATEAUX || []).concat([

/* ------------------------------- FRONSAC ------------------------------- */
{id:'la-dauphine', name:'Château de La Dauphine', cls:'libournais', growth:1, cat:'red',
 appellation:'Fronsac', commune:'Fronsac', lat:44.970, lng:-0.300, ha:53,
 owner:'Labrune family', blend:null,
 history:'An estate recorded from 1670, with the château itself completed around 1750 and named for the Dauphine, wife of the heir to the French throne. The last descendant of the Olivier family sold it to Christian Moueix of Ets J-P Moueix in 1985, which began its modern revival; the Labrune family have owned it since 2015.',
 terroir:'Fifty-three hectares on the clay-limestone slopes that give Fronsac its structure, below the limestone plateau.',
 sources:'The Wine Doctor; Decanter',
 style:'One of the names that carried Fronsac back into serious company after the long decline.'},

{id:'villars', name:'Château Villars', cls:'libournais', growth:1, cat:'red',
 appellation:'Fronsac', commune:'Saillans', lat:44.962, lng:-0.312, ha:30,
 owner:'Gaudrie family', blend:null,
 history:'Jean-Claude Gaudrie at Villars was, with Jean-Noël Hervé at Moulin Haut-Laroque, one of the two growers whose work in the late 1970s began Fronsac’s renaissance — the first glimmer of a more motivated generation taking over the family domaines.',
 terroir:'About thirty hectares on hills and slopes of clay and limestone, planted mostly to Merlot.',
 sources:'Decanter; The Wine Doctor',
 style:'A family estate, and one of the appellation’s reference points for what Fronsac can do.'},

{id:'moulin-haut-laroque', name:'Château Moulin Haut-Laroque', cls:'libournais', growth:1, cat:'red',
 appellation:'Fronsac', commune:'Saillans', lat:44.958, lng:-0.296, ha:15,
 owner:'Hervé family', blend:null,
 history:'Jean-Noël Hervé is named alongside Jean-Claude Gaudrie of Villars as one of the two pioneers of the Fronsac revival that began in the late 1970s, after a century in which the region had chased quantity over quality.',
 terroir:'Clay-limestone on the Fronsac côtes — the slope soils that the appellation is built on.',
 sources:'Decanter',
 style:'Long regarded as one of the finest wines of the appellation.'},

{id:'fontenil', name:'Château Fontenil', cls:'libournais', growth:1, cat:'red',
 appellation:'Fronsac', commune:'Saillans', lat:44.966, lng:-0.306, ha:11,
 owner:'Michel and Dany Rolland', blend:null,
 history:'Bought by Michel and Dany Rolland in 1986 and, by one account, essentially created by them during the 1980s — the personal estate of the most travelled consulting oenologist in Bordeaux.',
 terroir:'Eleven hectares at high elevation on the Fronsac plateau, beside Dalem and Villars in what Decanter calls the appellation’s hotspot.',
 sources:'The Wine Doctor; Decanter',
 style:'Ripe and polished, as you would expect of the address.'},

{id:'dalem', name:'Château Dalem', cls:'libournais', growth:1, cat:'red',
 appellation:'Fronsac', commune:'Saillans', lat:44.970, lng:-0.316, ha:15,
 owner:'Rullier family', blend:null,
 history:'A long-established Saillans estate and one of the handful of names that carried Fronsac’s reputation through the twentieth century, in the cluster of leading properties around Fontenil and Villars.',
 terroir:'High ground at about 83 metres in Saillans, on the clay-limestone of the Fronsac plateau.',
 sources:'The Wine Doctor; Decanter',
 style:'Concentrated, firm Fronsac from one of its better-sited vineyards.'},

{id:'de-carles', name:'Château de Carles', cls:'libournais', growth:1, cat:'red',
 appellation:'Fronsac', commune:'Saillans', lat:44.974, lng:-0.300, ha:20,
 owner:'de Castaing family', second:'Haut-Carles (prestige cuvée)', blend:null,
 history:'In the de Castaing family since 1900. Haut-Carles, the estate’s prestige cuvée, was created to show what the best parcels could do and is now the better-known of the two wines.',
 terroir:'Soils of clay with limestone and silt, planted almost entirely to Merlot.',
 sources:'The Wine Doctor',
 style:'A medieval château with a modern gravity cellar behind it.'},

{id:'la-vieille-cure', name:'Château La Vieille Cure', cls:'libournais', growth:1, cat:'red',
 appellation:'Fronsac', commune:'Saillans', lat:44.954, lng:-0.322, ha:20,
 owner:'American private ownership', blend:null,
 history:'An old presbytery estate — the name means the old parish house — bought by American investors in 1986 and rebuilt over the following decades into one of the appellation’s most consistent performers.',
 terroir:'Twenty hectares on a clay-limestone bedrock, one source describing the soil as heavy on limestone. Merlot with Cabernet Sauvignon and Cabernet Franc.',
 sources:'The Wine Doctor; Skurnik',
 style:'Polished and reliable, and for years among the best value on the Right Bank.'},

/* -------------------------- LALANDE-DE-POMEROL ------------------------- */
{id:'les-cruzelles', name:'Château Les Cruzelles', cls:'libournais', growth:3, cat:'red',
 appellation:'Lalande-de-Pomerol', commune:'Néac', lat:44.972, lng:-0.188, ha:10,
 owner:'Durantou family', blend:{ME:88,CF:12},
 history:'A personal project of Denis Durantou, the winemaker at Château L’Église-Clinet in Pomerol, who set out to show what the Néac plateau could do in the right hands. It remains with his family after his death in 2020.',
 terroir:'Ten hectares of clay-gravel on the Néac plateau — soils described as virtually identical to those of the Pomerol plateau, which the Néac ground geologically continues.',
 sources:'Vinovest; Berry Bros. & Rudd; The Wine Doctor',
 style:'Pomerol in all but name, at a fraction of the price.'},

{id:'la-chenade', name:'La Chenade', cls:'libournais', growth:3, cat:'red',
 appellation:'Lalande-de-Pomerol', commune:'Néac', lat:44.966, lng:-0.196, ha:6,
 owner:'Durantou family', blend:null,
 history:'The second string of the Durantou family’s Lalande holdings, made alongside Les Cruzelles and released as the earlier-drinking of the two.',
 terroir:'Clay and gravel on the Néac side of the appellation, from parcels worked with the same hand as Les Cruzelles.',
 sources:'Vinovest; The Wine Doctor',
 style:'Built to be drunk young, and priced to be.'},

{id:'la-fleur-de-bouard', name:'Château La Fleur de Boüard', cls:'libournais', growth:3, cat:'red',
 appellation:'Lalande-de-Pomerol', commune:'Lalande-de-Pomerol', lat:44.980, lng:-0.200, ha:30,
 owner:'de Boüard de Laforest family', second:'Le Plus de La Fleur de Boüard', blend:null,
 history:'The Lalande estate of Hubert de Boüard of Château Angélus, and widely regarded as the leading property of the appellation. Its top cuvée, Le Plus, is made from old vines and is pure Merlot.',
 terroir:'About thirty hectares around the cellar, of which twenty-five are planted: seventeen on clay and deeper gravel on the Néac plateau, and eight on soils of pebbles and clay.',
 sources:'The Wine Doctor; Vinovest',
 style:'Ambitious, modern and the appellation’s most visible name.'},

{id:'siaurac', name:'Château Siaurac', cls:'libournais', growth:3, cat:'red',
 appellation:'Lalande-de-Pomerol', commune:'Néac', lat:44.962, lng:-0.178, ha:45,
 owner:'Ownership changed during the 2010s — sources disagree', blend:null,
 history:'Held by the Guichard family from 1832, one of the longest single tenures in the appellation. Ownership changed in the 2010s, but sources conflict on the buyer: one names Les Terroirs de Suravenir in 2020, another the owners of Château Latour in 2014. The dashboard records the disagreement rather than choosing.',
 terroir:'A large holding on the Néac side, where clay and gravel continue the geology of the Pomerol plateau across the Barbanne stream.',
 sources:'Hachette; The Wine Cellar Insider',
 style:'One of the appellation’s historic estates, with a park and a château to match.'},

/* ------------------------ SAINT-ÉMILION SATELLITES --------------------- */
]);
