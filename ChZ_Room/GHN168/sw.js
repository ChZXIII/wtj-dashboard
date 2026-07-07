const CACHE_NAME = 'ghn168-app-v143';
const ASSETS = [
  'index.html',
  'app.js?v=143',
  'manifest.json?v=143',
  'assets/ghn_app_icon.png',
  'assets/logo.png',
  'assets/sidebar_logo_dark.png',
  'assets/sidebar_logo_light.png',
  'assets/GHN_company_seal.png',
  'assets/html2pdf.bundle.min.js',
  'signatures/sig_keng.png',
  'signatures/sig_hom.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET' || !e.request.url.startsWith('http')) return;

  e.respondWith(
    caches.match(e.request).then((cachedResponse) => {
      if (cachedResponse) {
        fetch(e.request).then((networkResponse) => {
          if (networkResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(e.request, networkResponse.clone());
            });
          }
        }).catch(() => {});
        return cachedResponse;
      }
      return fetch(e.request);
    })
  );
});
