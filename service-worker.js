'use strict';

var CACHE_NAME = 'bordeaux-classified-v131';
var APP_SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './assets/app.js',
  './assets/i18n.js',
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
  './data/appellations.js',
  './data/water.js',
  './data/geography.js',
  './data/graves.js',
  './data/libournais.js',
  './data/notes.js',
  './data/notes-nl.js',
  './data/overrides.js',
  './data/pomerol.js',
  './data/rightbank.js',
  './data/saintemilion.js',
  './data/sauternes.js',
  './data/ratings.js',
  './data/climate.js',
  './data/fiches.js',
  './data/fiches-nl.js',
  './data/cuvees.js',
  './data/coords.js',
  './data/phenology.js',
  './data/websites.js',
  './data/vintages-nl.js',
  './data/plantings.js',
  './data/fiches-url.js',
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

  /* The app's own code and styles follow the page: served from the network
     when there is one, from the cache when there is not. Cache-first here
     was a mistake - the page came off the network and its JavaScript came
     out of the previous deploy's cache, so new markup was driven by old
     code and anything newly added quietly did nothing. */
  if (/\.(?:js|css|webmanifest)$/.test(url.pathname) &&
      url.pathname.indexOf('/data/') === -1) {
    event.respondWith(
      fetch(request).then(function (response) {
        if (response.ok) {
          var copy = response.clone();
          event.waitUntil(caches.open(CACHE_NAME).then(function (cache) {
            return cache.put(request, copy);
          }));
        }
        return response;
      }).catch(function () {
        return caches.match(request);
      })
    );
    return;
  }

  /* Everything else - the data files, the fonts, the images - is large and
     changes rarely, so it is served from the cache at once and refreshed
     behind the back of the page. A change lands on the next visit rather
     than holding this one up. */
  event.respondWith(
    caches.match(request).then(function (cached) {
      if (cached) {
        event.waitUntil(
          fetch(request).then(function (response) {
            if (!response.ok) return;
            return caches.open(CACHE_NAME).then(function (cache) {
              return cache.put(request, response);
            });
          }).catch(function () {})
        );
        return cached;
      }
      return fetch(request);
    })
  );
});
