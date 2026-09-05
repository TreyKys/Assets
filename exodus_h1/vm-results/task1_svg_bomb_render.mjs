// Task 1.2 (render measurement) — load the billion-laughs SVG as
// data:image/svg+xml;base64,... inside an <img>, same as the app's AssetIcons render path,
// and measure decode time + memory in headless Chromium. Fresh browser per depth so a
// crashed/hung renderer from one case can't poison the next. (playwright-core in this
// install doesn't expose Browser.process(), so we track chrome-headless-shell by name —
// safe here since we run strictly one browser at a time.)
import { chromium } from '../vm-tools/node_modules/playwright/index.mjs';
import { execSync } from 'node:child_process';
import { buildBillionLaughsSvg, validateLikeApp } from './task1_svg_bomb_gen.mjs';

const depths = process.argv.slice(2).length ? process.argv.slice(2).map(Number) : [5, 10, 15, 18, 20];
const PER_CASE_TIMEOUT_MS = 20000;
const results = [];

function sumChromeRssMB() {
  try {
    // ps `comm` truncates to 15 chars ("chrome-headless"); use `args` (untruncated) instead.
    const out = execSync(`ps -eo rss,args | grep -i 'chrome-headless-shell' | grep -v grep || true`).toString();
    const total = out.split('\n').map((l) => parseInt(l.trim(), 10)).filter((n) => !isNaN(n)).reduce((a, b) => a + b, 0);
    return (total / 1024).toFixed(1);
  } catch { return null; }
}

function killAllChrome() {
  try { execSync(`pkill -9 -f chrome-headless-shell 2>/dev/null || true`); } catch { /* ignore */ }
}

for (const depth of depths) {
  const svg = buildBillionLaughsSvg(depth);
  validateLikeApp(svg); // proves this is the same shape the trusted validator accepts
  const b64 = Buffer.from(svg, 'utf8').toString('base64');
  const dataUri = `data:image/svg+xml;base64,${b64}`;

  const browser = await chromium.launch({ args: ['--disable-gpu'] });
  let status = 'loaded', t0 = Date.now(), t1 = t0, metrics = {};
  let peakRssMB = 0;
  const rssPoll = setInterval(() => {
    const v = parseFloat(sumChromeRssMB());
    if (!isNaN(v) && v > peakRssMB) peakRssMB = v;
  }, 1000);

  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const client = await context.newCDPSession(page);
    await client.send('Performance.enable');
    await page.setContent('<html><body><img id="i"></body></html>');

    t0 = Date.now();
    const evalPromise = page.evaluate((uri) => new Promise((resolve, reject) => {
      const img = document.getElementById('i');
      img.onload = () => resolve('load');
      img.onerror = () => reject(new Error('img error'));
      img.src = uri;
    }), dataUri);
    const timeoutPromise = new Promise((_, rej) => setTimeout(() => rej(new Error('Timeout waiting for img load')), PER_CASE_TIMEOUT_MS));
    await Promise.race([evalPromise, timeoutPromise]);
    t1 = Date.now();

    try {
      const m = await client.send('Performance.getMetrics');
      metrics = Object.fromEntries(m.metrics.map((x) => [x.name, x.value]));
    } catch { /* renderer may be pegged/unresponsive */ }
  } catch (err) {
    t1 = Date.now();
    status = /Timeout/i.test(err.message) ? 'timeout' : `error: ${err.message}`;
  }
  clearInterval(rssPoll);

  const row = {
    depth,
    leaf_uses: 2 ** depth,
    svg_bytes: svg.length,
    status,
    wall_ms: t1 - t0,
    jsHeapUsedSize_MB: metrics.JSHeapUsedSize ? (metrics.JSHeapUsedSize / 1e6).toFixed(1) : null,
    peak_chrome_rss_MB: peakRssMB || null,
  };
  results.push(row);
  console.log(JSON.stringify(row));

  try {
    await Promise.race([browser.close(), new Promise((r) => setTimeout(r, 3000))]);
  } catch { /* ignore */ }
  killAllChrome(); // belt-and-suspenders: a bombed renderer may not die from close()
}

console.log('\n--- summary table ---');
console.log('depth\tleaf_uses\tsvg_bytes\tstatus\twall_ms\tjsHeapUsed_MB\tpeak_chrome_rss_MB');
for (const r of results) {
  console.log(`${r.depth}\t${r.leaf_uses}\t${r.svg_bytes}\t${r.status}\t${r.wall_ms}\t${r.jsHeapUsedSize_MB}\t${r.peak_chrome_rss_MB}`);
}
