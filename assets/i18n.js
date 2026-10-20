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
    'Blend, this vintage': 'Samenstelling, deze jaargang',    'the estate’s usual blend':
        'de gebruikelijke assemblage van het domein',
    'the estate’s usual blend, unchanged this year':
        'de gebruikelijke assemblage van het domein, dit jaar onveranderd',
    'Picking': 'Pluk',
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

    /* sourcing - these live in title attributes, which the first pass over
       the interface never looked at because it only collected short text */
    'gathered by bordoverview.com': 'verzameld door bordoverview.com',
    'Gavin Quinney, from Customs/CIVB and six weather stations':
      'Gavin Quinney, uit gegevens van de douane/CIVB en zes weerstations',
    'from the UGCB register': 'uit het UGCB-register',
    'from Wikidata': 'uit Wikidata',
    'from OpenStreetMap': 'uit OpenStreetMap',
    'positions: OpenStreetMap contributors, ODbL · INAO · Wikidata':
      'posities: OpenStreetMap-bijdragers, ODbL · INAO · Wikidata',
    'To install this app, tap Share in Safari, then choose "Add to Home Screen".':
      'Tik in Safari op Deel en kies daarna “Zet op beginscherm” om deze app ' +
      'te installeren.',

    /* the 1855 ranks as the notes name them */
    'First Growths': 'Premiers Crus',
    'Second Growths': 'Deuxièmes Crus',
    'Third Growths': 'Troisièmes Crus',
    'Fourth Growths': 'Quatrièmes Crus',
    'Fifth Growths': 'Cinquièmes Crus',
    'this estate': 'dit domein',
    'this estate, translated': 'dit domein, vertaald',

    /* The cellar. */
    'My cellar': 'Mijn kelder',
    'In my cellar': 'In mijn kelder',
    'none': 'geen',
    'one bottle': 'één fles',
    'Wine': 'Wijn',
    'Bottles': 'Flessen',
    'Drink': 'Drinken',
    'No window': 'Geen venster',
    'running out of time': 'de tijd raakt op',
    'worth opening now': 'nu de moeite waard om te openen',
    'ready, and will keep': 'klaar, en kan nog blijven liggen',
    'not yet': 'nog niet',
    'the other wines, which are not on the window model':
      'de andere wijnen, die niet op het venstermodel staan',
    'past the window the dashboard gives them':
      'voorbij het venster dat het dashboard hun geeft',
    'Keeping a copy': 'Een kopie bewaren',
    'The file is plain text and holds nothing but what you have entered.':
      'Het bestand is platte tekst en bevat niets anders dan wat u hebt ingevoerd.',
    'Save to a file': 'Opslaan naar een bestand',
    'Load from a file': 'Laden uit een bestand',
    'That file could not be read as a cellar.':
      'Dat bestand kon niet als kelder gelezen worden.',
    'Nothing in that file was new.': 'Niets in dat bestand was nieuw.',
    'One fewer bottle': 'Eén fles minder',
    'One more bottle': 'Eén fles meer',
    'Bottles held': 'Flessen in bezit',
    'Bottle size': 'Flesformaat',
    'the owning group’s site': 'de site van de eigenaarsgroep',
    'Size': 'Formaat',
    'litres': 'liter',

    /* The sizes. The name is what the list shows; the two forms below it
       are what a count reads as, and Dutch does not always inflect the
       way English does - a magnum stays a magnum. */
    'Half bottle': 'Halve fles',
    'Bottle': 'Fles',
    'Magnum': 'Magnum',
    'Marie-Jeanne': 'Marie-Jeanne',
    'Double magnum': 'Dubbele magnum',
    'Jéroboam': 'Jéroboam',
    'Impériale': 'Impériale',
    'one half bottle': 'één halve fles',
    'one magnum': 'één magnum',
    'one Marie-Jeanne': 'één Marie-Jeanne',
    'one double magnum': 'één dubbele magnum',
    'one jéroboam': 'één jéroboam',
    'one impériale': 'één impériale',

    /* Side by side. */
    'Compare': 'Vergelijken',
    'Side by side': 'Naast elkaar',
    'One estate, several vintages': 'Eén domein, meerdere jaargangen',
    'One vintage, several estates': 'Eén jaargang, meerdere domeinen',
    'Estate': 'Domein',
    'Add an estate': 'Voeg een domein toe',
    'Choose…': 'Kies…',
    'Rank': 'Rang',
    'The season': 'Het seizoen',
    'The estate on the year': 'Het domein over het jaar',
    'The estate on the wine': 'Het domein over de wijn',
    'the estate’s usual': 'de gebruikelijke van het domein',
    'not made': 'niet gemaakt',
    'Pick two or more wines to put them side by side.':
      'Kies twee of meer wijnen om ze naast elkaar te zetten.',

    /* When to drink. The five maturity states are read off a list of
       forty-three rows, so they stay as short in Dutch as in English. */
    'In barrel': 'Op hout',
    'Serve it with': 'Serveren met',
    'this estate’s own suggestion': 'de eigen suggestie van dit domein',
    'this estate’s own suggestion, translated':
      'de eigen suggestie van dit domein, vertaald',
    'Scores on the estate’s sheet': 'Scores op de fiche van het domein',
    'reprinted by this estate, on each critic’s own scale':
      'overgenomen door dit domein, op de eigen schaal van elke criticus',
    'When to drink': 'Wanneer te drinken',
    'Too young': 'Te jong',
    'Opening': 'Opent zich',
    'At peak': 'Op zijn top',
    'Drink up': 'Opdrinken',
    'Past': 'Voorbij',
    'the estate’s own': 'van het domein zelf',
    'derived': 'afgeleid',
    'the window this estate published for this vintage':
      'het venster dat dit domein voor deze jaargang publiceerde',
    'the vintage’s window, moved for this estate’s rank and blend':
      'het venster van de jaargang, verschoven naar de rang en de samenstelling van dit domein',
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
    ['What you hold, in the sizes you hold it in, and editable here as ' +
     'well as on the vintage rows. It is kept in this browser on this ' +
     'machine and is sent nowhere, which means it will not follow you to ' +
     'another device and will go if the browser is cleared — so take ' +
     'a copy.',
     'Wat u in bezit hebt, in de formaten waarin u het hebt, en hier net ' +
     'zo goed te wijzigen als op de jaargangregels. Het wordt in deze ' +
     'browser op deze machine bewaard en wordt nergens heen gestuurd, wat ' +
     'betekent dat het u niet naar een ander apparaat volgt en verdwijnt ' +
     'als de browser wordt gewist — maak dus een kopie.'],

    ['Nothing in it yet. Open any château, open a vintage, and set the ' +
     'number of bottles.',
     'Nog niets. Open een château, open een jaargang en stel het aantal ' +
     'flessen in.'],

    ['A vertical reads one estate down its vintages; a horizontal reads ' +
     'one vintage across its estates. Everything here is what the rest of ' +
     'the dashboard holds, arranged so that two wines can be read against ' +
     'each other instead of one at a time.',
     'Een verticale leest één domein door zijn jaargangen heen; een ' +
     'horizontale leest één jaargang over zijn domeinen heen. Alles hier ' +
     'is wat de rest van het dashboard bevat, zo gerangschikt dat twee ' +
     'wijnen tegen elkaar gelezen kunnen worden in plaats van één voor één.'],

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
     'in de taal waarin het gepubliceerd is.'],

    ['The rank shown above is this dashboard’s editorial grouping by ' +
     'critical and market standing — it carries no official weight.',
     'De rang hierboven is de redactionele indeling van dit dashboard naar ' +
     'kritische en commerciële reputatie — ze heeft geen officiële status.']
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
    /* The tail is a note of its own - "First Growths", "editorial
       grouping" - so it goes through the table too. As a plain
       replacement this rule matched first and carried its tail through
       untranslated, leaving "Classificatie van 1855 · First Growths". */
    [/^Classification of (\d+) · (.+)$/, function (m) {
      var tail = say(DICTS.nl, m[2]);
      return 'Classificatie van ' + m[1] + ' · ' + (tail === null ? m[2] : tail);
    }],
    [/^(\d+) of (\d+) rated · each with its own price link$/,
     '$1 van $2 beoordeeld · elk met een eigen prijslink'],
    [/^(\d+) of (\d+) rated · (\d+) ready to drink now$/,
     '$1 van $2 beoordeeld · $3 nu te drinken'],
    [/^Choose up to (\d+) vintages\.$/, 'Kies maximaal $1 jaargangen.'],
    [/^(\d+(?:-\d+)?) months$/, '$1 maanden'],
    [/^(\d+) bottles$/, '$1 flessen'],
    [/^1 bottle$/, '1 fles'],
    [/^(\d+) half bottles$/, '$1 halve flessen'],
    [/^(\d+) magnums$/, '$1 magnums'],
    [/^(\d+) Marie-Jeannes$/, '$1 Marie-Jeannes'],
    [/^(\d+) double magnums$/, '$1 dubbele magnums'],
    [/^(\d+) jéroboams$/, '$1 jéroboams'],
    [/^(\d+) impériales$/, '$1 impériales'],
    [/^(\d+) different wines$/, '$1 verschillende wijnen'],
    [/^1 wine$/, '1 wijn'],
    /* Dutch writes a decimal with a comma, and litres do not take a
       plural after a number. */
    [/^([\d.]+) litres$/, function (m) {
      return m[1].replace('.', ',') + ' liter';
    }],
    [/^(\d+) bottles · (\d+) different wines$/, '$1 flessen · $2 verschillende wijnen'],
    [/^(\d+) bottles · 1 wine$/, '$1 flessen · 1 wijn'],
    [/^1 bottle · 1 wine$/, '1 fles · 1 wijn'],
    [/^(\d+) wines merged in\.$/, '$1 wijnen samengevoegd.'],
    [/^1 wine merged in\.$/, '1 wijn samengevoegd.'],
    [/^Add up to (\d+) estates\.$/, 'Voeg maximaal $1 domeinen toe.'],
    [/^(\d+) hl\/ha$/, '$1 hl/ha'],
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
     'Seizoen na seizoen in $1, $2–$3 — het gedocumenteerde karakter van elk jaar, geen beoordeling van een afzonderlijke wijn.'],    /* A group heading is a name, a note and a count, and only the middle
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

    /* A segment of the usual-blend bar: what the variety usually is,
       and what it was this year. */
    [/^(.+) ([\d.]+)% usually, ([\d.]+)% this year$/,
     function (m) { return m[1] + ' ' + m[2] + '% gebruikelijk, ' + m[3] +
                           '% dit jaar'; }],
    /* The phenology tooltip, whose tail counts the reports that agree. */
    [/^Flowering and véraison: Institut des Sciences de la Vigne et du Vin reference plots$/,
     'Bloei en véraison: referentiepercelen van het Institut des Sciences de la Vigne et du Vin'],
    [/^Flowering and véraison: Institut des Sciences de la Vigne et du Vin reference plots, (\d+) reports agree$/,
     'Bloei en véraison: referentiepercelen van het Institut des Sciences de la Vigne et du Vin, $1 rapporten komen overeen'],

    /* the word for picking, which arrives with the variety it
       introduces, the grape names being left as they are */
    [/^Picking (.+)$/, function (m) { return 'Pluk ' + m[1]; }],

    /* a picking span, the way Dutch writes it */
    [new RegExp('^(\\d+)\u2013(\\d+) (' + MON + ')$'),
     function (m) { return m[1] + '\u2013' + m[2] + ' ' + MONTHS[m[3]]; }],
    [new RegExp('^(\\d+) (' + MON + ') \u2013 (\\d+) (' + MON + ')$'),
     function (m) { return m[1] + ' ' + MONTHS[m[2]] + ' \u2013 ' + m[3] +
                           ' ' + MONTHS[m[4]]; }],
    [new RegExp('^from (\\d+) (' + MON + ')$'),
     function (m) { return 'vanaf ' + m[1] + ' ' + MONTHS[m[2]]; }],
    [new RegExp('^to (\\d+) (' + MON + ')$'),
     function (m) { return 'tot ' + m[1] + ' ' + MONTHS[m[2]]; }],

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

  function phrase(d, t) {
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

  /* A phrase is looked up trimmed, because "Flowering " and "Flowering"
     are the same phrase, and then given back the space it was found
     with. Without that, a label in its own element arrives against the
     number beside it: "Bloei4 juni". */
  function say(d, raw) {
    var t = raw.replace(/\s+/g, ' ').trim();
    if (!t) return null;
    var out = phrase(d, t);
    if (out === null) return null;
    return raw.match(/^\s*/)[0] + out + raw.match(/\s*$/)[0];
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
