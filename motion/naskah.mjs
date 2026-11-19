// kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
// Topik → naskah JSON memakai AI milik pengguna (isi .env; lihat .env.contoh).
// Pakai: node naskah.mjs "topik video" [--ai=gemini|openai|claude-code|codex|opencode] [--gaya=neon] [--nama=topikku]
// Tanpa kunci API? Pakai PROMPT-NASKAH.md di Claude/Gemini/ChatGPT gratis lalu simpan JSON-nya sendiri.
import {writeFileSync, mkdirSync, readFileSync} from 'node:fs';
import {bacaEnv, tanyaAI, berhenti} from './ai.mjs';

const argv = process.argv.slice(2);
const opsi = Object.fromEntries(argv.filter((a) => a.startsWith('--')).map((a) => a.slice(2).split('=')));
const topik = argv.filter((a) => !a.startsWith('--')).join(' ');
if (!topik) {
  console.error('Tulis topiknya, mis.: node naskah.mjs "3 kebiasaan pagi produktif"');
  process.exit(1);
}
const env = bacaEnv();
const penyedia = (opsi.ai ?? env.AI ?? 'gemini').toLowerCase();
const prompt = readFileSync('PROMPT-NASKAH.md', 'utf8').replace('[TOPIK]', topik);
const tanya = () => tanyaAI(penyedia, prompt, env, 'menulis naskah');

console.log(`• Meminta AI '${penyedia}' menulis naskah: ${topik}`);
const teks = await tanya();
const m = teks.match(/\{[\s\S]*\}/);
if (!m) berhenti('Balasan AI tidak berisi JSON:\n' + teks.slice(0, 500));
const naskah = JSON.parse(m[0]);
if (opsi.gaya) naskah.gaya = opsi.gaya;
naskah.handle = env.HANDLE || ''; // nama akun hanya dari pengaturan pengguna — AI kadang mengarang akun
// judul layar berupa label ("Hook", "Tips 1") → ganti dengan 4 kata awal narasi
for (const a of naskah.adegan ?? []) {
  if (!a.judul || /^(hook|tips?\s*\d*|penutup|pembuka|adegan\s*\d+|cta|intro|outro)$/i.test(a.judul.trim()))
    a.judul = String(a.teks ?? '').replace(/[.,!?]+$/, '').split(/\s+/).slice(0, 4).join(' ');
}
if (!Array.isArray(naskah.adegan) || !naskah.adegan.length) berhenti('JSON tidak punya daftar "adegan".');
const nama = opsi.nama ?? topik.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);
mkdirSync('naskah', {recursive: true});
writeFileSync(`naskah/${nama}.json`, JSON.stringify(naskah, null, 2));
console.log(`• naskah/${nama}.json: ${naskah.adegan.length} adegan. Periksa dulu, lalu: node buat.mjs naskah/${nama}.json`);
