// Synchronauts as an installed app. Caches nothing: the board only makes sense live. Its one job is the window that
// opens while the server is not running, which says how to start it instead of a browser error page.
'use strict';
const OFFLINE = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Synchronauts</title><style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#111114;color:#e8e8ed;
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;text-align:center;padding:24px;box-sizing:border-box}
code{background:#26262c;padding:3px 8px;border-radius:6px;font:13px ui-monospace,Menlo,monospace}
p{margin:6px 0}.dim{color:#8e8e96}</style></head><body><div>
<p>Synchronauts is not running. Start it in a terminal:</p><p><code>~/.synchronauts/syn ui</code></p>
<p class="dim">Synchronauts läuft nicht. Im Terminal starten mit dem Befehl oben.</p></div></body></html>`;

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', (e) => {
  if (e.request.mode !== 'navigate') return;  // the API and everything else go straight to the server
  e.respondWith(fetch(e.request).catch(() => new Response(OFFLINE, { headers: {
    'Content-Type': 'text/html; charset=utf-8',
    'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'",
  } })));
});
