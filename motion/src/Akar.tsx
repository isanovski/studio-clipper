import React from 'react';
import {Composition} from 'remotion';
import {Video, Props, totalFrame, FPS} from './Video';
// Props bawaan ditulis di sini (bukan impor naskah/contoh.json): installer tidak menyertakan folder naskah,
// dan render sungguhan selalu memakai --props dari buat.mjs.
const contoh = {
  judul: 'Contoh', gaya: 'garis', handle: '',
  adegan: [{judul: 'Contoh', teks: 'Tulis naskahmu di Isanovski Studio.', kunci: ['naskahmu'], ikon: '🎬', durasi: 3}],
};

export const Akar: React.FC = () => (
  <Composition
    id="Motion"
    component={Video}
    fps={FPS}
    width={1080}
    height={1920}
    durationInFrames={totalFrame(contoh as unknown as Props)}
    defaultProps={contoh as unknown as Props}
    calculateMetadata={({props}) => ({durationInFrames: totalFrame(props)})}
  />
);
