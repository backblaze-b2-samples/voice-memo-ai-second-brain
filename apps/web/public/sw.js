// Minimal service worker stub.
//
// Voice Memo AI Second Brain registers this file so the browser treats the
// app as installable (PWA). It deliberately does no caching: we don't want
// stale transcripts or stale memo lists, and the API responses are not
// safely cacheable across users.
//
// If you decide to add offline support later, scope it to the static asset
// shell — never cache `/memos`, `/summaries`, or any presigned URLs.

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", () => {
  // Pass-through. No interception.
});
