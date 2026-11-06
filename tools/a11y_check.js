// Accessibility check of the built site with axe-core (WCAG 2.1 A/AA rules), run in Chromium.
//   npm i axe-core@4.10.2 playwright     (once)   then:   node tools/a11y_check.js [public]
// Third-party frames (Getty, Sofascore, GoatCounter) are blocked so only our own markup is judged.
const path = require('path'), http = require('http'), fs = require('fs');
const { chromium } = require('playwright');
const axe = fs.readFileSync(require.resolve('axe-core/axe.min.js', { paths: [process.cwd(), __dirname, process.env.AXE_DIR || '.'] }), 'utf8');
const root = path.resolve(process.argv[2] || 'public');
const pages = ['index.html', 'latest.html', 'about.html', 'contact.html', 'opportunities.html', 'charter.html', 'liability.html', 'archive.html', 'search.html',
  ...fs.readdirSync(path.join(root, 'category')).map(f => 'category/' + f),
  ...fs.readdirSync(path.join(root, 'article')).slice(0, 12).map(f => 'article/' + f)];
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' };
const srv = http.createServer((q, r) => {
  const f = path.join(root, decodeURIComponent(q.url.split('?')[0]));
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); r.end(d); });
}).listen(0, async () => {
  const base = `http://127.0.0.1:${srv.address().port}/`;
  const b = await chromium.launch(); const out = {}; let total = 0;
  for (const vp of [{ width: 1300, height: 900 }, { width: 390, height: 844 }]) {
    const p = await b.newPage({ viewport: vp });
    await p.route(u => !u.href.startsWith(base), r => r.abort());
    for (const pg of pages) {
      if (fs.readFileSync(path.join(root, pg), 'utf8').includes('http-equiv="refresh"')) continue;
      await p.goto(base + pg); await p.addScriptTag({ content: axe });
      const res = await p.evaluate(() => axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] }));
      for (const v of res.violations) {
        const k = `${v.impact} · ${v.id}: ${v.help}`; out[k] = out[k] || new Set();
        v.nodes.slice(0, 3).forEach(n => out[k].add(`${pg} (${vp.width}px) ${n.target.join(' ')}`)); total++;
      }
    }
  }
  await b.close(); srv.close();
  console.log(`axe: ${pages.length} صفحة × عرضان، ${Object.keys(out).length} نوع ملاحظة`);
  for (const [k, s] of Object.entries(out)) { console.log('\n' + k); [...s].slice(0, 6).forEach(x => console.log('   ' + x)); }
  process.exit(Object.keys(out).some(k => /^(critical|serious)/.test(k)) ? 1 : 0);
});
