// kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
// 10 gaya ilustrasi (riset 14 Nov dari reel acuan "10 gaya animasi" — pola saja, bukan tiruan):
// pixel art, papan kapur, sketsa emas bercahaya, low-poly PS2, komik, flat vector, stickman minimalis,
// CGI mengilap, bata mainan, clay 3D. Ikon/emoji tiap adegan "digambar ulang" lewat filter SVG,
// latar dibuat sendiri dengan SVG/CSS. Semua font dari Google Fonts (OFL).
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {loadFont as fPixel} from '@remotion/google-fonts/PressStart2P';
import {loadFont as fKapur} from '@remotion/google-fonts/CabinSketch';
import {loadFont as fKomik} from '@remotion/google-fonts/Bangers';
import {loadFont as fClay} from '@remotion/google-fonts/Fredoka';
import {loadFont as fTekno} from '@remotion/google-fonts/Orbitron';
import {loadFont as fBata} from '@remotion/google-fonts/RubikMonoOne';
import {loadFont as fTangan} from '@remotion/google-fonts/Gaegu';
import {loadFont as fRubik} from '@remotion/google-fonts/Rubik';
import type {LatarProps, Tema} from './tema';

const PIXEL = fPixel().fontFamily;
const KAPUR = fKapur().fontFamily;
const KOMIK = fKomik().fontFamily;
const CLAY = fClay().fontFamily;
const TEKNO = fTekno().fontFamily;
const BATA = fBata().fontFamily;
const TANGAN = fTangan().fontFamily;
const RUBIK = fRubik().fontFamily;

// ── Filter SVG: dipasang sekali di Video, dipakai lewat CSS filter:url(#…) ──
const garis = (warna: string, tebal: number, dalam: number) => (
  <>
    <feColorMatrix in="SourceGraphic" type="saturate" values="0" result="abu" />
    <feConvolveMatrix in="abu" order="3" kernelMatrix="-1 -1 -1 -1 8 -1 -1 -1 -1" preserveAlpha="true" result="tepi" />
    <feColorMatrix in="tepi" type="matrix" values={`0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  ${dalam} ${dalam} ${dalam} 0 0`} result="dalam" />
    <feMorphology in="SourceAlpha" operator="dilate" radius={tebal} result="tebal" />
    <feComposite in="tebal" in2="SourceAlpha" operator="out" result="cincin" />
    <feColorMatrix in="cincin" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1 0" result="luar" />
    <feMerge result="putih"><feMergeNode in="luar" /><feMergeNode in="dalam" /></feMerge>
    <feFlood floodColor={warna} result="warna" />
    <feComposite in="warna" in2="putih" operator="in" result="garis" />
  </>
);
const piksel = (ukuran: number, id: string) => (
  <filter id={id} x="0" y="0" width="100%" height="100%">
    <feFlood x={ukuran / 2 - 1} y={ukuran / 2 - 1} height="2" width="2" />
    <feComposite width={ukuran} height={ukuran} />
    <feTile result="titik" />
    <feComposite in="SourceGraphic" in2="titik" operator="in" />
    <feMorphology operator="dilate" radius={ukuran / 2} result="blok" />
    <feComponentTransfer in="blok">
      <feFuncR type="discrete" tableValues="0 0.25 0.5 0.75 1" /><feFuncG type="discrete" tableValues="0 0.25 0.5 0.75 1" />
      <feFuncB type="discrete" tableValues="0 0.25 0.5 0.75 1" />
    </feComponentTransfer>
  </filter>
);
const poster = (n: string) => (
  <feComponentTransfer>
    <feFuncR type="discrete" tableValues={n} /><feFuncG type="discrete" tableValues={n} /><feFuncB type="discrete" tableValues={n} />
  </feComponentTransfer>
);

export const FilterIlustrasi: React.FC = () => (
  <svg width="0" height="0" style={{position: 'absolute'}}>
    <defs>
      {piksel(14, 'fx-piksel')}
      {piksel(30, 'fx-bata')}
      <filter id="fx-kapur" x="-10%" y="-10%" width="120%" height="120%">
        {garis('#F4F1E6', 4, 3)}
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="4" result="bising" />
        <feColorMatrix in="bising" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  3 0 0 0 -0.9" result="butir" />
        <feComposite in="garis" in2="butir" operator="in" result="kasar" />
        <feTurbulence type="turbulence" baseFrequency="0.04" numOctaves="1" seed="2" result="goyang" />
        <feDisplacementMap in="kasar" in2="goyang" scale="5" />
      </filter>
      <filter id="fx-emas" x="-20%" y="-20%" width="140%" height="140%">
        {garis('#F7C46A', 3, 2.2)}
        <feGaussianBlur in="garis" stdDeviation="7" result="pendar" />
        <feMerge><feMergeNode in="pendar" /><feMergeNode in="pendar" /><feMergeNode in="garis" /></feMerge>
      </filter>
      <filter id="fx-stickman" x="-10%" y="-10%" width="120%" height="120%">
        {garis('#FFFFFF', 2, 1.2)}
      </filter>
      <filter id="fx-flat" x="-5%" y="-5%" width="110%" height="110%">
        <feColorMatrix type="saturate" values="1.35" />
        {poster('0 0.3 0.6 0.85 1')}
      </filter>
      <filter id="fx-komik" x="-10%" y="-10%" width="120%" height="120%">
        <feColorMatrix in="SourceGraphic" type="saturate" values="1.6" result="jenuh" />
        <feComponentTransfer in="jenuh" result="datar">
          <feFuncR type="discrete" tableValues="0.1 0.55 1" /><feFuncG type="discrete" tableValues="0.1 0.55 1" /><feFuncB type="discrete" tableValues="0.1 0.55 1" />
        </feComponentTransfer>
        <feMorphology in="SourceAlpha" operator="dilate" radius="9" result="tebal" />
        <feFlood floodColor="#111" result="hitam" />
        <feComposite in="hitam" in2="tebal" operator="in" result="tepi" />
        <feMerge><feMergeNode in="tepi" /><feMergeNode in="datar" /></feMerge>
      </filter>
      <filter id="fx-ps2" x="-5%" y="-5%" width="110%" height="110%">
        <feFlood x="3" y="3" height="2" width="2" />
        <feComposite width="8" height="8" />
        <feTile result="titik" />
        <feComposite in="SourceGraphic" in2="titik" operator="in" />
        <feMorphology operator="dilate" radius="4" />
        {poster('0 0.2 0.45 0.7 0.9')}
      </filter>
      <filter id="fx-clay" x="-15%" y="-15%" width="130%" height="130%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="2.4" result="lembut" />
        <feColorMatrix in="lembut" type="saturate" values="0.85" result="pucat" />
        <feGaussianBlur in="SourceAlpha" stdDeviation="9" result="tinggi" />
        <feSpecularLighting in="tinggi" surfaceScale="7" specularConstant="0.9" specularExponent="22" lightingColor="#fff" result="kilap">
          <fePointLight x="-200" y="-300" z="420" />
        </feSpecularLighting>
        <feComposite in="kilap" in2="SourceAlpha" operator="in" result="kilap2" />
        <feComposite in="pucat" in2="kilap2" operator="arithmetic" k1="0" k2="1" k3="0.55" k4="0" />
      </filter>
      <filter id="fx-cgi" x="-15%" y="-15%" width="130%" height="130%">
        <feColorMatrix in="SourceGraphic" type="saturate" values="1.45" result="jenuh" />
        <feComponentTransfer in="jenuh" result="kontras">
          <feFuncR type="linear" slope="1.25" intercept="-0.08" /><feFuncG type="linear" slope="1.25" intercept="-0.08" /><feFuncB type="linear" slope="1.25" intercept="-0.08" />
        </feComponentTransfer>
        <feGaussianBlur in="SourceAlpha" stdDeviation="6" result="tinggi" />
        <feSpecularLighting in="tinggi" surfaceScale="5" specularConstant="1.1" specularExponent="35" lightingColor="#9fe6ff" result="kilap">
          <fePointLight x="900" y="-200" z="300" />
        </feSpecularLighting>
        <feComposite in="kilap" in2="SourceAlpha" operator="in" result="kilap2" />
        <feComposite in="kontras" in2="kilap2" operator="arithmetic" k1="0" k2="1" k3="0.7" k4="0" />
      </filter>
    </defs>
  </svg>
);

// ── Latar ──────────────────────────────────────────────────────────────────
const garisPindai = <div style={{position: 'absolute', inset: 0, background: 'repeating-linear-gradient(0deg,#0003 0 3px,transparent 3px 6px)'}} />;

const LatarPiksel: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: 'linear-gradient(#1a0b3b,#4b1677 55%,#e0457b)'}}>
    <svg width="1080" height="1920" style={{position: 'absolute', shapeRendering: 'crispEdges'}}>
      {Array.from({length: 40}).map((_, i) => <rect key={'b' + i} x={(i * 197) % 1080} y={(i * 131) % 700} width={8} height={8}
        fill="#fff" opacity={(Math.floor(f / 10) + i) % 3 ? 0.9 : 0.3} />)}
      {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => {
        const w = 110 + (i * 37) % 70; const h = 360 + (i * 151) % 420; const x = i * 125 - 20;
        return <g key={i}><rect x={x} y={1300 - h} width={w} height={h} fill={i % 2 ? '#2a0f55' : '#341568'} />
          {Array.from({length: Math.floor(h / 60)}).map((_, j) => <rect key={j} x={x + 18} y={1300 - h + 24 + j * 60} width={w - 36} height={16}
            fill={(i + j + Math.floor(f / 20)) % 4 ? '#ffd65a' : '#5b2a8a'} />)}</g>;
      })}
      <rect x="0" y="1300" width="1080" height="620" fill="#170733" />
      {Array.from({length: 12}).map((_, i) => <line key={'l' + i} x1={540} y1={1300} x2={-1200 + i * 320} y2={1920} stroke="#ff4fd8" strokeWidth={4} />)}
      {Array.from({length: 8}).map((_, i) => { const y = 1300 + Math.pow(((i + (f / 20) % 1) / 8), 2) * 620;
        return <line key={'h' + i} x1={0} y1={y} x2={1080} y2={y} stroke="#ff4fd8" strokeWidth={4} />; })}
    </svg>
    {garisPindai}
  </AbsoluteFill>
);

const LatarKapur: React.FC<LatarProps> = () => (
  <AbsoluteFill style={{background: '#6b4a2b'}}>
    <div style={{position: 'absolute', inset: 34, borderRadius: 10, background: 'radial-gradient(ellipse at 40% 35%,#3c5e48,#24392c 80%)',
      boxShadow: 'inset 0 0 120px #0008'}}>
      <svg width="1012" height="1852" style={{position: 'absolute', opacity: 0.16}}>
        <filter id="debu"><feTurbulence baseFrequency="0.02" numOctaves="3" seed="7" /><feColorMatrix values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0.6 0 0 0 -0.25" /></filter>
        <rect width="1012" height="1852" filter="url(#debu)" />
      </svg>
      <svg width="1012" height="1852" style={{position: 'absolute'}} fill="none" stroke="#f4f1e6" strokeOpacity={0.35} strokeWidth={4} strokeLinecap="round">
        <path d="M80 1500 q60 -40 120 0 t120 0" /><circle cx="860" cy="1560" r="46" /><path d="M820 220 l90 0 m-45 -45 l0 90" />
        <path d="M120 300 l120 40 l-30 -50 m30 50 l-50 20" />
      </svg>
      <div style={{position: 'absolute', bottom: 40, left: 60, right: 60, height: 22, background: '#4b3220', borderRadius: 6}} />
    </div>
  </AbsoluteFill>
);

const LatarEmas: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: '#050505'}}>
    <div style={{position: 'absolute', left: 240, right: 240, top: 640, height: 640, opacity: 0.55 + Math.sin(f / 12) * 0.08,
      background: 'linear-gradient(#f7c46a00,#f7c46a55)', clipPath: 'polygon(38% 0,62% 0,100% 100%,0 100%)', filter: 'blur(6px)'}} />
    <div style={{position: 'absolute', left: 260, right: 260, top: 1220, height: 110, borderRadius: '50%', border: '4px solid #f7c46a',
      boxShadow: '0 0 40px #f7c46a, inset 0 0 40px #f7c46a88'}} />
  </AbsoluteFill>
);

const LatarPS2: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: 'linear-gradient(#2b1d4f,#7b3b6b 50%,#e58b4f)'}}>
    <svg width="1080" height="1920" style={{position: 'absolute'}}>
      {[0, 1, 2, 3, 4, 5].map((i) => { const x = i * 190 - 30, h = 520 + (i * 173) % 380, w = 170;
        return <g key={i}><polygon points={`${x},1350 ${x},${1350 - h} ${x + w * 0.6},${1350 - h - 40} ${x + w * 0.6},1350`} fill="#4a2f55" />
          <polygon points={`${x + w * 0.6},1350 ${x + w * 0.6},${1350 - h - 40} ${x + w},${1350 - h} ${x + w},1350`} fill="#2e1d3a" /></g>; })}
      <polygon points="0,1350 1080,1350 1080,1920 0,1920" fill="#3a3a44" />
      <polygon points="0,1350 1080,1350 1080,1500 0,1560" fill="#4d4d58" />
      {Array.from({length: 6}).map((_, i) => <rect key={i} x={((i * 260 - f * 6) % 1300) - 100} y={1620} width={140} height={14} fill="#f2c230" />)}
    </svg>
  </AbsoluteFill>
);

const LatarKomik: React.FC<LatarProps> = ({f, aksen}) => (
  <AbsoluteFill style={{background: '#ffe14d'}}>
    <div style={{position: 'absolute', inset: 0, backgroundImage: 'radial-gradient(#e83a3a 28%,transparent 30%)', backgroundSize: '26px 26px', opacity: 0.35}} />
    <svg width="1080" height="1920" style={{position: 'absolute'}}>
      <polygon points={Array.from({length: 24}).map((_, i) => { const r = i % 2 ? 300 : 470 + Math.sin(f / 5 + i) * 14; const a = (i / 24) * Math.PI * 2;
        return `${540 + Math.cos(a) * r},${520 + Math.sin(a) * r}`; }).join(' ')} fill="#fff" stroke="#111" strokeWidth={10} />
      <rect x="22" y="22" width="1036" height="1876" fill="none" stroke="#111" strokeWidth={22} />
      <line x1="22" y1="1180" x2="1058" y2="1140" stroke="#111" strokeWidth={18} />
      <rect x="40" y="1160" width="1000" height="720" fill={aksen} opacity={0.18} />
    </svg>
  </AbsoluteFill>
);

const LatarFlat: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: '#13235a'}}>
    <svg width="1080" height="1920" style={{position: 'absolute'}}>
      {Array.from({length: 30}).map((_, i) => <circle key={i} cx={(i * 211) % 1080} cy={(i * 97) % 900} r={i % 3 ? 3 : 5} fill="#fff" opacity={0.7} />)}
      <circle cx="780" cy="420" r="150" fill="#ffe7a8" />
      <circle cx="840" cy="390" r="150" fill="#13235a" opacity={0.0} />
      {[0, 1, 2].map((i) => <g key={i} transform={`translate(${((i * 420 + f * 1.2) % 1400) - 300},${1640 + i * 60})`}>
        <ellipse cx="0" cy="0" rx="220" ry="70" fill="#f4f6ff" /><circle cx="-60" cy="-50" r="80" fill="#f4f6ff" /><circle cx="70" cy="-30" r="66" fill="#f4f6ff" /></g>)}
      <rect x="0" y="1780" width="1080" height="140" fill="#0b1640" />
    </svg>
  </AbsoluteFill>
);

const LatarStickman: React.FC<LatarProps> = ({f}) => {
  const k = Math.sin(f / 6) * 12;
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <svg width="1080" height="1920" style={{position: 'absolute'}} stroke="#fff" strokeWidth={3} fill="none" strokeLinecap="round">
        <line x1="60" y1="1290" x2="1020" y2="1290" />
        <g transform="translate(250,1180)"><circle cx="0" cy="-40" r="18" /><line x1="0" y1="-22" x2="0" y2="40" />
          <line x1="0" y1="0" x2={-26} y2={-30 + k} /><line x1="0" y1="0" x2={26} y2={-30 - k} />
          <line x1="0" y1="40" x2="-20" y2="110" /><line x1="0" y1="40" x2="20" y2="110" /></g>
        {Array.from({length: 18}).map((_, i) => <g key={i} transform={`translate(${90 + i * 52},${1700 + (i % 2) * 6})`}>
          <circle cx="0" cy="0" r="8" /><line x1="0" y1="8" x2="0" y2="30" /></g>)}
      </svg>
    </AbsoluteFill>
  );
};

const LatarCGI: React.FC<LatarProps> = ({f, aksen}) => (
  <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 30%,#1d2a3f,#06080d 70%)'}}>
    {Array.from({length: 26}).map((_, i) => <div key={i} style={{position: 'absolute', left: (i * 173) % 1080, top: ((i * 263 - f * (2 + (i % 3))) % 1300 + 1300) % 1300,
      width: 4, height: 4, borderRadius: 4, background: '#9fe6ff', opacity: 0.5}} />)}
    <div style={{position: 'absolute', left: 0, right: 0, top: 1280, bottom: 0, background: 'linear-gradient(#1a2333,#05070b)'}} />
    <div style={{position: 'absolute', left: 300, right: 300, top: 1250, height: 60, borderRadius: '50%', background: aksen, filter: 'blur(40px)', opacity: 0.6}} />
    <div style={{position: 'absolute', left: 0, right: 0, top: 1280, height: 2, background: '#9fe6ff55'}} />
  </AbsoluteFill>
);

const LatarBata: React.FC<LatarProps> = () => (
  <AbsoluteFill style={{background: 'linear-gradient(#8fd3ff,#cdeeff 45%)'}}>
    <div style={{position: 'absolute', left: 0, right: 0, top: 1180, bottom: 0, background: '#3fae3f',
      backgroundImage: 'radial-gradient(circle at 45% 40%,#7cdc6c 0 9px,#2f8f2f 10px 15px,transparent 16px)', backgroundSize: '48px 48px'}} />
    {[[80, 1000, '#e8443a'], [860, 980, '#2f6fd6'], [700, 1090, '#f2c230']].map(([x, y, c], i) => (
      <div key={i} style={{position: 'absolute', left: x as number, top: y as number, width: 150, height: 90, background: c as string, borderRadius: 6,
        boxShadow: 'inset -10px -10px 0 #0002', backgroundImage: 'radial-gradient(circle at 50% 50%,#fff5 0 10px,transparent 11px)', backgroundSize: '50px 45px'}} />
    ))}
  </AbsoluteFill>
);

const LatarClay: React.FC<LatarProps> = ({f}) => (
  <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 35%,#fbf1e2,#ead7bd 80%)'}}>
    {[[120, 1280, 240], [520, 1330, 300], [880, 1270, 220]].map(([x, y, r], i) => (
      <div key={i} style={{position: 'absolute', left: (x as number) - (r as number) / 2 + Math.sin(f / 30 + i) * 8, top: y as number, width: r as number, height: (r as number) * 0.55,
        borderRadius: '50%', background: '#fffaf2', boxShadow: '0 18px 30px #b8946b55, inset 0 -14px 20px #e9d6bd'}} />
    ))}
  </AbsoluteFill>
);

// ── Hiasan di sekitar ikon (bayangan, pantulan) ─────────────────────────────
export type HiasProps = {f: number; aksen: string};
const BayanganLembut: React.FC<HiasProps> = ({f}) => (
  <div style={{position: 'absolute', top: 690, left: '50%', width: 300 - Math.sin(f / 18) * 20, height: 46, marginLeft: -(300 - Math.sin(f / 18) * 20) / 2,
    borderRadius: '50%', background: '#0000002a', filter: 'blur(10px)'}} />
);

const Pendorong: React.FC<HiasProps> = ({f, aksen}) => (
  <>
    {[-110, 0, 110].map((x, i) => (
      <div key={i} style={{position: 'absolute', top: 650, left: 540 + x - 28, width: 56, height: 150 + Math.sin(f / 3 + i) * 25, borderRadius: '50%',
        background: `linear-gradient(${aksen},#ffffff00)`, filter: 'blur(8px)', opacity: 0.85}} />
    ))}
    <div style={{position: 'absolute', top: 1230, left: 340, width: 400, height: 50, borderRadius: '50%', background: aksen, filter: 'blur(30px)',
      opacity: 0.45 + Math.sin(f / 5) * 0.1}} />
  </>
);

// ── Daftar tema ilustrasi ─────────────────────────────────────────────────
type Dasar = Omit<Tema, 'Latar'>;
const t = (d: Dasar, Latar: Tema['Latar'], efek: string, Hias?: React.FC<HiasProps>): Tema => ({...d, Latar, efek, Hias});

export const TEMA_ILUSTRASI: Record<string, Tema> = {
  piksel: t({nama: 'Pixel Art', asal: 'ilustrasi', teks: '#ffffff', redup: '#d9b8ff', aksen: '#ffd65a', fontJudul: PIXEL, fontTeks: PIXEL, fontLabel: PIXEL,
    bobot: 400, kapital: true, judul: 'kotak', ikon: 'polos', sub: 'kotak', label: 'nomor', ukuranJudul: 60, ukuranSub: 34}, LatarPiksel, 'fx-piksel'),
  kapur: t({nama: 'Papan Kapur', asal: 'ilustrasi', teks: '#f4f1e6', redup: '#c9d3c7', aksen: '#ffe27a', fontJudul: KAPUR, fontTeks: KAPUR, fontLabel: KAPUR,
    bobot: 700, kapital: false, judul: 'ketik', ikon: 'polos', sub: 'kata', label: 'nomor'}, LatarKapur, 'fx-kapur'),
  emas: t({nama: 'Sketsa Emas', asal: 'ilustrasi', teks: '#fff6e0', redup: '#b39a6b', aksen: '#f7c46a', fontJudul: RUBIK, fontTeks: RUBIK, fontLabel: RUBIK,
    bobot: 600, kapital: false, judul: 'zoom', ikon: 'polos', sub: 'kata', label: 'nomor'}, LatarEmas, 'fx-emas'),
  ps2: t({nama: 'Low-poly PS2', asal: 'ilustrasi', teks: '#fff', redup: '#f3c9b0', aksen: '#ffcf4a', fontJudul: TEKNO, fontTeks: RUBIK, fontLabel: TEKNO,
    bobot: 800, kapital: true, judul: 'zoom', ikon: 'polos', sub: 'kotak', label: 'nomor', ukuranJudul: 84}, LatarPS2, 'fx-ps2', BayanganLembut),
  komik: t({nama: 'Komik', asal: 'ilustrasi', teks: '#111', redup: '#444', aksen: '#e83a3a', fontJudul: KOMIK, fontTeks: KOMIK, fontLabel: KOMIK,
    bobot: 400, kapital: true, judul: 'stiker', ikon: 'polos', sub: 'pil', label: 'stiker', ukuranSub: 64}, LatarKomik, 'fx-komik'),
  flat: t({nama: 'Flat Vector', asal: 'ilustrasi', teks: '#ffffff', redup: '#aab6e8', aksen: '#ffb347', fontJudul: RUBIK, fontTeks: RUBIK, fontLabel: RUBIK,
    bobot: 800, kapital: false, judul: 'naik', ikon: 'polos', sub: 'kotak', label: 'nomor'}, LatarFlat, 'fx-flat'),
  stickman: t({nama: 'Stickman Minimalis', asal: 'ilustrasi', teks: '#ffffff', redup: '#8a8a8a', aksen: '#ffffff', fontJudul: TANGAN, fontTeks: TANGAN, fontLabel: TANGAN,
    bobot: 700, kapital: false, judul: 'ketik', ikon: 'polos', sub: 'kata', label: 'nomor', ukuranJudul: 116}, LatarStickman, 'fx-stickman'),
  cgi: t({nama: 'CGI Mengilap', asal: 'ilustrasi', teks: '#eaf6ff', redup: '#7e93ad', aksen: '#38c6ff', fontJudul: TEKNO, fontTeks: RUBIK, fontLabel: TEKNO,
    bobot: 800, kapital: true, judul: 'zoom', ikon: 'polos', sub: 'kata', label: 'nomor', ukuranJudul: 80}, LatarCGI, 'fx-cgi', Pendorong),
  bata: t({nama: 'Bata Mainan', asal: 'ilustrasi', teks: '#13233a', redup: '#3b5370', aksen: '#e8443a', fontJudul: BATA, fontTeks: RUBIK, fontLabel: BATA,
    bobot: 400, kapital: true, judul: 'kotak', ikon: 'polos', sub: 'pil', label: 'nomor', ukuranJudul: 74}, LatarBata, 'fx-bata', BayanganLembut),
  clay: t({nama: 'Clay 3D', asal: 'ilustrasi', teks: '#5a3a24', redup: '#9a7a5c', aksen: '#e2683c', fontJudul: CLAY, fontTeks: CLAY, fontLabel: CLAY,
    bobot: 700, kapital: false, judul: 'naik', ikon: 'polos', sub: 'pil', label: 'nomor'}, LatarClay, 'fx-clay', BayanganLembut),
};
