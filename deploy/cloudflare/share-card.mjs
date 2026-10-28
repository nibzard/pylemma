/** Immutable replay artwork. The palette follows choices from the first player's side. */
export const WIDTH=1200, HEIGHT=630;
export const COLORS={
  background:[14,16,27], ink:[241,245,238], muted:[133,145,163],
  cooperate:[98,235,188], exploit:[255,115,132], exploited:[255,196,100], conflict:[91,71,130],
};
const FONT={
  A:['01110','10001','10001','11111','10001','10001','10001'],
  B:['11110','10001','10001','11110','10001','10001','11110'],
  C:['01111','10000','10000','10000','10000','10000','01111'],
  D:['11110','10001','10001','10001','10001','10001','11110'],
  E:['11111','10000','10000','11110','10000','10000','11111'],
  F:['11111','10000','10000','11110','10000','10000','10000'],
  G:['01111','10000','10000','10111','10001','10001','01111'],
  H:['10001','10001','10001','11111','10001','10001','10001'],
  I:['11111','00100','00100','00100','00100','00100','11111'],
  J:['00111','00010','00010','00010','10010','10010','01100'],
  K:['10001','10010','10100','11000','10100','10010','10001'],
  L:['10000','10000','10000','10000','10000','10000','11111'],
  M:['10001','11011','10101','10101','10001','10001','10001'],
  N:['10001','11001','10101','10011','10001','10001','10001'],
  O:['01110','10001','10001','10001','10001','10001','01110'],
  P:['11110','10001','10001','11110','10000','10000','10000'],
  Q:['01110','10001','10001','10001','10101','10010','01101'],
  R:['11110','10001','10001','11110','10100','10010','10001'],
  S:['01111','10000','10000','01110','00001','00001','11110'],
  T:['11111','00100','00100','00100','00100','00100','00100'],
  U:['10001','10001','10001','10001','10001','10001','01110'],
  V:['10001','10001','10001','10001','10001','01010','00100'],
  W:['10001','10001','10001','10101','10101','11011','10001'],
  X:['10001','10001','01010','00100','01010','10001','10001'],
  Y:['10001','10001','01010','00100','00100','00100','00100'],
  Z:['11111','00001','00010','00100','01000','10000','11111'],
  0:['01110','10001','10011','10101','11001','10001','01110'],
  1:['00100','01100','00100','00100','00100','00100','01110'],
  2:['01110','10001','00001','00010','00100','01000','11111'],
  3:['11110','00001','00001','01110','00001','00001','11110'],
  4:['00010','00110','01010','10010','11111','00010','00010'],
  5:['11111','10000','10000','11110','00001','00001','11110'],
  6:['01110','10000','10000','11110','10001','10001','01110'],
  7:['11111','00001','00010','00100','01000','01000','01000'],
  8:['01110','10001','10001','01110','10001','10001','01110'],
  9:['01110','10001','10001','01111','00001','00001','01110'],
  '@':['01110','10001','10111','10101','10111','10000','01111'],
  '?':['01110','10001','00001','00010','00100','00000','00100'],
  '.':['00000','00000','00000','00000','00000','00110','00110'],
  "'":['00100','00100','00000','00000','00000','00000','00000'],
  '-':['00000','00000','00000','11111','00000','00000','00000'],
  '_':['00000','00000','00000','00000','00000','00000','11111'],
  ' ':['00000','00000','00000','00000','00000','00000','00000'],
};

/** Never fabricate missing rounds or render incomplete/unknown formats. */
export function cardData(data) {
  const result=data?.result;
  if (!result) return null;
  const challenge=data.kind === 'challenge';
  if (!['arena','tournament','challenge'].includes(data.kind)) return null;
  const machine=challenge ? data.machines?.[0] : data.machine;
  const matches=challenge ? [result] : result.matches;
  const count=challenge ? 1 : data.kind === 'arena' ? 10 : 3;
  const rounds=data.kind === 'arena' && result.suite_version === 'arena-v2' ? 20 : 10;
  const total=challenge ? result.totals?.[0] : result.total;
  if (!machine || typeof machine.name !== 'string' || !Number.isInteger(total) ||
      total < 0 || total > count*rounds*5 || !Array.isArray(matches) || matches.length !== count ||
      (!challenge && (result.rules_version !== 'pd-v1' ||
        !(data.kind === 'arena' ? ['arena-v1','arena-v2'] : ['trust-v1']).includes(result.suite_version))) ||
      matches.some(match=>!Array.isArray(match.rounds) || match.rounds.length !== rounds ||
        match.rounds.some(round=>!Array.isArray(round.choices) || round.choices.length !== 2 ||
          round.choices.some(choice=>!['cooperate','betray'].includes(choice))))) return null;
  return {name:machine.name,total,rows:matches.map(match=>match.rounds.map(round=>round.choices))};
}

export function outcomeColor([left,right]) {
  return left === 'cooperate' ? (right === 'cooperate' ? COLORS.cooperate : COLORS.exploited) :
    (right === 'cooperate' ? COLORS.exploit : COLORS.conflict);
}

/** RGB pixels with a zero PNG filter byte before each scanline. */
export function cardPixels(card) {
  const stride=WIDTH*3+1, pixels=new Uint8Array(stride*HEIGHT);
  function rectangle(x,y,w,h,color) {
    for(let row=y;row<Math.min(y+h,HEIGHT);row++)
      for(let col=x;col<Math.min(x+w,WIDTH);col++) pixels.set(color,row*stride+1+col*3);
  }
  function text(value,x,y,scale,color) {
    for(const character of value.toUpperCase()) {
      const glyph=FONT[character] || FONT['?'];
      glyph.forEach((line,row)=>[...line].forEach((bit,col)=>{
        if(bit === '1') rectangle(x+col*scale,y+row*scale,scale,scale,color);
      }));
      x+=scale*6;
    }
  }
  rectangle(0,0,WIDTH,HEIGHT,COLORS.background);
  rectangle(64,43,12,12,COLORS.cooperate);
  text("PRISONER'S PYLEMMA",90,42,2,COLORS.muted);
  const name=card.name.length>29 ? card.name.slice(0,26)+'...' : card.name;
  text(name,64,92,5,COLORS.ink);
  // Shorter historical games retain their actual row/column counts.
  const columns=card.rows[0].length;
  const step=Math.min(36,Math.floor(720/columns));
  const startY=177+Math.floor((10-card.rows.length)*36/2);
  card.rows.forEach((row,y)=>row.forEach((choices,x)=>{
    const color=outcomeColor(choices);
    rectangle(64+x*step,startY+y*36,step-4,32,color);
    // A small highlight gives each square the appearance of a game tile.
    rectangle(64+x*step,startY+y*36,step-4,2,color.map(c=>Math.min(255,c+18)));
  }));
  const score=String(card.total), scale=score.length>3 ? 10 : 12;
  text(score,1136-(score.length*6-1)*scale,250,scale,COLORS.ink);
  text('POINTS',996-6*12,350,4,COLORS.muted);
  rectangle(64,553,1072,1,[45,50,66]);
  text('CAN YOU BEAT THIS?',64,580,3,COLORS.cooperate);
  text('PYLEMMA.AOR.FYI',956,586,2,COLORS.muted);
  return pixels;
}

const crcTable=Uint32Array.from({length:256},(_,n)=>{
  for(let i=0;i<8;i++) n=n&1 ? 0xedb88320^(n>>>1) : n>>>1;
  return n>>>0;
});
function chunk(type,body) {
  const bytes=new Uint8Array(body.length+12), view=new DataView(bytes.buffer);
  view.setUint32(0,body.length);
  bytes.set(new TextEncoder().encode(type),4); bytes.set(body,8);
  let crc=0xffffffff;
  for(const byte of bytes.subarray(4,-4)) crc=crcTable[(crc^byte)&255]^(crc>>>8);
  view.setUint32(bytes.length-4,(crc^0xffffffff)>>>0);
  return bytes;
}
export async function cardPng(card) {
  const compressed=new Blob([cardPixels(card)]).stream().pipeThrough(new CompressionStream('deflate'));
  const data=new Uint8Array(await new Response(compressed).arrayBuffer());
  const header=new Uint8Array(13), view=new DataView(header.buffer);
  view.setUint32(0,WIDTH); view.setUint32(4,HEIGHT); header[8]=8; header[9]=2;
  return new Blob([new Uint8Array([137,80,78,71,13,10,26,10]),
    chunk('IHDR',header),chunk('IDAT',data),chunk('IEND',new Uint8Array())],{type:'image/png'});
}
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function cardMetadata(card,origin,id) {
  const title=escape(`${card.name} scored ${card.total} points. Can you beat this?`);
  const image=escape(`${origin}/og/v1/${id}.png`);
  const url=escape(`${origin}/?replay=${id}`);
  const alt=escape(`${card.name}: ${card.total} points. Each row is an opponent; each square is a round. Mint: both cooperated. Coral: only you betrayed. Amber: only they betrayed. Purple: both betrayed.`);
  return `<title>${title}</title>
<meta property="og:type" content="website">
<meta property="og:title" content="${title}">
<meta property="og:description" content="Describe your strategy. Play the arena. Can you beat this score?">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${image}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="${WIDTH}">
<meta property="og:image:height" content="${HEIGHT}">
<meta property="og:image:alt" content="${alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${title}">
<meta name="twitter:image" content="${image}">
<meta name="twitter:image:alt" content="${alt}">`;
}
