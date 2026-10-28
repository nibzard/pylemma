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
