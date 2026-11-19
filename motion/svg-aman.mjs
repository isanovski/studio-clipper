// kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
// Penyaring SVG dari AI: hanya bentuk & gradien yang diizinkan. Tanpa skrip, tanpa tautan luar, tanpa teks/foreignObject.
const TAG = new Set(['svg', 'g', 'path', 'circle', 'ellipse', 'rect', 'polygon', 'polyline', 'line', 'defs',
  'lineargradient', 'radialgradient', 'stop']);
const BUANG_ISI = /<(script|style|foreignObject|text|title|desc|metadata|image|use|a|iframe)\b[\s\S]*?<\/\1\s*>/gi;
const ATRIBUT = new Set(['d', 'cx', 'cy', 'r', 'rx', 'ry', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'width', 'height', 'points', 'fill', 'stroke',
  'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'stroke-dasharray', 'opacity', 'fill-opacity', 'stroke-opacity', 'transform',
  'viewbox', 'id', 'offset', 'stop-color', 'stop-opacity', 'gradientunits', 'gradienttransform', 'fx', 'fy', 'fill-rule', 'clip-rule', 'xmlns']);
const NAMA_ASLI = {viewbox: 'viewBox', lineargradient: 'linearGradient', radialgradient: 'radialGradient', gradientunits: 'gradientUnits',
  gradienttransform: 'gradientTransform'};

export function svgAman(mentah, awalan = 'g') {
  if (typeof mentah !== 'string') return '';
  let s = mentah.replace(/<!--[\s\S]*?-->/g, '').replace(/<\?[\s\S]*?\?>/g, '').replace(/<!DOCTYPE[^>]*>/gi, '').replace(BUANG_ISI, '');
  const a = s.search(/<svg\b/i);
  const b = s.toLowerCase().lastIndexOf('</svg>');
  if (a < 0 || b < 0) return '';
  s = s.slice(a, b + 6);
  if (s.length > 20000) return '';
  const hasil = s.replace(/<\s*(\/?)\s*([a-zA-Z]+)([^>]*?)(\/?)\s*>/g, (_, tutup, nama, atr, sendiri) => {
    const n = nama.toLowerCase();
    if (!TAG.has(n)) return '';
    const tag = NAMA_ASLI[n] ?? n;
    if (tutup) return `</${tag}>`;
    const aman = [];
    for (const m of atr.matchAll(/([a-zA-Z:-]+)\s*=\s*("([^"]*)"|'([^']*)')/g)) {
      const k = m[1].toLowerCase();
      let v = (m[3] ?? m[4] ?? '').replace(/[<>]/g, '');
      if (!ATRIBUT.has(k)) continue;
      if (n === 'svg' && (k === 'width' || k === 'height')) continue; // ukuran diatur pemutar
      if (/javascript:|data:|expression|@import/i.test(v)) continue;
      if (/url\(/i.test(v) && !/^\s*url\(\s*#[\w-]+\s*\)\s*$/.test(v)) continue;
      if (k === 'xmlns') v = 'http://www.w3.org/2000/svg';
      if (k === 'id') v = `${awalan}-${v.replace(/[^\w-]/g, '')}`;
      v = v.replace(/url\(\s*#([\w-]+)\s*\)/g, `url(#${awalan}-$1)`);
      aman.push(`${NAMA_ASLI[k] ?? k}="${v}"`);
    }
    if (n === 'svg') aman.push('width="100%"', 'height="100%"');
    return `<${tag}${aman.length ? ' ' + aman.join(' ') : ''}${sendiri ? '/' : ''}>`;
  });
  return /<(path|circle|ellipse|rect|polygon|polyline|line)\b/.test(hasil) ? hasil : '';
}
