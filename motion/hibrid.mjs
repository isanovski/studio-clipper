// kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
// Hibrid: ubah hasil alat/klip (klip.json) jadi naskah motion yang menyelipkan kartu animasi.
// Pakai: node hibrid.mjs ../klip/hasil-klip [--gaya=neon] [--handle=@akun] [--judul="Judul video"]
// Hasil: naskah/hibrid.json  →  node buat.mjs naskah/hibrid.json
import {existsSync, readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {join, resolve, relative} from 'node:path';

const argv = process.argv.slice(2);
const opsi = Object.fromEntries(argv.filter((a) => a.startsWith('--')).map((a) => a.slice(2).split('=')));
const folder = resolve(argv.find((a) => !a.startsWith('--')) ?? '../klip/hasil-klip');
// hanya klip yang sudah dirender (punya file MP4) — klip yang belum dirender dilewati
const semua = JSON.parse(readFileSync(join(folder, 'klip.json'), 'utf8'));
const klips = semua.filter((k) => k.file && existsSync(join(folder, k.file)));
if (!klips.length) {
  console.error('Belum ada klip yang dirender di folder ini. Render dulu klipnya di Studio (Klip → centang → Render), lalu coba lagi.');
  process.exit(1);
}
if (klips.length < semua.length) console.log(`• ${semua.length - klips.length} klip belum dirender, dilewati.`);
const judul = opsi.judul ?? 'Momen terbaik';

const pendek = (s, n = 5) => s.replace(/[“”"]/g, '').split(/\s+/).slice(0, n).join(' ').replace(/[.,!?;:]+$/, '');

mkdirSync('naskah', {recursive: true});
const adegan = [
  // kartu pembuka: hook dari klip pertama
  {judul, teks: `${klips.length} momen paling penting dari video ini. Simak sampai habis.`, kunci: ['momen', 'penting'], ikon: '🎬'},
];
klips.forEach((k, i) => {
  adegan.push({
    judul: `Momen ${i + 1}: ${pendek(k.judul, 4)}`,
    teks: `Momen ${i + 1}. ${pendek(k.judul, 10)}.`,
    kunci: [`${i + 1}`],
    ikon: ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣'][i] ?? '▶️',
  });
  adegan.push({judul: pendek(k.judul, 6), video: relative(resolve('naskah'), join(folder, k.file))});
});
adegan.push({judul: 'Simpan dan bagikan', teks: 'Simpan video ini dan bagikan ke temanmu yang butuh.', kunci: ['simpan', 'bagikan'], ikon: '📌'});

const naskah = {judul, gaya: opsi.gaya ?? 'garis', handle: opsi.handle ?? '', adegan};
writeFileSync('naskah/hibrid.json', JSON.stringify(naskah, null, 2));
console.log(`• naskah/hibrid.json dibuat: ${adegan.length} adegan (${klips.length} klip asli).`);
console.log('  Ubah teks kartu sesukamu (atau minta Claude), lalu: node buat.mjs naskah/hibrid.json');
