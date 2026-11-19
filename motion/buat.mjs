// kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
// Motion Isanovski — naskah JSON → suara → subtitle → animasi → MP4 9:16.
// Pakai: node buat.mjs naskah/contoh.json [--gaya=neon] [--suara=say|rekaman|tanpa] [--suara-mac=Damayanti]
import {execFileSync} from 'node:child_process';
import {readFileSync, writeFileSync, mkdirSync, existsSync, copyFileSync, rmSync} from 'node:fs';
import {basename, dirname, join, resolve} from 'node:path';
import {svgAman} from './svg-aman.mjs';

const argv = process.argv.slice(2);
const opsi = Object.fromEntries(argv.filter((a) => a.startsWith('--')).map((a) => a.slice(2).split('=')));
const fileNaskah = argv.find((a) => !a.startsWith('--')) ?? 'naskah/contoh.json';
const naskah = JSON.parse(readFileSync(fileNaskah, 'utf8'));
const nama = basename(fileNaskah, '.json');
if (opsi.gaya) naskah.gaya = opsi.gaya;
// SVG objek per adegan (gambar.mjs atau naskah tempelan): saring lagi sebelum dirender
naskah.adegan.forEach((a, i) => { if (a.gambar) a.gambar = svgAman(a.gambar, `s${i + 1}`) || undefined; });
// nama akun hanya dari naskah/pengaturan pengguna — jangan sampai ikut nilai bawaan contoh.json (@isanovskisaputra)
naskah.handle = typeof naskah.handle === 'string' ? naskah.handle : (process.env.HANDLE || '');

const WIN = process.platform === 'win32';
const REMOTION = [join('node_modules', '@remotion', 'cli', 'remotion-cli.js')]; // tanpa npx/shell: aman di Windows
const modeSuara = opsi.suara ?? (process.platform === 'darwin' ? 'say' : WIN ? 'windows' : 'tanpa');
const suaraMac = opsi['suara-mac'] ?? 'Damayanti';

const log = (m) => console.log('• ' + m);

// Durasi WAV PCM dari header (tanpa ffprobe)
function durasiWav(p) {
  const b = readFileSync(p);
  let byteRate = 0;
  let i = 12;
  while (i < b.length - 8) {
    const id = b.toString('ascii', i, i + 4);
    const size = b.readUInt32LE(i + 4);
    if (id === 'fmt ') byteRate = b.readUInt32LE(i + 16);
    // `say` kadang menulis ukuran data 0xFFFFFFFF → pakai sisa panjang file
    if (id === 'data' && byteRate) return Math.min(size, b.length - i - 8) / byteRate;
    i += 8 + size + (size % 2);
  }
  throw new Error('WAV tidak valid: ' + p);
}

const dirSuara = join('public', 'suara', nama);
rmSync(dirSuara, {recursive: true, force: true});
mkdirSync(dirSuara, {recursive: true});

const dirKlip = join('public', 'klip', nama);
rmSync(dirKlip, {recursive: true, force: true});
mkdirSync(dirKlip, {recursive: true});
const durasiVideo = (p) =>
  parseFloat(execFileSync(process.execPath, [...REMOTION, 'ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).toString());
const dasarNaskah = dirname(resolve(fileNaskah));

if (modeSuara === 'voxcpm') {
  // Suara AI lokal VoxCPM2 (alat/suara): satu kali muat model untuk semua adegan.
  // VOXCPM_REFERENSI = rekaman WAV untuk clone (suara sendiri/berizin), VOXCPM_DESAIN = deskripsi suara.
  const daftar = join(dirSuara, 'daftar.json');
  writeFileSync(daftar, JSON.stringify(naskah.adegan.map((a) => (a.video ? null : a.teks))));
  const uv = [process.env.UV, join(process.env.HOME ?? process.env.USERPROFILE ?? '', '.local', 'bin', WIN ? 'uv.exe' : 'uv'),
    '/opt/homebrew/bin/uv'].find((p) => p && existsSync(p)) ?? 'uv';
  const args = ['run', '-q', resolve('..', 'suara', 'suara.py'), '--daftar', resolve(daftar), '--folder', resolve(dirSuara)];
  if (process.env.VOXCPM_REFERENSI) args.push('--referensi', process.env.VOXCPM_REFERENSI);
  if (process.env.VOXCPM_DESAIN) args.push('--desain', process.env.VOXCPM_DESAIN);
  log('Membuat suara dengan VoxCPM2 (AI lokal)…');
  execFileSync(uv, args, {stdio: 'inherit'});
}

naskah.adegan.forEach((a, i) => {
  const no = String(i + 1).padStart(2, '0');
  if (a.video) {
    // adegan hibrid: pakai klip asli (mis. hasil klip.py); path relatif terhadap file naskah
    const asal = resolve(dasarNaskah, a.video);
    if (!existsSync(asal)) throw new Error('Klip tidak ada: ' + asal);
    copyFileSync(asal, join(dirKlip, `${no}.mp4`));
    a.klip = `klip/${nama}/${no}.mp4`;
    a.durasi = Math.round(durasiVideo(asal) * 100) / 100;
    delete a.suara;
    log(`Adegan ${no}: ${a.durasi}s — KLIP ${a.video}`);
    return;
  }
  const tujuan = join(dirSuara, `${no}.wav`);
  const rekaman = join('rekaman', nama, `${no}.wav`);
  if (modeSuara === 'rekaman' || (modeSuara !== 'tanpa' && existsSync(rekaman))) {
    if (!existsSync(rekaman)) throw new Error(`Rekaman tidak ada: ${rekaman} (format WAV)`);
    copyFileSync(rekaman, tujuan);
  } else if (modeSuara === 'voxcpm') {
    if (!existsSync(tujuan)) throw new Error('Suara VoxCPM tidak terbentuk: ' + tujuan);
  } else if (modeSuara === 'say') {
    execFileSync('say', ['-v', suaraMac, '--data-format=LEI16@24000', '-o', tujuan, a.teks]);
  } else if (modeSuara === 'windows') {
    // Suara bawaan Windows (SAPI). Pakai suara Bahasa Indonesia kalau terpasang (mis. 'Microsoft Andika').
    const ps = `Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; ` +
      `$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'id-ID' } | Select-Object -First 1; ` +
      `if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; $s.SetOutputToWaveFile($env:STUDIO_WAV); $s.Speak($env:STUDIO_TEKS); $s.Dispose()`;
    execFileSync('powershell', ['-NoProfile', '-Command', ps], {env: {...process.env, STUDIO_WAV: resolve(tujuan), STUDIO_TEKS: a.teks}});
  } else {
    a.durasi = a.durasi ?? Math.max(2.5, a.teks.split(/\s+/).length / 2.6);
    delete a.suara;
    return;
  }
  a.suara = `suara/${nama}/${no}.wav`;
  a.durasi = Math.round(durasiWav(tujuan) * 100) / 100;
  log(`Adegan ${no}: ${a.durasi}s — ${a.judul}`);
});

mkdirSync('hasil', {recursive: true});
const fileProps = resolve('hasil', `${nama}.props.json`);
writeFileSync(fileProps, JSON.stringify(naskah, null, 2));
const keluar = resolve('hasil', `${nama}-${naskah.gaya}.mp4`);
log(`Render gaya "${naskah.gaya}" → ${keluar}`);
// --props memakai jalur RELATIF (tanpa huruf drive & spasi "Isanovski Studio"): di Windows jalur absolut bisa gagal dibaca
// dan Remotion diam-diam memakai naskah contoh.json.
const propsRel = join('hasil', `${nama}.props.json`).split('\\').join('/');
execFileSync(process.execPath, [...REMOTION, 'render', 'src/index.ts', 'Motion', keluar, `--props=${propsRel}`, '--log=error'], {
  stdio: 'inherit',
});
log('Selesai: ' + keluar);
