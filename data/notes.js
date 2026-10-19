/* ===========================================================================
   Bordeaux Dashboard — appellation and classification notes
   ---------------------------------------------------------------------------
   Two records, written to the same bar as the estate entries: an appellation
   gets an entry only where sources cover its history and its ground, and
   where sources disagree the entry says so instead of picking a side.

   Appellation notes are keyed by the map region id, so the twenty shapes on
   the map and the twenty pages here are the same twenty things. Sauternes
   and Barsac share a region because they share a hillside and a grower may
   label a Barsac wine as either.

   Sources are named per entry. The recurring ones: INAO, Decanter, The Wine
   Cellar Insider, Wine With Seth, Wikipedia, the Conseil des Grands Crus
   Classés en 1855, Wine Spectator, Vinorandum, bordeaux.com, Gilbert &
   Gaillard, glossary.wein.plus, Berry Bros. & Rudd and the appellation
   syndicates' own pages.
   =========================================================================== */

window.BDX_APPELLATION_NOTES = {

/* ============================== THE MÉDOC ============================== */
'medoc': {
  card:
    'Heavier, cooler ground than the communes upstream, so Merlot '
    + 'leads where Cabernet leads further south. No estate here was '
    + 'classified in 1855.',
  history:
    'Created by the decree of 1936 that drew the Médoc appellations in one '
    + 'stroke, and covering the northern third of the peninsula — the part '
    + 'still called the Bas-Médoc, where "bas" means downstream rather than '
    + 'lesser. Roughly 5,700 hectares across sixteen communes. No estate here '
    + 'was classified in 1855: the brokers who drew that list worked from the '
    + 'prices of the day, and the prices of the day were made further south.',
  terroir:
    'Further from the estuary and off the deep gravel banks that define the '
    + 'communes upstream. The ground is heavier and cooler, with more clay '
    + 'and limestone, so Merlot ripens where Cabernet Sauvignon would '
    + 'struggle — the reverse of the balance in the Haut-Médoc.',
  wines:
    'Merlot-led and earlier to drink than the classified Médoc, and made as '
    + 'much by independent growers and co-operatives as by châteaux. This is '
    + 'where the Crus Bourgeois and Crus Artisans are thickest on the ground.',
  sources: 'Wikipedia (Médoc AOC); Wine With Seth; INAO'
},

'haut-medoc': {
  card:
    'What is left between the six famous communes, and the home of '
    + 'five 1855 classified growths and the thickest concentration of '
    + 'Crus Bourgeois.',
  history:
    'The southern two-thirds of the peninsula, from the edge of Blanquefort '
    + 'up to Saint-Seurin-de-Cadourne, created by the same 1936 decree as the '
    + 'Médoc. The six communal appellations — Saint-Estèphe, Pauillac, '
    + 'Saint-Julien, Listrac, Moulis and Margaux — are cut out of it, so what '
    + 'carries the Haut-Médoc name is what is left between them. The '
    + 'boundaries were not settled at once: first delimited between 1940 and '
    + '1943, then revised between 1979 and 1985.',
  terroir:
    'Gravelly sand and clay, with bands of clay-limestone, on the long '
    + 'terraces the Garonne and the Gironde laid down. Well enough drained '
    + 'for Cabernet Sauvignon to lead most blends.',
  wines:
    'Five of the 1855 classified growths stand in the Haut-Médoc rather than '
    + 'in a commune of their own. They are La Lagune, La Tour Carnet, '
    + 'Belgrave, Camensac and Cantemerle, and around them lies the deepest '
    + 'concentration of Crus Bourgeois anywhere in Bordeaux.',
  sources: 'Wikipedia (Haut-Médoc AOC); INAO; Wine With Seth'
},

'saint-estephe': {
  card:
    'More clay through the gravel than its neighbours, so the ground '
    + 'drains slowly: the firmest and slowest-maturing wines of the '
    + 'Médoc.',
  history:
    'Recognised by decree on 14 November 1936, for red wine only, from the '
    + 'single commune of Saint-Estèphe. Vines go back to the Roman period; '
    + 'the shape of the modern vineyard owes most to the seventeenth century, '
    + 'when Dutch engineers drained the marshland and opened ground that had '
    + 'been unusable.',
  terroir:
    'The same Garonne gravel ridges as its neighbours, but with noticeably '
    + 'more clay mixed through them, over a base of limestone and marl. Water '
    + 'drains more slowly here than in Pauillac or Saint-Julien, which is a '
    + 'liability in a wet year and an asset in a drought.',
  wines:
    'The firmest and most tannic of the Médoc communes, and the slowest to '
    + 'come round. The northernmost classified growth in the Médoc, '
    + 'Calon-Ségur, is here; so are Cos d’Estournel and Montrose.',
  sources: 'Wine With Seth; Vins et Millésimes; Decanter'
},

'pauillac': {
  card:
    'Deep gravel laid down over four glaciations, and three of the '
    + 'five First Growths. Cassis, cedar and graphite, built to take '
    + 'decades.',
  history:
    'The commune that holds three of the five First Growths — Lafite, Latour '
    + 'and Mouton Rothschild — and the only one that does. Its port on the '
    + 'estuary mattered before its wine did: Pauillac was the deep-water stop '
    + 'where ocean-going ships transferred cargo for Bordeaux.',
  terroir:
    'Four main soil types, laid down in different glaciations, all of them '
    + 'strongly gravelly, which is why Cabernet Sauvignon does what it does '
    + 'here. The gravel differs bank by bank: Latour sits on Mindel II '
    + 'gravel, Lafite on Mindel I. Inland the soils carry more sand and the '
    + 'wines are lighter for it.',
  wines:
    'Cassis, cedar and graphite, with the structure to take decades. The '
    + 'benchmark against which Cabernet Sauvignon is measured anywhere.',
  sources: 'Decanter; Vinorandum; Millésima'
},

'saint-julien': {
  card:
    'Eleven classified growths on some 910 hectares of gravel plateau '
    + '— Margaux’s perfume with Pauillac’s frame, and the most '
    + 'consistent of the four.',
  history:
    'The smallest of the four great Médoc communes and the most tightly '
    + 'classified: eleven of its estates are 1855 growths — five Seconds, two '
    + 'Thirds and four Fourths, with no First and no Fifth — and they account '
    + 'for something close to 95% of roughly 910 hectares. Much of that land '
    + 'was bought and built on by Bordeaux merchants in the sixteenth and '
    + 'seventeenth centuries, once the marshes had been drained. The original '
    + 'Léoville estate was broken up at the Revolution and split again in '
    + '1840, which is why three Léovilles stand side by side today.',
  terroir:
    'Two well-drained gravel plateaux. The ridge along the estuary carries '
    + 'deep gravel and most of the Second Growths; further south the gravel '
    + 'thins over limestone, which is often credited for the commune’s '
    + 'finesse.',
  wines:
    'The middle ground between Margaux’s perfume and Pauillac’s power, '
    + 'and remarkably consistent for it. Léoville Las Cases and '
    + 'Ducru-Beaucaillou are the usual candidates for first-growth standing.',
  sources: 'Wikipedia (Saint-Julien AOC); Decanter; Wine With Seth'
},

'listrac': {
  card:
    'The highest ground in the Médoc, on a limestone plateau between '
    + 'two gravel ridges, and the one commune where Merlot takes the '
    + 'lead.',
  history:
    'Recognised by decree in 1957, which makes it the youngest of the six '
    + 'communal appellations of the Médoc. Sources put it at between 570 and '
    + '787 hectares, which is a wide enough spread to be worth stating as a '
    + 'range rather than a figure. It holds no 1855 growths; its best estates '
    + 'carry Cru Bourgeois Supérieur.',
  terroir:
    'The highest ground in the Médoc — the Fourcas plateau reaches somewhere '
    + 'between 43 and 50 metres depending on who is measuring — and the most '
    + 'mixed. Narrow streaks of gravel are separated by limestone and clay, '
    + 'with Pyrenean gravel to the west and Garonne gravel to the east of a '
    + 'central limestone plateau.',
  wines:
    'The one Médoc appellation where Merlot takes a defining role, because '
    + 'the clay and limestone suit it better than Cabernet. There is also a '
    + 'long local history of white vines, planted on some estates from the '
    + 'closing years of the nineteenth century.',
  sources: 'Wine With Seth; The Wine Doctor; Baur au Lac Vins'
},

'moulis': {
  card:
    'The smallest communal appellation: deep gravel at its eastern '
    + 'end against Margaux, clay and limestone inland.',
  history:
    'The smallest communal appellation in the Médoc at roughly 600 to 634 '
    + 'hectares, and by one account the oldest, with its AOC dated to 1938. '
    + 'Vines were established here in the Middle Ages, and the '
    + 'nineteenth-century vineyard was about twice the size of today’s. Like '
    + 'Listrac it has no 1855 growths.',
  terroir:
    'Gravel over clay and limestone. The most highly regarded vineyards sit '
    + 'at the eastern end, up against the northern boundary of Margaux, where '
    + 'the gravel is deepest.',
  wines:
    'Cabernet-led on the eastern gravel and rounder on the clay inland. '
    + 'Chasse-Spleen and Poujeaux have long been quoted as classed-growth '
    + 'quality at a Cru Bourgeois price.',
  sources: 'moulis.com; Wine With Seth; Wine Folly'
},

'margaux': {
  card:
    'The lightest and deepest gravel in the Médoc, over clay that '
    + 'forces roots down, and twenty-one classified growths — violets '
    + 'and fine-grained tannin.',
  history:
    'Established on 10 August 1954, and the largest of the communal '
    + 'appellations at somewhere between 1,410 and 1,530 hectares. It spans '
    + 'the communes of Margaux and Cantenac — merged into one commune in 2017 '
    + '— together with Soussans, Labarde and Arsac. Twenty-one of its estates '
    + 'are 1855 growths, more than any other commune, and Château Margaux is '
    + 'the only classified estate anywhere in Bordeaux that carries its '
    + 'appellation’s name.',
  terroir:
    'The lightest and deepest gravel in the Médoc, in beds reported at eight '
    + 'to twenty-one metres over compact clay that forces roots down. It is '
    + 'the only appellation to carry all six of the gravel terraces soil '
    + 'scientists have mapped, and there are real pockets of clay, chalk, '
    + 'limestone and sand among them.',
  wines:
    'The perfumed end of the Médoc: violets and red fruit over a finer-grained '
    + 'tannin than Pauillac’s. The spread of soils makes it the least '
    + 'uniform of the four great communes.',
  sources: 'Decanter; Château Cantenac Brown; Jane Anson; Wine With Seth'
},

/* ========================= GRAVES & SAUTERNES ========================== */
'pessac-leognan': {
  card:
    'Gravel mounds on the city’s doorstep, the earliest-ripening '
    + 'corner of Bordeaux, and the only appellation classified for red '
    + 'and dry white alike.',
  history:
    'The newest of the great appellations and the hardest won. Growers in the '
    + 'northern Graves formed the Syndicat Viticole des Hautes Graves in 1964 '
    + 'and asked immediately for an appellation of their own; the southern '
    + 'Graves had the numbers, with nearly 500 growers against 55 in the '
    + 'north, and it took André Lurton twenty-three years of tribunals to '
    + 'carry it. Pessac-Léognan was created on 9 September 1987 over ten '
    + 'communes, on the basis of a geological study by Pierre Becheler. '
    + 'Lurton also fought off the urban development that would have taken '
    + 'hundreds of hectares of vineyard: there were some 5,000 hectares of '
    + 'vines here in the nineteenth century and only 500 by 1975.',
  terroir:
    'Deep gravel mounds left by the Garonne, on the doorstep of the city and '
    + 'in places inside it. The gravel is what the name Graves means, and the '
    + 'warmth it holds is why this is the earliest-ripening corner of '
    + 'Bordeaux.',
  wines:
    'The only appellation in Bordeaux classified for red and dry white alike. '
    + 'Reds run to smoke, warm gravel and blackcurrant; the whites, from '
    + 'Sauvignon Blanc and Sémillon, are the most age-worthy dry whites in '
    + 'the region. Every classified growth of Graves now lies inside '
    + 'Pessac-Léognan, Haut-Brion among them.',
  sources: 'Decanter; Wikipedia (André Lurton); Vinorandum'
},

'graves': {
  card:
    'The gravel that named the region, running south from the city to '
    + 'Langon. Red and dry white in equal standing, over a smoky, '
    + 'warm-stone note.',
  history:
    'Reputed to be the oldest wine region of Bordeaux, and the one whose '
    + 'fortunes were made by the English trade after 1152. The appellation '
    + 'dates from 1937. In 1987 its northern half left to become '
    + 'Pessac-Léognan, taking all sixteen classified growths with it, so '
    + 'Graves today means the long southern stretch between the city and '
    + 'Langon.',
  terroir:
    'The gravel that gave the region its name — siliceous and stony, mixed '
    + 'through with sand and clay. It drains freely and ripens evenly, and it '
    + 'runs in beds rather than in a single sheet, which is why estates here '
    + 'are assembled parcel by parcel.',
  wines:
    'Red and dry white in roughly equal standing, the reds from Cabernet '
    + 'Sauvignon and Merlot, the whites from Sauvignon Blanc and Sémillon. '
    + 'The reds carry a smoky, warm-stone note that is the appellation’s '
    + 'signature.',
  sources: 'Taste France; The Wine Cellar Insider; Decanter; Wine With Seth'
},

'sauternes': {
  card:
    'Cold water off the Ciron meets the warm Garonne and the morning '
    + 'mists bring the botrytis. Sémillon, picked grape by grape over '
    + 'successive passes.',
  history:
    'Two appellations on one hillside. Barsac was recognised on 30 September '
    + '1936 under rules that run closely parallel to Sauternes’, and a '
    + 'grower in Barsac may label the wine either way — which is why they '
    + 'share a shape on this map and a classification in 1855.',
  terroir:
    'The Ciron runs cold out of the pine forest into the warmer Garonne, and '
    + 'the morning mists that follow are what let Botrytis cinerea take hold. '
    + 'Sauternes proper is clay-limestone with gravel hillocks; Barsac is '
    + 'flatter, on a karstified limestone platform with marl, and is '
    + 'generally held to give the finer, fresher wine while the other '
    + 'communes give the richer one.',
  wines:
    'Sémillon above all — more than 80% of the vines in the classified '
    + 'estates — with Sauvignon Blanc for acidity and a little Muscadelle. '
    + 'Picked grape by grape over successive passes through the vineyard, at '
    + 'yields that make it the most expensive wine in Bordeaux to produce.',
  sources: 'Conseil des Grands Crus Classés en 1855; Domaines Barons de '
    + 'Rothschild; IVES'
},

/* =============================== THE CÔTES ============================= */
'cotes-de-bourg': {
  card:
    'Clay-limestone and red alluvium on the heights above the '
    + 'estuary, with more Malbec in the blend than is usual anywhere in '
    + 'Bordeaux.',
  history:
    'Wine was made here in Roman times — the Romans are credited with '
    + 'planting Vitis biturica, the ancestor of the Cabernets, in the second '
    + 'century — and there are Roman remains in the port of Bourg itself. '
    + 'Sources give the appellation as 1920 or 1936; 1936 is the date most '
    + 'often cited, with whites following in 1945. In 2008 the appellation '
    + 'declined to join the Côtes de Bordeaux grouping and kept its own name.',
  terroir:
    'Clay-limestone and sandy-clay gravels, with a sienna-red alluvium on the '
    + 'heights above the estuary. The Gironde moderates the temperature and '
    + 'takes the edge off the frost risk.',
  wines:
    'Merlot-led, with more Malbec than is usual in Bordeaux — one source '
    + 'claims the highest proportion of any Bordeaux appellation, which is '
    + 'worth treating as a claim rather than a figure. Dark, iron-edged reds '
    + 'with a note of estuary salt.',
  sources: 'Wikipedia (Côtes de Bourg); The Wine Cellar Insider; Wine With Seth'
},

'blaye': {
  card:
    'South-facing clay-limestone on the escarpment above the Gironde, '
    + 'close enough to the water for the estuary to temper the season.',
  history:
    'Blaye guarded the estuary long before it sold wine: the citadel above '
    + 'the river is a Vauban fortification and a UNESCO site in its own right. '
    + 'The appellation took the name Blaye Côtes de Bordeaux under the 2009 '
    + 'reform that gathered several hillside appellations under one banner.',
  terroir:
    'The limestone escarpment above the right bank of the Gironde, on gentle '
    + 'south-facing slopes of well-draining clay-limestone that send roots '
    + 'deep. Close enough to the water for the estuary to temper the season.',
  wines:
    'Merlot-led and readier sooner than Bourg across the boundary — red plum '
    + 'and bramble over limestone freshness.',
  sources: 'The Wine Society; guide-bordeaux-gironde.com; Wine With Seth'
},

'castillon': {
  card:
    'Saint-Émilion’s limestone plateau running on eastward, named for '
    + 'the battle of 1453 that ended the Hundred Years’ War.',
  history:
    'Named for Castillon-la-Bataille, where the battle of 1453 ended the '
    + 'Hundred Years’ War and with it three centuries of English Bordeaux. '
    + 'Recognised as Côtes de Castillon in 1989 for red wine, and renamed '
    + 'Castillon Côtes de Bordeaux under the 2009 reform. Sources give its '
    + 'area as between about 2,300 and 3,000 hectares.',
  terroir:
    'The same limestone plateau that makes Saint-Émilion, running on eastward '
    + 'across the boundary, with more than a hundred metres of elevation '
    + 'between the river and the high ground.',
  wines:
    'Merlot with Cabernet Franc and a little Cabernet Sauvignon. The selling '
    + 'point is plain enough: the ground is Saint-Émilion’s and the price '
    + 'is not.',
  sources: 'glossary.wein.plus; Wine With Seth; Decanter; Gilbert & Gaillard'
},

/* ============================ THE LIBOURNAIS =========================== */
'fronsac': {
  card:
    'Clay-limestone hillsides that outsold Pomerol and Saint-Émilion '
    + 'until phylloxera. Merlot at about 78%, and the best value on the '
    + 'Right Bank.',
  history:
    'Fronsac sold for more than Pomerol and Saint-Émilion from the middle of '
    + 'the eighteenth century into the nineteenth, on the back of the '
    + 'Richelieu family’s patronage — the Duke took its wines repeatedly to '
    + 'the French court, and the château stayed in the family until the '
    + 'Revolution. Phylloxera ended that, and the appellation has been '
    + 'climbing back since the late 1970s. Recognised as Côtes de Fronsac in '
    + 'the late 1930s and simplified to Fronsac in 1976. Sources give it as '
    + 'roughly 770 to 825 hectares.',
  terroir:
    'Molasse du Fronsadais — a clay-limestone bedrock carrying sandstone — on '
    + 'hillsides above the Dordogne, with the Isle closing the eastern side. '
    + 'Only the higher ground on that bedrock is delimited; the flat alluvial '
    + 'terraces by the river fall outside the appellation. Gradients and '
    + 'exposures vary sharply, and some vineyards are terraced.',
  wines:
    'Merlot at around 78% of plantings, on limestone. Concentrated and '
    + 'mineral, and still the best-value serious wine on the Right Bank.',
  sources: 'Decanter; Wine With Seth; Cellar Tours'
},

'canon-fronsac': {
  card:
    'A small enclave at the top of the Canon plateau, on the same '
    + 'bedrock as Fronsac but with more sand and gravel mixed through '
    + 'it.',
  history:
    'An enclave in the south of Fronsac, between Fronsac itself and '
    + 'Saint-Michel-de-Fronsac, recognised in 1939 as Côtes de Canon Fronsac '
    + 'and renamed Canon Fronsac in 1964. Small, at somewhere between 220 and '
    + '305 hectares depending on the source.',
  terroir:
    'The same molasse du Fronsadais as its neighbour, at the top of the Canon '
    + 'plateau, but with more sand and gravel mixed in.',
  wines:
    'Decanter now calls the two appellations just about indistinguishable in '
    + 'style, with Merlot at about 78% in both. What separates them is '
    + 'history and name, more than taste.',
  sources: 'Decanter; Wine With Seth; Ponty vineyards'
},

'lalande-de-pomerol': {
  card:
    'Across the Barbanne stream from Pomerol, on much the same clay '
    + 'and fine gravel, with the same iron-rich crasse de fer beneath.',
  history:
    'Vines go back to the Middle Ages, when the Knights of St John kept a '
    + 'hospital here for pilgrims on the road to Santiago de Compostela, and '
    + 'the growers’ syndicate formed in 1886 to fight phylloxera is claimed '
    + 'as the oldest in France. The appellation’s date is genuinely '
    + 'disputed: 1936 in several guides, a 1935 decree in Decanter, and 1954 '
    + 'elsewhere — the last apparently marking the year Néac was absorbed. '
    + 'Before 1928 some growers here labelled their wine as Pomerol, and Néac '
    + 'estates sold theirs as Néac-Pomerol.',
  terroir:
    'Two communes, Lalande-de-Pomerol and Néac, divided from Pomerol by the '
    + 'Barbanne stream. Néac generally has the better ground: the Chevrol '
    + 'plateau carries clay and fine gravel much like Pomerol’s, and the '
    + 'same iron-oxide crasse de fer appears in the subsoil. Soils grow '
    + 'sandier westward, and Lalande has more gravel where Néac has more clay.',
  wines:
    'Merlot at around 75%. Pomerol’s plushness at a fraction of the price, '
    + 'and the first place to look when Pomerol itself has gone out of reach.',
  sources: 'Decanter; Wine With Seth; Wikipedia (Lalande-de-Pomerol AOC); '
    + 'The Wine Cellar Insider'
},

'pomerol': {
  card:
    'A plateau of blue clay over iron-rich crasse de fer, about '
    + 'twenty hectares of it, and no classification — the hierarchy '
    + 'here is made by price.',
  history:
    'Granted its appellation in 1936, in the first wave of INAO '
    + 'designations, and never classified — it is the one great appellation '
    + 'of Bordeaux that has never attempted a ranking of its estates. It was '
    + 'left out of 1855 because Right Bank wine sold for far less at the '
    + 'time; its reputation was made in the second half of the twentieth '
    + 'century, by individual estates rather than by any list. Small, at '
    + 'somewhere between 750 and 813 hectares.',
  terroir:
    'A plateau of rich blue clay over iron-oxide crasse de fer at the heart '
    + 'of the appellation, which holds water and suits Merlot as almost no '
    + 'other soil does. The blue clay covers only about twenty hectares, and '
    + 'Pétrus holds more than half of it. Towards the southern and western '
    + 'edges the ground turns to sand and gravel, and the wines lose tannin '
    + 'and concentration with it.',
  wines:
    'Merlot with Cabernet Franc, plush and dark-fruited, with an iron note '
    + 'that comes straight off the crasse de fer. The hierarchy here is made '
    + 'by reputation and price, which is to say by the market rather than by '
    + 'a commission.',
  sources: 'bordeaux.com; SommSelect; Wine With Seth; Wine Auctioneer'
},

'saint-emilion': {
  card:
    'Three grounds in one appellation: the limestone plateau, the '
    + 'clay slopes below it, and the gravel flats towards Pomerol.',
  history:
    'The oldest organised wine community in Bordeaux: the Jurade was founded '
    + 'in 1199, when John of England granted the town its charter, and was '
    + 'refounded by growers in 1948 as the ceremonial brotherhood that still '
    + 'proclaims judgment on each vintage. On 2 December 1999 the Jurisdiction '
    + 'of Saint-Émilion became the first wine-growing landscape inscribed on '
    + 'the UNESCO World Heritage List, and in 2001 the eight communes within '
    + 'it signed a charter to manage it. Around 5,400 hectares.',
  terroir:
    'Three grounds, not one. The limestone plateau around the town is the '
    + 'heart of it, giving dark, mineral wines — Ausone and Canon sit there. '
    + 'The clay-limestone côtes fall away from its edge. Out on the flat to '
    + 'the west, towards Pomerol, the soils turn sandy and gravelly, which is '
    + 'where Cheval Blanc and Figeac are.',
  wines:
    'Merlot led, with more Cabernet Franc than Pomerol — on the gravel at '
    + 'Cheval Blanc, a great deal more. The appellation covers everything '
    + 'from co-operative wine to the most expensive bottles on the Right '
    + 'Bank, which is what the classification exists to sort out.',
  sources: 'Saint-Émilion tourist board; UNESCO; Wine With Seth; Falstaff'
},

/* =========================== BETWEEN THE RIVERS ======================== */
'entre-deux-mers': {
  card:
    'Limestone and clay between two tidal rivers. The name covers dry '
    + 'white wine and nothing else — red grown here is sold as '
    + 'Bordeaux.',
  history:
    'The name is the land between two tides — the Garonne and the Dordogne, '
    + 'both tidal this far inland. The appellation dates from 1937 and '
    + 'allowed sweet wine at first; it was later restricted to dry white '
    + 'alone, by a decree sources date either to 23 September 1953 or to '
    + '1957. The same reform is credited with introducing the mandatory '
    + 'tasting panel that a wine must pass to carry the name.',
  terroir:
    'Limestone plateaux with clay and sandy gravel dropped by the streams '
    + 'that cut through them. The soils and the aspects are cooler than the '
    + 'Graves across the water, which is the point: this is white-wine ground.',
  wines:
    'Sauvignon Blanc, Sémillon and Muscadelle, dry and brisk. Most of the '
    + 'land here is actually planted to red grapes, but red wine from it '
    + 'cannot carry the Entre-Deux-Mers name — it is sold as Bordeaux. '
    + 'The appellation means dry white and nothing else.',
  sources: 'The Wine Cellar Insider; Wine With Seth; Insider Tasting'
}

};


/* ===========================================================================
   CLASSIFICATIONS
   ---------------------------------------------------------------------------
   `official` marks the six rankings with legal standing. The other four
   groupings in this dashboard are editorial: appellations gathered for
   convenience, not ranks. `listEdition` states which edition of the list the
   estates in this dashboard are drawn from, which is not always the current
   one — see `currency`.
   =========================================================================== */

window.BDX_CLASSIFICATION_NOTES = {

'1855': {
  official: true,
  origin:
    'Drawn up for the Exposition Universelle of 1855 in Paris, at the request '
    + 'of Napoleon III, who wanted the wines of Bordeaux ranked for display. '
    + 'The brokers of the Bordeaux place did not taste for it. They ranked by '
    + 'the prices the estates had held on the market over the preceding '
    + 'decades, which is why the list is best read as a snapshot of '
    + 'reputation and commerce in 1855 rather than a judgment of quality.',
  revision:
    'There is no mechanism for revising it, and in 170 years it has changed '
    + 'twice. Cantemerle was added as a Fifth Growth in September 1855, '
    + 'within months of publication. Mouton Rothschild was promoted from '
    + 'Second to First Growth on 21 June 1973, after decades of lobbying by '
    + 'Baron Philippe de Rothschild; one source records the order as signed '
    + 'by Jacques Chirac as Minister of Agriculture. Nothing else has moved. '
    + 'Estates have been divided, sold and renamed, and each part keeps the '
    + 'rank it was given.',
  listEdition: 'The 1855 list as it stands today, with Mouton as a First Growth.',
  sources: 'Wine Spectator; Wikipedia (First Growth); Wine With Seth'
},

'sauternes': {
  official: true,
  origin:
    'The sweet-wine half of the same 1855 exercise, ranked on the same basis '
    + 'of price, and given a tier that the Médoc list has no equivalent for: '
    + 'Château d’Yquem alone as Premier Cru Supérieur, the only estate in '
    + 'all Bordeaux ever to hold the rank.',
  revision:
    'Never revised. What has changed is the shape of the estates: properties '
    + 'have been divided over the years and each part kept its rank, which is '
    + 'why the total is given as 26 or 27 châteaux depending on how the '
    + 'divisions are counted.',
  listEdition: 'The 1855 Sauternes and Barsac list: Yquem, 11 Premiers Crus '
    + 'and 15 Deuxièmes Crus.',
  sources: 'Vinorandum; The Wine Cellar Insider; Conseil des Grands Crus '
    + 'Classés en 1855'
},

'stem': {
  official: true,
  origin:
    'Written into the appellation’s own specifications in 1955, and so the '
    + 'only Bordeaux classification designed from the start to be redone. It '
    + 'is run by the INAO, which approved the current regulations by decree '
    + 'on 14 May 2020 and appointed a seven-member commission in June of that '
    + 'year.',
  revision:
    'Revisable every ten years, and genuinely revised — which has made it the '
    + 'most quarrelsome list in France. The 2006 edition was annulled by the '
    + 'courts and the 1996 list reinstated; the 2012 reform moved the '
    + 'tastings and site inspections to outside professionals to reduce the '
    + 'grounds for challenge. The current edition was published on 8 '
    + 'September 2022 and holds for the 2022 to 2031 harvests. Two estates '
    + 'hold Premier Grand Cru Classé A — Figeac and Pavie — after Ausone, '
    + 'Cheval Blanc and Angélus chose not to apply.',
  listEdition: 'The 2022 edition, valid for the 2022–2031 harvests.',
  sources: 'INAO; Wine, Wit and Wisdom; Vins et Millésimes; Cellar Tours'
},

'graves': {
  official: true,
  origin:
    'Drafted in 1953, ratified in 1958 and modestly expanded on 16 February '
    + '1959, when four whites — Couhins-Lurton, Couhins, La Tour Martillac '
    + 'and Malartic-Lagravière — and two reds, de Fieuzal and Pape Clément, '
    + 'were added. Sixteen estates in all. It is the only Bordeaux '
    + 'classification that ranks red and dry white separately, and the only '
    + 'one with a single tier: an estate is a Cru Classé de Graves or it is '
    + 'not.',
  revision:
    'Never revised since 1959, and there is no cycle for doing so. Two '
    + 'properties have since been absorbed into La Mission Haut-Brion, '
    + 'leaving fourteen active classified estates. A revision is regularly '
    + 'called for and has never happened. All sixteen now lie within '
    + 'Pessac-Léognan, which did not exist when the list was drawn.',
  listEdition: 'The 1959 list.',
  sources: 'The Wine Cellar Insider; Berry Bros. & Rudd; Vinfolio; '
    + 'Wine With Seth'
},

'bourgeois': {
  official: true,
  origin:
    'The Crus Bourgeois are the estates of the Médoc below the 1855 list, and '
    + 'the name is far older than any modern ranking of them. The modern '
    + 'classification has been unstable: a three-tier list published in 2003 '
    + 'was annulled by the courts in 2007, after which the name survived from '
    + '2010 to 2019 as a single-tier quality mark awarded annually, with no '
    + 'hierarchy at all.',
  revision:
    'Three tiers were restored for the 2020 list — Exceptionnel, Supérieur '
    + 'and Cru Bourgeois — with revision every five years. Estates are judged '
    + 'on blind tastings of five consecutive vintages, to test consistency '
    + 'rather than a single good year. The 2020 list ran to 249 estates: 14 '
    + 'Exceptionnel, 56 Supérieur and 179 Cru Bourgeois. The 2025 revision '
    + 'cut it to 170 — 14, 36 and 120 — against stricter criteria, among '
    + 'them a mandatory environmental certification: level 2 for every estate '
    + 'and level 3, Haute Valeur Environnementale, for the two upper tiers. '
    + 'The next revision is due in 2030.',
  listEdition: 'The 2025 list of 170 estates, transcribed from the '
    + 'Alliance des Crus Bourgeois du Médoc’s own published classification.',
  sources: 'Decanter; Napa Valley Wine Academy; Wine With Seth; '
    + 'The Drinks Business'
},

'artisan': {
  official: true,
  origin:
    'A Cru Artisan is a small Médoc estate worked by its owner — the term '
    + 'describes the maker as much as the wine, and it was in use in the '
    + 'nineteenth century before falling out of it. A group of growers '
    + 'revived the defunct list in 1989, and the Union des Crus Artisans du '
    + 'Médoc obtained official recognition in 2006 for 44 estates.',
  revision:
    'Reviewed on a five-year cycle. Admission is decided by a jury of '
    + 'brokers, merchants and oenologists on a visit to the estate, worth 40% '
    + 'of the mark, and a blind tasting worth 60%; the estate must lie in one '
    + 'of the eight Médoc appellations. The list has contracted at each '
    + 'revision: from 44 at recognition to 36, and to the low thirties for '
    + 'the 2022 to 2026 vintages.',
  listEdition: 'The current roster, taken from the Syndicat des Crus '
    + 'Artisans du Médoc’s own château listing, with the appellation it gives '
    + 'for each estate.',
  currency:
    'One count to be aware of: the trade press reports the 2022–2026 ranking '
    + 'as 33 properties, while the syndicate’s own listing carries 34. This '
    + 'dashboard follows the syndicate.',
  sources: 'Decanter; bordeaux.com; Vinfolio; Union des Crus Artisans du Médoc'
},

/* ---- the editorial groupings: appellations, not ranks ---- */
'pomerol': {
  official: false,
  origin:
    'Pomerol has never classified its estates and has never tried. There is '
    + 'no list, no commission and no tiers.',
  revision:
    'The hierarchy here is made by reputation and by price. The groups used '
    + 'in this dashboard are an editorial convenience and carry no standing '
    + 'whatsoever.',
  sources: 'bordeaux.com; Wine With Seth'
},

'libournais': {
  official: false,
  origin:
    'Fronsac, Canon-Fronsac and Lalande-de-Pomerol have no classification '
    + 'between them. They are appellations, and the groups below are '
    + 'appellations too.',
  revision: 'Nothing to revise.',
  sources: 'Decanter; Wine With Seth'
},

'cotes': {
  official: false,
  origin:
    'The hillside appellations above the two rivers were gathered under the '
    + 'Côtes de Bordeaux banner by the reform of 2009 — Blaye and Castillon '
    + 'among them, while Bourg declined in 2008 and kept its own name. That '
    + 'is a grouping of appellations, not a ranking of estates.',
  revision: 'There is no classification here to revise.',
  sources: 'Wine With Seth; glossary.wein.plus; Wikipedia (Côtes de Bourg)'
},

'graves-doux': {
  official: false,
  origin:
    'Graves and Entre-Deux-Mers have no classification of their own. The '
    + 'classified growths of Graves all lie in Pessac-Léognan, which is a '
    + 'separate appellation and a separate list.',
  revision: 'Nothing to revise.',
  sources: 'Taste France; The Wine Cellar Insider'
}

};
