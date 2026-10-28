import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findings, comparison, outcome, REFERENCES } from '../../src/pylemma/web/static/story.mjs';

function match(pairs) {
  return {rounds:pairs.map((choices,i)=>({round:i+1,choices})),totals:[20,25]};
}

test('explains delayed retaliation and the final mutual betrayal streak',()=>{
  const data=match([
    ['cooperate','cooperate'],['cooperate','cooperate'],['cooperate','betray'],
    ['cooperate','cooperate'],['cooperate','cooperate'],['cooperate','betray'],
    ['betray','cooperate'],['betray','betray'],['betray','betray'],['betray','betray'],
  ]);
  assert.deepEqual(findings(data,['Forgiver','Opportunist']),[
    'Opportunist betrayed first, in round 3.',
    'Forgiver first betrayed in round 7, after 2 earlier betrayals by Opportunist.',
    'Both players betrayed in the last 3 rounds. Each earned only 3 points in those rounds.',
  ]);
});

test('distinguishes cooperation, simultaneous betrayal, and continued cooperation',()=>{
  const friendly=match(Array.from({length:10},()=>['cooperate','cooperate']));
  assert.deepEqual(findings(friendly,['A','B']),[
    'Both players cooperated in every round. Each earned 30 points.',
  ]);
  assert.equal(findings(match([['betray','betray']]),['A','B'])[0],
    'A and B both betrayed first, in round 1.');
  assert.equal(findings(match([['cooperate','betray'],['cooperate','cooperate']]),['A','B'])[1],
    "A kept cooperating after B's first betrayal.");
  assert.deepEqual(findings(match([]),['A','B']),[]);
});

test('provides an explicit reference and labels the result without declaring overall skill',()=>{
  assert.equal(REFERENCES[0].score,81);
  assert.equal(REFERENCES[1].score,78);
  assert.match(comparison(80),/1 point fewer/);
  assert.match(comparison(90),/9 points more/);
  assert.match(comparison(81),/matched the 81 points/);
  assert.equal(outcome({totals:[30,30]},['A','B']),'A draw: 30 points each.');
  assert.equal(outcome({totals:[20,25]},['A','B']),'B earned 25 points; A earned 20.');
});

// Arena facts and sharing must use recorded results, not fixed-suite baselines.
test('arena highlight identifies a recorded decision after repeated betrayal', async()=>{
  const {highlight,shareText} = await import('../../src/pylemma/web/static/story.mjs');
  const rounds = Array.from({length:10},(_,i)=>({round:i+1,choices:['cooperate','betray']}));
  assert.deepEqual(highlight({rounds},['Forgiver','Other']),{
    round:4,text:'Forgiver cooperated in round 4 after at least three earlier betrayals by Other.'});
  const text = shareText({name:'Forgiver',strategy:'Forgive once.'},{total:238,matches:Array(10)});
  assert.match(text,/238 points against 10 players/);
  assert.match(text,/Forgive once/);
  assert.doesNotMatch(text,/rank|best/i);
});

test('inspection highlights a recorded span only on a reviewed public trace', async()=>{
  const {inspectionUrl} = await import('../../src/pylemma/web/static/story.mjs');
  const publicUrl='https://logfire-eu.pydantic.dev/public-trace/00000000-0000-0000-0000-000000000000';
  assert.equal(inspectionUrl({logfire_url:publicUrl,logfire_access:'public'},'1234567890abcdef'), publicUrl+'?spanId=1234567890abcdef');
  assert.equal(inspectionUrl({logfire_url:publicUrl,logfire_access:'account'},'1234567890abcdef'), publicUrl);
  assert.equal(inspectionUrl({logfire_url:publicUrl,logfire_access:'public'},'invalid'), publicUrl);
  assert.equal(inspectionUrl({},'1234567890abcdef'),null);
});

test('highlights a recovery across matches and uses recorded round counts',async()=>{
  const {featuredDecision}=await import('../../src/pylemma/web/static/story.mjs');
  const recovery=match([...Array(6).fill(['cooperate','cooperate']),
    ...Array(4).fill(['betray','betray']),...Array(10).fill(['cooperate','cooperate'])]);
  recovery.opponent='Prober'; recovery.rounds[10].span_id='1234567890abcdef';
  const peaceful=match(Array(20).fill(['cooperate','cooperate']));
  peaceful.opponent='Friendly';
  const selected=featuredDecision([peaceful,recovery],'Visitor');
  assert.equal(selected.round,11);
  assert.equal(selected.opponent,'Prober');
  assert.equal(selected.spanId,'1234567890abcdef');
  assert.match(selected.text,/returned to cooperation/);
  assert.match(findings(peaceful,['A','B'])[0],/60 points/);
});
