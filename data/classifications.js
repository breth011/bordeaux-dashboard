/* ===========================================================================
   Bordeaux Dashboard — classification registry
   ---------------------------------------------------------------------------
   One entry per collection the dashboard can show. `tiers` lists the ranks
   within it, highest first, each with the score baseline the derivation model
   uses for an estate of that rank in an average year.
   =========================================================================== */

window.BDX_CLASSIFICATIONS = [
{
  id: '1855', name: 'Classification of 1855', region: 'Médoc & Graves',
  year: 1855, cat: 'red', estates: 61,
  blurb: 'Drawn up for the Paris Exposition Universelle on the basis of the prices the wines fetched, and almost untouched since. Still the most famous hierarchy in wine.',
  detail: 'Amended exactly once, in 1973, when Mouton Rothschild was promoted to First Growth. Château Haut-Brion in Graves is the only estate from outside the Médoc.',
  tiers: [
    { growth: 1, label: 'Premiers Crus',   note: 'First Growths',  base: 96 },
    { growth: 2, label: 'Deuxièmes Crus',  note: 'Second Growths', base: 93.5 },
    { growth: 3, label: 'Troisièmes Crus', note: 'Third Growths',  base: 92 },
    { growth: 4, label: 'Quatrièmes Crus', note: 'Fourth Growths', base: 91.5 },
    { growth: 5, label: 'Cinquièmes Crus', note: 'Fifth Growths',  base: 91 }
  ]
},
{
  id: 'sauternes', name: 'Sauternes & Barsac 1855', region: 'Sauternes',
  year: 1855, cat: 'sweet', estates: 27,
  blurb: 'The sweet-wine half of the 1855 classification, and the only one to award a rank above First Growth — to Château d’Yquem alone.',
  detail: 'Botrytised Sémillon and Sauvignon Blanc from the confluence of the cold Ciron and the warmer Garonne, whose autumn mists make noble rot possible.',
  tiers: [
    { growth: 0, label: 'Premier Cru Supérieur', note: 'Château d’Yquem', base: 98 },
    { growth: 1, label: 'Premiers Crus',  note: 'First Growths',  base: 93 },
    { growth: 2, label: 'Deuxièmes Crus', note: 'Second Growths', base: 90.5 }
  ]
},
{
  id: 'stem', name: 'Saint-Émilion 2022', region: 'Right Bank — Libournais',
  year: 2022, cat: 'red', estates: 14,
  blurb: 'The only Bordeaux classification that is genuinely revised — every ten years, with promotion and demotion both real possibilities.',
  detail: 'The 2022 edition is the sixth. Ausone, Cheval Blanc and Angélus all withdrew rather than take part, leaving Pavie and Figeac as the sole Premiers Grands Crus Classés A. Valid through the 2031 harvest.',
  tiers: [
    { growth: 1, label: 'Premiers Grands Crus Classés A', note: 'Pavie and Figeac', base: 96.5 },
    { growth: 2, label: 'Premiers Grands Crus Classés B', note: '12 estates', base: 94 },
    { growth: 3, label: 'Grands Crus Classés', note: '71 estates', base: 91.5 }
  ]
},
{
  id: 'pomerol', name: 'Pomerol', region: 'Right Bank — Libournais',
  year: null, cat: 'red', estates: 17, editorial: true,
  blurb: 'The most expensive wine in Bordeaux comes from a plateau of iron-rich clay barely 800 hectares across — and it has never been classified at all.',
  detail: 'Pomerol has no classification and no intention of making one. The grouping used here is editorial: a reading of settled critical and market standing, not an official rank. Treat the tiers as a convenience, not a verdict.',
  tiers: [
    { growth: 1, label: 'The first rank', note: 'editorial grouping', base: 96.5 },
    { growth: 2, label: 'Classic estates', note: 'editorial grouping', base: 94 },
    { growth: 3, label: 'Other notable estates', note: 'editorial grouping', base: 91.5 }
  ]
},
{
  id: 'graves', name: 'Crus Classés de Graves', region: 'Pessac-Léognan',
  year: 1959, cat: 'both', estates: 16,
  blurb: 'A flat list with no hierarchy — sixteen estates, classified for red, for white, or for both.',
  detail: 'First drawn up in 1953 and finalised in 1959. Every classified estate now falls inside the Pessac-Léognan appellation, created in 1987. Haut-Brion appears here as well as in the 1855 classification.',
  tiers: [
    { growth: 1, label: 'Crus Classés de Graves', note: 'no ranking within the list', base: 93 }
  ]
},
{
  id: 'bourgeois', name: 'Crus Bourgeois du Médoc 2025', region: 'Médoc',
  year: 2025, cat: 'red', estates: 170,
  blurb: 'The Médoc’s working tier — 170 estates and some 28 million bottles a year, where most of the value in the region actually sits.',
  detail: 'Annulled by the courts in 2007 and rebuilt as an annual selection, the three-tier hierarchy returned in 2020. The 2025 revision cut the list from 249 estates to 170 against stricter criteria, among them a mandatory environmental certification. Revised every five years; the next is due in 2030.',
  tiers: [
    { growth: 1, label: 'Crus Bourgeois Exceptionnels', note: '14 estates', base: 90.5 },
    { growth: 2, label: 'Crus Bourgeois Supérieurs', note: '36 estates', base: 89 },
    { growth: 3, label: 'Crus Bourgeois', note: '120 estates', base: 87.5 }
  ]
},
{
  id: 'libournais', name: 'Fronsac & Lalande-de-Pomerol',
  region: 'Right Bank \u2014 Libournais', year: null, cat: 'red', estates: 15,
  editorial: true,
  blurb: 'The appellations around Saint-\u00c9milion and Pomerol that were never classified \u2014 and where the clay-limestone can be as good as the ground two kilometres south.',
  detail: 'None of these appellations has a classification. The groups below are appellations, not ranks. Fronsac sold for more than Saint-\u00c9milion in the eighteenth century, fell away after phylloxera, and has been climbing back since the late 1970s. Lalande-de-Pomerol sits across the Barbanne stream from Pomerol itself, on the same N\u00e9ac gravel.',
  tiers: [
    { growth: 1, label: 'Fronsac', note: 'clay-limestone slopes and plateau', base: 90 },
    { growth: 2, label: 'Canon-Fronsac', note: 'more clay and sand', base: 90 },
    { growth: 3, label: 'Lalande-de-Pomerol', note: 'the N\u00e9ac plateau', base: 90 }
  ]
},
{
  id: 'cotes', name: 'The Côtes de Bordeaux',
  region: 'The slopes above both rivers', year: null, cat: 'red', estates: 12,
  editorial: true,
  blurb: 'The hillside appellations \u2014 Bourg, Blaye, Castillon, Francs, Cadillac \u2014 where limestone slopes do the work that gravel does in the M\u00e9doc.',
  detail: 'None of these is classified; the groups below are appellations, not ranks. Castillon sits on the same limestone plateau as Saint-\u00c9milion and is named for the battle of 1453 that ended the Hundred Years\u2019 War. Francs, at roughly 500 hectares, is the smallest appellation in Bordeaux.',
  tiers: [
    { growth: 1, label: 'C\u00f4tes de Bourg', note: 'clay-limestone over harder rock', base: 89.5 },
    { growth: 2, label: 'Blaye C\u00f4tes de Bordeaux', note: 'the limestone escarpment', base: 88.5 },
    { growth: 3, label: 'Castillon C\u00f4tes de Bordeaux', note: 'Saint-\u00c9milion\u2019s plateau', base: 89.5 }
  ]
},
{
  id: 'graves-doux', name: 'Graves & Entre-Deux-Mers',
  region: 'Left Bank & between the rivers', year: null, cat: 'both', estates: 9,
  editorial: true,
  blurb: 'The gravel that gave a region its name, and the dry whites of the country between the two rivers.',
  detail: 'None of these is classified; the groups below are appellations, not ranks. Loupiac and Sainte-Croix-du-Mont face Sauternes across the Garonne and catch the same autumn mists off the Ciron; in 1832 Jullien rated Loupiac at the level of the Sauternes second growths.',
  tiers: [
    { growth: 1, label: 'Graves', note: 'the gravel that named the region', base: 90 },
    { growth: 3, label: 'Entre-Deux-Mers', note: 'dry white between the rivers', base: 87.5 }
  ]
},
{
  id: 'artisan', name: 'Crus Artisans du Médoc', region: 'Médoc',
  year: 2006, cat: 'red', estates: 34,
  blurb: 'Smallholders who grow, make and sell their own wine — a category recognised since the 1850s, lost for a century, and formally revived in 2006.',
  detail: 'Properties are typically under five hectares and family-run. Admission turns on an estate visit and a blind tasting. The roster shown is the 2006 homologation plus the 2012 additions; later revisions have trimmed it.',
  tiers: [
    { growth: 1, label: 'Crus Artisans', note: 'no ranking within the list', base: 86.5 }
  ]
}
];

/* ---------------------------------------------------------------------------
   Appellation geography. `c` is the commune or appellation centroid used to
   place an estate that has no surveyed position; `r` is the scatter radius in
   degrees, so that several hundred markers stay legible instead of stacking
   on one point. These positions show the APPELLATION, not the property.
   --------------------------------------------------------------------------- */
window.BDX_APPELLATION_GEO = {
  'Médoc':            { c: [45.345, -0.870], r: 0.075 },
  'Haut-Médoc':       { c: [45.115, -0.720], r: 0.070 },
  'Listrac-Médoc':    { c: [45.080, -0.792], r: 0.018 },
  'Moulis-en-Médoc':  { c: [45.060, -0.762], r: 0.018 },
  'Margaux':          { c: [45.035, -0.672], r: 0.022 },
  'Pauillac':         { c: [45.200, -0.752], r: 0.022 },
  'Saint-Estèphe':    { c: [45.258, -0.768], r: 0.022 },
  'Saint-Julien':     { c: [45.148, -0.742], r: 0.016 },
  'Saint-Émilion':    { c: [44.893, -0.157], r: 0.034 },
  'Pomerol':          { c: [44.929, -0.192], r: 0.016 },
  'Pessac-Léognan':   { c: [44.745, -0.594], r: 0.055 },
  'Sauternes':        { c: [44.535, -0.318], r: 0.020 },
  'Barsac':           { c: [44.566, -0.315], r: 0.012 }
};
