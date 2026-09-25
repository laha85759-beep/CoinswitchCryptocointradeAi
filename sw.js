'use strict';

/**
 * Monetag / TheSmartMag Push Notification Service Worker
 * Zone ID: 11880194
 */
self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

try {
  importScripts('https://5gvci.com/act/files/service-worker.js?z=11880194');
} catch (e) {
  console.debug('Monetag SW import notice:', e);
}

self.addEventListener('push', (event) => {
  if (!(self.Notification && self.Notification.permission === 'granted')) {
    return;
  }
  let payload = {
    title: 'TheSmartMag Quant Terminal',
    body: 'Institutional AI Quant Signal Detected',
    icon: '/figures/overview.png',
    data: { url: 'https://trade.thesmartmag.com/' }
  };
  if (event.data) {
    try {
      payload = Object.assign(payload, event.data.json());
    } catch (err) {
      payload.body = event.data.text();
    }
  }
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: payload.icon,
      data: payload.data
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const urlToOpen = (event.notification.data && event.notification.data.url) || 'https://trade.thesmartmag.com/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (let client of windowClients) {
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(urlToOpen);
      }
    })
  );
});
