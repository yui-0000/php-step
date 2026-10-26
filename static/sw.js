const CACHE = 'php-step-shell-v9';
const SHELL = ['/', '/static/style.css', '/static/app.js', '/static/core.js', '/static/questions.js', '/static/sync.js', '/api/questions', '/manifest.webmanifest', '/static/icon.svg', '/static/icon-192.png', '/static/icon-512.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('php-step-shell-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== location.origin || !SHELL.includes(url.pathname)) return;
  event.respondWith(caches.open(CACHE).then(async cache => {
    // Check admission online; only a failed connection uses the offline copy.
    if (url.pathname === '/' || url.pathname === '/api/questions') {
      try {
        const response = await fetch(event.request);
        if (response.ok && !response.redirected) await cache.put(url.pathname, response.clone());
        return response;
      } catch {
        return (await cache.match(url.pathname)) || Response.error();
      }
    }
    return (await cache.match(url.pathname)) || fetch(event.request);
  }));
});
