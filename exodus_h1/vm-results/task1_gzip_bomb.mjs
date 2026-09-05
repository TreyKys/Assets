// Task 1.1 — measure the app's own gunzip primitive (native DecompressionStream('gzip'))
// against a highly-compressible payload, mirroring core/index.js's `gunzip()` wrapper:
//   const { DecompressionStream } = globalThis;
//   ... new Response(readable.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer() ...
// No output-size cap is applied anywhere in that path (confirmed by reading source).
import zlib from 'node:zlib';
import { promisify } from 'node:util';

const gzip = promisify(zlib.gzip);

async function gunzipViaDecompressionStream(compressed) {
  const stream = new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
  const buf = await new Response(stream).arrayBuffer();
  return Buffer.from(buf);
}

function peakRssMB() {
  return (process.memoryUsage().rss / 1024 / 1024).toFixed(1);
}

async function runCase(label, rawSizeBytes) {
  const raw = Buffer.alloc(rawSizeBytes, 0x00); // maximally compressible
  const compressed = await gzip(raw, { level: 9 });

  if (global.gc) global.gc();
  const rssBefore = peakRssMB();
  const t0 = Date.now();
  const out = await gunzipViaDecompressionStream(compressed);
  const t1 = Date.now();
  const rssAfter = peakRssMB();

  const ratio = (out.length / compressed.length).toFixed(0);
  console.log(
    `${label}\traw_input=${rawSizeBytes}\tgz_size=${compressed.length}\t` +
    `inflated=${out.length}\tratio=${ratio}x\ttime_ms=${t1 - t0}\t` +
    `rss_before_MB=${rssBefore}\trss_after_MB=${rssAfter}`
  );
  return { label, rawSizeBytes, gzSize: compressed.length, inflated: out.length, ratio, ms: t1 - t0, rssBefore, rssAfter };
}

const results = [];
console.log('label\traw_input\tgz_size\tinflated\tratio\ttime_ms\trss_before_MB\trss_after_MB');
results.push(await runCase('10MB-zeros', 10 * 1024 * 1024));
results.push(await runCase('200MB-zeros', 200 * 1024 * 1024));
results.push(await runCase('1GB-zeros', 1 * 1024 * 1024 * 1024));

console.log('\n--- summary (json) ---');
console.log(JSON.stringify(results, null, 2));
