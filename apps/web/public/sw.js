/* Yondo service worker: shows push notifications while the site is closed (docs/push-notifications.md).
   The payload carries no personal data: a short title/body and an in-app path. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

/** Only same-origin in-app paths are opened; anything else falls back to the notifications list. */
function safePath(url) {
  return typeof url === 'string' && /^\/(?!\/)[A-Za-z0-9/_\-?=&.%]*$/.test(url) ? url : '/notifications';
}

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = {};
  }
  const title = typeof data.title === 'string' && data.title ? data.title : 'Yondo';
  event.waitUntil(
    self.registration.showNotification(title, {
      body: typeof data.body === 'string' ? data.body : '',
      icon: '/icon-512.png',
      badge: '/icon-512.png',
      tag: data.notification_id || undefined,
      data: { url: safePath(data.url) },
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL(safePath(event.notification.data && event.notification.data.url), self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((wins) => {
      for (const w of wins) {
        if (new URL(w.url).origin === self.location.origin && 'focus' in w) {
          return w.focus().then((f) => (f && 'navigate' in f ? f.navigate(target) : f));
        }
      }
      return self.clients.openWindow(target);
    }),
  );
});
