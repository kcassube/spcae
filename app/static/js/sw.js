self.addEventListener('push', function(event){
  let data = {};
  try { data = event.data.json(); } catch(e) {}
  const title = data.title || 'Benachrichtigung';
  const body = data.body || (data.message || '');
  const url = data.url || '/';
  event.waitUntil(self.registration.showNotification(title, {
    body: body,
    icon: '/static/favicon.ico',
    data: { url }
  }));
});

self.addEventListener('notificationclick', function(event){
  event.notification.close();
  const url = event.notification.data && event.notification.data.url || '/';
  event.waitUntil(clients.matchAll({type: 'window'}).then(list => {
    for (const c of list){
      if (c.url.endsWith(url) && 'focus' in c) return c.focus();
    }
    if (clients.openWindow) return clients.openWindow(url);
  }));
});
