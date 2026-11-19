// kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0 (alat/LISENSI.md): dilarang dijual ulang.
import React from 'react';
import {
  AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import {TEMA, Tema} from './tema';
import {FilterIlustrasi} from './ilustrasi';

export const FPS = 30;

export type Adegan = {
  teks: string; // kalimat narasi (juga jadi subtitle)
  judul: string; // tulisan besar di layar (2–5 kata)
  kunci?: string[]; // kata yang disorot di subtitle
  ikon?: string; // emoji / simbol besar
  gambar?: string; // SVG objek buatan AI (gambar.mjs, sudah disaring svg-aman.mjs) — dipakai menggantikan emoji
  durasi?: number; // detik; diisi otomatis dari panjang suara
  suara?: string; // path di folder public/, mis. suara/01.wav
  klip?: string; // adegan video asli (path di public/, diisi buat.mjs dari file klip.py)
};

export type Props = {
  judul: string;
  gaya: string; // kunci di TEMA (14 template + 10 ilustrasi: piksel, kapur, emas, ps2, komik, flat, stickman, cgi, bata, clay)
  handle?: string;
  aksen?: string;
  adegan: Adegan[];
};

const JEDA = 0.35; // detik napas di akhir tiap adegan
export const frameAdegan = (a: Adegan) => Math.ceil(((a.durasi ?? 3) + (a.klip ? 0 : JEDA)) * FPS);
export const totalFrame = (p: Props) => p.adegan.reduce((s, a) => s + frameAdegan(a), 0);

const temaDari = (p: Props): Tema => TEMA[p.gaya] ?? TEMA.garis;
const warnaAdegan = (t: Tema, i: number, aksenProp?: string) => {
  const pn = t.panel?.[i % t.panel.length];
  return {bg: pn?.bg, teks: pn?.teks ?? t.teks, aksen: aksenProp ?? pn?.aksen ?? t.aksen,
    redup: pn ? (pn.teks === '#fff' || pn.teks === '#faf6ef' ? '#ffffffaa' : '#00000088') : t.redup};
};
const huruf = (t: Tema, s: string) => (t.kapital ? s.toUpperCase() : s);
const kontras = (hex: string) => {
  let h = hex.replace('#', '');
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return r * 0.299 + g * 0.587 + b * 0.114 > 150 ? '#111' : '#fff';
};

// ── Adegan hibrid: klip asli layar penuh + label judul ──────────────────────
const AdeganKlip: React.FC<{a: Adegan; p: Props}> = ({a, p}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = temaDari(p);
  const aksen = p.aksen ?? t.aksen;
  const masuk = spring({frame: f, fps, config: {damping: 15}});
  const keluar = interpolate(f, [2.6 * fps, 3 * fps], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <OffthreadVideo src={staticFile(a.klip!)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      {a.judul ? (
        <div style={{position: 'absolute', top: 230, left: 80, right: 80, opacity: keluar, transform: `translateY(${interpolate(masuk, [0, 1], [-40, 0])}px)`}}>
          <span style={{background: aksen, color: kontras(aksen), fontFamily: t.fontJudul, fontWeight: t.bobot, fontSize: 54, padding: '14px 26px',
            lineHeight: 1.5, boxDecorationBreak: 'clone', WebkitBoxDecorationBreak: 'clone'}}>
            {huruf(t, a.judul)}
          </span>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ── Subtitle mengikuti waktu bicara (perkiraan per panjang kata) ───────────
const Subtitle: React.FC<{a: Adegan; t: Tema; w: ReturnType<typeof warnaAdegan>}> = ({a, t, w}) => {
  const f = useCurrentFrame();
  const kata = a.teks.split(/\s+/).filter(Boolean);
  const total = (a.durasi ?? 3) * FPS;
  const bobot = kata.map((k) => k.length + 2);
  const jumlah = bobot.reduce((s, b) => s + b, 0);
  let acc = 0;
  const mulai = bobot.map((b) => { const m = (acc / jumlah) * total; acc += b; return m; });
  const aktif = Math.max(0, mulai.findIndex((m, i) => f >= m && (i === kata.length - 1 || f < mulai[i + 1])));
  const grup = Math.floor(aktif / 4) * 4;
  const kunci = new Set((a.kunci ?? []).map((k) => k.toLowerCase()));
  const kotak = t.sub === 'kotak';
  const pil = t.sub === 'pil';
  return (
    <div style={{position: 'absolute', left: 90, right: 90, bottom: 400, textAlign: 'center'}}>
      <span style={{display: 'inline-block', fontFamily: t.fontTeks, fontSize: t.ukuranSub ?? 58, fontWeight: 800, lineHeight: 1.3, padding: kotak || pil ? '14px 28px' : 0,
        background: kotak ? '#111111e6' : pil ? '#ffffffd9' : 'transparent', borderRadius: pil ? 999 : kotak ? 10 : 0,
        boxShadow: pil ? '0 12px 30px #0002' : undefined, color: kotak ? '#fff' : w.teks}}>
        {kata.slice(grup, grup + 4).map((k, i) => {
          const idx = grup + i;
          const sorot = idx === aktif;
          const penting = kunci.has(k.toLowerCase().replace(/[^\p{L}\p{N}]/gu, ''));
          const warna = sorot || penting ? (kotak ? t.aksen : w.aksen) : kotak ? '#fff' : pil ? t.teks : w.teks;
          return (
            <span key={idx} style={{display: 'inline-block', margin: '0 9px', color: warna, opacity: f >= mulai[idx] ? 1 : 0.35,
              transform: `scale(${sorot ? 1.1 : 1})`}}>{k}</span>
          );
        })}
      </span>
    </div>
  );
};

// ── Judul: 7 cara muncul ───────────────────────────────────────────────────
const Judul: React.FC<{a: Adegan; t: Tema; w: ReturnType<typeof warnaAdegan>}> = ({a, t, w}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const teks = huruf(t, a.judul);
  const kata = teks.split(' ');
  const dasar: React.CSSProperties = {position: 'absolute', top: 760, left: 90, right: 90, fontFamily: t.fontJudul, fontWeight: t.bobot,
    fontSize: t.ukuranJudul ?? (t.fontJudul.includes('Instrument') ? 128 : 104), lineHeight: 1.06, color: w.teks, fontStyle: t.miring ? 'italic' : undefined,
    letterSpacing: t.kapital ? '-0.01em' : '-0.02em'};
  if (t.judul === 'ketik') {
    const n = Math.floor(f * 1.4);
    return <div style={dasar}>{teks.split('').map((c, i) => <span key={i} style={{opacity: i < n ? 1 : 0,
      color: i >= teks.lastIndexOf(' ') + 1 ? w.aksen : w.teks}}>{c}</span>)}
      <span style={{opacity: Math.floor(f / 15) % 2 ? 1 : 0, color: w.aksen}}>▍</span></div>;
  }
  if (t.judul === 'zoom') {
    const s = interpolate(f, [0, 22], [1.7, 1], {extrapolateRight: 'clamp'});
    const b = interpolate(f, [0, 16], [14, 0], {extrapolateRight: 'clamp'});
    return <div style={{...dasar, top: 720, textAlign: 'center', transform: `scale(${s})`, filter: `blur(${b}px)`, opacity: interpolate(f, [0, 8], [0, 1])}}>{teks}</div>;
  }
  if (t.judul === 'stiker' || t.judul === 'kotak') {
    const baris: string[] = [];
    kata.forEach((k) => { const l = baris[baris.length - 1]; if (l && (l + ' ' + k).length <= 14) baris[baris.length - 1] = l + ' ' + k; else baris.push(k); });
    return <div style={{...dasar, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 14}}>
      {baris.map((b, i) => {
        const s = spring({frame: f - i * 5, fps, config: {damping: 12, stiffness: 170}});
        const bg = t.judul === 'stiker' ? (i % 2 ? '#fff' : w.aksen) : i === baris.length - 1 ? w.aksen : w.teks;
        return <span key={i} style={{background: bg, color: kontras(bg), padding: '6px 22px 12px', transform: `rotate(${t.judul === 'stiker' ? (i % 2 ? 2 : -3) : 0}deg) scale(${s})`,
          boxShadow: t.judul === 'stiker' ? '0 10px 0 #0002' : undefined, transformOrigin: 'left center'}}>{b}</span>;
      })}
    </div>;
  }
  if (t.judul === 'pil') {
    const s = spring({frame: f, fps, config: {damping: 14}});
    return <div style={{...dasar, top: 800, textAlign: 'center'}}>
      <span style={{display: 'inline-block', background: '#ffffffb3', border: '1.5px solid #fff', backdropFilter: 'blur(20px)', borderRadius: 999,
        padding: '26px 50px', fontSize: 74, boxShadow: '0 24px 60px #4f8cff26', transform: `scaleX(${interpolate(s, [0, 1], [0.3, 1])})`, opacity: s}}>
        <span style={{display: 'inline-block', width: 26, height: 26, borderRadius: '50%', background: w.aksen, marginRight: 22, verticalAlign: 'middle',
          transform: `translateY(${-Math.abs(Math.sin(f / 6)) * 18}px)`}} />{teks}
      </span>
    </div>;
  }
  if (t.judul === 'sorot') {
    const akhir = kata.pop() ?? '';
    const s = spring({frame: f - 8, fps, config: {damping: 15}});
    return <div style={dasar}>
      {kata.join(' ')}{' '}
      <span style={{position: 'relative', display: 'inline-block', fontFamily: '"Fraunces", serif', fontStyle: 'italic', fontWeight: 600}}>
        <span style={{position: 'absolute', left: -14, right: -14, top: '12%', bottom: '4%', background: '#9fb5b2', opacity: 0.55, transform: `scaleX(${s})`, transformOrigin: 'left'}} />
        <span style={{position: 'relative', color: w.aksen}}>{akhir}</span>
      </span>
    </div>;
  }
  // naik (bawaan)
  return <div style={dasar}>
    {kata.map((k, j) => {
      const s = spring({frame: f - j * 4, fps, config: {damping: 16}});
      return <span key={j} style={{display: 'inline-block', marginRight: 26, opacity: s, transform: `translateY(${interpolate(s, [0, 1], [60, 0])}px)`,
        color: j === kata.length - 1 ? w.aksen : w.teks, textShadow: t.ikon === 'cahaya' && j === kata.length - 1 ? `0 0 30px ${w.aksen}` : undefined}}>{k}</span>;
    })}
  </div>;
};

// ── Objek SVG buatan AI: viewBox dipas ke batas gambar sebenarnya (AI sering menggambar kecil) ──
const SvgObjek: React.FC<{svg: string; ukuran: number}> = ({svg, ukuran}) => {
  const ref = React.useRef<HTMLDivElement>(null);
  React.useLayoutEffect(() => {
    const el = ref.current?.querySelector('svg');
    if (!el) return;
    try {
      const b = (el as SVGGraphicsElement).getBBox();
      if (b.width > 0 && b.height > 0) {
        const sisi = Math.max(b.width, b.height) * 1.06;
        el.setAttribute('viewBox', `${b.x + b.width / 2 - sisi / 2} ${b.y + b.height / 2 - sisi / 2} ${sisi} ${sisi}`);
      }
    } catch { /* biarkan viewBox asli */ }
  }, [svg]);
  return <div ref={ref} style={{width: ukuran, height: ukuran}} dangerouslySetInnerHTML={{__html: svg}} />;
};

// ── Ikon: 6 bingkai ─────────────────────────────────────────────────────────
const Ikon: React.FC<{a: Adegan; t: Tema; w: ReturnType<typeof warnaAdegan>; i: number}> = ({a, t, w, i}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!a.ikon && !a.gambar) return null;
  const s = spring({frame: f - 6, fps, config: {damping: 9, mass: 0.8}});
  const mengambang = Math.sin(f / 18) * 8;
  const pos: React.CSSProperties = {position: 'absolute', top: 300, left: 0, right: 0, display: 'flex', justifyContent: 'center'};
  const emoji = (ukuran: number) => a.gambar
    ? <SvgObjek svg={a.gambar} ukuran={ukuran * 1.15} />
    : <span style={{fontSize: ukuran, lineHeight: 1}}>{a.ikon}</span>;
  if (t.efek) {
    // gaya ilustrasi: ikon besar "digambar ulang" lewat filter, melayang seperti terbang
    const miring = Math.sin(f / 14) * 4;
    return <>
      {t.Hias ? <t.Hias f={f} aksen={w.aksen} /> : null}
      <div style={{...pos, top: 200, transform: `scale(${s}) translateY(${mengambang * 1.6}px) rotate(${miring}deg)`}}>
        <div style={{padding: 30, filter: `url(#${t.efek})`}}>{emoji(430)}</div>
      </div>
    </>;
  }
  if (t.ikon === 'polaroid') {
    return <div style={pos}><div style={{background: '#fff', padding: '30px 30px 80px', boxShadow: '0 30px 60px #0003', transform: `rotate(${(i % 2 ? 4 : -5) * s}deg) scale(${s}) translateY(${mengambang}px)`}}>
      <div style={{width: 300, height: 300, background: '#ece6da', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{emoji(190)}</div>
      <div style={{position: 'absolute', top: -22, left: '50%', width: 160, height: 44, marginLeft: -80, background: '#f5d23acc', transform: 'rotate(-4deg)'}} />
    </div></div>;
  }
  if (t.ikon === 'kaca') {
    return <div style={pos}><div style={{width: 340, height: 340, borderRadius: 64, background: '#ffffff8c', border: '2px solid #ffffffcc', backdropFilter: 'blur(24px)',
      boxShadow: '0 30px 80px #0f172a22', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${s}) rotate(${interpolate(s, [0, 1], [-12, 0])}deg) translateY(${mengambang}px)`}}>
      {emoji(190)}</div></div>;
  }
  if (t.ikon === 'lingkaran') {
    return <div style={pos}><div style={{width: 360, height: 360, borderRadius: '50%', background: w.aksen, display: 'flex', alignItems: 'center', justifyContent: 'center',
      transform: `scale(${s}) translateY(${mengambang}px)`, boxShadow: `0 0 0 ${18 + Math.sin(f / 10) * 6}px ${w.aksen}33`}}>{emoji(200)}</div></div>;
  }
  if (t.ikon === 'kartu') {
    return <div style={pos}><div style={{width: 420, height: 320, borderRadius: 26, background: '#fff', border: '3px solid #141414', boxShadow: '12px 12px 0 #141414',
      display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', transform: `rotate(${(1 - s) * -10}deg) scale(${s})`}}>
      <span style={{position: 'absolute', top: -26, left: -26, width: 72, height: 72, borderRadius: '50%', background: w.aksen, color: kontras(w.aksen),
        fontFamily: t.fontLabel, fontSize: 34, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{i + 1}</span>
      {emoji(180)}</div></div>;
  }
  if (t.ikon === 'cahaya') {
    return <div style={{...pos, filter: `drop-shadow(0 0 40px ${w.aksen})`, transform: `scale(${s}) translateY(${mengambang}px)`}}>{emoji(250)}</div>;
  }
  return <div style={{...pos, transform: `scale(${s}) rotate(${interpolate(s, [0, 1], [-25, 0])}deg)`}}>{emoji(260)}</div>;
};

// ── Label adegan ────────────────────────────────────────────────────────────
const Label: React.FC<{t: Tema; w: ReturnType<typeof warnaAdegan>; i: number; n: number}> = ({t, w, i, n}) => {
  const no = `${String(i + 1).padStart(2, '0')} / ${String(n).padStart(2, '0')}`;
  if (t.label === 'nomor') return <div style={{position: 'absolute', top: 170, left: 90, fontFamily: t.fontLabel, fontSize: 30, letterSpacing: 6, color: w.redup}}>{no}</div>;
  if (t.label === 'stiker') return <div style={{position: 'absolute', top: 160, left: 90, fontFamily: t.fontLabel, fontSize: 30, background: '#141414', color: '#e2b33c',
    padding: '8px 18px', transform: 'rotate(-2deg)'}}>{no}</div>;
  return null;
};

const SatuAdegan: React.FC<{a: Adegan; i: number; n: number; p: Props}> = ({a, i, n, p}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = temaDari(p);
  const w = warnaAdegan(t, i, p.aksen);
  const garis = spring({frame: f - 10, fps, config: {damping: 14}});
  return (
    <AbsoluteFill>
      {w.bg ? <AbsoluteFill style={{background: w.bg}} /> : null}
      {w.bg ? <t.Latar f={f} i={i} n={n} aksen={w.aksen} judul={a.judul} /> : null}
      {a.suara ? <Audio src={staticFile(a.suara)} /> : null}
      <Label t={t} w={w} i={i} n={n} />
      <Ikon a={a} t={t} w={w} i={i} />
      <Judul a={a} t={t} w={w} />
      {t.judul === 'naik' ? <div style={{position: 'absolute', top: 1080, left: 90, height: 10, width: 300 * garis, background: w.aksen, borderRadius: 5}} /> : null}
      <Subtitle a={a} t={t} w={w} />
    </AbsoluteFill>
  );
};

export const Video: React.FC<Props> = (p) => {
  const f = useCurrentFrame();
  const t = temaDari(p);
  const aksen = p.aksen ?? t.aksen;
  const total = totalFrame(p);
  // adegan yang sedang tampil (untuk latar yang bergantung pada adegan)
  let dari = 0;
  let iAktif = 0;
  p.adegan.forEach((a, i) => { if (f >= dari) iAktif = i; dari += frameAdegan(a); });
  dari = 0;
  return (
    <AbsoluteFill style={{fontFamily: t.fontTeks, background: '#000'}}>
      {t.efek ? <FilterIlustrasi /> : null}
      {!t.panel ? <t.Latar f={f} i={iAktif} n={p.adegan.length} aksen={aksen} judul={p.adegan[iAktif]?.judul ?? ''} /> : null}
      {p.adegan.map((a, i) => {
        const d = frameAdegan(a);
        const el = (
          <Sequence key={i} from={dari} durationInFrames={d}>
            {a.klip ? <AdeganKlip a={a} p={p} /> : <SatuAdegan a={a} i={i} n={p.adegan.length} p={p} />}
          </Sequence>
        );
        dari += d;
        return el;
      })}
      {t.label === 'progres' ? (
        <div style={{position: 'absolute', top: 120, left: 90, right: 90, display: 'flex', gap: 10}}>
          {p.adegan.map((_, i) => <div key={i} style={{flex: 1, height: 8, borderRadius: 8, background: i <= iAktif ? aksen : '#00000018'}} />)}
        </div>
      ) : null}
      {p.handle ? (
        <div style={{position: 'absolute', top: t.label === 'progres' ? 150 : 110, right: 90, fontSize: 30, color: warnaAdegan(t, iAktif, p.aksen).redup, fontFamily: t.fontLabel}}>
          {p.handle}
        </div>
      ) : null}
      {t.label !== 'progres' ? <div style={{position: 'absolute', bottom: 0, left: 0, height: 8, width: `${(f / total) * 100}%`, background: aksen}} /> : null}
    </AbsoluteFill>
  );
};
