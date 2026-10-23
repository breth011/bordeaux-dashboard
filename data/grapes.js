/* =========================================================================
   Bordeaux Dashboard — the grape varieties, as background

   This file is reference text, not sourced data. Everything else the
   dashboard shows about a wine was read out of the estate's own sheet and
   says which document it came from; this is the standing description of a
   variety, written once, and it carries no vintage and no provenance.

   What is sourced sits beside it in the app: the share each variety takes
   across the blends actually held, counted from data/fiches.js at render
   time. So the prose says what Cabernet Sauvignon is for and the figure
   says how much of it this dataset has actually seen.

   Parentages are the DNA findings, not tradition: Cabernet Sauvignon as
   Cabernet Franc x Sauvignon Blanc (Bowers and Meredith, 1997), Merlot as
   Cabernet Franc x Magdeleine Noire des Charentes (Boursiquot and others,
   2009), Carmenere as Cabernet Franc x Gros Cabernet.

   Keys are the codes the blends use, and must match GRAPES in
   assets/app.js — a variety missing from that table is dropped from the
   bar and the blend stops adding up to a hundred.
   ========================================================================= */

window.BDX_GRAPES = {

CS: {
  colour: 'red',
  also: '',
  parents: 'Cabernet Franc × Sauvignon Blanc',
  ripens: 'late',
  gives: 'Colour, tannin, cassis and cedar — the frame a wine ages on',
  where: 'The deep gravel of the Left Bank: Pauillac, Saint-Julien, ' +
         'Saint-Estèphe, Margaux',
  note: 'Small berries and thick skins, so there is a great deal of skin ' +
        'for the amount of juice — which is where the colour and the ' +
        'tannin come from. It ripens late and needs the warmest ground to ' +
        'do it; in a cool year the tannin stays green and the wine tastes ' +
        'of stalks. The Médoc’s gravel terraces drain fast and hold the ' +
        'day’s heat into the night, which is why the Left Bank is ' +
        'Cabernet country and why the same vine planted on cold clay ' +
        'across the river never gets there.'
},

ME: {
  colour: 'red',
  also: '',
  parents: 'Cabernet Franc × Magdeleine Noire des Charentes',
  ripens: 'early — a fortnight or so before Cabernet Sauvignon',
  gives: 'Flesh and roundness, plum and fig, softer tannin, more alcohol',
  where: 'The clay and limestone of the Right Bank, and the cooler, ' +
         'damper soils everywhere. The most planted variety in the ' +
         'Gironde by a wide margin',
  note: 'It buds early and ripens early, and both ends cost it something: ' +
        'the early bud is what spring frost takes, and a wet June gives ' +
        'it coulure, the flower failing to set. The estates’ own season ' +
        'notes in this dashboard say so again and again — when a vintage ' +
        'is described as hard on the Merlot, that is usually what ' +
        'happened. The same earliness is what saves a wet autumn: the ' +
        'Merlot is in the cellar before the Cabernets are picked.'
},

CF: {
  colour: 'red',
  also: 'Bouchet, on the Right Bank',
  parents: 'A parent of both Cabernet Sauvignon and Merlot',
  ripens: 'mid — earlier than Cabernet Sauvignon',
  gives: 'Perfume: violet, raspberry, graphite, and fine-grained tannin',
  where: 'Saint-Émilion above all. Cheval Blanc is famously built on it ' +
         'and Ausone around half',
  note: 'The older of the two Cabernets and the parent of the other. It ' +
        'ripens earlier than Cabernet Sauvignon, which is why it works on ' +
        'the Right Bank’s cooler clay where its child would not — and in ' +
        'a cool year it shows the same green pyrazine, leaf and pepper, ' +
        'rather than violets. Planted for scent more than for structure.'
},

PV: {
  colour: 'red',
  also: '',
  parents: 'Obscure; probably from the south-west, not Bordeaux',
  ripens: 'very late — later than Cabernet Sauvignon',
  gives: 'Deep colour, violet, firm tannin and spice',
  where: 'Small plantings on the warmest Left Bank gravel, rarely more ' +
         'than a tenth of a blend',
  note: 'For most of the twentieth century it was a gamble: in a cool ' +
        'decade it simply failed to ripen, and a great deal of it was ' +
        'pulled out. Warmer autumns have made it ripen more often than ' +
        'not, and the plantings have come back — which is why it appears ' +
        'in recent blends in this dashboard more than in old ones. Used ' +
        'in percentages, as seasoning.'
},

CA: {
  colour: 'red',
  also: 'Grande Vidure',
  parents: 'Cabernet Franc × Gros Cabernet',
  ripens: 'very late',
  gives: 'Colour and a dark, savoury fruit',
  where: 'All but gone from Bordeaux. Still permitted, almost never ' +
         'planted',
  note: 'It was widely grown before phylloxera and did not come back ' +
        'after it: too late to ripen, too unreliable to set. It survived ' +
        'in Chile, where it had been exported as Merlot and was grown and ' +
        'sold as Merlot for over a century — until 1994, when it was ' +
        'identified for what it was.'
},

MA: {
  colour: 'red',
  also: 'Côt; Pressac, on the Right Bank',
  parents: 'Prunelard × Magdeleine Noire des Charentes',
  ripens: 'mid',
  gives: 'Colour, dark fruit, a firm acid line',
  where: 'A little, here and there. Its centre of gravity moved to ' +
         'Cahors and then to Argentina',
  note: 'Common in Bordeaux until the frost of February 1956, which ' +
        'killed a great deal of it and which growers replanted mostly ' +
        'with Merlot. Still permitted in the appellations and still found ' +
        'in a few blends in small amounts.'
},

SEM: {
  colour: 'white',
  also: 'Chevrier',
  parents: 'Native to the Bordeaux region',
  ripens: 'mid',
  gives: 'Body, lanolin and honey, low acidity; with age, beeswax and ' +
         'toast',
  where: 'The backbone of Sauternes and Barsac, and the larger part of ' +
         'most dry Graves whites',
  note: 'Thin-skinned, which is the whole point and the whole risk. It ' +
        'takes Botrytis cinerea readily, and under the right autumn — ' +
        'damp mornings off the Ciron, dry afternoons — the rot shrivels ' +
        'the berry and concentrates what is left into Sauternes. Under ' +
        'the wrong autumn the same thin skin simply rots, and the crop ' +
        'is lost.'
},

SB: {
  colour: 'white',
  also: '',
  parents: 'A parent of Cabernet Sauvignon; related to Traminer',
  ripens: 'early to mid',
  gives: 'Acidity and aroma: citrus, cut grass, boxwood',
  where: 'Blended with Sémillon in both the dry whites and the sweet',
  note: 'In the dry whites of Pessac-Léognan it supplies the nose and the ' +
        'cut. In Sauternes it does something less obvious and more ' +
        'important: it is the acid spine that keeps a wine carrying 120 ' +
        'grams of sugar a litre from tasting like syrup.'
},

SG: {
  colour: 'white',
  also: '',
  parents: 'A pink-skinned mutation of Sauvignon Blanc',
  ripens: 'early to mid',
  gives: 'More body and less green pyrazine than its parent',
  where: 'Small plantings, mostly Graves and Pessac-Léognan',
  note: 'The same vine as Sauvignon Blanc with a pink skin, and it makes ' +
        'a rounder, less overtly grassy wine. Easy to leave out: this ' +
        'dashboard once drew Opalie de Château Coutet as a 93% blend ' +
        'because Sauvignon Gris was missing from its own list of ' +
        'varieties, and the seven per cent had nowhere to go.'
},

MU: {
  colour: 'white',
  also: '',
  parents: 'No relation to Muscat, despite the name',
  ripens: 'early',
  gives: 'A grapey, floral lift',
  where: 'A few per cent at most, in sweet blends and some dry ones',
  note: 'Aromatic and prone to rot, which in Sauternes is less of an ' +
        'objection than elsewhere. Permitted up to a small share and ' +
        'used for scent; almost never seen on its own.'
}

};

/* The seven varieties admitted to the Bordeaux and Bordeaux Supérieur
   appellations in 2021 as variétés d'intérêt à fin d'adaptation — planted
   against a warming climate, capped at 5% of an estate's vineyard and 10%
   of a blend, and not permitted in the classified appellations this
   dashboard is mostly about. None of them appears in any blend here; they
   are listed because the question of what Bordeaux is allowed to plant is
   now an open one. */
window.BDX_GRAPES_NEW = {
  red: ['Arinarnoa', 'Castets', 'Marselan', 'Touriga Nacional'],
  white: ['Alvarinho', 'Liliorila', 'Petit Manseng']
};
