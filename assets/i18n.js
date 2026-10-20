/* ===========================================================================
   Dutch for the interface.

   The dashboard is written in English in one place — the markup and the
   render functions — and said in another language on the way out. Every
   entry below matches a whole piece of text, never a part of one: a label,
   a heading, a button, a counted phrase. That is what makes this safe to
   run over the entire page. The châteaux's own words and the vintage
   reports match nothing here and are left exactly as published, which is
   also the honest thing to do with quoted material.

   Scores, hectares, hl/ha, °C, mm and the grape names stay as they are:
   they read the same in both languages.
   =========================================================================== */
(function () {
  'use strict';

  var MONTHS = {
    January: 'januari', February: 'februari', March: 'maart', April: 'april',
    May: 'mei', June: 'juni', July: 'juli', August: 'augustus',
    September: 'september', October: 'oktober', November: 'november',
    December: 'december'
  };
  var MON = Object.keys(MONTHS).join('|');

  /* --- whole phrases ------------------------------------------------------ */
  var NL = {
    /* masthead and tabs */
    'Install app': 'App installeren',
    '☾ Dark': '☾ Donker',
    '☀ Light': '☀ Licht',
    '⚙ Settings': '⚙ Instellingen',
    'Language': 'Taal',
    'Appellations': 'Appellaties',
    'Classifications': 'Classificaties',
    'Producers & map': 'Producenten & kaart',
    'Vintage reports': 'Jaargangen',

    /* the filter row */
    'Search': 'Zoeken',
    'Appellation': 'Appellatie',
    'All appellations': 'Alle appellaties',
    '← All appellations': '← Alle appellaties',
    'Show scores from': 'Scores tonen van',
    'All vintages': 'Alle jaargangen',
    'Reset': 'Wissen',

    /* the appellations */
    'The appellations': 'De appellaties',
    'the classifications': 'de classificaties',
    'Left Bank': 'Linkeroever',
    'Right Bank': 'Rechteroever',
    'Between the rivers': 'Tussen de rivieren',
    'The Médoc': 'De Médoc',
    'The sweet wines': 'De zoete wijnen',
    'The Libournais': 'Het Libournais',
    'The Côtes': 'De Côtes',
    'West of the Gironde and the Garonne — gravel, Cabernet Sauvignon':
      'Westelijk van de Gironde en de Garonne — grind, Cabernet Sauvignon',
    'East of the Gironde and north of the Dordogne — clay and limestone, Merlot':
      'Oostelijk van de Gironde en noordelijk van de Dordogne — klei en kalksteen, Merlot',
    'The Entre-Deux-Mers, Garonne to Dordogne — dry white':
      'De Entre-Deux-Mers, Garonne tot Dordogne — droge witte wijn',

    /* one appellation */
    'See it on the map': 'Bekijk op de kaart',
    'Read the appellation': 'Lees over de appellatie',
    'History': 'Geschiedenis',
    'Terroir': 'Terroir',
    'The wines': 'De wijnen',
    'The vintages': 'De jaargangen',
    'The châteaux': 'De châteaux',
    'The estates': 'De domeinen',
    'Vintage': 'Jaargang',
    'Season': 'Seizoen',
    'What happened': 'Wat er gebeurde',
    'No sourced note for this appellation yet.':
      'Nog geen onderbouwde notitie voor deze appellatie.',

    /* the classifications */
    'The classifications': 'De classificaties',
    'an appellation': 'een appellatie',
    'Official classifications': 'Officiële classificaties',
    'Rankings with legal standing': 'Rangordes met wettelijke status',
    'Never classified': 'Nooit geclassificeerd',
    'Groupings of appellations, not ranks':
      'Groeperingen van appellaties, geen rangordes',
    'list superseded': 'lijst vervangen',
    'Unclassified': 'Niet geclassificeerd',
    'Classified for': 'Geclassificeerd voor',
    'Listed': 'Vermeld',
    'The group shown above is an appellation, not a rank.':
      'De groep hierboven is een appellatie, geen rangorde.',

    /* the map */
    'All of Bordeaux': 'Heel Bordeaux',
    'Click an appellation to see its châteaux':
      'Klik op een appellatie om de châteaux te zien',
    'Close the château list': 'Sluit de lijst met châteaux',
    'Château, commune, proprietor…': 'Château, gemeente, eigenaar…',

    /* one estate */
    'Estate detail': 'Gegevens van het domein',
    'Close ✕': 'Sluiten ✕',
    'Classification': 'Classificatie',
    'Vineyard': 'Wijngaard',
    'Proprietor': 'Eigenaar',
    'Second wine': 'Tweede wijn',
    'Website': 'Website',
    'House style': 'Huisstijl',
    'Typical blend': 'Typische samenstelling',
    'Variety': 'Druif',
    'Share': 'Aandeel',
    'Rating': 'Score',
    'Blend, this vintage': 'Samenstelling, deze jaargang',
    'Exactly the estate’s typical blend.':
      'Precies de typische samenstelling van het domein.',
    'Flowering': 'Bloei',
    'Véraison': 'Véraison',
    '· Véraison': '· Véraison',

    /* what a fiche technique says */
    'Blend': 'Samenstelling',
    'Harvest': 'Oogst',
    'Picked': 'Geoogst',
    'Yield': 'Opbrengst',
    'Alcohol': 'Alcohol',
    'New oak': 'Nieuw hout',
    'Decanting': 'Decanteren',
    'Serve at': 'Serveren op',
    'Drink': 'Drinken',

    /* buying it */
    'Find this exact vintage': 'Vind precies deze jaargang',
    'Cheapest online': 'Goedkoopste online',
    'Shopping': 'Winkelen',
    'All merchants': 'Alle handelaren',
    'Web search': 'Zoeken op het web',

    /* sourcing */
    'gathered by bordoverview.com': 'verzameld door bordoverview.com',
    'this estate': 'dit domein',
    'this estate, translated': 'dit domein, vertaald',
    'reported': 'gerapporteerd',
    'Weather.': 'Weer.',
    'Pavie and Figeac': 'Pavie en Figeac',

    /* the editorial groupings, which live in data/classifications.js */
    'The Côtes de Bordeaux': 'De Côtes de Bordeaux',
    'The first rank': 'De eerste rang',
    'Classic estates': 'Klassieke domeinen',
    'Other notable estates': 'Andere vooraanstaande domeinen',
    'First rank': 'Eerste rang',
    'Classic estate': 'Klassiek domein',
    'Notable estate': 'Vooraanstaand domein',
    'editorial grouping': 'redactionele indeling',
    'no ranking within the list': 'geen rangorde binnen de lijst',
    'clay-limestone slopes and plateau': 'klei-kalkhellingen en plateau',
    'more clay and sand': 'meer klei en zand',
    'the Néac plateau': 'het plateau van Néac',
    'clay-limestone over harder rock': 'klei-kalk op harder gesteente',
    'the limestone escarpment': 'de kalksteenrand',
    'Saint-Émilion’s plateau': 'het plateau van Saint-Émilion',
    'the gravel that named the region': 'het grind dat de regio zijn naam gaf',
    'dry white between the rivers': 'droge witte wijn tussen de rivieren',

    /* the settings panel */
    'English': 'English',
    'Nederlands': 'Nederlands'
  };

  /* Whole paragraphs. These live in a list rather than in the table above
     because an object literal cannot have a key built up across lines. */
  var LONG = [
    ['Twenty pieces of ground, each with its own rules about what may be ' +
     'planted and how. An appellation says where a wine is from. It does ' +
     'not say how good anyone thinks it is — for that, see',
     'Twintig stukken grond, elk met eigen regels over wat er geplant mag ' +
     'worden en hoe. Een appellatie zegt waar een wijn vandaan komt. Ze ' +
     'zegt niet hoe goed iemand hem vindt — daarvoor, zie'],

    ['Where a critic published a rating for a particular château it is ' +
     'shown on that château. What the season itself did is known for the ' +
     'appellation whether or not any one wine was rated, so it is ' +
     'recorded here.',
     'Waar een criticus een score voor een bepaald château publiceerde, ' +
     'staat die bij dat château. Wat het seizoen zelf deed, is bekend voor ' +
     'de appellatie, of er nu een wijn beoordeeld is of niet, en wordt ' +
     'daarom hier vastgelegd.'],

    ['Bordeaux has no single hierarchy. It has six official ones, drawn up ' +
     'at different times, on different banks, by different people and for ' +
     'different reasons — and great appellations that were never ranked at ' +
     'all. A classification ranks estates; that is not the same thing as',
     'Bordeaux heeft geen enkele rangorde. Het heeft zes officiële, ' +
     'opgesteld op verschillende momenten, op verschillende oevers, door ' +
     'verschillende mensen en om verschillende redenen — en grote ' +
     'appellaties die nooit zijn gerangschikt. Een classificatie ' +
     'rangschikt domeinen; dat is niet hetzelfde als'],

    ['The interface. What the châteaux and the vintage reports say is left ' +
     'in the language it was published in.',
     'De interface. Wat de châteaux en de jaargangverslagen zeggen, blijft ' +
     'in de taal waarin het gepubliceerd is.']
  ];
  LONG.forEach(function (pair) { NL[pair[0]] = pair[1]; });

  /* --- phrases that carry a number or a name ------------------------------ */
  var RE = [
    [/^Every estate on both banks · (\d+) appellations · six classifications · (\d+) vintages, (\d+)–(\d+)$/,
     'Elk domein op beide oevers · $1 appellaties · zes classificaties · $2 jaargangen, $3–$4'],
    [/^(\d+) estates$/, '$1 domeinen'],
    [/^(\d+) estate$/, '$1 domein'],
    [/^(\d+) of (\d+) estates$/, '$1 van $2 domeinen'],
    [/^(\d+) estates · no classification$/, '$1 domeinen · geen classificatie'],
    [/^(\d+) hectares$/, '$1 hectare'],
    [/^Classification of (\d+)$/, 'Classificatie van $1'],
    [/^Classification of (\d+) · (.+)$/, 'Classificatie van $1 · $2'],
    [/^(\d+) of (\d+) rated · each with its own price link$/,
     '$1 van $2 beoordeeld · elk met een eigen prijslink'],
    [/^All vintages, (\d+)–(\d+)$/, 'Alle jaargangen, $1–$2'],
    [/^(\d+) critics, averaging ([\d.]+) · they differ by ([\d.]+) points$/,
     '$1 critici, gemiddeld $2 · ze verschillen $3 punten'],
    [/^(\d+) critics, averaging ([\d.]+)$/, '$1 critici, gemiddeld $2'],
    [/^(\d+) critics$/, '$1 critici'],
    [/^1 critic$/, '1 criticus'],
    [/^The (\d{4}) season$/, 'Het seizoen $1'],
    [/^Blend, (\d{4})$/, 'Samenstelling, $1'],
    [/^Drink (\d+)–(\d+)$/, 'Drinken $1–$2'],
    [/^in (.+), across ([\d,.]+) ha$/, 'in $1, over $2 ha'],
    [/^in (.+), across ([\d,.]+) ha ·$/, 'in $1, over $2 ha ·'],
    [/^Commune adjustments: (.+)$/, 'Correcties per gemeente: $1'],
    [/^Appellation · (\d+) châteaux$/, 'Appellatie · $1 châteaux'],
    [/^Appellation · (\d+) château$/, 'Appellatie · $1 château'],
    [/^(.+) in (\d{4}) · (\d+) rated, (\d+) without a rating$/,
     '$1 in $2 · $3 beoordeeld, $4 zonder score'],
    [/^(.+) in (\d{4}) · (\d+) rated$/, '$1 in $2 · $3 beoordeeld'],
    [/^No published rating for (\d{4}): (.+)$/,
     'Geen gepubliceerde score voor $1: $2'],
    [/^and (\d+) more$/, 'en $1 meer'],
    [/^No estate matches these filters\. Try clearing the search box or lowering the minimum score\.$/,
     'Geen domein past bij deze filters. Maak het zoekveld leeg of verlaag de minimumscore.'],
    [/^Season by season in (.+), (\d+)–(\d+) — the documented character of each year, not a rating of any one wine\.$/,
     'Seizoen na seizoen in $1, $2–$3 — het gedocumenteerde karakter van elk jaar, geen beoordeling van een afzonderlijke wijn.'],
    [/^Against the estate’s typical blend: (.+)$/,
     'Tegenover de typische samenstelling van het domein: $1'],
    /* A group heading is a name, a note and a count, and only the middle
       part is ours to say differently - so ask the table about that part
       and leave the name alone. Last in the list: the specific rules above
       must have their turn first. */
    [/^(.+) · (.+) · (\d+)$/, function (m) {
      var a = say(DICTS.nl, m[1]), b = say(DICTS.nl, m[2]);
      if (a === null && b === null) return null;
      return (a || m[1]) + ' · ' + (b || m[2]) + ' · ' + m[3];
    }],
    [/^(.+) · (.+)$/, function (m) {
      var a = say(DICTS.nl, m[1]), b = say(DICTS.nl, m[2]);
      if (a === null && b === null) return null;
      return (a || m[1]) + ' · ' + (b || m[2]);
    }],

    /* a date the way Dutch writes it */
    [new RegExp('^(\\d+) (' + MON + ')$'),
     function (m) { return m[1] + ' ' + MONTHS[m[2]]; }],
    [new RegExp('^of rain, (' + MON + ') to (' + MON + ')$'),
     function (m) { return 'regen, ' + MONTHS[m[1]] + ' tot ' + MONTHS[m[2]]; }]
  ];

  var DICTS = { nl: { exact: NL, re: RE } };

  /* --- applying it -------------------------------------------------------- */
  /* What was changed, so switching back to English does not need a reload. */
  var undo = [];
  var ATTRS = ['placeholder', 'aria-label', 'title', 'alt'];

  function say(d, raw) {
    var t = raw.replace(/\s+/g, ' ').trim();
    if (!t) return null;
    if (d.exact[t]) return d.exact[t];
    for (var i = 0; i < d.re.length; i++) {
      var m = t.match(d.re[i][0]);
      if (!m) continue;
      var out = d.re[i][1];
      return typeof out === 'function' ? out(m)
        : out.replace(/\$(\d)/g, function (_, n) { return m[+n]; });
    }
    return null;
  }

  function walk(root, d) {
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        var tag = n.parentNode && n.parentNode.nodeName;
        if (tag === 'SCRIPT' || tag === 'STYLE') return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var n, hits = [];
    while ((n = w.nextNode())) {
      var out = say(d, n.nodeValue);
      if (out !== null && out !== n.nodeValue) hits.push([n, n.nodeValue, out]);
    }
    hits.forEach(function (h) {
      undo.push([h[0], null, h[1]]);
      h[0].nodeValue = h[2];
    });

    /* and the words that live in attributes */
    var els = root.querySelectorAll ? root.querySelectorAll('*') : [];
    Array.prototype.forEach.call(els, function (e) {
      ATTRS.forEach(function (a) {
        if (!e.hasAttribute(a)) return;
        var v = e.getAttribute(a), out = say(d, v);
        if (out !== null && out !== v) {
          undo.push([e, a, v]);
          e.setAttribute(a, out);
        }
      });
    });
  }

  function restore() {
    for (var i = undo.length - 1; i >= 0; i--) {
      var u = undo[i];
      if (u[1] === null) u[0].nodeValue = u[2];
      else u[0].setAttribute(u[1], u[2]);
    }
    undo = [];
  }

  var current = 'en', watching = null;

  function apply(root) {
    var d = DICTS[current];
    if (d) walk(root || document.body, d);
  }

  /* Each render replaces a section's markup wholesale, so rather than ask
     every render function to remember, watch for the new nodes and say them
     in the chosen language as they arrive. Only nodeValue and attributes are
     touched here, never the tree, so this cannot set itself off. */
  function watch() {
    if (watching || !window.MutationObserver) return;
    watching = new MutationObserver(function (recs) {
      if (current === 'en') return;
      recs.forEach(function (r) {
        Array.prototype.forEach.call(r.addedNodes, function (n) {
          if (n.nodeType === 1) apply(n);
          else if (n.nodeType === 3) {
            var out = say(DICTS[current], n.nodeValue);
            if (out !== null && out !== n.nodeValue) {
              undo.push([n, null, n.nodeValue]);
              n.nodeValue = out;
            }
          }
        });
      });
    });
    watching.observe(document.body, { childList: true, subtree: true });
  }

  window.BDX_LANG = {
    /* which languages there are, in the order the settings panel shows them */
    list: [['en', 'English'], ['nl', 'Nederlands']],

    get: function () { return current; },

    stored: function () {
      try { return localStorage.getItem('bdx-lang') || 'en'; } catch (e) { return 'en'; }
    },

    set: function (lang, rerender) {
      if (lang !== 'en' && !DICTS[lang]) lang = 'en';
      if (lang === current) return;
      restore();                     /* back to the written English first */
      current = lang;
      try { localStorage.setItem('bdx-lang', lang); } catch (e) {}
      document.documentElement.setAttribute('lang', lang);
      if (rerender) rerender();      /* the views rebuild their own markup */
      if (lang !== 'en') apply(document.body);
      watch();
    },

    /* Start-up: adopt the stored choice without the restore-and-rerender. */
    start: function () {
      var lang = this.stored();
      if (DICTS[lang]) {
        current = lang;
        document.documentElement.setAttribute('lang', lang);
        apply(document.body);
      }
      watch();
    },

    /* For code that needs one phrase rather than a whole subtree. */
    t: function (s) {
      if (current === 'en') return s;
      var out = say(DICTS[current], s);
      return out === null ? s : out;
    }
  };
})();
