/* ===========================================================================
   Bordeaux Dashboard — application engine
   ---------------------------------------------------------------------------
   Collections: 1855 Médoc, 1855 Sauternes, Saint-Émilion 2022, Pomerol
   (editorial), Crus Classés de Graves, Crus Bourgeois 2020, Crus Artisans.
   No build step, no framework. Leaflet is the only external dependency.
   =========================================================================== */
(function () {
'use strict';

/* Read once, and read from the clock: the drinking windows are judged
   against it, so a hardcoded year would quietly rot. */
var NOW = new Date().getFullYear();
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
/* Unpack the delta-encoded rings in appellations.js: the first point in
   full, then each later one as a change in ten-thousandths of a degree. */
function decodeRings(encoded) {
  return encoded.map(function (s) {
    var parts = s.split(';'), first = parts[0].split(',');
    var lat = Math.round(parseFloat(first[0]) * 1e4);
    var lng = Math.round(parseFloat(first[1]) * 1e4);
    var ring = [[lat / 1e4, lng / 1e4]];
    for (var i = 1; i < parts.length; i++) {
      var d = parts[i].split(',');
      lat += parseInt(d[0], 10);
      lng += parseInt(d[1], 10);
      ring.push([lat / 1e4, lng / 1e4]);
    }
    return ring;
  });
}

/* Where the INAO has digitised an appellation, its official delimitation
   replaces the drawn outline. Done before the holes are resolved below, so
   a communal appellation is cut out of its parent using both real shapes —
   and it has to be: the official Haut-Médoc contains every one of Pauillac,
   Margaux, Saint-Julien, Saint-Estèphe, Listrac and Moulis in full, because
   those parcels carry both names in law. Without the cut-out Haut-Médoc
   would paint straight over all six. */
(function applyOfficialOutlines() {
  var A = window.BDX_AOC;
  if (!A) return;
  window.BDX_MAP.regions.forEach(function (r) {
    if (A[r.id]) {
      r.rings = decodeRings(A[r.id]);
      r.official = true;
    }
  });
})();

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
/* Corrected positions, laid over the master data before anything is placed.
   Only estates whose own coordinate fell outside the appellation as the INAO
   delimits it are listed, and only where the replacement falls inside it. */
(function applyCorrectedCoords() {
  var C = window.BDX_COORDS;
  if (!C) return;
  CH.forEach(function (ch) {
    var c = C[ch.id];
    if (!c) return;
    ch.lat = c[0];
    ch.lng = c[1];
    ch.coordFixed = true;
    /* "Approximate" means the dashboard does not know where the estate is.
       Once a surveyed position is supplied it does, so the flag goes - the
       marker stops being faded and the drawer stops saying "Placed by
       appellation". The estate may still be sparse in every other field;
       that is a different thing and keeps its own flag. */
    ch.approx = false;
  });
})();

CH.forEach(function (ch) {
  if (ch.lat !== undefined) return;
  /* A position worked out from the appellation is approximate by
     definition, so say so here rather than trusting that it was said
     earlier. Until the Doisy estates lost their wrong coordinates, every
     estate reaching this point had already been flagged by addSparse and
     the two could not come apart. */
  ch.approx = true;
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
var RATINGS = window.BDX_RATINGS || {};

/* A hand-entered score is a single critic's published figure and stands as
   written. Everything else falls back to the derived rating: the mean of the
   critics who rated that wine, which is a reading of the consensus rather
   than anyone's verdict, and is labelled as such. */
function scoreFor(ch, year) {
  if (notProduced(ch, year)) return { none: true, notMade: true };
  var o = SCORES[ch.id + '|' + year];
  if (o && o.score) return { score: o.score, verified: true, src: o.src };
  var r = RATINGS[ch.id + '|' + year];
  if (r) {
    return { score: Math.round(r[0]), exact: r[0], derived: true,
             n: r[1], spread: r[2], panel: r[3],
             src: r[1] + ' critics' };
  }
  return { none: true };
}

/* Who each column is. The figures are shown as each critic published them,
   on their own scale, because converting them for display would misquote
   them — the conversion exists only to take the average. */
var CRITIC_NAMES = {
  RP: ['Wine Advocate', 100], NM: ['Neal Martin, Vinous', 100],
  JR: ['Jancis Robinson', 20], TA: ['Tim Atkin', 100],
  BD: ['Bettane & Desseauve', 20], WS: ['James Suckling', 100],
  JL: ['Jeff Leve', 100], De: ['Decanter', 0],
  RVF: ['La Revue du Vin de France', 20], JA: ['Jane Anson', 100],
  LeP: ['Le Point', 20], PW: ['Perswijn', 5],
  RG: ['René Gabriel', 20], CK: ['Chris Kissack', 100]
};


/* The panel opens below and to the right by default. Near the edge of the
   box that scrolls it, that puts it outside and the box clips it — so
   measure once on entry and flip. Done in script because CSS cannot know
   how much room is left. */
function placeRatingPanel(wrap) {
  var panel = wrap.querySelector('.ratingpanel');
  if (!panel) return;
  panel.classList.remove('up', 'leftward');
  var bound = wrap.closest('.refpage, .drawer-body, .pane-list, .vintagegrid');
  var b = bound ? bound.getBoundingClientRect()
                : { top: 0, left: 0,
                    bottom: window.innerHeight, right: window.innerWidth };
  var r = panel.getBoundingClientRect();
  if (r.bottom > b.bottom - 6 && (r.height + 12) < (wrap.getBoundingClientRect().top - b.top)) {
    panel.classList.add('up');
  }
  if (r.right > b.right - 6) panel.classList.add('leftward');
}

(function wireRatingPanels() {
  function hit(e) {
    var w = e.target && e.target.closest ? e.target.closest('.ratingwrap') : null;
    if (w) placeRatingPanel(w);
  }
  document.addEventListener('mouseover', hit, true);
  document.addEventListener('focusin', hit, true);
})();

function ratingPanel(r) {
  if (!r || !r.panel) return '';
  /* Spans, not a table: the collapsed row's score lives inside a <button>,
     where a table is not valid content. */
  var rows = r.panel.split('|').map(function (bit) {
    var p = bit.split(':'), who = CRITIC_NAMES[p[0]] || [p[0], 0];
    var outOf = who[1];
    /* Decanter changed scale twice; read it off the value as the build did. */
    if (!outOf) outOf = parseFloat(p[1]) <= 5 ? 5 : (parseFloat(p[1]) <= 20 ? 20 : 100);
    return '<span class="rprow"><span class="who">' + who[0] + '</span>' +
           '<span class="num">' + p[1] + '<span class="of">/' + outOf + '</span></span></span>';
  }).join('');
  return '<span class="ratingpanel">' + rows +
    '<span class="rpfoot">' + r.n + ' critics, averaging ' + r.exact +
    (r.spread ? ' \u00b7 they differ by ' + r.spread + ' points' : '') +
    '<br>gathered by bordoverview.com</span></span>';
}

/* Every published rating this dashboard holds for one estate. */
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
  /* Which of the estate's wines the drawer is showing. Always reset to the
     grand vin when a drawer opens: the grand vin is what the estate is
     known for, and is the thing anyone opening a château came to see. */
  wine: 'grand',
  tiers: {}, active: null, tables: false,
  /* The comparison opens on something rather than on nothing: a vertical of
     the four most recent vintages worth the name, which is a reading the
     moment the tab is pressed. */
  cmp: { mode: 'vertical', estate: 'lynch-bages', years: [2010, 2015, 2016, 2019],
         vintage: 2016, estates: [] }
};

var el = {};
['tabAppellations','tabClassifications','tabProducers','tabVintages','tabCompare',
 'search','appellation','vintage',
 'chips','resultcount','appellations','classifications','compare','workspace','paneList',
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
          'sauternes', 'barsac'] },
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
  'sauternes': 'The sweet wines', 'barsac': 'The sweet wines',
  'saint-emilion': 'The Libournais', 'pomerol': 'The Libournais',
  'lalande-de-pomerol': 'The Libournais', 'fronsac': 'The Libournais',
  'canon-fronsac': 'The Libournais',
  'cotes-de-bourg': 'The Côtes', 'blaye': 'The Côtes',
  'castillon': 'The Côtes',
  'entre-deux-mers': 'Entre-Deux-Mers'
};

/* The appellation notes in the language being read. The Dutch file holds
   the same fields; anything it has not got yet falls back to the English,
   so a half-finished translation shows as English rather than as a gap. */
/* The vintage as it should be read: the Dutch weather and report where
   they exist, the English where they do not. Everything else about the
   year - the ratings, the drinking window, the commune adjustments - is
   numbers and is shared. */
function vintage(yr) {
  var en = V[yr];
  if (!en) return en;
  var lang = window.BDX_LANG ? BDX_LANG.get() : 'en';
  if (lang === 'en') return en;
  var alt = (window.BDX_VINTAGES_NL || {})[yr];
  if (!alt) return en;
  var out = {};
  for (var k in en) out[k] = en[k];
  if (alt.weather) out.weather = alt.weather;
  if (alt.report) out.report = alt.report;
  return out;
}

function apNote(id) {
  var en = AP_NOTES[id] || null;
  if (!en) return null;
  var lang = window.BDX_LANG ? BDX_LANG.get() : 'en';
  if (lang === 'en') return en;
  var alt = (window.BDX_APPELLATION_NOTES_NL || {})[id];
  if (!alt) return en;
  var out = {};
  for (var k in en) out[k] = en[k];
  for (var k2 in alt) if (alt[k2]) out[k2] = alt[k2];
  return out;
}

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
  wireVintageRows();
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
/* ------------------------------- comparison ------------------------------ */
/* Two wines next to each other is how this society actually tastes: a
   vertical, one estate down its vintages, and a horizontal, one vintage
   across its estates. The dashboard held everything needed for both and
   would only show it one drawer at a time, which is the one arrangement in
   which no comparison can be made.

   Columns rather than rows, because the columns are the wines - that is how
   they stand on the table - and reading down a column is reading one glass. */

var CMP_MAX = 6;

function cmpWines() {
  var c = state.cmp;
  if (c.mode === 'vertical') {
    var ch = chateauById(c.estate);
    if (!ch) return [];
    return c.years.map(function (yr) { return { ch: ch, yr: yr }; });
  }
  return c.estates.map(function (id) {
    return { ch: chateauById(id), yr: c.vintage };
  }).filter(function (w) { return w.ch; });
}

function chateauById(id) {
  for (var i = 0; i < CH.length; i++) if (CH[i].id === id) return CH[i];
  return null;
}

/* One row of the table. value() is given the wine and returns a cell, or
   null when that wine has nothing to say; a row where every wine returns
   null is left out entirely rather than printed as a line of dashes.

   Where every wine gives the same answer the row collapses into one cell
   across the width. A vertical repeats its estate's appellation and rank in
   every column otherwise, which is four copies of a fact that is not what
   is being compared - but dropping the row would lose the fact, and it is
   worth stating once. */
function cmpRow(label, wines, value) {
  var cells = wines.map(value);
  var any = cells.some(function (c) { return c !== null && c !== ''; });
  if (!any) return '';
  var same = wines.length > 1 && cells.every(function (c) { return c === cells[0]; });
  var body = same
    ? '<td class="cmp-same" colspan="' + wines.length + '">' + cells[0] + '</td>'
    : cells.map(function (c) {
        return '<td>' + (c === null || c === '' ? '<span class="cmp-nil">—</span>' : c) + '</td>';
      }).join('');
  return '<tr><th scope="row">' + label + '</th>' + body + '</tr>';
}

function cmpTable(wines) {
  if (!wines.length) {
    return '<p class="cmp-empty">Pick two or more wines to put them side by side.</p>';
  }
  var vertical = state.cmp.mode === 'vertical';

  var head = '<tr><td class="cmp-corner"></td>' + wines.map(function (w) {
    return '<th scope="col"><button class="cmp-head" data-ch="' + w.ch.id + '">' +
      (vertical ? w.yr : w.ch.name) + '</button>' +
      '<span class="cmp-sub">' + (vertical ? w.ch.name : w.yr) + '</span></th>';
  }).join('') + '</tr>';

  var body =
    cmpRow('Appellation', wines, function (w) { return w.ch.appellation; }) +
    cmpRow('Rank', wines, function (w) { return rankLabel(w.ch); }) +
    cmpRow('Rating', wines, function (w) {
      var r = scoreFor(w.ch, w.yr);
      if (r.notMade) return '<span class="cmp-nil">not made</span>';
      if (r.none) return null;
      var col = scoreColor(r.score);
      return '<span class="cmp-score" style="background:' + col + ';color:' +
        (inkOn(col) ? '#121211' : '#fff') + '">' + r.score + '</span>';
    }) +
    cmpRow('When to drink', wines, function (w) {
      var win = drinkWindow(w.ch, w.yr);
      if (!win) return null;
      var m = maturity(win);
      return '<span class="cmp-win">' + win.from + '–' + win.to + '</span>' +
        '<span class="mat mat-' + m.k + '">' + m.label + '</span>';
    }) +
    cmpRow('The season', wines, function (w) {
      var rt = vintageRating(w.ch, w.yr);
      var col = ratingColor(rt);
      return '<span class="cmp-score" style="background:' + col + ';color:' +
        (inkOn(col) ? '#121211' : '#fff') + '">' + rt + '</span>';
    }) +
    cmpRow('Blend', wines, function (w) {
      var f = fiche(w.ch, w.yr);
      var b = (f && f.blend) || w.ch.blend;
      if (!b) return null;
      return blendBar(b) + (f && f.blend ? '' :
        '<span class="cmp-note">the estate’s usual</span>');
    }) +
    cmpRow('Picked', wines, function (w) {
      var f = fiche(w.ch, w.yr);
      return (f && f.harvest) || null;
    }) +
    cmpRow('Yield', wines, function (w) {
      var f = fiche(w.ch, w.yr);
      return f && f.yld ? f.yld + ' hl/ha' : null;
    }) +
    cmpRow('The estate on the year', wines, function (w) {
      var f = fiche(w.ch, w.yr);
      return f && f.note ? '<span class="cmp-prose">' + f.note + '</span>' : null;
    }) +
    cmpRow('The estate on the wine', wines, function (w) {
      var f = fiche(w.ch, w.yr);
      return f && f.taste ? '<span class="cmp-prose">' + f.taste + '</span>' : null;
    });

  return '<div class="cmp-scroll"><table class="cmp cmp-' + wines.length + '">' +
    '<thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>';
}

function renderCompare() {
  var c = state.cmp;
  var vertical = c.mode === 'vertical';

  var modes = '<div class="cmp-modes">' +
    '<button class="chip" aria-pressed="' + vertical + '" data-cmode="vertical">' +
      'One estate, several vintages</button>' +
    '<button class="chip" aria-pressed="' + !vertical + '" data-cmode="horizontal">' +
      'One vintage, several estates</button>' +
    '</div>';

  var picker;
  if (vertical) {
    /* Only the estates that have something to compare: an estate with no
       rating in any year would open onto an empty table. */
    var opts = CH.slice().sort(function (a, b) { return a.name.localeCompare(b.name); })
      .map(function (ch) {
        return '<option value="' + ch.id + '"' + (ch.id === c.estate ? ' selected' : '') +
          '>' + ch.name + '</option>';
      }).join('');
    picker = '<div class="cmp-pick"><div class="field"><label for="cmpEstate">Estate</label>' +
      '<select id="cmpEstate">' + opts + '</select></div></div>' +
      '<p class="cmp-help">Choose up to ' + CMP_MAX + ' vintages.</p>' +
      '<div class="cmp-years">' + YEARS.map(function (yr) {
        var on = c.years.indexOf(yr) !== -1;
        var full = !on && c.years.length >= CMP_MAX;
        return '<button class="cmp-year' + (on ? ' on' : '') + '"' +
          (full ? ' disabled' : '') + ' data-cyear="' + yr + '">' + yr + '</button>';
      }).join('') + '</div>';
  } else {
    var yopts = YEARS.map(function (yr) {
      return '<option value="' + yr + '"' + (yr === c.vintage ? ' selected' : '') +
        '>' + yr + '</option>';
    }).join('');
    var chosen = c.estates.map(function (id) {
      var ch = chateauById(id);
      return ch ? '<button class="cmp-chosen" data-cdrop="' + id + '">' + ch.name +
        ' <span aria-hidden="true">✕</span></button>' : '';
    }).join('');
    var addable = CH.slice().sort(function (a, b) { return a.name.localeCompare(b.name); })
      .filter(function (ch) { return c.estates.indexOf(ch.id) === -1; })
      .map(function (ch) { return '<option value="' + ch.id + '">' + ch.name + '</option>'; })
      .join('');
    picker = '<div class="cmp-pick">' +
      '<div class="field"><label for="cmpVintage">Vintage</label>' +
        '<select id="cmpVintage">' + yopts + '</select></div>' +
      '<div class="field"><label for="cmpAdd">Add an estate</label>' +
        '<select id="cmpAdd"' + (c.estates.length >= CMP_MAX ? ' disabled' : '') + '>' +
        '<option value="">Choose…</option>' + addable + '</select></div>' +
      '</div>' +
      (chosen ? '<div class="cmp-chosenrow">' + chosen + '</div>'
              : '<p class="cmp-help">Add up to ' + CMP_MAX + ' estates.</p>');
  }

  el.compare.innerHTML =
    '<div class="ref-head"><h2>Side by side</h2>' +
      '<p>A vertical reads one estate down its vintages; a horizontal reads one ' +
      'vintage across its estates. Everything here is what the rest of the ' +
      'dashboard holds, arranged so that two wines can be read against each ' +
      'other instead of one at a time.</p></div>' +
    modes + picker + cmpTable(cmpWines());

  wireCompare();
}

function wireCompare() {
  var root = el.compare;

  Array.prototype.forEach.call(root.querySelectorAll('[data-cmode]'), function (b) {
    b.addEventListener('click', function () {
      state.cmp.mode = b.getAttribute('data-cmode');
      renderCompare();
    });
  });

  var est = root.querySelector('#cmpEstate');
  if (est) est.addEventListener('change', function () {
    state.cmp.estate = est.value;
    renderCompare();
  });

  Array.prototype.forEach.call(root.querySelectorAll('[data-cyear]'), function (b) {
    b.addEventListener('click', function () {
      var yr = Number(b.getAttribute('data-cyear'));
      var at = state.cmp.years.indexOf(yr);
      if (at !== -1) state.cmp.years.splice(at, 1);
      else if (state.cmp.years.length < CMP_MAX) state.cmp.years.push(yr);
      /* Oldest first, left to right: a vertical is read as a sequence. */
      state.cmp.years.sort(function (a, b2) { return a - b2; });
      renderCompare();
    });
  });

  var vin = root.querySelector('#cmpVintage');
  if (vin) vin.addEventListener('change', function () {
    state.cmp.vintage = Number(vin.value);
    renderCompare();
  });

  var add = root.querySelector('#cmpAdd');
  if (add) add.addEventListener('change', function () {
    if (add.value && state.cmp.estates.length < CMP_MAX) {
      state.cmp.estates.push(add.value);
      renderCompare();
    }
  });

  Array.prototype.forEach.call(root.querySelectorAll('[data-cdrop]'), function (b) {
    b.addEventListener('click', function () {
      var id = b.getAttribute('data-cdrop');
      var at = state.cmp.estates.indexOf(id);
      if (at !== -1) state.cmp.estates.splice(at, 1);
      renderCompare();
    });
  });

  /* A column heading opens that estate, so a comparison can be left for the
     full reading and come back to. */
  Array.prototype.forEach.call(root.querySelectorAll('.cmp-head'), function (b) {
    b.addEventListener('click', function () { openDrawer(b.getAttribute('data-ch')); });
  });
}

function renderReference() {
  renderAppellations();
  renderClassifications();
  renderCompare();
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
    /* Picking a vintage puts a score on every card, so order by it: a list
       of that year's wines that is not in that year's order is a puzzle. */
    if (state.vintage) {
      var yr = Number(state.vintage);
      members = members.slice().sort(function (a, b) {
        var sa = scoreFor(a, yr), sb = scoreFor(b, yr);
        var va = sa.none ? -1 : (sa.exact || sa.score);
        var vb = sb.none ? -1 : (sb.exact || sb.score);
        if (vb !== va) return vb - va;
        return a.name.localeCompare(b.name);
      });
    }
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
          (sub && !sub.none
            ? ' · <span class="' + (sub.panel ? 'ratingwrap' : '') + '"><b>' + sub.score +
              '</b>' + (sub.panel ? ratingPanel(sub) : '') + '</span> in ' + state.vintage
            : '') +
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

/* The same shape with the communal appellations left in. Haut-Médoc is drawn
   with Pauillac, Margaux, Saint-Julien, Saint-Estèphe, Listrac and Moulis cut
   out of it, because on the map they are their own places — but in law those
   parcels are Haut-Médoc too, so pointing at the name shows the whole of it. */
function wholeRingsPath(r) {
  return r.rings.map(function (ring) { return smooth(ring, true); }).join(' ');
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
  var s = '<g class="m-water-body">';

  if (window.BDX_WATER && window.BDX_WATER.length) {
    /* The Atlantic is in here too: BD TOPAGE stops at the coast and Natural
       Earth's ocean stops at the river mouth, so the two are unioned and the
       seam closed, which is what lets the Gironde reach the sea. */
    /* Surveyed water. Drawn as it is, with no smoothing: the whole point is
       that the bank follows the one the vineyards are delimited against. */
    decodeRings(window.BDX_WATER).forEach(function (ring) {
      s += '<path d="' + polyPath(ring) + '"/>';
    });
    s += '</g>';
    return s;
  }

  /* Fallback only, if water.js is missing. */
  s += '<path d="' + smooth(G.sea, true) + '"/>' +
       '<path d="' + smooth(G.arcachon, true) + '"/>' +
       '<path d="' + smooth(G.estuary, true) + '"/></g>';
  s += '<path class="m-river m-river-lg" d="' + smooth(G.garonne) + '"/>';
  s += '<path class="m-river m-river-md" d="' + smooth(G.dordogne) + '"/>';
  return s;
}

/* A ring straight to a path, corners intact. */
function polyPath(ring) {
  var d = '';
  for (var i = 0; i < ring.length; i++) {
    d += (i ? 'L' : 'M') + px(ring[i][1]).toFixed(1) + ' ' + py(ring[i][0]).toFixed(1);
  }
  return d + 'Z';
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

  /* One shape that the hover fills in, drawn over the outlines and under the
     type. Empty until a name or an outline is pointed at. */
  s += '<path class="m-area-hot" id="mapHot" d=""/>';

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
  var listBtn = document.getElementById('mapList');
  if (listBtn) listBtn.addEventListener('click', function () {
    el.paneList.classList.toggle('is-open');
  });

  /* Pointing at a name lights up the ground it belongs to, and the other way
     round. The name is the easier target of the two: the riverside communes
     are slivers a few pixels wide, while their labels sit out in open
     country on a leader line. */
  var hot = zoomG.querySelector('#mapHot');
  function regionById2(id) {
    var R = window.BDX_MAP.regions;
    for (var i = 0; i < R.length; i++) if (R[i].id === id) return R[i];
    return null;
  }
  function setHot(id) {
    if (!hot) return;
    var reg = id && regionById2(id);
    hot.setAttribute('d', reg ? wholeRingsPath(reg) : '');
    Array.prototype.forEach.call(zoomG.querySelectorAll('.m-area-lbl'), function (l) {
      l.classList.toggle('is-hot', !!id && l.getAttribute('data-region') === id);
    });
  }

  Array.prototype.forEach.call(zoomG.querySelectorAll('[data-region]'), function (node) {
    var id = node.getAttribute('data-region');
    node.addEventListener('click', function (e) {
      if (mapDragged()) return;
      e.stopPropagation();
      setHot(null);
      enterRegion(id);
    });
    node.addEventListener('mouseenter', function () { setHot(id); });
    node.addEventListener('mouseleave', function () { setHot(null); });
    /* Touch has no hover, so the first tap lights the area and the click
       that follows enters it — the highlight is the feedback for the tap. */
    node.addEventListener('pointerdown', function () { setHot(id); });
  });
  var hostEl = document.getElementById('map');
  if (hostEl) hostEl.addEventListener('pointerleave', function () { setHot(null); });

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

  /* The appellation names are obstacles as well - Dordogne used to settle
     across Fronsac - but only on the first attempt. If honouring them would
     leave no room on the river at all, the name is better slightly over one
     of them than missing. */
  var alsoTaken = [];
  Array.prototype.forEach.call(zoomG.querySelectorAll('.m-area-lbl'), function (e) {
    if (e.style.display === 'none') return;
    var r = e.getBoundingClientRect();
    if (r.width) alsoTaken.push(r);
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
    function settle(obstacles) {
      for (var i = 0; i < tries.length; i++) {
        tp.setAttribute('startOffset', tries[i] + '%');
        var r = t.getBoundingClientRect();
        if (!r.width) continue;
        if (r.left < fr.left + 8 || r.right > fr.right - 8 ||
            r.top < fr.top + 8 || r.bottom > fr.bottom - 8) continue;
        var clash = false;
        for (var m = 0; m < obstacles.length; m++) {
          if (overlapArea(r, obstacles[m]) > 0) { clash = true; break; }
        }
        if (clash) continue;
        taken.push(r);
        return true;
      }
      return false;
    }

    if (settle(taken.concat(alsoTaken))) return;
    if (settle(taken)) return;
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
  /* Seventy-one estate positions come from OpenStreetMap, which is ODbL
     and asks to be credited where the data is shown. */
  var credit = '<text class="m-credit" x="' + (MS.w - 22) + '" y="' +
    (MS.h - 10) + '" text-anchor="end">positions: OpenStreetMap contributors, ' +
    'ODbL · INAO · Wikidata</text>';
  g.innerHTML = credit +
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


/* ===========================================================================
   Type-ahead on the search box.

   The box already filters the list; this lets you go straight to one estate
   without reading the list at all. Matching ignores accents and punctuation
   in both directions, so "leglise" finds Clos l'Église and "petrus" finds
   Pétrus, and a match on the start of any word ranks above one in the middle
   — typing "lafite" should not offer Lafite's neighbours first.
   =========================================================================== */
var acItems = [], acIndex = -1, acBox = null;

function acKey(s) {
  return deaccent(String(s)).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}
/* The same thing with the gaps closed up, so a name written L’Église can be
   found by typing leglise - the apostrophe becomes a space in acKey, and a
   query without one would never match across it. */
function acTight(s) {
  return deaccent(String(s)).toLowerCase().replace(/[^a-z0-9]+/g, '');
}

function acSearch(q) {
  var k = acKey(q), t = acTight(q);
  if (t.length < 2) return [];

  /* Appellations first. Typing "paui" should offer the place as readily as
     the estates in it, and there are only twenty-odd of them, so they never
     crowd the list. */
  var places = [];
  window.BDX_MAP.regions.forEach(function (r) {
    var name = acKey(r.name), at = name.indexOf(k);
    if (at === 0 || (at > 0 && name.charAt(at - 1) === ' ') || acTight(r.name).indexOf(t) === 0) {
      places.push({ region: r, n: chateauxInRegion(r).length });
    }
  });
  places.sort(function (a, b) { return acKey(a.region.name).indexOf(k) - acKey(b.region.name).indexOf(k); });

  var starts = [], words = [], inside = [];
  for (var i = 0; i < CH.length; i++) {
    var ch = CH[i], name = acKey(ch.name), tight = acTight(ch.name);
    var at = name.indexOf(k);
    if (at === 0) starts.push(ch);
    else if (at > 0 && name.charAt(at - 1) === ' ') words.push(ch);
    else if (at > 0 || tight.indexOf(t) >= 0) inside.push(ch);
  }
  return places.slice(0, 3).concat(starts, words, inside).slice(0, 9);
}

function acClose() {
  acItems = []; acIndex = -1;
  if (acBox) { acBox.style.display = 'none'; acBox.innerHTML = ''; }
}

function acRender(list) {
  if (!acBox) return;
  acItems = list;
  acIndex = -1;
  if (!list.length) { acClose(); return; }
  acBox.innerHTML = list.map(function (item, i) {
    if (item.region) {
      return '<button type="button" class="acrow acplace" data-i="' + i + '">' +
        '<span class="acname">' + item.region.name + '</span>' +
        '<span class="acwhere">Appellation · ' + item.n + ' château' +
        (item.n === 1 ? '' : 'x') + '</span></button>';
    }
    var def = clsDef(item.cls);
    return '<button type="button" class="acrow" data-i="' + i + '" data-ch="' + item.id + '">' +
      '<span class="acname">' + item.name + '</span>' +
      '<span class="acwhere">' + item.appellation +
      (def && def.name ? ' · ' + rankLabel(item) : '') + '</span></button>';
  }).join('');
  acBox.style.display = '';
}

function acChoose(i) {
  var item = acItems[i];
  if (!item) return;
  acClose();
  if (el.search) el.search.value = '';
  state.q = '';
  /* An appellation takes you to its ground; an estate opens its drawer. */
  if (item.region) {
    enterRegion(item.region.id);
    return;
  }
  refresh();
  openDrawer(item.id);
}

function acMove(d) {
  if (!acItems.length) return;
  acIndex = (acIndex + d + acItems.length) % acItems.length;
  Array.prototype.forEach.call(acBox.querySelectorAll('.acrow'), function (b, i) {
    b.classList.toggle('on', i === acIndex);
  });
}

function wireTypeahead() {
  if (!el.search) return;
  var field = el.search.parentNode;
  field.style.position = 'relative';
  acBox = document.createElement('div');
  acBox.className = 'acbox';
  acBox.style.display = 'none';
  field.appendChild(acBox);

  el.search.setAttribute('autocomplete', 'off');
  el.search.addEventListener('input', function () {
    acRender(acSearch(el.search.value));
  });
  el.search.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); acMove(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); acMove(-1); }
    else if (e.key === 'Enter') {
      if (acItems.length) { e.preventDefault(); acChoose(acIndex >= 0 ? acIndex : 0); }
    } else if (e.key === 'Escape') { acClose(); }
  });
  acBox.addEventListener('mousedown', function (e) {
    var b = e.target.closest ? e.target.closest('.acrow') : null;
    if (!b) return;
    e.preventDefault();
    acChoose(parseInt(b.getAttribute('data-i'), 10));
  });
  el.search.addEventListener('blur', function () { setTimeout(acClose, 120); });
}

function openDrawer(id) {
  var ch = null;
  for (var i = 0; i < CH.length; i++) if (CH[i].id === id) { ch = CH[i]; break; }
  if (!ch) return;
  /* openDrawer is also how the wine selector redraws, so it keeps the
     choice when reopening the same estate and resets it on a new one. */
  if (state.active !== id) state.wine = 'grand';
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
      ' title="from ' + (site[1] === 'ugcb' ? 'the UGCB register'
                        : site[1] === 'osm' ? 'OpenStreetMap' : 'Wikidata') + '">' +
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
  /* How many of the years actually carry a rating - the one fact the old
     Critic ratings strip knew that this list does not say for itself. It
     has to be counted the way the rows below are scored, not off the small
     table of hand-entered figures the strip used: that said 4 of 43 for an
     estate whose rows show ratings for most of them. */
  body += wineSwitcher(ch);

  var ratedYears = YEARS.filter(function (yr) { return !scoreFor(ch, yr).none; }).length;
  /* How many of the forty-three are worth opening this year. It is the first
     thing anyone standing in front of a cellar wants to know, so it goes in
     the heading rather than waiting to be counted off the rows. */
  var readyNow = YEARS.filter(function (yr) {
    var m = maturity(drinkWindow(ch, yr));
    return m && (m.k === 'peak' || m.k === 'late');
  }).length;
  /* The other wines carry no critic score and no window, so the heading
     counts what they do have: the years with a sheet on file. */
  var sel = wineById(ch, state.wine);
  var onFile = YEARS.filter(function (yr) {
    return wineFiche(ch, state.wine, yr);
  }).length;
  var hint = state.wine === 'grand'
    ? ratedYears + ' of ' + YEARS.length + ' rated · ' + readyNow + ' ready to drink now'
    : onFile + ' of ' + YEARS.length + ' with a sheet on file';
  body +=
    '<div class="section"><h3>' +
      (state.wine === 'grand' ? 'All vintages, 1982–2024'
                              : sel.name + ', 1982–2024') +
      '<span class="hint">' + hint + '</span></h3>' +
      '<div class="vintagelist">' +
        YEARS.map(function (yr) {
          return state.wine === 'grand' ? vintageRow(ch, yr)
                                        : cuveeRow(ch, state.wine, yr);
        }).join('') +
      '</div></div>';

  el.drawerBody.innerHTML = body;
  el.drawerBody.scrollTop = 0;
  el.drawer.classList.add('is-open');
  el.scrim.classList.add('is-open');
  el.drawer.setAttribute('aria-hidden', 'false');

  document.getElementById('closeDrawer').addEventListener('click', closeDrawer);

  var ws = document.getElementById('wineSel');
  if (ws) ws.addEventListener('change', function () {
    state.wine = ws.value;
    openDrawer(ch.id);
    el.drawerBody.scrollTop = 0;
  });

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

/* What the estate itself published about this wine. The estate's own words
   take precedence over the Bordeaux-wide account: where a château describes
   its own season or its own wine, that is what is shown, and the regional
   text is not repeated underneath. Sourcing is kept quiet - a short grey
   line, not a badge - because it should be checkable, not loud. */
function fiche(ch, yr) {
  var F = window.BDX_FICHES;
  var en = (F && F[ch.id + '|' + yr]) || null;
  if (!en) return null;
  var lang = window.BDX_LANG ? BDX_LANG.get() : 'en';
  if (lang === 'en') return en;
  var alt = (window.BDX_FICHES_NL || {})[ch.id + '|' + yr];
  if (!alt) return en;
  /* Field by field, so a tasting note that has been translated shows in
     Dutch even when the vintage note beside it has not. */
  var out = {};
  for (var k in en) out[k] = en[k];
  if (alt.note) out.note = alt.note;
  if (alt.taste) out.taste = alt.taste;
  if (alt.decant) out.decant = alt.decant;
  if (alt.window) out.window = alt.window;
  return out;
}

function fichesBlock(ch, yr) {
  var f = fiche(ch, yr);
  if (!f) return '';
  var s = '';

  if (f.blend) {
    s += '<p class="subhead">Blend, ' + yr + '</p>' +
      blendBar(f.blend) +
      '<div class="tableview' + (state.tables ? ' on' : '') + '">' +
        blendTable(f.blend) + '</div>';
    if (ch.blend) {
      var moved = GRAPE_ORDER.filter(function (k) {
        return (f.blend[k] || 0) !== (ch.blend[k] || 0);
      }).map(function (k) {
        var d = (f.blend[k] || 0) - (ch.blend[k] || 0);
        return GRAPES[k].name + ' ' + (d > 0 ? '+' : '') + Math.round(d * 10) / 10;
      });
      s += '<p class="src">' + (moved.length
        ? 'Against the estate’s typical blend: ' + moved.join(' · ')
        : 'Exactly the estate’s typical blend.') + '</p>';
    }
  }

  var fx = [];
  if (f.yld) fx.push(['Yield', f.yld + ' hl/ha']);
  if (f.alc) fx.push(['Alcohol', f.alc + '% vol']);
  if (f.oak) fx.push(['New oak', f.oak + '%']);
  if (f.ph) fx.push(['pH', f.ph]);
  if (f.temp) fx.push(['Serve at', f.temp.join('–') + ' °C']);
  if (fx.length) {
    s += '<dl class="factgrid">' + fx.map(function (p) {
      return '<div class="fact"><dt>' + p[0] + '</dt><dd>' + p[1] + '</dd></div>';
    }).join('') + '</dl>';
  }

  /* The decanting advice and the keeping remark are shown by drinkBlock,
     with the window they belong beside. */
  return s;
}

/* The appellation's yield and the region's rain. Neither is this estate:
   the yield is every grower in the appellation, the rain is six weather
   stations across Bordeaux. Kept beside the season rather than in the
   château's own block for exactly that reason. */
function appellationLine(ch, yr) {
  var Y = window.BDX_YIELDS, R = window.BDX_RAIN;
  var y = Y && Y[ch.appellation], yv = y && y.y[yr];
  var r = R && R[yr];
  var bits = [];
  if (yv) {
    bits.push('<b>' + yv + ' hl/ha</b> in ' +
      (y.as || ch.appellation) + (y.ha ? ', across ' + y.ha.toLocaleString() + ' ha' : ''));
  }
  if (r) bits.push('<b>' + r.marSep + ' mm</b> of rain, March to September');
  if (!bits.length) return '';
  return '<div class="phenology">' + bits.join(' · ') +
    '<span class="src" title="Gavin Quinney, from Customs/CIVB and six weather stations">' +
    'Quinney</span></div>';
}

/* The season, told by the estate where it told it, and by the region where
   it did not. Each half falls back on its own: an estate that published a
   tasting note but no weather still gets the regional weather beneath it. */
function seasonBlock(ch, yr, v, o) {
  var f = fiche(ch, yr);
  var weather = (f && f.note) ? f.note : vintage(yr).weather;
  /* ntl and ttl mark a passage the estate published in French and that is
     shown here in English. It is still the estate's note, so it is said on
     the line that was already there rather than announced separately. */
  var wSrc = (f && f.note) ? (f.ntl ? 'this estate, translated' : 'this estate')
                           : 'Bordeaux';
  var wine = (f && f.taste) ? f.taste : ((o && o.note) ? o.note : vintage(yr).report);
  var tSrc = (f && f.taste) ? (f.ttl ? 'this estate, translated' : 'this estate')
                            : ((o && o.note) ? (o.src || 'reported') : 'Bordeaux');

  return '<p class="subhead">The ' + yr + ' season</p>' +
    '<p class="vintagereport">' + weather + '</p>' +
    '<p class="src">' + wSrc + '</p>' +
    '<p class="vintagereport">' + wine + '</p>' +
    '<p class="src">' + tSrc + '</p>' +
    phenologyLine(yr, ch) +
    appellationLine(ch, yr);
}

/* ------------------------- the estate's other wines ---------------------- */
/* An estate is not one wine. fiches.js holds the grand vin, the wine it is
   judged on, and cuvees.js holds the rest: the second wine, the dry white,
   the occasional odd cuvee. The drawer opens on the grand vin always, and
   offers the others beside it - the question "what else do they make?" is
   a real one, and until now the dashboard could not answer it. */

var CUVEES = window.BDX_CUVEES || {};
var CUVEE_WINES = window.BDX_CUVEE_WINES || {};

/* The grand vin is always first, and always present. */
function winesOf(ch) {
  var list = [{ slug: 'grand', name: ch.name, role: 'grand',
                colour: ch.cat === 'sweet' ? 'sweet'
                        : ch.cat === 'white' ? 'white' : 'red' }];
  var more = CUVEE_WINES[ch.id] || [];
  for (var i = 0; i < more.length; i++) list.push(more[i]);
  return list;
}

function wineById(ch, slug) {
  var list = winesOf(ch);
  for (var i = 0; i < list.length; i++) if (list[i].slug === slug) return list[i];
  return list[0];
}

/* The record for one wine in one year, whichever store it lives in. */
function wineFiche(ch, slug, yr) {
  if (!slug || slug === 'grand') return fiche(ch, yr);
  return CUVEES[ch.id + '|' + slug + '|' + yr] || null;
}

var ROLE_LABEL = { grand: 'the grand vin', second: 'second wine',
                   other: 'another cuvée' };

/* ----------------------------- when to drink ----------------------------- */
/* The vintage file carries one window per year, for "a classified-growth red
   of that year". That is the right place to start and the wrong answer for
   any one bottle: a fifth growth of 2016 is not on Latour's schedule, and a
   Merlot-led Pomerol is not on a Cabernet-led Pauillac's.

   So the window shown against an estate is the vintage's window moved by the
   two things this dashboard actually knows about the wine - where it ranks
   and what it is made of - and it says, wherever it appears, that it was
   derived that way. Where the estate published a window of its own, that one
   is used instead and is marked as the estate's.

   This is indicative in the same sense as the vintage ratings: it is not a
   critic's drinking window and does not stand in for one. Unlike a score,
   though, a window is advice rather than a measurement, which is why it is
   offered at all - the question "is this ready?" has no published answer for
   most of these 472 wines. */

/* What a rank is worth, in years, as [opens later, holds longer]. A first
   growth asks for more patience and then repays it for far longer; the lower
   tiers come round sooner and do not keep as well.

   Deliberately gentle, because for the Médoc this is a ranking of 1855
   prices and the fifth growths contain some of the longest-lived wines on
   the left bank. The score below is allowed to matter more than this does. */
var TIER_SHIFT = {
  0: [1, 6], 1: [1, 5], 2: [1, 3], 3: [0, 1], 4: [0, 0], 5: [0, -2]
};

function drinkWindow(ch, yr) {
  if (notProduced(ch, yr)) return null;
  var f = fiche(ch, yr);
  if (f && f.wy) return { from: f.wy[0], to: f.wy[1], src: 'estate' };

  var v = V[yr];
  if (!v) return null;
  var q = vintageRating(ch, yr);
  var t = TIER_SHIFT[ch.growth] || [0, 0];
  var from, to, floor = 3;

  if (ch.cat === 'sweet') {
    /* Sauternes runs on another clock altogether: a great year is barely
       awake at ten and can still be alive at seventy. Rank counts for more
       here than anywhere else, so it carries double weight on the far end. */
    from = yr + (q >= 95 ? 12 : q >= 88 ? 10 : 8) + t[0];
    to = yr + Math.max(15, Math.round(18 + (q - 70) * 1.15)) + t[1] * 2;
    floor = 5;
  } else if (ch.cat === 'white') {
    /* The dry whites of Pessac-Léognan keep far longer than their reputation
       allows, and nothing like as long as the reds beside them. */
    from = yr + 2;
    to = yr + Math.max(5, Math.round(7 + (q - 88) * 0.7)) + Math.round(t[1] / 2);
    floor = 1;
  } else {
    from = v.drinkFrom + t[0];
    to = v.drinkTo + t[1];

    /* Cabernet asks to be waited for and then lasts; Merlot gives earlier
       and is done sooner. Only the gap between the two carries any signal,
       so an estate with no blend on file stays on the vintage's own clock. */
    if (ch.blend) {
      var g = Math.round(((ch.blend.CS || 0) - (ch.blend.ME || 0)) / 30);
      from += g;
      to += g;
    }

    /* A year that went badly in this estate's own appellation does not hold
       as long as the vintage's headline suggests, and the reverse. */
    to += Math.round((q - 90) / 5);
  }

  /* And what the critics actually said about this wine in this year, where
     they said anything - the one piece of evidence here that knows what the
     estate is doing now rather than in 1855.

     What counts is the margin over the wine's own vintage, not the score in
     the absolute. A 92 in an 85-point year is an estate that rose above a
     difficult season, and those are the wines that outlast the window their
     vintage is given; the same 92 in a 97-point year is an estate that fell
     short of an easy one. Measured against a fixed number instead, every
     wine in a weak year came out short-lived together, which is the one
     thing a drinking window must not do - it is in the weak years that
     knowing which estate rose above it is worth anything at all. */
  var r = scoreFor(ch, yr);
  if (!r.none) {
    var over = r.score - q;
    to += Math.round(over / 1.5);
    from += Math.round(over / 4);
  }

  from = Math.max(yr + floor, from);
  to = Math.max(from + 2, to);
  return { from: from, to: to, src: 'derived' };
}

/* Where this year falls inside that window. The middle is where a bottle is
   worth opening; both edges are a warning, in opposite directions.

   The edges are measured in years left rather than as a share of the window,
   because a share gets it wrong at both extremes: a fifty-year window read
   proportionally calls a wine "drink up" with fifteen good years in hand,
   and a six-year window never warns at all. */
function maturity(w) {
  if (!w) return null;
  if (NOW < w.from) return { k: 'young', label: 'Too young' };
  if (NOW > w.to) return { k: 'past', label: 'Past' };
  var span = w.to - w.from;
  if (w.to - NOW <= Math.max(3, span * 0.12)) return { k: 'late', label: 'Drink up' };
  if (NOW - w.from <= Math.max(2, span * 0.15)) return { k: 'opening', label: 'Opening' };
  return { k: 'peak', label: 'At peak' };
}

/* The selector only appears where there is something to select. One wine
   needs no dropdown, and an estate with nothing but its grand vin on file
   should not be made to look as though something is missing. */
function wineSwitcher(ch) {
  var list = winesOf(ch);
  if (list.length < 2) return '';
  var opts = list.map(function (w) {
    var n = YEARS.filter(function (yr) {
      return wineFiche(ch, w.slug, yr);
    }).length;
    return '<option value="' + w.slug + '"' +
      (w.slug === state.wine ? ' selected' : '') + '>' + w.name +
      ' — ' + (ROLE_LABEL[w.role] || w.role) +
      (n ? ' · ' + n + ' vintages on file' : '') + '</option>';
  }).join('');
  return '<div class="section winepick">' +
    '<label for="wineSel">Which wine</label>' +
    '<select id="wineSel">' + opts + '</select></div>';
}

function drinkBlock(ch, yr) {
  var w = drinkWindow(ch, yr);
  if (!w) return '';
  var m = maturity(w);
  var f = fiche(ch, yr);
  var s = '<p class="subhead">When to drink</p>' +
    '<div class="drink">' +
      '<span class="drinkspan">' + w.from + '–' + w.to + '</span>' +
      '<span class="mat mat-' + m.k + '">' + m.label + '</span>' +
      '<span class="flag ' + (w.src === 'estate' ? 'flag-verified' : 'flag-modelled') +
        '">' + (w.src === 'estate' ? 'the estate’s own' : 'derived') + '</span>' +
    '</div>' +
    '<p class="src">' + (w.src === 'estate'
      ? 'the window this estate published for this vintage'
      : 'the vintage’s window, moved for this estate’s rank and blend') + '</p>';

  /* Where the estate said something about keeping without naming years, it
     belongs here next to the window rather than loose further down. */
  if (f && f.window && !f.wy) {
    s += '<p class="notetext">' + f.window + '</p>' +
      '<p class="src">this estate' + (f.wtl ? ', translated' : '') + '</p>';
  }
  if (f && f.decant) {
    s += '<p class="notetext">' + f.decant + '</p>' +
      '<p class="src">this estate' + (f.dtl ? ', translated' : '') + '</p>';
  }
  return s;
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
  /* The maturity sits in the collapsed head so that the question these rows
     are really asked - which of these should I open? - can be answered by
     running an eye down the list, without opening any of them. */
  var m = maturity(drinkWindow(ch, yr));

  return '<div class="vrow" data-year="' + yr + '" style="border-left:3px solid ' + edge + '">' +
    '<button class="vrow-head"><span class="yr">' + yr + '</span>' +
      '<span class="sc' + (rated && r.panel ? ' ratingwrap' : '') + '">' +
        (rated ? r.score : '—') + (rated ? ratingPanel(r) : '') + '</span>' +
      (m ? '<span class="mat mat-' + m.k + '">' + m.label + '</span>'
         : '<span class="mat mat-none"></span>') +
      '<span class="teaser">' + teaser + '</span>' +
      '<span class="chev">▾</span></button>' +
    '<div class="vrow-body">' +

      (rated
        ? '<p class="subhead">Rating</p>' +
          '<div class="ratingwrap" style="font-size:12.5px"><b>' + r.score + '/100</b>' +
            '<span class="src">' + (r.src || 'reported') + '</span>' +
            ratingPanel(r) + '</div>' +
          (o && o.note ? '<p class="notetext">' + o.note + '</p>' : '')
        : '') +

      (o && o.blend
        ? '<p class="subhead">Blend, this vintage</p>' +
          blendBar(o.blend) +
          '<div class="tableview' + (state.tables ? ' on' : '') + '">' +
            blendTable(o.blend) + '</div>'
        : '') +

      drinkBlock(ch, yr) +
      fichesBlock(ch, yr) +
      seasonBlock(ch, yr, v, o) +

      '<p class="subhead">Find this exact vintage</p>' +
      '<div class="buylinks">' + buyLinks(ch, yr).map(function (l) {
        return '<a class="buy' + (l.primary ? ' primary' : '') +
               '" target="_blank" rel="noopener noreferrer" href="' + l.url + '">' +
               l.label + ' <span style="opacity:.7;font-size:11px">' + l.host + '</span></a>';
      }).join('') + '</div>' +
    '</div></div>';
}

/* A year of one of the estate's other wines.

   Deliberately plainer than the grand vin's row. The critics rate the
   grand vin, so there is no score to show here and none is invented; the
   vintage report belongs to the appellation and is already one tap away
   on the grand vin. What a second wine's sheet does carry - its own
   blend, its alcohol, its time in wood - is what this shows, and a year
   with no sheet says so rather than pretending to be empty. */
function cuveeRow(ch, slug, yr) {
  var f = wineFiche(ch, slug, yr);
  var v = V[yr];
  if (!f) {
    return '<div class="vrow vrow-thin" data-year="' + yr + '">' +
      '<button class="vrow-head" disabled><span class="yr">' + yr + '</span>' +
      '<span class="teaser">No sheet on file for this wine</span></button></div>';
  }
  var bits = [];
  if (f.alc) bits.push(f.alc + '%');
  if (f.oak) bits.push(f.oak);
  if (f.yld) bits.push(f.yld + ' hl/ha');

  return '<div class="vrow" data-year="' + yr + '" ' +
      'style="border-left:3px solid ' + ratingColor(vintageRating(ch, yr)) + '">' +
    '<button class="vrow-head"><span class="yr">' + yr + '</span>' +
      '<span class="sc"></span>' +
      '<span class="mat mat-none"></span>' +
      '<span class="teaser">' + (bits.join(' · ') || v.report) + '</span>' +
      '<span class="chev">▾</span></button>' +
    '<div class="vrow-body">' +
      (f.blend
        ? '<p class="subhead">Blend, ' + yr + '</p>' + blendBar(f.blend) +
          '<div class="tableview' + (state.tables ? ' on' : '') + '">' +
            blendTable(f.blend) + '</div>'
        : '') +
      (bits.length
        ? '<dl class="factgrid">' +
            (f.alc ? '<div class="fact"><dt>Alcohol</dt><dd>' + f.alc + '%</dd></div>' : '') +
            (f.oak ? '<div class="fact"><dt>Ageing</dt><dd>' + f.oak + '</dd></div>' : '') +
            (f.yld ? '<div class="fact"><dt>Yield</dt><dd>' + f.yld + ' hl/ha</dd></div>' : '') +
            (f.harvest ? '<div class="fact"><dt>Picked</dt><dd>' + f.harvest + '</dd></div>' : '') +
          '</dl>'
        : '') +
      (f.note ? '<p class="subhead">The estate on the year</p>' +
                '<p class="notetext">' + f.note + '</p>' : '') +
      (f.taste ? '<p class="subhead">The estate on the wine</p>' +
                 '<p class="notetext">' + f.taste + '</p>' : '') +
      '<p class="src">this estate’s own sheet for this wine</p>' +
    '</div></div>';
}

/* ----------------------- the vintages, by appellation -------------------- */
/* What the season did is known for the appellation even where no estate was
   rated, so the year-by-year reading lives here now rather than being split
   into a number for each château. */
function regionCat(r) {
  if (r.id === 'sauternes' || r.id === 'barsac') return 'sweet';
  if (r.id === 'entre-deux-mers') return 'white';
  return 'red';
}

function regionVintageRating(r, year) {
  return vintageRating({ cat: regionCat(r), appellation: r.apps[0] }, year);
}


/* Every estate of one appellation in one year, best first. The rating is the
   same derived figure the drawer shows, and carries the same panel of critics
   on hover, so the ranking can be questioned without leaving the page. */
/* The vintage table only exists on a single appellation's page, so its rows
   are wired there rather than beside the card list. */
function wireVintageRows() {
  Array.prototype.forEach.call(el.appellations.querySelectorAll('.vt-row'), function (tr) {
    tr.addEventListener('click', function (e) {
      var name = e.target.closest ? e.target.closest('.vr-name') : null;
      if (name) { openDrawer(name.getAttribute('data-ch')); return; }
      if (e.target.closest && e.target.closest('.ratingpanel')) return;
      var yr = parseInt(tr.getAttribute('data-vt'), 10);
      state.apVintage = (state.apVintage === yr) ? null : yr;
      renderAppellationPage(state.apPage);
      var open = el.appellations.querySelector('.vt-row.on');
      if (open) open.scrollIntoView({ block: 'center' });
    });
  });
}

function vintageRoster(r, yr) {
  return rosterHtml(CH.filter(function (ch) { return inRegion(ch, r); }), r.name, yr);
}

/* The same ranked list for any set of estates, so the vintage-report chips -
   which each stand for several appellations - can open one too. */
function rosterHtml(list, label, yr) {
  var rated = [], unrated = [];
  list.forEach(function (ch) {
    var sc = scoreFor(ch, yr);
    if (sc.none) unrated.push(ch); else rated.push({ ch: ch, sc: sc });
  });
  rated.sort(function (a, b) { return (b.sc.exact || b.sc.score) - (a.sc.exact || a.sc.score); });
  if (!rated.length && !unrated.length) return '';

  /* This is the other place the dashboard lists individual wines - every
     estate of one appellation in one year - so it answers the same question
     the estate's own rows do, and in the same words. */
  var rows = rated.map(function (x) {
    var col = scoreColor(x.sc.score);
    var m = maturity(drinkWindow(x.ch, yr));
    return '<li><span class="vr-score' + (x.sc.panel ? ' ratingwrap' : '') +
      '" style="background:' + col + ';color:' + (inkOn(col) ? '#121211' : '#fff') + '">' +
      x.sc.score + (x.sc.panel ? ratingPanel(x.sc) : '') + '</span>' +
      '<button class="vr-name" data-ch="' + x.ch.id + '">' + x.ch.name + '</button>' +
      (m ? '<span class="mat mat-' + m.k + '">' + m.label + '</span>' : '') +
      '<span class="vr-rank">' + rankLabel(x.ch) + '</span></li>';
  }).join('');

  return '<div class="vroster"><h5>' + label + ' in ' + yr + ' · ' +
    rated.length + ' rated' + (unrated.length ? ', ' + unrated.length + ' without a rating' : '') +
    '</h5><ol class="vrlist">' + rows + '</ol>' +
    (unrated.length ? '<p class="src">No published rating for ' + yr + ': ' +
      unrated.slice(0, 12).map(function (c) { return c.name; }).join(' · ') +
      (unrated.length > 12 ? ' and ' + (unrated.length - 12) + ' more' : '') + '</p>' : '') +
    '</div>';
}

function vintageTable(r) {
  var rows = YEARS.map(function (yr) {
    var v = vintage(yr), rt = regionVintageRating(r, yr);
    var open = state.apVintage === yr;
    return '<tr class="vt-row' + (open ? ' on' : '') + '" data-vt="' + yr + '">' +
      '<th scope="row">' + yr + '</th>' +
      '<td><span class="vt-bar"><span style="width:' +
        Math.max(0, Math.min(100, (rt - 60) * 2.5)).toFixed(0) +
        '%;background:' + ratingColor(rt) + '"></span></span>' +
        '<b class="vt-num">' + rt + '</b></td>' +
      '<td class="vt-rep">' + v.report +
        (open ? vintageRoster(r, yr) : '') + '</td></tr>';
  }).join('');
  return '<table class="vintable"><caption>Season by season in ' + r.name +
    ', 1982–2024 — the documented character of each year, not a rating of ' +
    'any one wine.</caption><thead><tr><th>Vintage</th><th>Season</th>' +
    '<th>What happened</th></tr></thead><tbody>' + rows + '</tbody></table>';
}


/* The season's measured dates, from the ISVV's reference plots. These are
   observations, not a reading of consensus like the ratings beside them, so
   they are labelled as measured and carry how many reports agreed. */
var MONTH_NAME = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December'];
function fmtMonthDay(md) {
  if (!md) return '';
  var p = md.split('-');
  return parseInt(p[1], 10) + ' ' + MONTH_NAME[parseInt(p[0], 10)];
}
/* The season's three dates in the order they happen: flowering and véraison
   as the ISVV measured them on its reference plots, then the day this estate
   says it started picking. Two sources, one timeline, because that is how
   the year reads — and the source line says which is which. */
function phenologyLine(yr, ch) {
  var P = window.BDX_PHENOLOGY, ph = P && P[yr];
  var f = ch ? fiche(ch, yr) : null;
  var bits = [], src = [];
  if (ph && ph.flowering) bits.push('Flowering <b>' + fmtMonthDay(ph.flowering) + '</b>');
  if (ph && ph.veraison) bits.push('Véraison <b>' + fmtMonthDay(ph.veraison) + '</b>');
  if (bits.length) src.push('ISVV');
  if (f && f.harvest) {
    bits.push('Picking from <b>' + f.harvest + '</b>');
    src.push('this estate');
  }
  if (!bits.length) return '';
  return '<div class="phenology">' + bits.join(' · ') +
    '<span class="src" title="Flowering and véraison: Institut des Sciences de la ' +
    'Vigne et du Vin reference plots' + (ph && ph.n > 1 ? ', ' + ph.n + ' reports agree' : '') +
    '">' + src.join(' · ') + '</span></div>';
}

/* Each chip on a vintage card is a score for a stretch of ground, so it can
   be asked which wines earned it. The appellations behind each one: */
var VG_GROUPS = {
  medoc:     ['medoc', 'haut-medoc', 'saint-estephe', 'pauillac', 'saint-julien',
              'listrac', 'moulis', 'margaux'],
  pessac:    ['pessac-leognan', 'graves'],
  rightbank: ['saint-emilion', 'pomerol'],
  sauternes: ['sauternes', 'barsac']
};

function renderVintages() {
  var html = '';
  YEARS.forEach(function (yr) {
    var v = vintage(yr), rb = RB[yr], open = null;
    var defs = [['medoc', 'Médoc', v.medoc], ['pessac', 'Pessac-Léognan', v.pessac],
                ['rightbank', 'Saint-Émilion & Pomerol', rb.r],
                ['sauternes', 'Sauternes & Barsac', v.sauternes]];
    var chips = defs.map(function (c) {
      var col = ratingColor(c[2]), on = state.vgOpen === yr + '|' + c[0];
      if (on) open = c;
      return '<button type="button" class="ratechip' + (inkOn(col) ? ' ink-dark' : '') +
             (on ? ' on' : '') + '" data-grp="' + c[0] + '" data-yr="' + yr +
             '" style="background:' + col + '">' + c[1] + ' ' + c[2] + '</button>';
    }).join('');
    var d = [];
    if (v.app) Object.keys(v.app).forEach(function (k) { d.push(k + ' ' + (v.app[k] > 0 ? '+' : '') + v.app[k]); });
    if (rb.app) Object.keys(rb.app).forEach(function (k) { d.push(k + ' ' + (rb.app[k] > 0 ? '+' : '') + rb.app[k]); });
    html += '<article class="vgcard">' +
      '<div><div class="vgyear">' + yr + '</div>' +
        '<div style="font-size:11px;color:var(--text-muted);margin-top:4px">Drink ' +
          v.drinkFrom + '–' + v.drinkTo + '</div></div>' +
      '<div><p class="weather"><b>Weather.</b> ' + v.weather + '</p><p>' + v.report + '</p>' +
        phenologyLine(yr) +
        '<div class="ratings">' + chips + '</div>' +
        (open ? rosterHtml(CH.filter(function (ch) {
            return VG_GROUPS[open[0]].indexOf(regionIdOf(ch)) >= 0;
          }), open[1], yr) : '') +
        (d.length ? '<div style="font-size:11px;color:var(--text-muted);margin-top:6px">' +
          'Commune adjustments: ' + d.join(' · ') + '</div>' : '') +
      '</div></article>';
  });
  el.vintageGrid.innerHTML = html;

  /* The grid element survives each render, so the listener goes on once.
     Adding it per render would stack handlers and a chip would toggle itself
     back shut. */
  if (!el.vintageGrid.dataset.wired) {
    el.vintageGrid.dataset.wired = '1';
    el.vintageGrid.addEventListener('click', vgClick);
  }
}

function vgClick(e) {
  var name = e.target.closest ? e.target.closest('.vr-name') : null;
  if (name) { openDrawer(name.getAttribute('data-ch')); return; }
  if (e.target.closest && e.target.closest('.ratingpanel')) return;
  var chip = e.target.closest ? e.target.closest('.ratechip') : null;
  if (!chip) return;
  var key = chip.getAttribute('data-yr') + '|' + chip.getAttribute('data-grp');
  state.vgOpen = (state.vgOpen === key) ? null : key;
  renderVintages();
}

/* Which appellation an estate sits in, by id rather than by printed name. */
function regionIdOf(ch) {
  var R = window.BDX_MAP.regions;
  for (var i = 0; i < R.length; i++) if (inRegion(ch, R[i])) return R[i].id;
  return '';
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
  el.tabCompare.setAttribute('aria-selected', v === 'compare');
  document.body.classList.toggle('map-page', v === 'producers');
  if (v !== 'producers') {
    el.paneList.classList.remove('is-open');
  }
  el.appellations.style.display    = v === 'appellations' ? '' : 'none';
  el.classifications.style.display = v === 'classifications' ? '' : 'none';
  el.compare.style.display         = v === 'compare' ? '' : 'none';
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


/* ===========================================================================
   The settings panel.

   One setting so far, the interface language. Switching it puts the written
   English back, rebuilds every view from source and then says the result in
   the chosen language - see assets/i18n.js, which matches whole phrases and
   so leaves the estates' own words alone.
   =========================================================================== */
function rerenderEverything() {
  renderReference();
  renderVintages();
  buildAppellationSelect();
  refresh();
  buildChips();
  if (state.active) openDrawer(state.active);
}

function wireSettings() {
  var btn = document.getElementById('settingsBtn');
  var panel = document.getElementById('settings');
  var opts = document.getElementById('langOpts');
  if (!btn || !panel || !opts || !window.BDX_LANG) return;

  function paint() {
    opts.innerHTML = BDX_LANG.list.map(function (l) {
      return '<button type="button" class="langbtn' +
        (BDX_LANG.get() === l[0] ? ' on' : '') + '" data-lang="' + l[0] +
        '" aria-pressed="' + (BDX_LANG.get() === l[0]) + '">' + l[1] + '</button>';
    }).join('');
  }
  paint();

  function shut() {
    panel.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
  }
  btn.addEventListener('click', function () {
    panel.hidden = !panel.hidden;
    btn.setAttribute('aria-expanded', String(!panel.hidden));
  });
  opts.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('.langbtn') : null;
    if (!b) return;
    BDX_LANG.set(b.getAttribute('data-lang'), rerenderEverything);
    paint();
    shut();
  });
  document.addEventListener('click', function (e) {
    if (panel.hidden) return;
    if (e.target.closest && e.target.closest('.settings-wrap')) return;
    shut();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hidden) shut();
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

  /* Last, so the first render is already on screen to be translated. */
  wireSettings();
  if (window.BDX_LANG) BDX_LANG.start();

  el.search.addEventListener('input', function () { state.q = el.search.value; refresh(); });
  wireTypeahead();
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
  el.tabCompare.addEventListener('click', function () {
    setView('compare');
    renderCompare();
  });
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
