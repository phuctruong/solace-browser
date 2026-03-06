/**
 * sw.js — Solace Browser Service Worker
 * Enables PWA install, offline support, and push notifications.
 */

const CACHE_NAME = 'solace-v1';
const OFFLINE_URL = '/offline.html';

// Assets to cache on install — yinyang branding icons MUST be precached
const PRECACHE_URLS = [
  '/',
  '/home.html',
  '/app-store.html',
  '/css/solace.css',
  '/js/solace-core.js',
  '/favicon.ico',
  '/favicon.svg',
  '/manifest.json',
  '/images/yinyang/yinyang-logo-32.png',
  '/images/yinyang/yinyang-logo-48.png',
  '/images/yinyang/yinyang-logo-128.png',
  '/images/yinyang/yinyang-logo-256.png',
  '/images/yinyang/yinyang-logo-512.png',
  '/images/pwa/icon-192.png',
  '/images/pwa/icon-512.png',
];

// Install: cache shell assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch(() => {
        // Non-critical — some assets may not exist yet
      });
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch: network-first for API, cache-first for static assets
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // API calls: network only (no caching)
  if (url.pathname.startsWith('/api/')) return;

  // Static assets: stale-while-revalidate
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, clone);
            });
          }
          return response;
        })
        .catch(() => {
          // Offline: return cached or offline page
          return cached || caches.match(OFFLINE_URL);
        });

      return cached || fetchPromise;
    })
  );
});

// Push notifications (for scheduled task completion, approval requests)
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body || 'Solace Browser needs your attention',
    icon: '/images/pwa/icon-192.png',
    badge: '/images/pwa/icon-192.png',
    tag: data.tag || 'solace-notification',
    data: { url: data.url || '/home.html' },
    actions: data.actions || [
      { action: 'approve', title: 'Approve' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
  };

  event.waitUntil(self.registration.showNotification(data.title || 'Solace Browser', options));
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/home.html';

  if (event.action === 'approve') {
    // Handle approval action
    event.waitUntil(
      self.clients.matchAll({ type: 'window' }).then((clients) => {
        const client = clients.find((c) => c.visibilityState === 'visible');
        if (client) {
          client.postMessage({ type: 'approval', action: 'approve', tag: event.notification.tag });
        }
      })
    );
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes(url) && 'focus' in client) {
          return client.focus();
        }
      }
      return self.clients.openWindow(url);
    })
  );
});
