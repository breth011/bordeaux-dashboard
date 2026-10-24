/* Phase 3.0: the canonical estate list, as the dashboard builds it.

     node tools/canonical-view.js > out.json

   Read-only. Loads the data files the page loads, in the page's order,
   into a sandbox with a bare `window`, then expands them the way
   assets/app.js section 1 does: full records default their `cls`,
   the compact lists become sparse records with ids `cls + '-' + slug`,
   and the Graves cross-list is applied. Nothing is written.

   It repeats app.js rather than running it, because app.js needs a DOM.
   tools/test-phase30.py checks the result against the counts in
   classifications.js, so the two cannot drift apart unnoticed.
*/
'use strict';
var fs = require('fs');
var path = require('path');
var vm = require('vm');

var ROOT = path.join(__dirname, '..');
var FILES = ['classifications.js', 'chateaux.js', 'sauternes.js',
             'saintemilion.js', 'pomerol.js', 'graves.js',
             'crubourgeois.js', 'cruartisan.js', 'libournais.js',
             'batch2.js', 'batch3.js', 'batch4.js', 'cuvees.js'];

var sandbox = { window: {} };
vm.createContext(sandbox);
FILES.forEach(function (f) {
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'data', f), 'utf8'),
                  sandbox, { filename: f });
});
var W = sandbox.window;

/* The same slug as app.js. */
function slug(s) {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

var out = [];
(W.BDX_CHATEAUX || []).forEach(function (ch) {
  out.push({
    id: ch.id, name: ch.name,
    cls: ch.cls || (ch.cat === 'sweet' ? 'sauternes' : '1855'),
    growth: ch.growth, cat: ch.cat || null,
    appellation: ch.appellation || null, commune: ch.commune || null,
    second: ch.second || null, sparse: false
  });
});
function sparse(name, appellation, cls, growth) {
  out.push({ id: cls + '-' + slug(name), name: name, cls: cls,
             growth: growth, cat: 'red', appellation: appellation,
             commune: appellation, second: null, sparse: true });
}
(W.BDX_STEM_GCC || []).forEach(function (n) { sparse(n, 'Saint-Émilion', 'stem', 3); });
(W.BDX_POMEROL_OTHER || []).forEach(function (n) { sparse(n, 'Pomerol', 'pomerol', 3); });
var CB = W.BDX_CRU_BOURGEOIS || {};
[['exceptionnel', 1], ['superieur', 2], ['bourgeois', 3]].forEach(function (p) {
  (CB[p[0]] || []).forEach(function (row) { sparse(row[0], row[1], 'bourgeois', p[1]); });
});
((W.BDX_CRU_ARTISAN || {}).current || []).forEach(function (row) {
  sparse(row[0], row[1], 'artisan', 1);
});

var cross = {};
(W.BDX_GRAVES_CROSSLIST || []).forEach(function (id) { cross[id] = 'graves'; });
/* The other wines, as cuvees.js lists them: name, role, colour. */
var wines = W.BDX_CUVEE_WINES || {};
out.forEach(function (e) {
  e.cross = cross[e.id] || null;
  e.wines = (wines[e.id] || []).map(function (c) {
    return { name: c.name, role: c.role, colour: c.colour || null };
  });
});

process.stdout.write(JSON.stringify({
  collections: (W.BDX_CLASSIFICATIONS || []).map(function (c) {
    return { id: c.id, name: c.name, year: c.year, estates: c.estates,
             editorial: !!c.editorial };
  }),
  estates: out
}, null, 1));
