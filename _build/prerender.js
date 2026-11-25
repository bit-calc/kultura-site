// Prerender the three homes (/, /ru/, /en/) so search and AI crawlers that don't run JavaScript see the content.
// Run after build.py:  node _build/prerender.js
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const ROOT = path.resolve(__dirname, '..');
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.png': 'image/png', '.svg': 'image/svg+xml', '.mp4': 'video/mp4', '.txt': 'text/plain', '.xml': 'application/xml' };

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  let fp = path.join(ROOT, p);
  if (fp.endsWith('/') || (fs.existsSync(fp) && fs.statSync(fp).isDirectory())) fp = path.join(fp, 'index.html');
  if (!fs.existsSync(fp)) { res.writeHead(404); return res.end('404'); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(fp)] || 'application/octet-stream' });
  fs.createReadStream(fp).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(8765, r));
  const browser = await chromium.launch();
  for (const route of ['/', '/ru/', '/en/']) {
    const page = await browser.newPage();
    await page.route('**/*', r => r.request().url().startsWith('http://localhost:8765') ? r.continue() : r.abort());
    await page.goto('http://localhost:8765' + route, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelectorAll('#slist .svc').length > 0 && document.querySelectorAll('#jr [data-art]').length > 0);
    const html = await page.evaluate(() => {
      document.querySelectorAll('video').forEach(v => { v.pause(); });
      document.querySelectorAll('script[src*="googletagmanager.com"]').forEach(s => s.remove());   // the tag loader adds it again in the visitor's browser
      return '<!doctype html>\n' + document.documentElement.outerHTML;
    });
    fs.writeFileSync(path.join(ROOT, route, 'index.html'), html);
    console.log('prerendered', route, html.length);
    await page.close();
  }
  await browser.close();
  server.close();
})();
