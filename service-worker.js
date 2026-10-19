'use strict';

var CACHE_NAME = 'bordeaux-classified-v4';
var APP_SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './assets/app.js',
  './assets/styles.css',
  './assets/fonts/firasans-400-latin.woff2',
  './assets/fonts/firasans-400-latinext.woff2',
  './assets/fonts/firasans-600-latin.woff2',
  './assets/fonts/firasans-600-latinext.woff2',
  './assets/crest.png',
  './assets/icon-192.png',
  './assets/icon-512.png',
  './assets/icon.svg',
  './data/batch2.js',
  './data/batch3.js',
  './data/chateaux.js',
  './data/classifications.js',
  './data/cruartisan.js',
  './data/crubourgeois.js',
  './data/geography.js',
  './data/graves.js',
  './data/libournais.js',
  './data/notes.js',
  './data/overrides.js',
  './data/pomerol.js',
  './data/rightbank.js',
  './data/saintemilion.js',
  './data/sauternes.js',
  './data/vintages.js'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(APP_SHELL.map(function (path) {
        return new URL(path, self.registration.scope).href;
      }));
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (key) {
        if (key.indexOf('bordeaux-classified-') === 0 && key !== CACHE_NAME) {
          return caches.delete(key);
        }
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function (event) {
  var request = event.request;
  var url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then(function (response) {
        if (response.ok) {
          var copy = response.clone();
          event.waitUntil(caches.open(CACHE_NAME).then(function (cache) {
            return cache.put(new URL('./index.html', self.registration.scope).href, copy);
          }));
        }
        return response;
      }).catch(function () {
        return caches.match(new URL('./index.html', self.registration.scope).href);
      })
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(function (cached) {
      return cached || fetch(request);
    })
  );
});
