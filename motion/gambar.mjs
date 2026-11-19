// kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
// AI menggambar objek SVG untuk tiap adegan (satu kali panggil untuk semua adegan).
// Pakai: node gambar.mjs naskah/topikku.json [--ai=gemini|openai|claude-code|codex|opencode]
// Hasil: adegan[i].gambar = SVG (sudah disaring). Gaya ilustrasi (kapur, piksel, dll.) menggambar ulang SVG ini lewat filter.
import {readFileSync, writeFileSync} from 'node:fs';
import {bacaEnv, tanyaAI, berhenti} from './ai.mjs';
import {svgAman} from './svg-aman.mjs';

const argv = process.argv.slice(2);
const opsi = Object.fromEntries(argv.filter((a) => a.startsWith('--')).map((a) => a.slice(2).split('=')));
const file = argv.find((a) => !a.startsWith('--'));
globalThis.__lunak = !('ketat' in opsi); // gagal menggambar → video tetap dibuat dengan emoji
if (!file) berhenti('Pakai: node gambar.mjs naskah/topikku.json');
const naskah = JSON.parse(readFileSync(file, 'utf8'));
const env = bacaEnv();
const penyedia = (opsi.ai ?? env.AI ?? 'gemini').toLowerCase();
const adegan = naskah.adegan.filter((a) => !a.klip && !a.video);

const daftar = adegan.map((a, i) => `${i + 1}. judul: "${a.judul}" | narasi: "${a.teks}"${a.ikon ? ` | petunjuk ikon: ${a.ikon}` : ''}`).join('\n');
const prompt = `Kamu ilustrator vektor. Gambarlah SATU objek utama untuk tiap adegan video pendek di bawah ini, sebagai SVG.

Aturan tiap SVG:
- <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">, latar TRANSPARAN (jangan ada persegi latar).
- Satu objek konkret yang mewakili adegan (benda, kendaraan, alat, hewan, orang sederhana), di tengah, mengisi ±90% kanvas (jangan kecil).
- Gaya flat illustration: bentuk tegas, 3–6 warna cerah dan kontras, boleh gradien sederhana, garis tepi gelap tipis boleh.
- Hanya elemen: path, circle, ellipse, rect, polygon, polyline, line, g, defs, linearGradient, radialGradient, stop.
- DILARANG: teks/huruf/angka, <text>, gambar luar, skrip, style, filter. Maksimal ±2500 karakter per SVG.

Adegan:
${daftar}

Balas HANYA ${adegan.length} SVG berurutan sesuai nomor adegan, tiap SVG lengkap dari <svg ...> sampai </svg>, tanpa penjelasan dan tanpa blok kode.`;

console.log(`• Meminta AI '${penyedia}' menggambar ${adegan.length} objek SVG…`);
const teks = await tanyaAI(penyedia, prompt, env, 'menggambar objek SVG');
const svg = teks.match(/<svg\b[\s\S]*?<\/svg>/gi) ?? [];
if (!svg.length) berhenti('Balasan AI tidak berisi SVG:\n' + teks.slice(0, 400));
let jadi = 0;
adegan.forEach((a, i) => {
  const aman = svgAman(svg[i], `s${i + 1}`);
  // penjaga mutu: model kecil kadang hanya menggambar satu gumpalan → pakai emoji saja
  const bentuk = (aman.match(/<(path|circle|ellipse|rect|polygon|polyline|line)\b/g) ?? []).length;
  const kembar = svg.filter((x) => x === svg[i]).length > 1;
  if (aman && bentuk >= 4 && !kembar) { a.gambar = aman; jadi++; } else delete a.gambar;
});
writeFileSync(file, JSON.stringify(naskah, null, 2));
console.log(`• ${jadi}/${adegan.length} objek tergambar${jadi < adegan.length ? ' (sisanya tetap memakai emoji)' : ''}.`);
