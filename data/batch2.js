/* ===========================================================================
   Bordeaux Dashboard — research batch 2
   ---------------------------------------------------------------------------
   Estates for the fourteen appellations that were drawn on the map but had
   no châteaux in them. Same bar as batch 1: an estate appears only where a
   source covers BOTH its history and its terroir. Where sources disagree,
   the entry records the disagreement instead of choosing a side.

   Sources consulted: Decanter (Bourg & Blaye, Castillon, the Saint-Émilion
   satellites), The Wine Cellar Insider, The Wine Doctor, The Wine Society,
   Skurnik, the Saint-Émilion tourist board's producer files, Wine Folly's
   Bordeaux guides, guide-bordeaux-gironde.com, UGCB, Wikipedia (André
   Lurton, Blaye), and producers' own technical sheets via Bordeaux Tradition.
   =========================================================================== */

window.BDX_CHATEAUX = (window.BDX_CHATEAUX || []).concat([

/* ======================= LIBOURNAIS — CANON-FRONSAC ===================== */
{id:'moulin-pey-labrie', name:'Château Moulin Pey-Labrie', cls:'libournais', growth:2, cat:'red',
 appellation:'Canon-Fronsac', commune:'Fronsac', lat:44.948, lng:-0.300, ha:7,
 owner:'Hubau family', blend:{ME:95,MA:5},
 history:'Founded in 1988 by Bénédicte and Grégoire Hubau, neither of whom came to Bordeaux from wine. They brought in Michel Rolland to consult, and the estate became one of the names that re-established Canon-Fronsac — an appellation whose wines outsold Saint-Émilion and Pomerol well into the 1800s before phylloxera and a long decline.',
 terroir:'Clay and limestone on the slopes of the Canon plateau, with vines averaging close to sixty-five years. Unusually for this largely flat corner of the Right Bank, the vines run along limestone hillsides. Farmed organically and biodynamically.',
 sources:'The Wine Cellar Insider; Kermit Lynch',
 style:'Concentrated, mineral Canon-Fronsac from very old vines.'},

{id:'vrai-canon-bouche', name:'Château Vrai Canon Bouché', cls:'libournais', growth:2, cat:'red',
 appellation:'Canon-Fronsac', commune:'Fronsac', lat:44.951, lng:-0.294, ha:12,
 owner:'Absorbed into Château de La Dauphine', blend:{ME:60,CF:40},
 history:'Named for a former owner, Edgar Bouché. Held by the Roux family from 1953, bought by Philip Haseth-Møller in 2005, then sold to the Labrune family in 2020. 2021 was its final vintage: the vineyard has since been folded into Château de La Dauphine, so the label is now historic.',
 terroir:'Twelve hectares of clay and limestone at the peak of the Canon-Fronsac plateau.',
 sources:'The Wine Cellar Insider',
 style:'A label that no longer exists, but one worth knowing when a bottle turns up.'},

/* ===================== LIBOURNAIS — SAINT-ÉMILION SATELLITES ============ */
/* ============================ THE CÔTES ================================= */
{id:'roc-de-cambes', name:'Château Roc de Cambes', cls:'cotes', growth:1, cat:'red',
 appellation:'Côtes de Bourg', commune:'Bourg-sur-Gironde', lat:45.045, lng:-0.560, ha:12.5,
 owner:'Mitjavile family', blend:{ME:85,CS:15},
 history:'The estate of François Mitjavile, who also makes Le Tertre-Rôteboeuf in Saint-Émilion, and the wine that proved what Bourg could do. Farr Vintners calls it head and shoulders the best wine of the appellation.',
 terroir:'Twelve and a half hectares in a natural amphitheatre above the estuary, on clay-limestone with gravel over harder limestone — a profile not dissimilar to Tertre-Rôteboeuf’s. Many of the vines are close to fifty years old.',
 sources:'Decanter; Farr Vintners; Comptoir des Millésimes',
 style:'Made like a Saint-Émilion and priced like one, which in Bourg makes it an outlier.'},

{id:'monconseil-gazin', name:'Château Monconseil-Gazin', cls:'cotes', growth:2, cat:'red',
 appellation:'Blaye Côtes de Bordeaux', commune:'Plassac', lat:45.150, lng:-0.610, ha:44,
 owner:'Baudet family', blend:{ME:60,CS:30,MA:10},
 history:'The château dates from around 1500 and local legend ties the name to a council held by Charlemagne in the ninth century. Bought by the Baudet family in 1894; six hectares at Gazin were added in the 1950s, which gave the estate its present name, and later purchases brought it to forty-four.',
 terroir:'Twenty-four hectares of vines on gentle south-facing slopes of the limestone escarpment above Plassac, on well-draining clay-limestone that sends the roots deep. Close enough to the Gironde for the estuary to temper the climate.',
 sources:'The Wine Society; guide-bordeaux-gironde.com',
 style:'Merlot-led and ready sooner than neighbouring Bourg, as Blaye tends to be.'},

{id:'joanin-becot', name:'Château Joanin Bécot', cls:'cotes', growth:3, cat:'red',
 appellation:'Castillon Côtes de Bordeaux', commune:'Saint-Philippe-d’Aiguilhe', lat:44.872, lng:-0.030, ha:7,
 owner:'Juliette Bécot', blend:null,
 history:'The Castillon estate of Juliette Bécot of Château Beau-Séjour Bécot in Saint-Émilion. The appellation takes its name from Castillon-la-Bataille, where the battle of 1453 ended the Hundred Years’ War.',
 terroir:'The highest vineyards in all Castillon, on the same limestone plateau that continues into Saint-Émilion — the appellation rises through more than a hundred metres of elevation, and its soils are predominantly limestone and clay.',
 sources:'Decanter; The Wine Doctor; Borie-Manoux',
 style:'Castillon’s selling point is that the ground is Saint-Émilion’s; this is the case in point.'},

/* ============ GRAVES, ENTRE-DEUX-MERS & THE SWEET WHITES =============== */
{id:'chantegrive', name:'Château de Chantegrive', cls:'graves-doux', growth:1, cat:'red',
 appellation:'Graves', commune:'Podensac', lat:44.600, lng:-0.420, ha:90,
 owner:'Lévêque family', blend:null,
 history:'Begun in 1966, when Henri and Françoise Lévêque bought two hectares and started buying more. It is now about ninety hectares and among the largest and most prominent estates in Graves. Hubert de Boüard of Angélus has consulted since 2006, and the estate took High Environmental Value certification in 2017.',
 terroir:'Assembled parcel by parcel across the southern Graves communes of Cérons, Illats, Podensac and Virelade, on a mix of gravel, sand, limestone and small quartz stones.',
 sources:'The Wine Cellar Insider; UGCB; The Connected Table',
 style:'Red and white, and the estate that showed southern Graves could be built from scratch.'},

{id:'respide-medeville', name:'Château Respide-Médeville', cls:'graves-doux', growth:1, cat:'red',
 appellation:'Graves', commune:'Toulenne', lat:44.540, lng:-0.390, ha:12,
 owner:'Chatin family', blend:null,
 history:'An estate recorded from 1630, in the southern Graves near Langon. The Chatin family acquired it in 2021, choosing it for the quality of its ground.',
 terroir:'Gravelly soils that suit red and white alike — the gravel and pebbles that give the whole appellation its name and its minerality.',
 sources:'The Connected Table; The Wine Cellar Insider',
 style:'Small, serious, and made in both colours.'},

{id:'bonnet', name:'Château Bonnet', cls:'graves-doux', growth:3, cat:'white',
 appellation:'Entre-Deux-Mers', commune:'Grézillac', lat:44.820, lng:-0.200, ha:201,
 owner:'Vignobles André Lurton', blend:null,
 history:'Bought in 1897 by Léonce Récapet, who had a distillery in the Entre-Deux-Mers and spent the phylloxera years buying ruined vineyards and replanting them. It became the Lurton family’s headquarters in 1953, the year André Lurton inherited it; frost took the vines three years later and he rebuilt. As secretary then president of the appellation’s syndicat he drew up its specification for dry white wine with Émile Peynaud, and introduced a tasting examination as a condition of the appellation. Sources give the estate as 201 hectares or 135.',
 terroir:'Clay-limestone slopes and limestone plateaux between the Garonne and the Dordogne. Whites from Sauvignon, Sémillon, Colombard and Muscadelle; reds from Merlot and Cabernet Sauvignon.',
 sources:'Wikipedia (André Lurton); The Wine Cellar Insider; Wine Folly; andrelurton.com',
 style:'The estate that made Entre-Deux-Mers mean dry white wine worth drinking.'},

]);
