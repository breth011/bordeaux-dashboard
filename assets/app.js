/* ===========================================================================
   Bordeaux Dashboard — application engine
   ---------------------------------------------------------------------------
   Collections: 1855 Médoc, 1855 Sauternes, Saint-Émilion 2022, Pomerol
   (editorial), Crus Classés de Graves, Crus Bourgeois 2020, Crus Artisans.
   No build step, no framework. Leaflet is the only external dependency.
   =========================================================================== */
(function () {
'use strict';

var NOW = 2026;
var V   = window.BDX_VINTAGES;
var RB  = window.BDX_RIGHTBANK;
var CLS = window.BDX_CLASSIFICATIONS;
var GEO = window.BDX_APPELLATION_GEO;
var SCORES  = window.BDX_SCORES || {};
var SKIPPED = window.BDX_NOT_PRODUCED || {};
var YEARS = Object.keys(V).map(Number).sort(function (a, b) { return b - a; });

/* ===========================================================================
   1. BUILD THE ESTATE LIST
   Records written out in full keep their own data. Compact lists (the 71
   Saint-Émilion Grands Crus Classés, the Pomerol field, 249 Crus Bourgeois,
   50 Crus Artisans) are expanded here into sparse records: verified name,
   rank and appellation, with blend and position falling back to appellation
   defaults that the UI flags.
   =========================================================================== */
var CH = window.BDX_CHATEAUX || [];

function slug(s) {
  return s.normalize ? s.normalize('NFD').replace(/[̀-ͯ]/g, '')
      .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
    : s.toLowerCase().replace(/[^a-z0-9]+/g, '-');
}

/* Existing full records predate the `cls` field. */
CH.forEach(function (ch) {
  if (!ch.cls) ch.cls = ch.cat === 'sweet' ? 'sauternes' : '1855';
  /* perf nudges the score off the rank baseline. Estates added without one
     sit exactly on it — and without this default the arithmetic produced
     NaN and the score chart silently drew nothing. */
  if (typeof ch.perf !== 'number') ch.perf = 0;
});

function addSparse(name, appellation, cls, growth, commune) {
  var id = cls + '-' + slug(name);
  CH.push({
    id: id, name: name, cls: cls, growth: growth, cat: 'red',
    appellation: appellation, commune: commune || appellation,
    /* No blend. The estate's own encépagement is not in this dataset, and an
       appellation average presented as this château's blend would be an
       invention — so the dashboard shows nothing rather than a guess. */
    blend: null, approx: true, sparse: true, perf: 0
  });
}

(window.BDX_STEM_GCC || []).forEach(function (n) {
  addSparse(n, 'Saint-Émilion', 'stem', 3);
});
(window.BDX_POMEROL_OTHER || []).forEach(function (n) {
  addSparse(n, 'Pomerol', 'pomerol', 3);
});
var CB = window.BDX_CRU_BOURGEOIS || {};
[['exceptionnel', 1], ['superieur', 2], ['bourgeois', 3]].forEach(function (p) {
  (CB[p[0]] || []).forEach(function (row) { addSparse(row[0], row[1], 'bourgeois', p[1]); });
});
var CA = window.BDX_CRU_ARTISAN || {};
/* The syndicate publishes an appellation for each estate now, so they go
   where they belong rather than into the Médoc generally. */
(CA.current || []).forEach(function (row) {
  addSparse(row[0], row[1], 'artisan', 1);
});

/* Haut-Brion is classified under both 1855 and the 1959 Graves list. */
var CROSS = {};
(window.BDX_GRAVES_CROSSLIST || []).forEach(function (id) { CROSS[id] = 'graves'; });

/* Deterministic position for estates with no surveyed location.
   The point is sampled INSIDE that appellation's own outline, so a dot can
   never sit outside the region it belongs to. It shows the APPELLATION, not
   the property, and the UI says so wherever it matters. */
function hash(s) {
  var h = 2166136261;
  for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function mulberry(seed) {
  var a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    var t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
/* Ray casting, in raw lat/lng. */
function inAnyRing(lat, lng, rings) {
  for (var i = 0; i < rings.length; i++) if (pointInPoly(lat, lng, rings[i])) return true;
  return false;
}
function inRegionShape(lat, lng, reg) {
  if (!inAnyRing(lat, lng, reg.rings)) return false;
  return !(reg.holes && reg.holes.length && inAnyRing(lat, lng, reg.holes));
}
function pointInPoly(lat, lng, poly) {
  var inside = false;
  for (var i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    var yi = poly[i][0], xi = poly[i][1], yj = poly[j][0], xj = poly[j][1];
    if (((yi > lat) !== (yj > lat)) &&
        (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi)) inside = !inside;
  }
  return inside;
}
/* Carve the communal appellations out of the region that contains them.
   The hole rings ARE the neighbour's rings, so the cut-out can never drift
   away from the shape it is cut from. */
(function resolveHoles() {
  var R = window.BDX_MAP.regions;
  function byId(id) {
    for (var i = 0; i < R.length; i++) if (R[i].id === id) return R[i];
    return null;
  }
  R.forEach(function (r) {
    r.holes = [];
    (r.holesOf || []).forEach(function (id) {
      var o = byId(id);
      if (o) o.rings.forEach(function (ring) { r.holes.push(ring); });
    });
  });
})();

function regionForAppellation(app) {
  var R = window.BDX_MAP.regions;
  for (var i = 0; i < R.length; i++) if (R[i].apps.indexOf(app) !== -1) return R[i];
  return null;
}
CH.forEach(function (ch) {
  if (ch.lat !== undefined) return;
  var reg = regionForAppellation(ch.appellation);
  var rnd = mulberry(hash(ch.id));
  if (reg) {
    /* Pick a part in proportion to its area, then sample inside it, so a
       two-part appellation like Sauternes & Barsac fills both. */
    var areas = reg.rings.map(function (ring) {
      var a = 0;
      for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        a += (ring[j][1] * ring[i][0] - ring[i][1] * ring[j][0]);
      }
      return Math.abs(a / 2);
    });
    var total = areas.reduce(function (x, y) { return x + y; }, 0);
    var pick = rnd() * total, ring = reg.rings[0];
    for (var ri = 0; ri < reg.rings.length; ri++) {
      pick -= areas[ri];
      if (pick <= 0) { ring = reg.rings[ri]; break; }
    }
    var la0 = Infinity, la1 = -Infinity, ln0 = Infinity, ln1 = -Infinity;
    ring.forEach(function (p) {
      if (p[0] < la0) la0 = p[0]; if (p[0] > la1) la1 = p[0];
      if (p[1] < ln0) ln0 = p[1]; if (p[1] > ln1) ln1 = p[1];
    });
    var cLa = (la0 + la1) / 2, cLn = (ln0 + ln1) / 2;
    for (var t = 0; t < 160; t++) {
      var la = la0 + rnd() * (la1 - la0), ln = ln0 + rnd() * (ln1 - ln0);
      if (pointInPoly(la, ln, ring)) {
        /* Nudge off the drawn edge — but the nudge is toward the bounding
           box centre, which for a long diagonal shape like the Médoc lies
           outside the shape. Keep the nudge only if it stays inside. */
        var sLa = cLa + (la - cLa) * 0.92, sLn = cLn + (ln - cLn) * 0.92;
        if (!pointInPoly(sLa, sLn, ring)) { sLa = la; sLn = ln; }
        if (reg.holes && reg.holes.length && inAnyRing(sLa, sLn, reg.holes)) continue;
        ch.lat = sLa; ch.lng = sLn;
        return;
      }
    }
    ch.lat = cLa; ch.lng = cLn;
    return;
  }
  var g = (window.BDX_APPELLATION_GEO || {})[ch.appellation] || { c: [45.0, -0.6], r: 0.05 };
  var ang = rnd() * Math.PI * 2, rad = Math.sqrt(rnd()) * g.r;
  ch.lat = g.c[0] + rad * Math.cos(ang) * 0.7;
  ch.lng = g.c[1] + rad * Math.sin(ang);
});

function clsDef(id) {
  for (var i = 0; i < CLS.length; i++) if (CLS[i].id === id) return CLS[i];
  return null;
}
function tierDef(ch) {
  var c = clsDef(ch.cls);
  if (!c) return null;
  for (var i = 0; i < c.tiers.length; i++) if (c.tiers[i].growth === ch.growth) return c.tiers[i];
  return null;
}
function inCollection(ch, id) { return ch.cls === id || CROSS[ch.id] === id; }
function countIn(id) {
  return CH.filter(function (c) { return inCollection(c, id); }).length;
}

var SHORT_RANK = {
  '1855':      ['', '1er Cru', '2ème Cru', '3ème Cru', '4ème Cru', '5ème Cru'],
  'sauternes': ['1er Cru Supérieur', '1er Cru', '2ème Cru'],
  'stem':      ['', '1er Grand Cru Classé A', '1er Grand Cru Classé B', 'Grand Cru Classé'],
  'pomerol':   ['', 'First rank', 'Classic estate', 'Notable estate'],
  'graves':    ['', 'Cru Classé de Graves'],
  'bourgeois': ['', 'Cru Bourgeois Exceptionnel', 'Cru Bourgeois Supérieur', 'Cru Bourgeois'],
  'artisan':   ['', 'Cru Artisan'],
  'libournais': ['', 'Fronsac', 'Canon-Fronsac', 'Lalande-de-Pomerol'],
  'cotes':      ['', 'Côtes de Bourg', 'Blaye Côtes de Bordeaux',
                 'Castillon Côtes de Bordeaux'],
  'graves-doux': ['', 'Graves', '', 'Entre-Deux-Mers']
};
function rankLabel(ch) {
  var a = SHORT_RANK[ch.cls];
  return (a && a[ch.growth]) || (tierDef(ch) || {}).label || '';
}

/* ===========================================================================
   2. GRAPE VARIETIES — fixed validated categorical order, never cycled
   =========================================================================== */
var GRAPES = {
  CS:  { name: 'Cabernet Sauvignon', slot: 1 },
  ME:  { name: 'Merlot',             slot: 2 },
  CF:  { name: 'Cabernet Franc',     slot: 3 },
  PV:  { name: 'Petit Verdot',       slot: 4 },
  CA:  { name: 'Carménère',          slot: 5 },
  MA:  { name: 'Malbec',             slot: 6 },
  SEM: { name: 'Sémillon',           slot: 1 },
  SB:  { name: 'Sauvignon Blanc',    slot: 2 },
  MU:  { name: 'Muscadelle',         slot: 3 }
};
var GRAPE_ORDER = ['CS', 'ME', 'CF', 'PV', 'CA', 'MA', 'SEM', 'SB', 'MU'];

function cssVar(n) {
  return getComputedStyle(document.documentElement).getPropertyValue(n).trim();
}
function grapeColor(k) { return cssVar('--series-' + GRAPES[k].slot); }
function rankColor(ch) { return cssVar('--rank-' + Math.min(5, ch.growth)); }

function inkOn(hex) {
  var m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return false;
  var c = [1, 2, 3].map(function (i) {
    var v = parseInt(m[i], 16) / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  });
  return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) > 0.42;
}

/* ===========================================================================
   3. DERIVATION MODEL — everything here is MODELLED, never sourced
   =========================================================================== */
/* Everything in the Libournais takes the Right Bank vintage ratings: these
   are Merlot on clay and limestone, and their seasons track Pomerol's, not
   the Médoc's. */
var RIGHT_BANK = ['Saint-Émilion', 'Pomerol', 'Fronsac', 'Canon-Fronsac',
  'Lalande-de-Pomerol', 'Côtes de Bourg', 'Blaye Côtes de Bordeaux',
  'Castillon Côtes de Bordeaux'];

function vintageRating(ch, year) {
  var v = V[year];
  if (!v) return null;
  var base, d = 0;
  if (ch.cat === 'sweet') {
    base = v.sauternes;
  } else if (RIGHT_BANK.indexOf(ch.appellation) !== -1) {
    var rb = RB[year];
    base = rb.r;
    d = (rb.app && rb.app[ch.appellation]) || 0;
  } else if (ch.cat === 'white') {
    /* Dry whites are picked early and swing far less by vintage than reds. */
    base = 90 + (v.pessac - 90) * 0.6;
    d = 0;
  } else if (ch.appellation === 'Pessac-Léognan') {
    base = v.pessac;
    d = (v.app && v.app[ch.appellation]) || 0;
  } else {
    base = v.medoc;
    d = (v.app && v.app[ch.appellation]) || 0;
  }
  return Math.max(50, Math.min(100, Math.round(base + d)));
}


function notProduced(ch, year) {
  return (SKIPPED[ch.id] || []).indexOf(year) !== -1;
}
/* A score is a thing a critic published, or it is nothing. There is no
   modelled score any more: the old one was derived from the estate's rank
   and the quality of the season, which is a plausible number and not a
   rating. Where no rating was published, the dashboard says so. */
function scoreFor(ch, year) {
  if (notProduced(ch, year)) return { none: true, notMade: true };
  var o = SCORES[ch.id + '|' + year];
  if (o && o.score) return { score: o.score, verified: true, src: o.src };
  return { none: true };
}

/* Every published rating this dashboard holds for one estate. */
function publishedRatings(ch) {
  var rows = [];
  YEARS.forEach(function (yr) {
    var o = SCORES[ch.id + '|' + yr];
    if (o && o.score) rows.push({ yr: yr, score: o.score, src: o.src });
  });
  return rows;
}

function ratingsSection(ch) {
  var rows = publishedRatings(ch);
  /* Nothing published means no section at all. The absence is the fact; it
     does not need announcing on every estate. */
  if (!rows.length) return '';
  return '<div class="section"><h3>Critic ratings ' +
    '<span class="hint">' + rows.length + ' of ' + YEARS.length +
    ' vintages on record</span></h3>' +
    '<div class="critratings">' + rows.map(function (r) {
      return '<span class="rating"><b>' + r.yr + '</b>' +
        '<span class="rating-n" style="background:' + scoreColor(r.score) +
        ';color:' + (inkOn(scoreColor(r.score)) ? '#121211' : '#fff') + '">' +
        r.score + '</span>' +
        '<span class="rating-src">' + (r.src || 'reported') + '</span></span>';
    }).join('') + '</div></div>';
}

/* The estate's typical encépagement, unchanged. It used to be shifted year
   by year towards Cabernet in the warm vintages, which produced a blend no
   estate ever declared; a vintage blend now appears only where one was
   actually published. */

function deaccent(s) {
  return s.normalize ? s.normalize('NFD').replace(/[̀-ͯ]/g, '') : s;
}

/* websites.js is keyed on the estate name stripped of its accents, its
   Château/Clos/Domaine prefix and its punctuation, because the growers' own
   register and Wikidata spell the same property three different ways. The
   key is built here exactly as it was built when the file was generated. */
function siteKey(name) {
  return deaccent(name).toLowerCase()
    .replace(/^(chateau|ch\.|clos|domaine|le|la|les)\s+/, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/^ +| +$/g, '');
}
function siteFor(ch) {
  var S = window.BDX_SITES;
  return (S && S[siteKey(ch.name)]) || null;
}
function slugPlus(s) {
  return deaccent(s).toLowerCase().replace(/[^a-z0-9]+/g, '+').replace(/^\+|\+$/g, '');
}
function buyLinks(ch, year) {
  var q = deaccent(ch.name) + ' ' + year;
  var ws = slugPlus(ch.name + ' ' + ch.appellation + ' bordeaux france');
  return [
    { label: 'Cheapest online', host: 'Wine-Searcher', primary: true,
      url: 'https://www.wine-searcher.com/find/' + ws + '/' + year },
    { label: 'Shopping', host: 'Google Shopping',
      url: 'https://www.google.com/search?tbm=shop&q=' + encodeURIComponent(q) },
    { label: 'Vivino', host: 'Vivino',
      url: 'https://www.vivino.com/search/wines?q=' + encodeURIComponent(q) },
    { label: 'All merchants', host: 'Web search',
      url: 'https://www.google.com/search?q=' + encodeURIComponent(q + ' buy bottle price') }
  ];
}

/* ===========================================================================
   5. SEQUENTIAL RAMP (one hue, light to dark) for score magnitude
   =========================================================================== */
function seqStep(value, lo, hi) {
  var steps = ['--seq-250', '--seq-300', '--seq-400', '--seq-450', '--seq-500', '--seq-550', '--seq-650'];
  var t = Math.max(0, Math.min(0.999, (value - lo) / (hi - lo)));
  return cssVar(steps[Math.floor(t * steps.length)]);
}
function scoreColor(s) { return seqStep(s, 78, 100); }
function ratingColor(r) { return seqStep(r, 60, 100); }

/* ===========================================================================
   6. STATE
   =========================================================================== */
var state = {
  apPage: null, clsPage: null,
  view: 'home',       /* home | producers | vintages */
  cls: null,          /* active collection id, or null for everything */
  region: null,
  q: '', appellation: '', vintage: '',
  tiers: {}, active: null, tables: false
};

var el = {};
['tabAppellations','tabClassifications','tabProducers','tabVintages',
 'search','appellation','vintage',
 'chips','resultcount','appellations','classifications','workspace','paneList',
 'vintageGrid','drawer','scrim',
 'drawerHead','drawerBody','themeBtn','resetBtn','filters','crumb'
].forEach(function (id) { el[id] = document.getElementById(id); });

/* ===========================================================================
   7. FILTERING
   =========================================================================== */
function activeTiers() {
  var def = state.cls ? clsDef(state.cls) : null;
  if (!def) return null;
  return def.tiers;
}
function visibleChateaux() {
  var q = deaccent(state.q.trim().toLowerCase());
  return CH.filter(function (ch) {
    if (state.cls && !inCollection(ch, state.cls)) return false;
    if (state.cls && state.tiers[ch.cls + ':' + ch.growth] === false) return false;
    if (state.region) {
      var rg = regionById(state.region);
      if (rg && !inRegion(ch, rg)) return false;
    }
    if (state.appellation && ch.appellation !== state.appellation) return false;
    if (q) {
      var hay = deaccent((ch.name + ' ' + ch.appellation + ' ' + (ch.commune || '') + ' ' +
                (ch.owner || '') + ' ' + (ch.second || '')).toLowerCase());
      if (hay.indexOf(q) === -1) return false;
    }
    /* Choosing a vintage narrows to the estates that actually made a wine
       that year. It used to narrow to the ones with a score, which was
       harmless when every score was modelled and would now hide almost
       everything. */
    if (state.vintage && notProduced(ch, Number(state.vintage))) return false;
    return true;
  });
}

/* ===========================================================================
   8. HOME — choose a collection
   =========================================================================== */
/* ===========================================================================
   6a. THE REFERENCE PAGES — appellations and classifications
   ---------------------------------------------------------------------------
   Two ways into the same estates. An appellation is a piece of ground; a
   classification is a list somebody drew up about it. Those are not the same
   question, so they are not the same page.
   =========================================================================== */
var AP_NOTES  = window.BDX_APPELLATION_NOTES || {};
var CLS_NOTES = window.BDX_CLASSIFICATION_NOTES || {};

/* The first division in Bordeaux is which side of the water you are on: it
   decides the grape, the soil and the shape of the wine before anything
   else does. The old district names are kept on each card, because an
   appellation belongs to both. */
var AP_GROUPS = [
  { title: 'Left Bank', note: 'West of the Gironde and the Garonne — gravel, Cabernet Sauvignon',
    ids: ['medoc', 'haut-medoc', 'saint-estephe', 'pauillac', 'saint-julien',
          'listrac', 'moulis', 'margaux', 'pessac-leognan', 'graves',
          'sauternes'] },
  { title: 'Right Bank', note: 'East of the Gironde and north of the Dordogne — clay and limestone, Merlot',
    ids: ['saint-emilion', 'pomerol', 'lalande-de-pomerol', 'fronsac',
          'canon-fronsac', 'cotes-de-bourg', 'blaye', 'castillon'] },
  { title: 'Between the rivers', note: 'The Entre-Deux-Mers, Garonne to Dordogne — dry white',
    ids: ['entre-deux-mers'] }
];

/* The district each appellation also belongs to, shown on its card. */
var AP_DISTRICT = {
  'medoc': 'The Médoc', 'haut-medoc': 'The Médoc',
  'saint-estephe': 'The Médoc', 'pauillac': 'The Médoc',
  'saint-julien': 'The Médoc', 'listrac': 'The Médoc',
  'moulis': 'The Médoc', 'margaux': 'The Médoc',
  'pessac-leognan': 'Graves', 'graves': 'Graves',
  'sauternes': 'The sweet wines',
  'saint-emilion': 'The Libournais', 'pomerol': 'The Libournais',
  'lalande-de-pomerol': 'The Libournais', 'fronsac': 'The Libournais',
  'canon-fronsac': 'The Libournais',
  'cotes-de-bourg': 'The Côtes', 'blaye': 'The Côtes',
  'castillon': 'The Côtes',
  'entre-deux-mers': 'Entre-Deux-Mers'
};

function apNote(id) { return AP_NOTES[id] || null; }

/* A card wants a line, not a paragraph. Take whole sentences while they
   fit, and only fall back to cutting mid-sentence when the first one is
   already too long to show. */
function teaser(text, max) {
  max = max || 150;
  if (text.length <= max) return text;
  var stop = text.lastIndexOf('. ', max);
  if (stop > 50) return text.slice(0, stop + 1);
  var sp = text.lastIndexOf(' ', max);
  return text.slice(0, sp > 0 ? sp : max) + '…';
}

function chateauxInRegion(r) {
  return CH.filter(function (ch) { return inRegion(ch, r); })
           .sort(function (x, y) { return x.name.localeCompare(y.name); });
}

/* A list of estates, grouped, each one a way into its drawer. */
/* `withHa` is off for the classification lists, where the hectarage is
   noise beside the rank; the estate's own page keeps it. */
function estateGrid(list, labelFor, withHa) {
  var buckets = [], index = {};
  list.forEach(function (ch) {
    var k = labelFor(ch);
    if (!index[k]) { index[k] = { label: k, items: [] }; buckets.push(index[k]); }
    index[k].items.push(ch);
  });
  return buckets.map(function (b) {
    return '<div class="ref-group"><h4>' + b.label +
      ' <span class="ref-n">' + b.items.length + '</span></h4><div class="ref-cards">' +
      b.items.map(function (ch) {
        return '<button class="ref-card" data-ch="' + ch.id + '">' +
          '<span class="ref-card-name">' + ch.name + '</span>' +
          '<span class="ref-card-meta">' +
            (ch.commune && ch.commune !== ch.appellation ? ch.commune : '') +
            (withHa && ch.ha ? (ch.commune && ch.commune !== ch.appellation ? ' · ' : '') +
              ch.ha + ' ha' : '') + '</span></button>';
      }).join('') + '</div></div>';
  }).join('');
}

function wireEstateCards(root) {
  Array.prototype.forEach.call(root.querySelectorAll('.ref-card'), function (b) {
    b.addEventListener('click', function () { openDrawer(b.dataset.ch); });
  });
}

/* ------------------------------- appellations ------------------------------ */
function renderAppellations() {
  if (state.apPage) return renderAppellationPage(state.apPage);

  var html = '<div class="ref-intro"><h2>The appellations</h2>' +
    '<p>Twenty pieces of ground, each with its own rules about what may be ' +
    'planted and how. An appellation says where a wine is from. It does not ' +
    'say how good anyone thinks it is — for that, see ' +
    '<button class="linkish" id="toCls">the classifications</button>.</p></div>';

  AP_GROUPS.forEach(function (g) {
    html += '<section class="ref-band"><div class="ref-band-head">' +
      '<h3>' + g.title + '</h3></div><div class="ref-grid">';
    g.ids.forEach(function (id) {
      var r = regionById(id);
      if (!r) return;
      var n = chateauxInRegion(r).length;
      var note = apNote(id);
      html += '<button class="apcard" data-ap="' + id + '">' +
        '<h4>' + r.name + '</h4>' +
        '<span class="apyear">' + (AP_DISTRICT[id] || '') + '</span>' +
        '<p>' + (note ? (note.card || teaser(note.wines)) : '') + '</p>' +
        '<span class="apcount">' + n + ' château' + (n === 1 ? '' : 'x') + '</span>' +
        '</button>';
    });
    html += '</div></section>';
  });

  el.appellations.innerHTML = html;
  Array.prototype.forEach.call(el.appellations.querySelectorAll('.apcard'), function (b) {
    b.addEventListener('click', function () {
      state.apPage = b.dataset.ap; renderAppellations(); window.scrollTo(0, 0);
    });
  });
  var t = document.getElementById('toCls');
  if (t) t.addEventListener('click', function () { setView('classifications'); });
}

function renderAppellationPage(id) {
  var r = regionById(id), note = apNote(id);
  if (!r) { state.apPage = null; return renderAppellations(); }
  var list = chateauxInRegion(r);

  var html = '<div class="ref-head">' +
    '<button class="ref-back" id="apBack">← All appellations</button>' +
    '<h2>' + r.name + '</h2>' +
    '<span class="ref-sub">' + r.apps.join(' · ') + ' · ' + list.length +
      ' château' + (list.length === 1 ? '' : 'x') + '</span>' +
    '<span class="ref-head-gap"></span>' +
    '<button class="ref-map" id="apMap">See it on the map</button></div>';

  if (note) {
    html += '<div class="ref-prose">' +
      '<section><h3>History</h3><p>' + note.history + '</p></section>' +
      '<section><h3>Terroir</h3><p>' + note.terroir + '</p></section>' +
      '<section><h3>The wines</h3><p>' + note.wines + '</p></section>' +
      '<p class="ref-src">Sources: ' + note.sources + '</p></div>';
  } else {
    html += '<div class="ref-prose"><p class="ref-src">No sourced note for this ' +
      'appellation yet.</p></div>';
  }

  html += '<h3 class="ref-listhead">The vintages</h3>' +
    '<p class="ref-lead">Where a critic published a rating for a particular ' +
    'château it is shown on that château. What the season itself did is ' +
    'known for the appellation whether or not any one wine was rated, so it ' +
    'is recorded here.</p>' + vintageTable(r) +
    '<h3 class="ref-listhead">The châteaux</h3>' +
    estateGrid(list, function (ch) {
      var d = clsDef(ch.cls);
      return d ? d.name : 'Unclassified';
    }, true);

  el.appellations.innerHTML = html;
  document.getElementById('apBack').addEventListener('click', function () {
    state.apPage = null; renderAppellations(); window.scrollTo(0, 0);
  });
  document.getElementById('apMap').addEventListener('click', function () {
    showRegionOnMap(id);
  });
  wireEstateCards(el.appellations);
}

function showRegionOnMap(id) {
  openCollection(null);
  setTimeout(function () { enterRegion(id); }, 80);
}

/* ----------------------------- classifications ----------------------------- */
function renderClassifications() {
  if (state.clsPage) return renderClassificationPage(state.clsPage);

  var official = CLS.filter(function (c) {
    var n = CLS_NOTES[c.id]; return n && n.official;
  });
  var unranked = CLS.filter(function (c) {
    var n = CLS_NOTES[c.id]; return !n || !n.official;
  });

  var html = '<div class="ref-intro"><h2>The classifications</h2>' +
    '<p>Bordeaux has no single hierarchy. It has six official ones, drawn up ' +
    'at different times, on different banks, by different people and for ' +
    'different reasons — and great appellations that were never ranked at all. ' +
    'A classification ranks estates; that is not the same thing as ' +
    '<button class="linkish" id="toAp">an appellation</button>.</p></div>' +
    '<section class="ref-band"><div class="ref-band-head"><h3>Official classifications</h3>' +
    '<span>Rankings with legal standing</span></div><div class="ref-grid">';

  official.forEach(function (c) {
    var n = CLS_NOTES[c.id], count = countIn(c.id);
    html += '<button class="apcard" data-cls="' + c.id + '">' +
      '<h4>' + c.name + '</h4>' +
      '<span class="apyear">' + c.region + (c.year ? ' · ' + c.year : '') + '</span>' +
      '<p>' + c.blurb + '</p>' +
      '<span class="apcount">' + count + ' estates' +
        (n && n.superseded ? ' · <b class="stale">list superseded</b>' : '') +
      '</span></button>';
  });
  html += '</div></section>';

  html += '<section class="ref-band"><div class="ref-band-head">' +
    '<h3>Never classified</h3><span>Groupings of appellations, not ranks</span>' +
    '</div><div class="ref-grid">';
  unranked.forEach(function (c) {
    html += '<button class="apcard apcard-quiet" data-cls="' + c.id + '">' +
      '<h4>' + c.name + '</h4><p>' + c.blurb + '</p>' +
      '<span class="apcount">' + countIn(c.id) + ' estates · no classification</span>' +
      '</button>';
  });
  html += '</div></section>';

  el.classifications.innerHTML = html;
  Array.prototype.forEach.call(el.classifications.querySelectorAll('.apcard'), function (b) {
    b.addEventListener('click', function () {
      state.clsPage = b.dataset.cls; renderClassifications(); window.scrollTo(0, 0);
    });
  });
  var t = document.getElementById('toAp');
  if (t) t.addEventListener('click', function () { setView('appellations'); });
}

function renderClassificationPage(id) {
  var c = clsDef(id), n = CLS_NOTES[id];
  if (!c) { state.clsPage = null; return renderClassifications(); }
  var list = CH.filter(function (ch) { return inCollection(ch, id); })
               .sort(function (x, y) {
                 return (x.growth - y.growth) || x.name.localeCompare(y.name);
               });

  var html = '<div class="ref-head">' +
    '<button class="ref-back" id="clsBack">← All classifications</button>' +
    '<h2>' + c.name + '</h2>' +
    '<span class="ref-sub">' + c.region + (c.year ? ' · ' + c.year : '') +
      ' · ' + list.length + ' estates</span>' +
    '<span class="ref-head-gap"></span>' +
    '<button class="ref-map" id="clsMap">See them on the map</button></div>';

  if (n) {
    html += '<div class="ref-prose">' +
      '<section><h3>How it came about</h3><p>' + n.origin + '</p></section>' +
      '<section><h3>How and when it is revised</h3><p>' + n.revision + '</p></section>';
    if (n.listEdition) {
      html += '<section><h3>The list shown here</h3><p>' + n.listEdition + '</p>' +
        (n.currency ? '<p class="ref-warn"><b>' +
          (n.superseded ? 'Superseded.' : 'Note.') + '</b> ' + n.currency +
          '</p>' : '') +
        '</section>';
    }
    html += '<p class="ref-src">Sources: ' + n.sources + '</p></div>';
  }

  html += '<h3 class="ref-listhead">The estates</h3>' +
    estateGrid(list, function (ch) {
      var t = tierDef(ch);
      return t ? t.label : 'Listed';
    });

  el.classifications.innerHTML = html;
  document.getElementById('clsBack').addEventListener('click', function () {
    state.clsPage = null; renderClassifications(); window.scrollTo(0, 0);
  });
  document.getElementById('clsMap').addEventListener('click', function () {
    openCollection(id);
  });
  wireEstateCards(el.classifications);
}

/* Both reference pages, rebuilt — used on load and on a theme change. */
function renderReference() {
  renderAppellations();
  renderClassifications();
}

function openCollection(id) {
  state.cls = id;
  state.region = null;
  state.tiers = {};
  state.q = ''; state.appellation = ''; state.vintage = '';
  if (el.search) el.search.value = '';
  if (el.appellation) el.appellation.value = '';
  if (el.vintage) el.vintage.value = '';
  buildChips();
  buildAppellationSelect();
  setView('producers');
  refresh();
}

/* ===========================================================================
   9. PRODUCER LIST
   =========================================================================== */
function groupsForView() {
  if (state.cls) {
    var d = clsDef(state.cls);
    return d.tiers.map(function (t) {
      return { cls: state.cls, growth: t.growth, label: t.label, note: t.note };
    });
  }
  var out = [];
  CLS.forEach(function (c) {
    c.tiers.forEach(function (t) {
      out.push({ cls: c.id, growth: t.growth, label: t.label,
                 note: c.name + ' · ' + t.note });
    });
  });
  return out;
}

function renderList() {
  var list = visibleChateaux();
  var scope = state.cls ? countIn(state.cls) : CH.length;
  el.resultcount.textContent = list.length + ' of ' + scope + ' estates';

  if (!list.length) {
    el.paneList.innerHTML = '<p class="empty">No estate matches these filters. ' +
      'Try clearing the search box or lowering the minimum score.</p>';
    return;
  }

  var html = '';
  groupsForView().forEach(function (g) {
    var members = list.filter(function (ch) {
      return inCollection(ch, g.cls) && ch.growth === g.growth;
    });
    if (!members.length) return;
    var swatch = cssVar('--rank-' + Math.min(5, g.growth));
    html += '<section class="growth-group">' +
      '<div class="growth-head">' +
        '<span class="rankbar" style="background:' + swatch + '"></span>' +
        '<h2>' + g.label + '</h2>' +
        '<span class="count">' + g.note + ' · ' + members.length + '</span>' +
      '</div><div class="pgrid">';
    members.forEach(function (ch) {
      var sub = state.vintage ? scoreFor(ch, Number(state.vintage)) : null;
      html += '<button class="pcard' + (state.active === ch.id ? ' is-active' : '') +
        '" data-ch="' + ch.id + '" style="border-left-color:' + swatch + '">' +
        '<span class="pname">' + ch.name + '</span>' +
        '<span class="pmeta">' + ch.appellation +
          (ch.commune && ch.commune !== ch.appellation ? ' · ' + ch.commune : '') + '</span>' +
        '<span class="pfoot">' + (ch.ha ? ch.ha + ' ha' : '') +
          (sub && !sub.none ? ' · <b>' + sub.score + '</b> in ' + state.vintage : '') +
        '</span></button>';
    });
    html += '</div></section>';
  });
  el.paneList.innerHTML = html;

  Array.prototype.forEach.call(el.paneList.querySelectorAll('.pcard'), function (b) {
    b.addEventListener('click', function () { openDrawer(b.dataset.ch); });
  });
}

/* ===========================================================================
   10. MAP — two drawn maps, no tile service
   ---------------------------------------------------------------------------
   Overview:  land, ocean, estuary, rivers and the outline of every
              appellation, with the type placed so nothing overlaps. No
              estate dots — this map is for finding your region.
   Region:    one appellation, framed and named, with its châteaux and the
              villages around them. Click an outline to go in; ← to come out.
   =========================================================================== */
var G = window.BDX_MAP;
var MB = G.bounds, MS = G.size;
var view = { k: 1, tx: 0, ty: 0 };
var svgEl, zoomG, markerG, mapTip, mapReady = false;
var mapDragged = function () { return false; };

function isDark() {
  var t = document.documentElement.getAttribute('data-theme');
  return t === 'dark' || (!t && window.matchMedia('(prefers-color-scheme: dark)').matches);
}

function px(lng) { return (lng - MB.west) / (MB.east - MB.west) * MS.w; }
function py(lat) { return (MB.north - lat) / (MB.north - MB.south) * MS.h; }

/* Catmull-Rom through the points as cubic Béziers, so coastlines and
   appellation outlines read as drawn curves rather than polygons. */
function smooth(pts, closed) {
  var P = pts.map(function (p) { return [px(p[1]), py(p[0])]; });
  if (P.length < 2) return '';
  var d = 'M' + P[0][0].toFixed(1) + ',' + P[0][1].toFixed(1);
  var n = P.length;
  for (var i = 0; i < (closed ? n : n - 1); i++) {
    var p0 = closed ? P[(i - 1 + n) % n] : P[Math.max(0, i - 1)];
    var p1 = P[i];
    var p2 = closed ? P[(i + 1) % n] : P[Math.min(n - 1, i + 1)];
    var p3 = closed ? P[(i + 2) % n] : P[Math.min(n - 1, i + 2)];
    var c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    var c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += 'C' + c1[0].toFixed(1) + ',' + c1[1].toFixed(1) + ' ' +
                c2[0].toFixed(1) + ',' + c2[1].toFixed(1) + ' ' +
                p2[0].toFixed(1) + ',' + p2[1].toFixed(1);
  }
  return d + (closed ? 'Z' : '');
}

function regionById(id) {
  for (var i = 0; i < G.regions.length; i++) if (G.regions[i].id === id) return G.regions[i];
  return null;
}
function inRegion(ch, r) { return r.apps.indexOf(ch.appellation) !== -1; }

/* How many estates the current filters leave in each region. */
function regionCount(r) {
  var n = 0, q = deaccent(state.q.trim().toLowerCase());
  for (var i = 0; i < CH.length; i++) {
    var ch = CH[i];
    if (!inRegion(ch, r)) continue;
    if (state.cls && !inCollection(ch, state.cls)) continue;
    if (q && deaccent(ch.name.toLowerCase()).indexOf(q) === -1) continue;
    n++;
  }
  return n;
}

function ringsPath(r) {
  var parts = r.rings.map(function (ring) { return smooth(ring, true); });
  (r.holes || []).forEach(function (ring) { parts.push(smooth(ring, true)); });
  return parts.join(' ');
}
function regionBBox(r) {
  var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  r.rings.forEach(function (ring) {
    ring.forEach(function (p) {
      var x = px(p[1]), y = py(p[0]);
      if (x < x0) x0 = x; if (x > x1) x1 = x;
      if (y < y0) y0 = y; if (y > y1) y1 = y;
    });
  });
  return { x0: x0, y0: y0, x1: x1, y1: y1 };
}

/* The SVG letterboxes into its pane, so viewBox units are not screen
   pixels. Map type, town marks and estate dots are counter-scaled by the
   zoom AND by that fit factor, which lets their sizes be read as CSS px. */
function svgScale() {
  if (!svgEl) return 1;
  var r = svgEl.getBoundingClientRect();
  if (!r.width || !r.height) return 1;
  return Math.min(r.width / MS.w, r.height / MS.h) || 1;
}
function screenInv() { return 1 / (view.k * svgScale()); }

/* --------------------------- base geography ---------------------------- */
/* The water is painted after the appellations, not before. An appellation's
   boundary is a line with width, and where it runs along the bank half of
   that line used to fall on the river — a pale rule laid across the Gironde.
   Drawing the water last lets the river cover what strays into it, so the
   river keeps the shape it has and the appellations get a clean edge. */
function waterDefsSvg() {
  /* Courses the water names are set along. They live inside the zoomed group
     with the geography, so the text rides the river at every zoom; only the
     glyph size is held constant, in rescaleLabels. */
  var s = '<defs>' +
    '<path id="wp-gironde" fill="none" d="' + smooth(G.girondeCentre) + '"/>' +
    '<path id="wp-garonne" fill="none" d="' + smooth(G.garonne) + '"/>' +
    '<path id="wp-dordogne" fill="none" d="' + smooth(G.dordogne) + '"/>' +
    '</defs>';
  return s;
}

/* Ocean, bassin and estuary are one body of water, so they are drawn in one
   group and the group carries the transparency. Painted as three separate
   translucent shapes they darkened wherever they overlapped, which drew a
   seam across open water. */
function waterSvg() {
  var s = '<g class="m-water-body">' +
    '<path d="' + smooth(G.sea, true) + '"/>' +
    '<path d="' + smooth(G.arcachon, true) + '"/>' +
    '<path d="' + smooth(G.estuary, true) + '"/>' +
    '</g>';
  s += '<path class="m-river m-river-lg" d="' + smooth(G.garonne) + '"/>';
  s += '<path class="m-river m-river-md" d="' + smooth(G.dordogne) + '"/>';
  return s;
}

/* --------------------------- overview map ------------------------------ */
function overviewSvg() {
  var s = waterDefsSvg();

  /* Outlines first, so type always sits on top of them. */
  G.regions.forEach(function (r) {
    var n = regionCount(r);
    s += '<path class="m-area' + (n ? '' : ' empty') + '" data-region="' + r.id +
         '" d="' + ringsPath(r) + '"><title>' + r.name +
         ' — ' + n + ' château' + (n === 1 ? '' : 'x') + '</title></path>';
  });

  /* Leader lines from the narrow riverside communes out to open country. */
  G.regions.forEach(function (r) {
    var an = r.leader || r.label;
    s += '<line class="m-leader" data-for="' + r.id + '" x1="' + px(r.label[1]).toFixed(1) +
         '" y1="' + py(r.label[0]).toFixed(1) + '" x2="' + px(an[1]).toFixed(1) +
         '" y2="' + py(an[0]).toFixed(1) + '"/>';
  });

  G.regions.forEach(function (r) {
    var n = regionCount(r);
    s += '<g class="m-lbl m-area-lbl' + (n ? '' : ' empty') + '" data-region="' + r.id +
         '" data-x="' + px(r.label[1]).toFixed(1) + '" data-y="' + py(r.label[0]).toFixed(1) + '">' +
         '<text class="m-area-name" y="0">' + r.name.toUpperCase() + '</text></g>';
  });

  s += waterSvg() + waterLabelsSvg(true) + townsSvg(function (t) { return t.ov; });
  return s;
}

/* ---------------------------- region map ------------------------------- */
function regionSvg(r) {
  var s = waterDefsSvg();

  G.regions.forEach(function (o) {
    if (o.id === r.id) return;
    s += '<path class="m-area ghost" data-region="' + o.id + '" d="' +
         ringsPath(o) + '"><title>' + o.name + '</title></path>';
  });
  s += '<path class="m-area active" d="' + ringsPath(r) + '"/>';

  /* Neighbouring appellations keep their names, small and quiet. */
  G.regions.forEach(function (o) {
    if (o.id === r.id) return;
    s += '<g class="m-lbl m-area-lbl ghost" data-region="' + o.id +
         '" data-x="' + px(o.label[1]).toFixed(1) + '" data-y="' + py(o.label[0]).toFixed(1) + '">' +
         '<text class="m-area-name" y="0">' + o.name.toUpperCase() + '</text></g>';
  });

  var bb = regionBBox(r), pad = 0.22;
  var latPad = (bb.y1 - bb.y0), lngPad = (bb.x1 - bb.x0);
  s += waterSvg() + waterLabelsSvg(false) + townsSvg(function (t) {
    var x = px(t.lng), y = py(t.lat);
    return x > bb.x0 - lngPad * pad - 40 && x < bb.x1 + lngPad * pad + 40 &&
           y > bb.y0 - latPad * pad - 40 && y < bb.y1 + latPad * pad + 40;
  });

  s += '<g id="mapMarkers"></g>';
  return s;
}

function pathLabelsSvg() {
  return (G.pathLabels || []).map(function (w) {
    return '<text class="m-path-label ' + w.cls + '" data-size="' + w.size +
      '" data-dy="' + (w.dy || 0) + '">' +
      '<textPath href="#wp-' + w.path + '" startOffset="' + w.offset +
      '" text-anchor="middle">' + w.n + '</textPath></text>';
  }).join('');
}

function waterLabelsSvg(overviewOnly) {
  return pathLabelsSvg() + G.waterLabels.filter(function (w) { return overviewOnly ? w.ov : true; })
    .map(function (w) {
      return '<g class="m-lbl m-water-g" data-x="' + px(w.lng).toFixed(1) +
        '" data-y="' + py(w.lat).toFixed(1) + '">' +
        '<text class="m-water-label" font-size="' + w.size +
        '" transform="rotate(' + w.rot + ')">' + w.n + '</text></g>';
    }).join('');
}

function townsSvg(pred) {
  return G.towns.filter(pred).map(function (t) {
    var r = t.t === 1 ? 5 : t.t === 2 ? 3.8 : 3;
    var s = '<g class="m-lbl m-town t' + t.t + '" data-x="' + px(t.lng).toFixed(1) +
            '" data-y="' + py(t.lat).toFixed(1) + '">';
    if (t.t === 1) {
      s += '<circle class="m-town-dot" cx="0" cy="0" r="' + r + '"/>' +
           '<circle class="m-town-ring" cx="0" cy="0" r="' + (r + 3) + '"/>';
    } else {
      s += '<rect class="m-town-dot" x="' + (-r) + '" y="' + (-r) + '" width="' + (r * 2) +
           '" height="' + (r * 2) + '" transform="rotate(45)"/>';
    }
    return s + '<text class="m-town-label" x="' + t.dx + '" y="' + t.dy +
           '" text-anchor="' + t.anchor + '">' + t.n + '</text></g>';
  }).join('');
}

/* ------------------------------ assembly ------------------------------- */
function initMap() {
  var host = document.getElementById('map');
  host.innerHTML =
    '<svg id="mapSvg" viewBox="0 0 ' + MS.w + ' ' + MS.h + '" ' +
      'preserveAspectRatio="xMidYMid meet" role="img" ' +
      'aria-label="Map of the Bordeaux wine region">' +
      /* SVG clips to the element box, not to the viewBox, so without this
         the sea and anything else beyond the frame bleeds across the page. */
      '<defs><clipPath id="mapClip"><rect x="0" y="0" width="' + MS.w +
        '" height="' + MS.h + '"/></clipPath></defs>' +
      '<g clip-path="url(#mapClip)">' +
        '<rect class="m-land" x="0" y="0" width="' + MS.w + '" height="' + MS.h + '"/>' +
        '<g id="mapZoom"></g>' +
      '</g>' +
      '<g class="m-scale" id="mapScale"></g>' + compass() +
      '<rect class="m-frame" x="1" y="1" width="' + (MS.w - 2) + '" height="' + (MS.h - 2) + '"/>' +
    '</svg>' +
    '<div class="map-tip" id="mapTip"></div>' +
    '<div class="map-head" id="mapHead"></div>' +
    '<div class="map-zoom">' +
      '<button id="zIn" aria-label="Zoom in">+</button>' +
      '<button id="zOut" aria-label="Zoom out">−</button>' +
    '</div>';

  svgEl = document.getElementById('mapSvg');
  zoomG = document.getElementById('mapZoom');
  mapTip = document.getElementById('mapTip');
  mapReady = true;
  wireMapInteraction();
  renderMap();
}

function compass() {
  return '<g class="m-compass" transform="translate(' + (MS.w - 34) + ',40)">' +
    '<path d="M0,-17 L5,4 L0,0 L-5,4 Z"/><text y="19" text-anchor="middle">N</text></g>';
}

function renderMap() {
  if (!mapReady) return;
  hideMapTip();
  var r = state.region ? regionById(state.region) : null;
  zoomG.innerHTML = r ? regionSvg(r) : overviewSvg();
  markerG = document.getElementById('mapMarkers');

  var shown = visibleChateaux().length;
  var d = state.cls ? clsDef(state.cls) : null;
  document.getElementById('mapHead').innerHTML =
    (r ? '<button class="map-back" id="mapBack">← All appellations</button>' +
         '<span class="map-title">' + r.name + '</span>' +
         '<button class="map-back" id="mapRead">Read the appellation</button>'
       : '<span class="map-title">' + (d ? d.name : 'All of Bordeaux') + '</span>' +
         '<span class="map-hint">Click an appellation to see its châteaux</span>') +
    '<span class="map-head-gap"></span>' +
    '<button class="map-back" id="mapFilters">Filters</button>' +
    '<button class="map-back" id="mapList">Châteaux ' + shown + '</button>';

  var back = document.getElementById('mapBack');
  if (back) back.addEventListener('click', exitRegion);
  var readBtn = document.getElementById('mapRead');
  if (readBtn) readBtn.addEventListener('click', function () {
    state.apPage = r.id;
    setView('appellations');
    renderAppellations();
    window.scrollTo(0, 0);
  });
  var filtBtn = document.getElementById('mapFilters');
  if (filtBtn) filtBtn.addEventListener('click', function () {
    el.filters.classList.toggle('open');
  });
  var listBtn = document.getElementById('mapList');
  if (listBtn) listBtn.addEventListener('click', function () {
    el.paneList.classList.toggle('is-open');
  });

  Array.prototype.forEach.call(zoomG.querySelectorAll('[data-region]'), function (node) {
    node.addEventListener('click', function (e) {
      if (mapDragged()) return;
      e.stopPropagation();
      enterRegion(node.getAttribute('data-region'));
    });
  });

  if (r) fitTo(regionBBox(r), 46); else fitTo({ x0: 0, y0: 0, x1: MS.w, y1: MS.h }, 0);
  rescaleLabels();
  nudgeWaterLabels();
  placeTownLabels();
  placePathLabels();
  placeAreaLabels();
  updateScaleBar();
  renderLegend(r);
  if (r) renderMarkers();
}

/* The rank key belongs with the dots, so it appears only on a region map,
   and lists just the ranks actually present there. */
function renderLegend(r) {
  var box = document.getElementById('mapLegend');
  if (!box) return;
  if (!r) { box.style.display = 'none'; return; }
  var list = visibleChateaux().filter(function (ch) { return inRegion(ch, r); });
  if (!list.length) { box.style.display = 'none'; return; }

  var seen = [], approx = false;
  list.forEach(function (ch) {
    if (ch.approx) approx = true;
    var key = ch.cls + ':' + ch.growth;
    for (var i = 0; i < seen.length; i++) if (seen[i].key === key) return;
    seen.push({ key: key, growth: ch.growth, label: rankLabel(ch),
                cls: ch.cls, n: 0 });
  });
  list.forEach(function (ch) {
    var key = ch.cls + ':' + ch.growth;
    for (var i = 0; i < seen.length; i++) if (seen[i].key === key) seen[i].n++;
  });
  seen.sort(function (a, b) { return a.cls === b.cls ? a.growth - b.growth : a.cls < b.cls ? -1 : 1; });

  box.style.display = '';
  box.innerHTML = '<h4>' + r.name + '</h4><ul>' +
    seen.map(function (t) {
      return '<li><span class="swatch" style="background:' +
        cssVar('--rank-' + Math.min(5, t.growth)) + '"></span>' + t.label +
        ' <span style="color:var(--text-muted)">' + t.n + '</span></li>';
    }).join('') + '</ul>' +
    (approx ? '<div style="margin-top:6px;color:var(--text-muted)">Faded dots are placed by ' +
              'appellation, not by surveyed position.</div>' : '');
}

function enterRegion(id) {
  state.region = id;
  renderMap();
  renderList();
  el.paneList.classList.add('is-open');
  var d = regionById(id);
  if (el.crumb) {
    var c = state.cls ? clsDef(state.cls) : null;
    el.crumb.textContent = (c ? c.name + ' · ' : '') + (d ? d.name : '');
  }
}
function exitRegion() {
  state.region = null;
  hideMapTip();
  el.paneList.classList.remove('is-open');
  renderMap();
  renderList();
  refreshCrumb();
}

function fitTo(bb, pad) {
  var w = Math.max(40, (bb.x1 - bb.x0) + pad * 2);
  var h = Math.max(40, (bb.y1 - bb.y0) + pad * 2);
  view.k = Math.max(1, Math.min(14, Math.min(MS.w / w, MS.h / h)));
  view.tx = MS.w / 2 - view.k * (bb.x0 + bb.x1) / 2;
  view.ty = MS.h / 2 - view.k * (bb.y0 + bb.y1) / 2;
  applyView();
}

/* Keep the drawing covering the frame: you can never drag empty space into
   view, and at full zoom-out (k = 1) the only legal offset is 0, so the map
   simply does not move. */
function clampView() {
  var minTx = MS.w * (1 - view.k), minTy = MS.h * (1 - view.k);
  view.tx = Math.min(0, Math.max(minTx, view.tx));
  view.ty = Math.min(0, Math.max(minTy, view.ty));
}

function applyView() {
  if (!zoomG) return;
  clampView();
  if (svgEl) svgEl.classList.toggle('pannable', view.k > 1.001);
  zoomG.setAttribute('transform',
    'translate(' + view.tx.toFixed(2) + ',' + view.ty.toFixed(2) + ') scale(' + view.k.toFixed(4) + ')');
}

function setZoom(k, cx, cy) {
  k = Math.max(1, Math.min(14, k));
  if (cx === undefined) { cx = MS.w / 2; cy = MS.h / 2; }
  var wx = (cx - view.tx) / view.k, wy = (cy - view.ty) / view.k;
  var changed = Math.abs(k - view.k) > 1e-4;
  view.k = k; view.tx = cx - wx * k; view.ty = cy - wy * k;
  applyView();
  if (changed) {
    updateScaleBar(); rescaleLabels(); nudgeWaterLabels();
    placeTownLabels(); placePathLabels(); placeAreaLabels();
    scheduleMarkerResize();
  }
}

var resizeTimer = null;
function scheduleMarkerResize() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(renderMarkers, 70);
}

/* ---------------------------------------------------------------------
   Automatic label placement.

   With 29 appellations the names cannot be positioned by hand: every change
   to a shape, a count or the window moves them. Each name starts where it
   is written and, if that collides, is tried at rings of increasing radius
   until it finds clear space, with its leader line redrawn to follow. A
   name may travel a long way from its shape — that is how a crowded wine
   map has always been drawn. Largest appellations are placed first, since
   moving them far is what costs the most meaning.
   --------------------------------------------------------------------- */
var PLACE_OFFSETS = (function () {
  var out = [[0, 0]];
  [18, 34, 54, 80, 112, 150, 196, 248].forEach(function (rad) {
    for (var a = 0; a < 16; a++) {
      var t = a / 16 * Math.PI * 2;
      out.push([Math.round(Math.cos(t) * rad * 1.5), Math.round(Math.sin(t) * rad)]);
    }
  });
  return out;
})();

function rectsHit(a, b) {
  return !(a.right <= b.left || b.right <= a.left ||
           a.bottom <= b.top || b.bottom <= a.top);
}
function overlapArea(a, b) {
  if (!rectsHit(a, b)) return 0;
  return (Math.min(a.right, b.right) - Math.max(a.left, b.left)) *
         (Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
}

/* Where a leader points: the written anchor, or the middle of the shape. */
function regionAnchor(r) {
  if (r.leader) return [px(r.leader[1]), py(r.leader[0])];
  var bb = regionBBox(r);
  return [(bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2];
}

/* The drawn frame sits inside the <svg> element, because the viewBox is
   letterboxed into it. Type must stay inside the FRAME, not merely inside
   the element — otherwise names cross the border drawn round the map. */
function frameRect() {
  var r = svgEl.getBoundingClientRect();
  var sc = Math.min(r.width / MS.w, r.height / MS.h);
  var w = MS.w * sc, h = MS.h * sc;
  var left = r.left + (r.width - w) / 2, top = r.top + (r.height - h) / 2;
  return { left: left, top: top, right: left + w, bottom: top + h };
}

/* Water names are anchored to a feature rather than placed freely, but the
   frame changes size with the window and the chrome above it, while their
   type stays a constant size on screen. At a small frame they can therefore
   push past the border — so they are pulled back inside it here, before the
   appellation names are placed around them. */
function nudgeWaterLabels() {
  if (!zoomG || !svgEl) return;
  var inv = screenInv(), fr = frameRect(), pad = 8;
  Array.prototype.forEach.call(zoomG.querySelectorAll('.m-water-g'), function (g) {
    var bx = parseFloat(g.getAttribute('data-x'));
    var by = parseFloat(g.getAttribute('data-y'));
    g.setAttribute('transform', 'translate(' + bx + ',' + by + ') scale(' + inv + ')');
    /* The clamp below keeps a name inside the frame. On the overview that
       is right; zoomed in it dragged names for water a hundred kilometres
       away into the corner of a view they have nothing to do with. */
    var at = vbToScreen(bx, by);
    if (at[0] < fr.left || at[0] > fr.right || at[1] < fr.top || at[1] > fr.bottom) {
      g.style.display = 'none';
      return;
    }
    g.style.display = '';
    var r = g.getBoundingClientRect();
    var dx = 0, dy = 0;
    if (r.left < fr.left + pad) dx = fr.left + pad - r.left;
    else if (r.right > fr.right - pad) dx = fr.right - pad - r.right;
    if (r.top < fr.top + pad) dy = fr.top + pad - r.top;
    else if (r.bottom > fr.bottom - pad) dy = fr.bottom - pad - r.bottom;
    if (dx || dy) {
      g.setAttribute('transform',
        'translate(' + (bx + dx * inv) + ',' + (by + dy * inv) + ') scale(' + inv + ')');
    }
  });
}

/* Where a point of the drawing lands on screen, zoom and letterboxing
   both taken into account. */
function vbToScreen(x, y) {
  var fr = frameRect();
  var sx = (fr.right - fr.left) / MS.w, sy = (fr.bottom - fr.top) / MS.h;
  return [fr.left + (x * view.k + view.tx) * sx,
          fr.top + (y * view.k + view.ty) * sy];
}

/* Town names are pinned to their town, not placed freely, so when the view
   zooms they can end up half outside the frame and get cut by the clip.
   A town off the edge loses its name and its mark; a town on the edge whose
   name would be clipped keeps the mark and loses the name. */
function placeTownLabels() {
  if (!zoomG || !svgEl) return;
  var fr = frameRect();
  Array.prototype.forEach.call(zoomG.querySelectorAll('.m-town'), function (g) {
    g.style.display = '';
    var label = g.querySelector('.m-town-label');
    if (label) label.style.display = '';
    var dot = g.querySelector('.m-town-dot');
    if (!dot) return;
    var d = dot.getBoundingClientRect();
    var cx = (d.left + d.right) / 2, cy = (d.top + d.bottom) / 2;
    if (cx < fr.left || cx > fr.right || cy < fr.top || cy > fr.bottom) {
      g.style.display = 'none';
      return;
    }
    if (!label) return;
    var r = label.getBoundingClientRect();
    if (r.width && (r.left < fr.left + 2 || r.right > fr.right - 2 ||
                    r.top < fr.top + 2 || r.bottom > fr.bottom - 2)) {
      label.style.display = 'none';
    }
  });
}

/* A river name is set on a textPath, so it goes where the river goes. Zoomed
   in, the stretch carrying the name often lies outside the frame and the name
   is cut by the clip. Slide it along its own river to a stretch that is fully
   in view, and drop it only if the river has no such stretch left. */
function placePathLabels() {
  if (!zoomG || !svgEl) return;
  var fr = frameRect();
  var taken = [];
  Array.prototype.forEach.call(
    zoomG.querySelectorAll('.m-town-label,.m-water-label'), function (e) {
      if (e.style.display === 'none') return;
      var r = e.getBoundingClientRect();
      if (r.width) taken.push(r);
    });

  Array.prototype.forEach.call(zoomG.querySelectorAll('.m-path-label'), function (t) {
    var tp = t.querySelector('textPath');
    if (!tp) return;
    var home = t.getAttribute('data-offset');
    if (home === null) {
      home = parseFloat(tp.getAttribute('startOffset'));
      t.setAttribute('data-offset', home);
    } else {
      home = parseFloat(home);
    }
    t.style.display = '';

    /* The written offset first, so the overview keeps the positions that
       were chosen for it; then outwards along the river from there. */
    var tries = [home];
    for (var d = 3; d <= 100; d += 3) {
      if (home + d <= 99) tries.push(home + d);
      if (home - d >= 1) tries.push(home - d);
    }
    for (var i = 0; i < tries.length; i++) {
      tp.setAttribute('startOffset', tries[i] + '%');
      var r = t.getBoundingClientRect();
      if (!r.width) continue;
      if (r.left < fr.left + 8 || r.right > fr.right - 8 ||
          r.top < fr.top + 8 || r.bottom > fr.bottom - 8) continue;
      var clash = false;
      for (var m = 0; m < taken.length; m++) if (overlapArea(r, taken[m]) > 0) { clash = true; break; }
      if (clash) continue;
      taken.push(r);
      return;
    }
    tp.setAttribute('startOffset', home + '%');
    t.style.display = 'none';
  });
}

function placeAreaLabels() {
  if (!zoomG || !svgEl) return;
  var inv = screenInv();
  var pane = frameRect();
  /* The written label positions were composed for the whole region in one
     frame — several sit far out in open country on a leader line, which is
     what keeps the overview readable. Zoomed in, those positions are
     meaningless and send a name a long way from its appellation, so past
     the overview the name is placed on the shape itself instead. */
  var zoomed = view.k > 1.05;

  var fixed = [];
  Array.prototype.forEach.call(
    zoomG.querySelectorAll('.m-town-label,.m-water-label,.m-path-label'),
    function (e) {
      if (e.style.display === 'none') return;
      var r = e.getBoundingClientRect();
      if (r.width) fixed.push(r);
    });

  var labels = Array.prototype.slice.call(zoomG.querySelectorAll('.m-area-lbl'));
  labels.forEach(function (g) {
    var reg = regionById(g.getAttribute('data-region'));
    var bb = reg ? regionBBox(reg) : { x0: 0, x1: 1, y0: 0, y1: 1 };
    g.setAttribute('data-area', ((bb.x1 - bb.x0) * (bb.y1 - bb.y0)).toFixed(0));
  });
  labels.sort(function (a, b) {
    return parseFloat(b.getAttribute('data-area')) - parseFloat(a.getAttribute('data-area'));
  });

  labels.forEach(function (g) {
    var id = g.getAttribute('data-region');
    var reg = regionById(id);
    var lead = zoomG.querySelector('.m-leader[data-for="' + id + '"]');
    if (!reg) return;

    /* An appellation off the edge of the view gets no name at all, which
       also frees room for the ones you can actually see. */
    var bb = regionBBox(reg);
    var tl = vbToScreen(bb.x0, bb.y0), br = vbToScreen(bb.x1, bb.y1);
    var visible = br[0] > pane.left && tl[0] < pane.right &&
                  br[1] > pane.top && tl[1] < pane.bottom;
    g.style.display = visible ? '' : 'none';
    if (lead) lead.style.display = (visible && !zoomed) ? '' : 'none';
    if (!visible) return;

    var anchor = regionAnchor(reg);
    var bx = zoomed ? anchor[0] : parseFloat(g.getAttribute('data-x'));
    var by = zoomed ? anchor[1] : parseFloat(g.getAttribute('data-y'));

    var best = null;
    for (var i = 0; i < PLACE_OFFSETS.length; i++) {
      /* Zoomed in, a name may only shuffle a short way to dodge a clash:
         it must stay recognisably on its own appellation. */
      if (zoomed && (Math.abs(PLACE_OFFSETS[i][0]) > 90 ||
                     Math.abs(PLACE_OFFSETS[i][1]) > 60)) continue;
      var ox = bx + PLACE_OFFSETS[i][0] * inv;
      var oy = by + PLACE_OFFSETS[i][1] * inv;
      g.setAttribute('transform', 'translate(' + ox + ',' + oy + ') scale(' + inv + ')');
      var r = g.getBoundingClientRect();
      if (r.left < pane.left + 10 || r.right > pane.right - 10 ||
          r.top < pane.top + 10 || r.bottom > pane.bottom - 10) continue;
      var area = 0;
      for (var m = 0; m < fixed.length; m++) area += overlapArea(r, fixed[m]);
      if (area === 0) { best = [ox, oy, 0]; break; }
      if (!best || area < best[2]) best = [ox, oy, area];
    }
    /* No offset fitted inside the frame. Falling back to the bare anchor
       used to put the name half outside the border — which is how a
       neighbour whose shape only clips the view got its name drawn across
       the frame. Take the anchor only if it too sits clear; else no name. */
    if (!best) {
      g.setAttribute('transform', 'translate(' + bx + ',' + by + ') scale(' + inv + ')');
      var ar = g.getBoundingClientRect();
      if (ar.left < pane.left + 10 || ar.right > pane.right - 10 ||
          ar.top < pane.top + 10 || ar.bottom > pane.bottom - 10) {
        g.style.display = 'none';
        if (lead) lead.style.display = 'none';
        return;
      }
      best = [bx, by, 0];
    }
    g.setAttribute('transform', 'translate(' + best[0] + ',' + best[1] + ') scale(' + inv + ')');
    fixed.push(g.getBoundingClientRect());

    /* A leader is for a name that had to stand away from its appellation.
       Where the name sits on the shape itself there is nothing to lead to,
       and the line only clutters it. */
    var near = Math.hypot(best[0] - anchor[0], best[1] - anchor[1]) < 58;
    if (lead && near) lead.style.display = 'none';

    if (lead && !zoomed && !near) {
      lead.setAttribute('x1', best[0].toFixed(1));
      lead.setAttribute('y1', best[1].toFixed(1));
      lead.setAttribute('x2', anchor[0].toFixed(1));
      lead.setAttribute('y2', anchor[1].toFixed(1));
    }
  });
}

function rescaleLabels() {
  if (!zoomG) return;
  var inv = screenInv().toFixed(4);
  Array.prototype.forEach.call(zoomG.querySelectorAll('.m-lbl'), function (g) {
    g.setAttribute('transform',
      'translate(' + g.getAttribute('data-x') + ',' + g.getAttribute('data-y') +
      ') scale(' + inv + ')');
  });
  Array.prototype.forEach.call(zoomG.querySelectorAll('.m-area, .m-leader'), function (p) {
    p.setAttribute('stroke-width', (1.4 * screenInv()).toFixed(2));
  });
  /* Water names ride the river path, so they cannot be counter-scaled by a
     transform — their type size is set directly instead. */
  var finv = screenInv();
  Array.prototype.forEach.call(zoomG.querySelectorAll('.m-path-label'), function (t) {
    t.setAttribute('font-size', (parseFloat(t.getAttribute('data-size')) * finv).toFixed(2));
    t.setAttribute('dy', (parseFloat(t.getAttribute('data-dy')) * finv).toFixed(2));
    /* The halo has to shrink with the type. Left in user units it grew with
       the zoom until the white was wider than the letters it was meant to
       separate, and the thin strokes of the italic were eaten from both
       sides — which is what made a river name unreadable zoomed in. */
    t.style.strokeWidth = (1.3 * finv).toFixed(3) + 'px';
  });
}

function kmToUnits(km) {
  var dLng = km / (111.32 * Math.cos(44.95 * Math.PI / 180));
  return px(MB.west + dLng) - px(MB.west);
}
function updateScaleBar() {
  var g = document.getElementById('mapScale');
  if (!g) return;
  var choices = [1, 2, 5, 10, 20, 50, 100], km = choices[0], len = 0;
  for (var i = 0; i < choices.length; i++) {
    var l = kmToUnits(choices[i]) * view.k;
    km = choices[i]; len = l;
    if (l >= 58) break;
  }
  /* The bottom-left corner is open water now, and dark ink on dark water
     cannot be read. The bar hangs from the right-hand edge instead. */
  var x0 = MS.w - 22 - len, y0 = MS.h - 26;
  g.innerHTML =
    '<line x1="' + x0 + '" y1="' + y0 + '" x2="' + (x0 + len).toFixed(1) + '" y2="' + y0 + '"/>' +
    '<line x1="' + x0 + '" y1="' + (y0 - 4) + '" x2="' + x0 + '" y2="' + (y0 + 4) + '"/>' +
    '<line x1="' + (x0 + len).toFixed(1) + '" y1="' + (y0 - 4) + '" x2="' + (x0 + len).toFixed(1) +
      '" y2="' + (y0 + 4) + '"/>' +
    '<text x="' + (x0 + len / 2).toFixed(1) + '" y="' + (y0 - 8) + '" text-anchor="middle">' +
      km + ' km</text>';
}

/* Where on the map, in real coordinates, did this event happen? */
function clientToLatLng(ev) {
  if (!svgEl) return null;
  var p = svgPoint(ev);
  var wx = (p.x - view.tx) / view.k, wy = (p.y - view.ty) / view.k;
  return [MB.north - wy / MS.h * (MB.north - MB.south),
          MB.west + wx / MS.w * (MB.east - MB.west)];
}

function svgPoint(ev) {
  var p = svgEl.createSVGPoint();
  p.x = ev.clientX; p.y = ev.clientY;
  var m = svgEl.getScreenCTM();
  return m ? p.matrixTransform(m.inverse()) : { x: MS.w / 2, y: MS.h / 2 };
}

function wireMapInteraction() {
  /* No setPointerCapture here. Capturing the pointer on pointerdown
     re-targets the following `click` at the <svg>, so it never reaches the
     appellation path underneath and nothing happens when you click a region.
     Instead we listen on window for the duration of a drag, and suppress the
     click only when the pointer actually moved. */
  var down = null, moved = false;

  function onMove(e) {
    if (!down) return;
    var rect = svgEl.getBoundingClientRect();
    var sc = MS.w / rect.width;
    var dx = e.clientX - down.x, dy = e.clientY - down.y;
    if (!moved && Math.abs(dx) + Math.abs(dy) < 4) return;
    moved = true;
    svgEl.classList.add('dragging');
    view.tx += dx * sc;
    view.ty += dy * sc;
    down.x = e.clientX; down.y = e.clientY;
    applyView();
  }
  function onUp() {
    down = null;
    svgEl.classList.remove('dragging');
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', onUp);
    /* Let the click that follows through only if this was not a drag. */
    if (moved) setTimeout(function () { moved = false; }, 0);
  }

  svgEl.addEventListener('pointerdown', function (e) {
    if (e.button !== 0) return;
    down = { x: e.clientX, y: e.clientY };
    moved = false;
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  });

  svgEl.addEventListener('mouseleave', hideMapTip);

  /* The hover card belongs to one château and to nothing else. It is shown
     by entering a dot and dismissed the moment the pointer is anywhere that
     is not that dot — moving off it, pressing, or clicking. Relying on the
     dot's own mouseleave is not enough: the dot can be re-rendered or
     covered while the pointer is still on it, and then nothing dismisses it. */
  function dismissUnlessOnDot(e) {
    if (!e.target || !e.target.closest || !e.target.closest('.est')) hideMapTip();
  }
  var mapHost = document.getElementById('map');
  mapHost.addEventListener('pointermove', dismissUnlessOnDot);
  mapHost.addEventListener('pointerdown', dismissUnlessOnDot);
  mapHost.addEventListener('click', dismissUnlessOnDot);

  /* The region key describes the appellation you are looking at, so a click
     on ground outside that appellation puts it away; a click back inside
     brings it back. Clicks on the map's own controls are not map clicks. */
  mapHost.addEventListener('click', function (e) {
    if (!state.region) return;
    if (e.target.closest && e.target.closest('.map-zoom, .map-head, .map-legend')) return;
    var r = regionById(state.region);
    var ll = clientToLatLng(e);
    var box = document.getElementById('mapLegend');
    if (!r || !ll || !box) return;
    box.style.display = inRegionShape(ll[0], ll[1], r) ? '' : 'none';
  });

  /* Pinch to zoom. The wheel handler below is a mouse affordance and a
     phone has no wheel, which left the +/- buttons as the only way to get
     closer — a map that does not answer two fingers reads as broken. The
     drag above is single-pointer, so a second finger cancels it rather than
     yanking the map sideways, and marks the gesture as moved so the click
     that follows a pinch does not open an appellation. */
  var pts = Object.create(null), pinching = null;
  function pointerCount() { return Object.keys(pts).length; }
  function pinchPair() {
    var k = Object.keys(pts);
    return [pts[k[0]], pts[k[1]]];
  }
  svgEl.addEventListener('pointerdown', function (e) {
    pts[e.pointerId] = { x: e.clientX, y: e.clientY };
    if (pointerCount() === 2) {
      var pair = pinchPair();
      pinching = {
        d: Math.hypot(pair[0].x - pair[1].x, pair[0].y - pair[1].y) || 1,
        k: view.k
      };
      down = null;
      moved = true;
      svgEl.classList.remove('dragging');
    }
  });
  svgEl.addEventListener('pointermove', function (e) {
    if (!pts[e.pointerId]) return;
    pts[e.pointerId] = { x: e.clientX, y: e.clientY };
    if (!pinching || pointerCount() !== 2) return;
    var pair = pinchPair();
    var d = Math.hypot(pair[0].x - pair[1].x, pair[0].y - pair[1].y) || 1;
    var mid = svgPoint({
      clientX: (pair[0].x + pair[1].x) / 2,
      clientY: (pair[0].y + pair[1].y) / 2
    });
    setZoom(pinching.k * (d / pinching.d), mid.x, mid.y);
  });
  /* Listened for on window: a finger can leave the <svg> before it lifts. */
  function releasePointer(e) {
    delete pts[e.pointerId];
    if (pointerCount() < 2) pinching = null;
  }
  window.addEventListener('pointerup', releasePointer);
  window.addEventListener('pointercancel', releasePointer);

  svgEl.addEventListener('wheel', function (e) {
    e.preventDefault();
    var p = svgPoint(e);
    setZoom(view.k * (e.deltaY < 0 ? 1.18 : 1 / 1.18), p.x, p.y);
  }, { passive: false });

  mapDragged = function () { return moved; };

  document.getElementById('zIn').addEventListener('click', function () { setZoom(view.k * 1.5); });
  document.getElementById('zOut').addEventListener('click', function () { setZoom(view.k / 1.5); });
}

/* Estate dots — region map only. The overview deliberately has none. */
function renderMarkers() {
  if (!mapReady || !state.region) return;
  markerG = document.getElementById('mapMarkers');
  if (!markerG) return;
  var r = regionById(state.region);
  var list = visibleChateaux().filter(function (ch) { return inRegion(ch, r); });
  var inv = screenInv(), s = '';
  list.slice().sort(function (a, b) { return (b.ha || 6) - (a.ha || 6); }).forEach(function (ch) {
    var rad = (ch.ha ? Math.max(3.4, Math.min(9, 2.4 + Math.sqrt(ch.ha) * 0.5)) : 3.1) * inv;
    s += '<circle class="est r' + Math.min(5, ch.growth) + (ch.approx ? ' approx' : '') +
         '" data-ch="' + ch.id + '" cx="' + px(ch.lng).toFixed(1) + '" cy="' + py(ch.lat).toFixed(1) +
         '" r="' + rad.toFixed(2) + '" stroke-width="' + (1.2 * inv).toFixed(2) + '"><title>' +
         ch.name + ' — ' + rankLabel(ch) + '</title></circle>';
  });
  markerG.innerHTML = s;
  hideMapTip();

  Array.prototype.forEach.call(markerG.querySelectorAll('.est'), function (c) {
    c.addEventListener('click', function (e) {
      if (mapDragged()) return;
      e.stopPropagation(); openDrawer(c.dataset.ch);
    });
    c.addEventListener('mouseenter', function (e) { showMapTip(c.dataset.ch, e); });
    c.addEventListener('mouseleave', hideMapTip);
  });
}

function hideMapTip() {
  if (mapTip) { mapTip.classList.remove('on'); mapTip.style.left = '-9999px'; }
}

function showMapTip(id, ev) {
  var ch = null;
  for (var i = 0; i < CH.length; i++) if (CH[i].id === id) { ch = CH[i]; break; }
  if (!ch) return;
  var d = clsDef(ch.cls);
  mapTip.innerHTML = '<b>' + ch.name + '</b>' +
    '<span class="r">' + rankLabel(ch) + ' · ' + ch.appellation + '</span>' +
    '<span class="r">' + (d ? d.name : '') + (ch.ha ? ' · ' + ch.ha + ' ha' : '') + '</span>' +
    (ch.approx ? '<span class="r i">Placed by appellation</span>' : '');
  var host = document.getElementById('map').getBoundingClientRect();
  mapTip.classList.add('on');
  var w = mapTip.offsetWidth, h = mapTip.offsetHeight;
  mapTip.style.left = Math.max(6, Math.min(host.width - w - 6, ev.clientX - host.left + 14)) + 'px';
  mapTip.style.top = Math.max(6, Math.min(host.height - h - 6, ev.clientY - host.top - h - 12)) + 'px';
}

function fitToVisible() {
  renderMap();
}

/* ===========================================================================
   11. BLEND BAR — stacked, 2px gaps, direct labels + key + table (relief rule)
   =========================================================================== */
function blendBar(parts) {
  var keys = GRAPE_ORDER.filter(function (k) { return parts[k] > 0; });
  var bar = '<div class="blendbar">', key = '<div class="blendkey">';
  keys.forEach(function (k) {
    var c = grapeColor(k), pct = parts[k];
    bar += '<div class="blendseg' + (inkOn(c) ? ' ink-dark' : '') +
           '" style="flex:' + pct + ';background:' + c + '" title="' +
           GRAPES[k].name + ' ' + pct + '%">' + (pct >= 8 ? pct + '%' : '') + '</div>';
    key += '<span><i style="background:' + c + '"></i>' + GRAPES[k].name + ' ' + pct + '%</span>';
  });
  return bar + '</div>' + key + '</div>';
}
function blendTable(parts) {
  var keys = GRAPE_ORDER.filter(function (k) { return parts[k] > 0; });
  var h = '<table class="dt"><thead><tr><th>Variety</th><th>Share</th></tr></thead><tbody>';
  keys.forEach(function (k) {
    h += '<tr><td>' + GRAPES[k].name + '</td><td class="num">' + parts[k] + '%</td></tr>';
  });
  return h + '</tbody></table>';
}

/* ===========================================================================
   12. SCORE-BY-VINTAGE COLUMN CHART
   =========================================================================== */

function openDrawer(id) {
  var ch = null;
  for (var i = 0; i < CH.length; i++) if (CH[i].id === id) { ch = CH[i]; break; }
  if (!ch) return;
  state.active = id;
  hideMapTip();
  var def = clsDef(ch.cls);

  el.drawerHead.innerHTML =
    '<div style="flex:1 1 auto"><h2>' + ch.name + '</h2>' +
      '<div class="sub"><span class="rank-pill" style="background:' + rankColor(ch) +
        ';color:' + (inkOn(rankColor(ch)) ? '#121211' : '#fff') + '">' +
      rankLabel(ch) + '</span> ' + (def ? def.name : '') + ' · ' + ch.appellation +
      (CROSS[ch.id] ? ' · also a ' + clsDef(CROSS[ch.id]).name : '') + '</div></div>' +
    '<button class="iconbtn" id="closeDrawer" aria-label="Close">Close ✕</button>';

  var fx = [['Classification', rankLabel(ch) + (def && def.year ? ' · ' + def.year : '')],
            ['Appellation', ch.appellation]];
  if (ch.ha) fx.push(['Vineyard', ch.ha + ' hectares']);
  if (ch.owner) fx.push(['Proprietor', ch.owner]);
  if (ch.second) fx.push(['Second wine', ch.second]);
  if (ch.wine) fx.push(['Classified for', ch.wine]);
  var site = siteFor(ch);
  if (site) {
    fx.push(['Website', '<a href="' + site[0] + '" target="_blank" rel="noopener noreferrer"' +
      ' title="from ' + (site[1] === 'ugcb' ? 'the UGCB register' : 'Wikidata') + '">' +
      site[0].replace(/^https?:\/\//, '') + '</a>']);
  }

  var facts = '<dl class="factgrid">' + fx.map(function (f) {
    return '<div class="fact"><dt>' + f[0] + '</dt><dd>' + f[1] + '</dd></div>';
  }).join('') + '</dl>';

  var body = facts;

  if (ch.sparse) {
    body += '<div class="notice" style="margin:16px 0">' +
      '<b>A verified name and rank, and little else.</b> This estate’s classification and ' +
      'appellation come from the published list. Its own encépagement, hectarage, proprietor ' +
      'and house style are not in this dataset, so <b>no blend is shown at all</b> and the map ' +
      'position shows the appellation rather than the property. The price links are exact.</div>';
  }

  if (def && def.editorial) {
    body += '<div class="notice" style="margin:16px 0">' +
      '<b>' + def.name + ' has no classification.</b> ' +
      (ch.cls === 'pomerol'
        ? 'The rank shown above is this dashboard’s editorial grouping by critical and ' +
          'market standing — it carries no official weight.'
        : 'The group shown above is an appellation, not a rank.') + '</div>';
  }

  if (ch.history) {
    body += '<div class="section"><h3>History ' +
      (ch.sources ? '<span class="hint">' + ch.sources + '</span>' : '') +
      '</h3><p class="notetext">' + ch.history + '</p></div>';
  }
  if (ch.terroir) {
    body += '<div class="section"><h3>Terroir</h3>' +
      '<p class="notetext">' + ch.terroir + '</p></div>';
  }
  if (ch.style) {
    body += '<div class="section"><h3>House style</h3>' +
      '<p class="housestyle">' + ch.style + '</p></div>';
  }

  body += ch.blend
    ? '<div class="section"><h3>Typical blend</h3>' +
        blendBar(ch.blend) +
        '<div class="tableview' + (state.tables ? ' on' : '') + '">' + blendTable(ch.blend) + '</div></div>'
    : '';
  body += ratingsSection(ch) +

    '<div class="section"><h3>All vintages, 1982–2024' +
      '<span class="hint">' + YEARS.length + ' vintages · each with its own price link</span></h3>' +
      '<div class="vintagelist">' +
        YEARS.map(function (yr) { return vintageRow(ch, yr); }).join('') +
      '</div></div>';

  el.drawerBody.innerHTML = body;
  el.drawerBody.scrollTop = 0;
  el.drawer.classList.add('is-open');
  el.scrim.classList.add('is-open');
  el.drawer.setAttribute('aria-hidden', 'false');

  document.getElementById('closeDrawer').addEventListener('click', closeDrawer);

  Array.prototype.forEach.call(el.drawerBody.querySelectorAll('.vrow-head'), function (b) {
    b.addEventListener('click', function () { b.parentNode.classList.toggle('open'); });
  });
  renderList();
}

function closeDrawer() {
  el.drawer.classList.remove('is-open');
  el.scrim.classList.remove('is-open');
  el.drawer.setAttribute('aria-hidden', 'true');
  state.active = null;
  renderList();
}

function vintageRow(ch, yr) {
  var r = scoreFor(ch, yr), v = V[yr];
  var o = SCORES[ch.id + '|' + yr];

  if (r.notMade) {
    return '<div class="vrow" data-year="' + yr + '" style="border-left:3px solid var(--border-strong)">' +
      '<button class="vrow-head"><span class="yr">' + yr + '</span><span class="sc">—</span>' +
      '<span class="teaser">No grand vin produced — the estate declared no vintage.</span>' +
      '<span class="chev">▾</span></button>' +
      '<div class="vrow-body"><p class="vintagereport">' + v.report + '</p></div></div>';
  }

  var rated = !r.none;
  var edge = rated ? scoreColor(r.score) : 'var(--border)';
  var teaser = rated && o && o.note ? o.note : v.report;

  return '<div class="vrow" data-year="' + yr + '" style="border-left:3px solid ' + edge + '">' +
    '<button class="vrow-head"><span class="yr">' + yr + '</span>' +
      '<span class="sc">' + (rated ? r.score : '—') + '</span>' +
      '<span class="teaser">' + teaser + '</span>' +
      '<span class="chev">▾</span></button>' +
    '<div class="vrow-body">' +

      (rated
        ? '<p class="subhead">Rating · ' + (r.src || 'reported') + '</p>' +
          '<div style="font-size:12.5px"><b>' + r.score + '/100</b></div>' +
          (o && o.note ? '<p class="notetext">' + o.note + '</p>' : '')
        : '') +

      (o && o.blend
        ? '<p class="subhead">Blend, this vintage</p>' +
          blendBar(o.blend) +
          '<div class="tableview' + (state.tables ? ' on' : '') + '">' +
            blendTable(o.blend) + '</div>'
        : '') +

      '<p class="subhead">The ' + yr + ' season</p>' +
      '<p class="vintagereport"><b>Weather.</b> ' + v.weather +
        '<br><b>The vintage.</b> ' + v.report + '</p>' +

      '<p class="subhead">Find this exact vintage</p>' +
      '<div class="buylinks">' + buyLinks(ch, yr).map(function (l) {
        return '<a class="buy' + (l.primary ? ' primary' : '') +
               '" target="_blank" rel="noopener noreferrer" href="' + l.url + '">' +
               l.label + ' <span style="opacity:.7;font-size:11px">' + l.host + '</span></a>';
      }).join('') + '</div>' +
    '</div></div>';
}

/* ----------------------- the vintages, by appellation -------------------- */
/* What the season did is known for the appellation even where no estate was
   rated, so the year-by-year reading lives here now rather than being split
   into a number for each château. */
function regionCat(r) {
  if (r.id === 'sauternes') return 'sweet';
  if (r.id === 'entre-deux-mers') return 'white';
  return 'red';
}

function regionVintageRating(r, year) {
  return vintageRating({ cat: regionCat(r), appellation: r.apps[0] }, year);
}

function vintageTable(r) {
  var rows = YEARS.map(function (yr) {
    var v = V[yr], rt = regionVintageRating(r, yr);
    return '<tr><th scope="row">' + yr + '</th>' +
      '<td><span class="vt-bar"><span style="width:' +
        Math.max(0, Math.min(100, (rt - 60) * 2.5)).toFixed(0) +
        '%;background:' + ratingColor(rt) + '"></span></span>' +
        '<b class="vt-num">' + rt + '</b></td>' +
      '<td class="vt-rep">' + v.report + '</td></tr>';
  }).join('');
  return '<table class="vintable"><caption>Season by season in ' + r.name +
    ', 1982–2024 — the documented character of each year, not a rating of ' +
    'any one wine.</caption><thead><tr><th>Vintage</th><th>Season</th>' +
    '<th>What happened</th></tr></thead><tbody>' + rows + '</tbody></table>';
}


function renderVintages() {
  var html = '';
  YEARS.forEach(function (yr) {
    var v = V[yr], rb = RB[yr];
    var chips = [['Médoc', v.medoc], ['Pessac-Léognan', v.pessac],
                 ['Saint-Émilion & Pomerol', rb.r], ['Sauternes & Barsac', v.sauternes]]
      .map(function (c) {
        var col = ratingColor(c[1]);
        return '<span class="ratechip' + (inkOn(col) ? ' ink-dark' : '') +
               '" style="background:' + col + '">' + c[0] + ' ' + c[1] + '</span>';
      }).join('');
    var d = [];
    if (v.app) Object.keys(v.app).forEach(function (k) { d.push(k + ' ' + (v.app[k] > 0 ? '+' : '') + v.app[k]); });
    if (rb.app) Object.keys(rb.app).forEach(function (k) { d.push(k + ' ' + (rb.app[k] > 0 ? '+' : '') + rb.app[k]); });
    html += '<article class="vgcard">' +
      '<div><div class="vgyear">' + yr + '</div>' +
        '<div style="font-size:11px;color:var(--text-muted);margin-top:4px">Drink ' +
          v.drinkFrom + '–' + v.drinkTo + '</div></div>' +
      '<div><p class="weather"><b>Weather.</b> ' + v.weather + '</p><p>' + v.report + '</p>' +
        '<div class="ratings">' + chips + '</div>' +
        (d.length ? '<div style="font-size:11px;color:var(--text-muted);margin-top:6px">' +
          'Commune adjustments: ' + d.join(' · ') + '</div>' : '') +
      '</div></article>';
  });
  el.vintageGrid.innerHTML = html;
}

/* ===========================================================================
   15. FILTER UI
   =========================================================================== */
function buildChips() {
  var tiers = activeTiers();
  if (!tiers) { el.chips.innerHTML = ''; el.chips.style.display = 'none'; return; }
  el.chips.style.display = '';
  el.chips.innerHTML = tiers.map(function (t) {
    var key = state.cls + ':' + t.growth;
    var n = CH.filter(function (c) {
      return inCollection(c, state.cls) && c.growth === t.growth;
    }).length;
    return '<button class="chip" data-k="' + key + '" aria-pressed="true">' +
      '<span class="dot" style="background:' + cssVar('--rank-' + Math.min(5, t.growth)) + '"></span>' +
      t.label + ' <span style="color:var(--text-muted)">' + n + '</span></button>';
  }).join('');
  Array.prototype.forEach.call(el.chips.querySelectorAll('.chip'), function (b) {
    b.addEventListener('click', function () {
      var k = b.dataset.k;
      state.tiers[k] = state.tiers[k] === false;
      b.setAttribute('aria-pressed', state.tiers[k] === false ? 'false' : 'true');
      refresh();
    });
  });
}

function buildAppellationSelect() {
  var pool = state.cls ? CH.filter(function (c) { return inCollection(c, state.cls); }) : CH;
  var apps = pool.map(function (c) { return c.appellation; })
    .filter(function (v, i, a) { return a.indexOf(v) === i; }).sort();
  el.appellation.innerHTML = '<option value="">All appellations</option>' +
    apps.map(function (a) { return '<option>' + a + '</option>'; }).join('');
}

function refreshCrumb() {
  if (!el.crumb) return;
  var c = state.cls ? clsDef(state.cls) : null;
  var r = state.region ? regionById(state.region) : null;
  el.crumb.textContent = (c ? c.name : 'All of Bordeaux') + (r ? ' · ' + r.name : '');
}

function refresh() {
  renderList();
  renderMap();
  refreshCrumb();
}

/* ===========================================================================
   16. VIEWS & WIRING
   =========================================================================== */
function setView(v) {
  state.view = v;
  el.tabAppellations.setAttribute('aria-selected', v === 'appellations');
  el.tabClassifications.setAttribute('aria-selected', v === 'classifications');
  el.tabProducers.setAttribute('aria-selected', v === 'producers');
  el.tabVintages.setAttribute('aria-selected', v === 'vintages');
  document.body.classList.toggle('map-page', v === 'producers');
  if (v !== 'producers') {
    el.paneList.classList.remove('is-open');
    el.filters.classList.remove('open');
  }
  el.appellations.style.display    = v === 'appellations' ? '' : 'none';
  el.classifications.style.display = v === 'classifications' ? '' : 'none';
  el.workspace.style.display = v === 'producers' ? '' : 'none';
  el.vintageGrid.style.display = v === 'vintages' ? '' : 'none';
  el.filters.style.display   = v === 'producers' ? '' : 'none';
  if (v === 'producers' && map) {
    setTimeout(fitToVisible, 60);
  }
}

function applyTheme(mode) {
  if (mode) document.documentElement.setAttribute('data-theme', mode);
  else document.documentElement.removeAttribute('data-theme');
  try { localStorage.setItem('bdx-theme', mode || ''); } catch (e) {}
  el.themeBtn.textContent = isDark() ? '☀ Light' : '☾ Dark';
  renderReference();
  refresh();
  if (state.active) openDrawer(state.active);
}

function initAppInstall() {
  var installBtn = document.getElementById('installBtn');
  var installPrompt = null;
  var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  var isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
    navigator.standalone === true;

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./service-worker.js').catch(function (error) {
      console.error('The offline app could not be initialized.', error);
    });
  }

  if (isStandalone) return;

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    installPrompt = event;
    installBtn.hidden = false;
  });

  window.addEventListener('appinstalled', function () {
    installBtn.hidden = true;
    installPrompt = null;
  });

  if (isIOS) installBtn.hidden = false;
  installBtn.addEventListener('click', function () {
    if (!installPrompt) {
      window.alert('To install this app, tap Share in Safari, then choose "Add to Home Screen".');
      return;
    }
    installBtn.disabled = true;
    installPrompt.prompt();
    installPrompt.userChoice.then(function () {
      installPrompt = null;
      installBtn.hidden = true;
      installBtn.disabled = false;
    }).catch(function (error) {
      console.error('The app installation prompt failed.', error);
      installBtn.disabled = false;
    });
  });
}

function init() {
  try {
    var saved = localStorage.getItem('bdx-theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
  } catch (e) {}

  el.vintage.innerHTML = '<option value="">All vintages</option>' +
    YEARS.map(function (y) { return '<option>' + y + '</option>'; }).join('');

  renderReference();
  renderVintages();
  buildAppellationSelect();
  initMap();
  renderList();
  setView('appellations');

  el.themeBtn.textContent = isDark() ? '☀ Light' : '☾ Dark';
  el.themeBtn.addEventListener('click', function () { applyTheme(isDark() ? 'light' : 'dark'); });
  initAppInstall();

  el.search.addEventListener('input', function () { state.q = el.search.value; refresh(); });
  el.appellation.addEventListener('change', function () { state.appellation = el.appellation.value; refresh(); });
  el.vintage.addEventListener('change', function () { state.vintage = el.vintage.value; refresh(); });
  el.resetBtn.addEventListener('click', function () {
    state.q = ''; state.appellation = ''; state.vintage = '';
    state.tiers = {}; state.region = null;
    el.search.value = ''; el.appellation.value = ''; el.vintage.value = '';
    buildChips(); refresh();
  });

  el.tabAppellations.addEventListener('click', function () {
    setView('appellations');
  });
  el.tabClassifications.addEventListener('click', function () {
    setView('classifications');
  });
  el.tabProducers.addEventListener('click', function () { setView('producers'); refresh(); });
  el.tabVintages.addEventListener('click', function () { setView('vintages'); });
  el.scrim.addEventListener('click', closeDrawer);
  var lc = document.getElementById('listClose');
  if (lc) lc.addEventListener('click', function () {
    el.paneList.classList.remove('is-open');
  });

  /* Anywhere outside a château dot dismisses the hover card, including
     clicks in the list or the filter bar. */
  document.addEventListener('click', function (e) {
    if (!e.target.closest || !e.target.closest('.est')) hideMapTip();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (el.drawer.classList.contains('is-open')) closeDrawer();
    else if (el.filters.classList.contains('open')) el.filters.classList.remove('open');
    else if (el.paneList.classList.contains('is-open')) el.paneList.classList.remove('is-open');
    else if (state.region) exitRegion();
  });
  var rsz = null;
  window.addEventListener('resize', function () {
    clearTimeout(rsz);
    rsz = setTimeout(function () { rescaleLabels(); renderMarkers(); updateScaleBar(); }, 120);
  });

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
    if (!document.documentElement.getAttribute('data-theme')) {
      renderReference(); refresh();
    }
  });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();

})();
