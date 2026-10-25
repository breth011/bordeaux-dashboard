/* Phase 4: every legacy data global, as JSON, for the migration.

     node tools/legacy-dump.js > out.json

   Read-only. Runs each data/*.js file into a sandbox with a bare
   `window` (the way the page and tools/canonical-view.js do) and writes
   { file: { GLOBAL: value } } (window.X and top-level var X alike), so the migration reads exactly the
   values the page reads, including the two provenance files the page
   does not load. Nothing is written.
*/
'use strict';
var fs = require('fs');
var path = require('path');
var vm = require('vm');

/* An optional argument names another data directory (Phase 4 dual read). */
var DATA = process.argv[2] || path.join(__dirname, '..', 'data');
var out = {};
fs.readdirSync(DATA).filter(function (f) { return /[.]js$/.test(f); })
  .sort().forEach(function (f) {
    var sandbox = { window: {} };
    vm.createContext(sandbox);
    vm.runInContext(fs.readFileSync(path.join(DATA, f), 'utf8'), sandbox,
                    { filename: f });
    /* A file may assign window.X or declare a top-level var X (which
       lands on the sandbox itself); both are what the page sees. */
    var g = {};
    Object.keys(sandbox).sort().forEach(function (k) {
      if (k !== 'window') g[k] = sandbox[k];
    });
    Object.keys(sandbox.window).sort().forEach(function (k) {
      g[k] = sandbox.window[k];
    });
    out[f] = g;
  });
process.stdout.write(JSON.stringify(out));
