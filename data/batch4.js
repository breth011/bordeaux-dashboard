/* ===========================================================================
   Bordeaux Dashboard — research batch 4
   ---------------------------------------------------------------------------
   Two estates asked for by name that no list brought in: Château de la
   Commanderie in Lalande-de-Pomerol, and Château Chasse-Spleen in Moulis,
   which left the Crus Bourgeois and is on none of the official lists.

   Same bar as the earlier batches: history and terroir from sources, and
   conflicts between sources recorded rather than resolved. Where the
   sources give different plantings, no blend is shown. Neither estate has a
   surveyed position here, so both are placed by appellation and the map
   marks them approximate.

   This Commanderie is neither the Saint-Émilion classed growth
   (stem-chateau-la-commanderie), the Saint-Estèphe Cru Bourgeois, nor the
   Pomerol estate of the same name.

   Sources: Syndicat viticole de Lalande-de-Pomerol, INAO, The Wine Society,
   P&A Gelin, Wikipedia, The Wine Cellar Insider, Millesima.
   =========================================================================== */

window.BDX_CHATEAUX = (window.BDX_CHATEAUX || []).concat([

/* -------------------------- LALANDE-DE-POMEROL ------------------------- */
{id:'commanderie-lalande', name:'Château de la Commanderie', cls:'libournais', growth:3, cat:'red',
 appellation:'Lalande-de-Pomerol', commune:'Lalande-de-Pomerol', ha:29,
 owner:'Karine and Jean de Colbert since 2019, per the appellation’s syndicate — merchants still name the Lafon family', blend:null,
 history:'Named for the commandery the Knights of St John of Jerusalem kept here in the twelfth century, beside the church, to shelter pilgrims on the road to Santiago de Compostela; the appellation dates its vineyard to that commandery and took the order’s white cross as its emblem. Merchants describe it as a Lafon family property since 1955, made and distributed for decades with Établissements Jean-Pierre Moueix, and for years the only Lalande-de-Pomerol in the Moueix list. The appellation’s syndicate records a sale in 2019 to Karine and Jean de Colbert. The dashboard records both rather than choosing.',
 terroir:'Twenty-nine hectares of vines around the château. The upper part is sandy gravel over mottled sandy clay; the middle and lower slopes are sandy gravel over deep clayey sand. A selection of 4.5 hectares from the best parcels makes the Cuvée Rubis. Merchants give the planting as 80% Merlot and 20% Cabernet Franc, or as 75% Merlot, 20% Cabernet Franc and 5% Cabernet Sauvignon, so no blend is shown.',
 sources:'Syndicat viticole de Lalande-de-Pomerol; INAO; The Wine Society; P&A Gelin',
 style:'A long-standing name of the appellation, and for years the Lalande in the Moueix portfolio.'},

/* ------------------------ THE MÉDOC BEYOND THE LISTS ------------------- */
{id:'chasse-spleen', name:'Château Chasse-Spleen', cls:'medoc-hors', growth:1, cat:'red',
 appellation:'Moulis-en-Médoc', commune:'Moulis-en-Médoc',
 owner:'Merlaut family, through the Villars line, since 1976', second:'L’Héritage de Chasse-Spleen', blend:null,
 history:'Carved out of the old Grand-Poujeaux estate, which was divided from 1822; Chasse-Spleen itself came out of further divisions in the 1860s. From the Castaing family it passed to German wine merchants shortly before the First World War, was confiscated as enemy property, and was sold at auction in 1922 to the Lahary family. A consortium controlled by the Merlaut family bought it in 1976, and Jacques Merlaut’s daughter Bernadette Villars ran it until she and her husband died in a climbing accident in the Pyrenees in 1992. Sources name different members of the family in charge since: Céline Villars-Foubet (Wikipedia) and Claire Villars (The Wine Cellar Insider). The name — “chase away melancholy” — is credited to Byron in 1821 or to Baudelaire; neither story is documented. One of six Crus Exceptionnels in the Cru Bourgeois list of 1932, it stayed in the top tier until the courts annulled that classification in 2007, and it is not on the 2025 list. In 2023 it bought its neighbour, Château Brillette.',
 terroir:'Gravel, with clay and limestone in places, around Grand-Poujeaux at the eastern end of Moulis. Sources give the vineyard as 80, 90 or 135 hectares, and disagree on the planting: 73% Cabernet Sauvignon, 20% Merlot and 7% Petit Verdot (Wikipedia, Millesima), or 52% Cabernet Sauvignon, 39% Merlot, 5% Petit Verdot and 4% Cabernet Franc after what The Wine Cellar Insider describes as a major replanting. No blend is shown until that is settled. Three hectares of Sémillon and Sauvignon Blanc, planted in 1990, make a white sold as Bordeaux Blanc, because Moulis is an appellation for red wine only.',
 sources:'Wikipedia; The Wine Cellar Insider; Millesima',
 style:'The Moulis long quoted as classed-growth quality at a Cru Bourgeois price.'}

]);
