import {test} from 'node:test';
import assert from 'node:assert/strict';
import {inflateSync} from 'node:zlib';
import {cardData,cardPixels,cardPng,cardMetadata,COLORS,WIDTH,HEIGHT} from '../share-card.mjs';

const choices=[['cooperate','cooperate'],['betray','cooperate'],['cooperate','betray'],['betray','betray']];
function replay() {
  return {kind:'arena',machine:{name:'@tester',public_listing:false},result:{
    suite_version:'arena-v2',rules_version:'pd-v1',total:425,
    matches:Array.from({length:10},()=>({rounds:Array.from({length:20},(_,i)=>({choices:choices[i%4]}))})),
  }};
}
test('every square preserves its recorded outcome and orientation',()=>{
  const data=cardData(replay()), pixels=cardPixels(data), stride=WIDTH*3+1;
  for (const [i,color] of [COLORS.cooperate,COLORS.exploit,COLORS.exploited,COLORS.conflict].entries()) {
    const offset=(177+10)*stride+1+(64+i*36+10)*3;
    assert.deepEqual([...pixels.slice(offset,offset+3)],color);
  }
  assert.equal(data.rows.length,10);
  assert.equal(data.rows[0].length,20);
  assert.equal(data.total,425);
});
test('PNG encodes actual pixels with valid dimensions and lossless compression',async()=>{
  const data=cardData(replay());
  const png=Buffer.from(await (await cardPng(data)).arrayBuffer());
  assert.deepEqual([...png.subarray(0,8)],[137,80,78,71,13,10,26,10]);
  assert.equal(png.readUInt32BE(16),WIDTH);
  assert.equal(png.readUInt32BE(20),HEIGHT);
  const chunks=[];
  for(let offset=8;offset<png.length;) {
    const size=png.readUInt32BE(offset),type=png.toString('ascii',offset+4,offset+8);
    if(type === 'IDAT') chunks.push(png.subarray(offset+8,offset+8+size));
    offset+=size+12;
  }
  assert.deepEqual(inflateSync(Buffer.concat(chunks)),Buffer.from(cardPixels(data)));
  assert.ok(png.length<100000);
  assert.deepEqual(png,Buffer.from(await (await cardPng(data)).arrayBuffer()));
});
test('rejects incomplete or unknown records but supports all completed game formats',()=>{
  const data=replay();
  data.result.matches[0].rounds.pop();
  assert.equal(cardData(data),null);
  assert.equal(cardData({}),null);
  assert.equal(cardData({...replay(),kind:'unknown'}),null);
  const old=replay(); old.result.suite_version='arena-v1';
  old.result.matches.forEach(match=>match.rounds.splice(10));
  assert.equal(cardData(old).rows[0].length,10);
  old.result.suite_version='future';
  assert.equal(cardData(old),null);
  const bad=replay(); bad.result.matches[0].rounds[0].choices=['other','betray'];
  assert.equal(cardData(bad),null);
  const tournament=replay();
  tournament.kind='tournament'; tournament.result.suite_version='trust-v1'; tournament.result.total=81;
  tournament.result.matches.splice(3);
  tournament.result.matches.forEach(match=>match.rounds.splice(10));
  assert.equal(cardData(tournament).rows.length,3);
  assert.equal(cardData({kind:'challenge',machines:[{name:'@left'},{name:'@right'}],
    result:{totals:[30,30],rounds:Array.from({length:10},()=>({choices:['cooperate','cooperate']}))}}).total,30);
});
test('metadata escapes user text and exposes absolute crawler-readable image URLs',()=>{
  const data=cardData(replay()); data.name='"><script>alert(1)</script>';
  const tags=cardMetadata(data,'https://example.test','00000000-0000-4000-8000-000000000001');
  assert.ok(!tags.includes('<script>'));
  assert.match(tags,/&quot;&gt;&lt;script&gt;/);
  assert.match(tags,/name="twitter:card" content="summary_large_image"/);
  assert.match(tags,/https:\/\/example.test\/og\/v1\/.+\.png/);
  assert.doesNotMatch(tags,/rank|strategy description/i);
});
