// Service Worker mínimo para habilitar PWA (Add to Home Screen)
self.addEventListener('install', function (e) {
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(self.clients.claim());
});

// Não faz cache de downloads; apenas permite o install do PWA
self.addEventListener('fetch', function (e) {
  // Deixa o navegador tratar normalmente (sem offline cache para não quebrar downloads)
  return;
});
