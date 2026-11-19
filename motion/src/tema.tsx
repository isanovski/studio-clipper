// kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
// Mesin tema Motion: 3 gaya awal + 11 gaya dari template video di isanovskisaputra.biz.id/kode
// (T01–T11 & Kolase milik Isanovski sendiri). Tiap tema = palet + font + latar + cara judul/ikon/subtitle muncul.
import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {loadFont as fArchivo} from '@remotion/google-fonts/ArchivoBlack';
import {loadFont as fSerif} from '@remotion/google-fonts/InstrumentSerif';
import {loadFont as fInter} from '@remotion/google-fonts/Inter';
import {loadFont as fDMMono} from '@remotion/google-fonts/DMMono';
import {loadFont as fFraunces} from '@remotion/google-fonts/Fraunces';
import {loadFont as fJakarta} from '@remotion/google-fonts/PlusJakartaSans';
import {loadFont as fGrotesk} from '@remotion/google-fonts/SpaceGrotesk';

const ARCHIVO = fArchivo().fontFamily;
const SERIF = fSerif().fontFamily;
const INTER = fInter().fontFamily;
const DMMONO = fDMMono().fontFamily;
const FRAUNCES = fFraunces().fontFamily;
const JAKARTA = fJakarta().fontFamily;
const GROTESK = fGrotesk().fontFamily;

export type ModeJudul = 'naik' | 'ketik' | 'zoom' | 'stiker' | 'sorot' | 'pil' | 'kotak';
export type ModeIkon = 'polos' | 'polaroid' | 'kaca' | 'lingkaran' | 'kartu' | 'cahaya';
export type ModeSub = 'kata' | 'kotak' | 'pil';
export type ModeLabel = 'nomor' | 'stiker' | 'progres' | 'tidak';

export type Panel = {bg: string; teks: string; aksen?: string};
export type LatarProps = {f: number; i: number; n: number; aksen: string; judul: string};

export type Tema = {
  nama: string;
  asal: string; // template sumber
  teks: string;
  redup: string;
  aksen: string;
  fontJudul: string;
  fontTeks: string;
  fontLabel: string;
  bobot: number;
  kapital: boolean;
  miring?: boolean; // judul serif miring
  judul: ModeJudul;
  ikon: ModeIkon;
  sub: ModeSub;
  label: ModeLabel;
  panel?: Panel[]; // warna bergantian per adegan
  Latar: React.FC<LatarProps>;
  efek?: string; // id filter SVG gaya ilustrasi (ilustrasi.tsx) untuk ikon
  Hias?: React.FC<{f: number; aksen: string}>; // hiasan di bawah ikon (bayangan dll.)
  ukuranJudul?: number;
  ukuranSub?: number;
};

const isi: React.CSSProperties = {position: 'absolute', inset: 0};

// ── Latar ──────────────────────────────────────────────────────────────────
const LatarGaris: React.FC<LatarProps> = ({f, aksen}) => {
  const g = (f * 0.6) % 80;
  return (
    <AbsoluteFill style={{background: '#0B1B2B'}}>
      <svg width="1080" height="1920" style={{position: 'absolute', opacity: 0.35}}>
        {Array.from({length: 16}).map((_, i) => <line key={'v' + i} x1={i * 80 - g} y1={0} x2={i * 80 - g} y2={1920} stroke="#5C7A96" />)}
        {Array.from({length: 26}).map((_, i) => <line key={'h' + i} x1={0} y1={i * 80 + g} x2={1080} y2={i * 80 + g} stroke="#5C7A96" />)}
        <circle cx={900} cy={360} r={140 + Math.sin(f / 20) * 10} fill="none" stroke={aksen} strokeWidth={2} strokeDasharray="8 10" />
      </svg>
    </AbsoluteFill>
  );
};
const LatarNeon: React.FC<LatarProps> = ({f, aksen}) => (
  <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 30%, #2A0D3F, #0A0612 70%)'}}>
    <div style={{position: 'absolute', left: 0, right: 0, top: (f * 3) % 620, height: 3, background: aksen, opacity: 0.22}} />
    <div style={{position: 'absolute', bottom: 0, height: 700, width: '100%', background: `repeating-linear-gradient(90deg, transparent 0 118px, ${aksen}55 118px 120px)`,
      transform: 'perspective(600px) rotateX(60deg)', transformOrigin: 'bottom'}} />
  </AbsoluteFill>
);
const LatarKertas: React.FC<LatarProps> = ({aksen}) => (
  <AbsoluteFill style={{background: '#F2EBDD'}}>
    <div style={{...isi, opacity: 0.18, background: 'repeating-linear-gradient(0deg, #0000 0 46px, #8C827355 46px 48px)'}} />
    <div style={{position: 'absolute', left: 70, top: 0, bottom: 0, width: 3, background: aksen, opacity: 0.6}} />
  </AbsoluteFill>
);
// T01 Panggung Kutipan Sinematik: putih tulang, vinyet lembut, kata raksasa samar di belakang
const LatarSinematik: React.FC<LatarProps> = ({f, judul}) => (
  <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 40%, #fbfbf9 0%, #ecebe7 70%, #d6d6d3 100%)'}}>
    <div style={{position: 'absolute', top: 380, left: -40, right: -40, textAlign: 'center', fontFamily: ARCHIVO, fontSize: 300,
      color: '#1b1b1b', opacity: 0.05, transform: `scale(${1 + f / 900})`, whiteSpace: 'nowrap', textTransform: 'uppercase'}}>
      {judul.split(' ')[0]}
    </div>
    <div style={{position: 'absolute', bottom: 0, left: 0, right: 0, height: 260, background: 'linear-gradient(transparent, #cfcfcb)'}} />
  </AbsoluteFill>
);
// T02 Kata Kunci Minimal: putih, cincin hijau buram melayang
const LatarMinimal: React.FC<LatarProps> = ({f, aksen}) => (
  <AbsoluteFill style={{background: '#fff', overflow: 'hidden'}}>
    {[[-260, 1500, 700], [700, -200, 600], [820, 1650, 500]].map(([x, y, s], i) => (
      <div key={i} style={{position: 'absolute', left: x, top: y + Math.sin((f + i * 40) / 60) * 20, width: s, height: s, borderRadius: '50%',
        border: `70px solid ${aksen}1f`, filter: 'blur(18px)'}} />
    ))}
  </AbsoluteFill>
);
// T03 Kolase Kertas: krem, titik halftone, sobekan kertas kraft di atas
const sobek = 'polygon(0 0,100% 0,100% 78%,96% 86%,91% 79%,85% 90%,79% 82%,72% 92%,66% 83%,59% 91%,52% 81%,45% 93%,38% 84%,31% 92%,24% 81%,17% 90%,10% 82%,4% 91%,0 84%)';
const LatarKolase: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: '#efe5cf'}}>
    <div style={{...isi, opacity: 0.35, backgroundImage: 'radial-gradient(#b9a888 1.6px, transparent 1.8px)', backgroundSize: '18px 18px'}} />
    <div style={{position: 'absolute', top: -20, left: -20, right: -20, height: 320, background: '#c9a46b', clipPath: sobek,
      transform: `translateY(${Math.sin(f / 50) * 4}px)`, boxShadow: 'inset 0 -20px 40px #0002'}} />
    <div style={{position: 'absolute', bottom: 120, right: -40, width: 420, height: 160, background: '#f6f2ea', transform: 'rotate(-8deg)', clipPath: sobek, opacity: 0.9}} />
  </AbsoluteFill>
);
// T04 Editorial Hangat: gradasi peach, cahaya jendela miring, bayangan daun
const LatarHangat: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: 'linear-gradient(160deg, #f8e3d0 0%, #f3cfae 55%, #e7b48d 100%)', overflow: 'hidden'}}>
    <div style={{position: 'absolute', top: -200, left: 200, width: 500, height: 2400, transform: 'rotate(28deg)', background: 'linear-gradient(90deg, #fff0, #fff7 40%, #fff0)', opacity: 0.7}} />
    {[0, 1, 2, 3].map((i) => (
      <div key={i} style={{position: 'absolute', top: 120 + i * 90, left: 760 + Math.sin((f + i * 30) / 40) * 12, width: 220, height: 70, borderRadius: '50%',
        background: '#2a1a12', opacity: 0.08, filter: 'blur(14px)', transform: `rotate(${-30 + i * 18}deg)`}} />
    ))}
    <div style={{position: 'absolute', left: 540 - 360, top: 330, width: 720, height: 720, borderRadius: '50%', border: '3px solid #a5512a33'}} />
  </AbsoluteFill>
);
// T05 UI Aplikasi Kaca: abu kebiruan + gumpalan warna lembut bergerak
const LatarKaca: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: '#eef1f7', overflow: 'hidden'}}>
    {[['#4f8cff', 160, 300], ['#f7c9cf', 760, 900], ['#9fd8c8', 200, 1500]].map(([c, x, y], i) => (
      <div key={i} style={{position: 'absolute', left: +x + Math.sin((f + i * 50) / 45) * 40, top: +y + Math.cos((f + i * 30) / 55) * 40, width: 520, height: 520,
        borderRadius: '50%', background: c as string, opacity: 0.35, filter: 'blur(90px)'}} />
    ))}
  </AbsoluteFill>
);
// T06 Bicara + Sisipan: krem hangat + gelembung obrolan samar
const LatarBicara: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: 'linear-gradient(180deg, #fbe2d6, #f6e9e1)'}}>
    {[[90, 230, 380], [560, 1560, 420]].map(([x, y, w], i) => (
      <div key={i} style={{position: 'absolute', left: x, top: y + Math.sin((f + i * 60) / 50) * 10, width: w, height: 120, borderRadius: 40,
        background: i ? '#7c5cff22' : '#ffffffaa', boxShadow: '0 10px 30px #0001'}} />
    ))}
  </AbsoluteFill>
);
// T07 Dokumenter Retro: panel warna rata berganti tiap adegan + huruf raksasa samar
const LatarRetro: React.FC<LatarProps> = ({judul}) => (
  <AbsoluteFill>
    <div style={{position: 'absolute', top: 260, width: '100%', textAlign: 'center', fontFamily: ARCHIVO, fontSize: 900, lineHeight: 1, color: '#000', opacity: 0.07}}>
      {judul.trim()[0] ?? ''}
    </div>
    <div style={{...isi, opacity: 0.12, backgroundImage: 'radial-gradient(#000 0.8px, transparent 1px)', backgroundSize: '6px 6px'}} />
  </AbsoluteFill>
);
// T08 Tekno Gelap Oranye: panggung gelap, busur cahaya oranye, lantai mengilap
const LatarTekno: React.FC<LatarProps> = ({f, aksen}) => (
  <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 70%, #1b1410 0%, #0b0b0e 60%)', overflow: 'hidden'}}>
    <div style={{position: 'absolute', left: 540 - 620, top: 980, width: 1240, height: 1240, borderRadius: '50%', border: `6px solid ${aksen}`,
      filter: 'blur(3px)', opacity: 0.55 + Math.sin(f / 25) * 0.15}} />
    <div style={{position: 'absolute', left: 540 - 620, top: 980, width: 1240, height: 1240, borderRadius: '50%', boxShadow: `0 -30px 120px ${aksen}66`}} />
    <div style={{position: 'absolute', bottom: 0, width: '100%', height: 640, background: 'linear-gradient(transparent, #ffb36b14 60%, #000)',
      transform: 'perspective(800px) rotateX(55deg)', transformOrigin: 'bottom'}} />
  </AbsoluteFill>
);
// T09 Iklan Jasa Krem: krem bergaris kisi + barcode
const LatarIklan: React.FC<LatarProps> = () => (
  <AbsoluteFill>
    <div style={{...isi, backgroundImage: 'linear-gradient(#0b0b0b12 1px, transparent 1px), linear-gradient(90deg, #0b0b0b12 1px, transparent 1px)', backgroundSize: '60px 60px'}} />
    <div style={{position: 'absolute', right: 80, bottom: 150, width: 220, height: 70, background: 'repeating-linear-gradient(90deg,#0b0b0b 0 3px,transparent 3px 6px,#0b0b0b 6px 8px,transparent 8px 13px)', opacity: 0.8}} />
  </AbsoluteFill>
);
// T10 Grid Lampu Sorot: kertas kisi, sapuan tinta hitam, kerucut lampu sorot
const LatarSorot: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: '#fbfbf8', overflow: 'hidden'}}>
    <div style={{...isi, backgroundImage: 'linear-gradient(#14141410 1px, transparent 1px), linear-gradient(90deg, #14141410 1px, transparent 1px)', backgroundSize: '54px 54px'}} />
    <svg width="1080" height="1920" style={{position: 'absolute'}}>
      <path d="M-40 1680 C 220 1600, 420 1760, 640 1650 S 1000 1590, 1120 1660" stroke="#141414" strokeWidth={70} fill="none" strokeLinecap="round" opacity={0.9}
        strokeDasharray="1600" strokeDashoffset={interpolate(f, [0, 20], [1600, 0], {extrapolateRight: 'clamp'})} />
    </svg>
    <div style={{position: 'absolute', top: -200, left: 540 - 500 + Math.sin(f / 60) * 60, width: 1000, height: 1500,
      background: 'radial-gradient(ellipse at 50% 0%, #e2b33c33, transparent 65%)', clipPath: 'polygon(42% 0, 58% 0, 100% 100%, 0 100%)'}} />
  </AbsoluteFill>
);
// T11 Daftar Sumber: terang berkisi, aksen hijau toska
const LatarDaftar: React.FC<LatarProps> = () => (
  <AbsoluteFill style={{background: '#f6f7f4'}}>
    <div style={{...isi, backgroundImage: 'linear-gradient(#5c6f7014 1px, transparent 1px), linear-gradient(90deg, #5c6f7014 1px, transparent 1px)', backgroundSize: '72px 72px'}} />
  </AbsoluteFill>
);

// ── Daftar tema ─────────────────────────────────────────────────────────────
import {TEMA_ILUSTRASI} from './ilustrasi';

export const TEMA: Record<string, Tema> = {
  garis: {nama: 'Garis', asal: 'awal', teks: '#E8F1FA', redup: '#7d9ab4', aksen: '#4FC3F7', fontJudul: '"Courier New", monospace', fontTeks: '"Courier New", monospace',
    fontLabel: '"Courier New", monospace', bobot: 900, kapital: false, judul: 'naik', ikon: 'polos', sub: 'kata', label: 'nomor', Latar: LatarGaris},
  neon: {nama: 'Neon', asal: 'awal', teks: '#FFFFFF', redup: '#a596c2', aksen: '#FF3EA5', fontJudul: '"Arial Black", Arial, sans-serif', fontTeks: '"Arial Black", Arial, sans-serif',
    fontLabel: '"Arial Black", Arial, sans-serif', bobot: 900, kapital: false, judul: 'naik', ikon: 'cahaya', sub: 'kata', label: 'nomor', Latar: LatarNeon},
  kertas: {nama: 'Kertas', asal: 'awal', teks: '#1D1A16', redup: '#6f6656', aksen: '#E4572E', fontJudul: 'Georgia, serif', fontTeks: 'Georgia, serif',
    fontLabel: 'Georgia, serif', bobot: 900, kapital: false, judul: 'naik', ikon: 'polos', sub: 'kata', label: 'nomor', Latar: LatarKertas},
  sinematik: {nama: 'Panggung Sinematik', asal: 'T01', teks: '#1b1b1b', redup: '#6b6b68', aksen: '#1b1b1b', fontJudul: ARCHIVO, fontTeks: INTER, fontLabel: INTER,
    bobot: 400, kapital: true, judul: 'zoom', ikon: 'polaroid', sub: 'kata', label: 'tidak', Latar: LatarSinematik},
  minimal: {nama: 'Kata Kunci Minimal', asal: 'T02', teks: '#111111', redup: '#6a6a6a', aksen: '#3fae3f', fontJudul: INTER, fontTeks: INTER, fontLabel: INTER,
    bobot: 800, kapital: false, judul: 'ketik', ikon: 'lingkaran', sub: 'kata', label: 'tidak', Latar: LatarMinimal},
  kolase: {nama: 'Kolase Kertas', asal: 'T03 · Kolase Vox', teks: '#1b1b1b', redup: '#6f6450', aksen: '#f5d23a', fontJudul: SERIF, fontTeks: INTER, fontLabel: ARCHIVO,
    bobot: 400, kapital: false, judul: 'stiker', ikon: 'polaroid', sub: 'kotak', label: 'stiker', Latar: LatarKolase},
  hangat: {nama: 'Editorial Hangat', asal: 'T04', teks: '#2a1a12', redup: '#7a4f36', aksen: '#a5512a', fontJudul: SERIF, fontTeks: INTER, fontLabel: INTER,
    bobot: 400, kapital: true, judul: 'naik', ikon: 'lingkaran', sub: 'kata', label: 'nomor', Latar: LatarHangat},
  kaca: {nama: 'UI Aplikasi Kaca', asal: 'T05', teks: '#0f172a', redup: '#5b6478', aksen: '#4f8cff', fontJudul: INTER, fontTeks: INTER, fontLabel: INTER,
    bobot: 800, kapital: false, judul: 'pil', ikon: 'kaca', sub: 'pil', label: 'progres', Latar: LatarKaca},
  bicara: {nama: 'Bicara + Sisipan', asal: 'T06', teks: '#1e1630', redup: '#6d5f73', aksen: '#7c5cff', fontJudul: INTER, fontTeks: INTER, fontLabel: INTER,
    bobot: 900, kapital: true, judul: 'naik', ikon: 'kaca', sub: 'kotak', label: 'tidak', Latar: LatarBicara},
  retro: {nama: 'Dokumenter Retro', asal: 'T07', teks: '#111', redup: '#444', aksen: '#f2c230', fontJudul: ARCHIVO, fontTeks: INTER, fontLabel: ARCHIVO,
    bobot: 400, kapital: true, judul: 'kotak', ikon: 'lingkaran', sub: 'kata', label: 'stiker', Latar: LatarRetro,
    panel: [{bg: '#f2f2f2', teks: '#111', aksen: '#3fae3f'}, {bg: '#3fae3f', teks: '#0b0b0b', aksen: '#f2c230'}, {bg: '#c9d3dc', teks: '#111', aksen: '#d62828'},
      {bg: '#6e1414', teks: '#fff', aksen: '#f2c230'}, {bg: '#2f6fd6', teks: '#fff', aksen: '#f2c230'}, {bg: '#0b0b0b', teks: '#fff', aksen: '#3fae3f'}]},
  tekno: {nama: 'Tekno Gelap Oranye', asal: 'T08', teks: '#f4f1ee', redup: '#a49c95', aksen: '#ffb36b', fontJudul: INTER, fontTeks: INTER, fontLabel: DMMONO,
    bobot: 800, kapital: false, judul: 'naik', ikon: 'cahaya', sub: 'kata', label: 'nomor', Latar: LatarTekno},
  iklan: {nama: 'Iklan Jasa Krem', asal: 'T09', teks: '#0b0b0b', redup: '#5b5550', aksen: '#d62839', fontJudul: INTER, fontTeks: INTER, fontLabel: DMMONO,
    bobot: 900, kapital: false, judul: 'kotak', ikon: 'kartu', sub: 'kata', label: 'nomor', Latar: LatarIklan,
    panel: [{bg: '#faf6ef', teks: '#0b0b0b'}, {bg: '#0b0b0b', teks: '#faf6ef', aksen: '#f08f9a'}]},
  sorot: {nama: 'Grid Lampu Sorot', asal: 'T10', teks: '#141414', redup: '#5f5a50', aksen: '#b8241c', fontJudul: SERIF, fontTeks: INTER, fontLabel: ARCHIVO,
    bobot: 400, kapital: false, miring: true, judul: 'ketik', ikon: 'kartu', sub: 'kata', label: 'stiker', Latar: LatarSorot},
  daftar: {nama: 'Daftar Sumber', asal: 'T11', teks: '#1d2a2b', redup: '#5c6f70', aksen: '#f07a2b', fontJudul: JAKARTA, fontTeks: JAKARTA, fontLabel: GROTESK,
    bobot: 800, kapital: false, judul: 'sorot', ikon: 'kartu', sub: 'pil', label: 'progres', Latar: LatarDaftar},
  ...TEMA_ILUSTRASI,
};

export const SERIF_FONT = SERIF;
export const FRAUNCES_FONT = FRAUNCES;
