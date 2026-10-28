import { test } from 'node:test';
import assert from 'node:assert/strict';
import { clearPreviousResults, operate, MAX_GENERATIONS, validId } from '../storage.mjs';

class Storage {
  values = new Map();
  pending = Promise.resolve();
  async list({prefix,limit=Infinity}) { return new Map([...this.values].filter(([key])=>key.startsWith(prefix)).slice(0,limit)); }
  async get(key) { return structuredClone(this.values.get(key)); }
  async put(key, value) {
    if (typeof key === 'object') {
      for (const [k,v] of Object.entries(key)) this.values.set(k,structuredClone(v));
    } else this.values.set(key,structuredClone(value));
  }
  transaction(fn) {
    const result = this.pending.then(()=>fn(this));
    this.pending = result.catch(()=>{});
    return result;
  }
}

test('reservations are atomic and retain a lifetime ceiling across dates', async()=>{
  const storage = new Storage();
  const request = {operation:'reserve',kind:'generation',limit:100};
  const outcomes = await Promise.all(Array.from({length:110},()=>operate(storage,request,new Date('2026-10-28'))));
  assert.equal(outcomes.filter(Boolean).length,100);
  for (let day=29; day<=31; day++) {
    for(let i=0;i<100;i++) assert.equal(await operate(storage,request,new Date(`2026-10-${day}`)),true);
  }
  assert.equal(await storage.get('lifetime:generation'),MAX_GENERATIONS);
  assert.equal(await operate(storage,request,new Date('2026-11-01')),false);
});

test('records survive a new request handler and remain immutable', async()=>{
  const storage = new Storage();
  const id = '01234567-89ab-4cde-8fab-0123456789ab';
  await operate(storage,{operation:'put',kind:'machine',id,data:{name:'Trust'}});
  assert.deepEqual(await operate(storage,{operation:'get',kind:'machine',id}),{name:'Trust'});
  await assert.rejects(operate(storage,{operation:'put',kind:'machine',id,data:{name:'Changed'}}));
  assert.equal(await operate(storage,{operation:'get',kind:'replay',id}),null);
  assert.equal(validId('../private'),false);
});

test('indexes only consented completed games and preserves shared ranks across pages',async()=>{
  const storage = new Storage();
  const machine = (id,listed) => ({id,name:'Player '+id,public_listing:listed});
  const replay = (score,listed=true) => ({kind:'tournament',machine:machine('a',listed),
    created_at:'2026-10-28T12:00:00+00:00',
    result:{rules_version:'pd-v1',suite_version:'trust-v1',total:score,
      matches:Array.from({length:3},()=>({rounds:Array(10).fill({})}))}});
  const put = (n,data) => operate(storage,{operation:'put',kind:'replay',
    id:`00000000-0000-0000-0000-${String(n).padStart(12,'0')}`,data});
  await put(1,replay(81)); await put(2,replay(81)); await put(3,replay(78));
  await put(4,replay(150,false));
  const partial = replay(100); partial.result.matches[0].rounds=[]; await put(5,partial);
  const unknown = replay(100); unknown.result.suite_version='future'; await put(6,unknown);
  const challenge={kind:'challenge',machines:[machine('a',true),machine('b',false)],
    result:{rounds:Array(10).fill({}),totals:[50,0]}};
  await put(7,challenge);
  const a=await operate(storage,{operation:'public_games',ranked:true,limit:2});
  const b=await operate(storage,{operation:'public_games',ranked:true,offset:2,limit:2});
  assert.equal(a.total,3); assert.deepEqual(a.entries.map(e=>e.rank),[1,1]);
  assert.equal(b.entries[0].rank,3); assert.equal(b.next_offset,null);
  const both=structuredClone(challenge); both.machines[1].public_listing=true;
  both.created_at='2026-10-29T00:00:00+00:00'; await put(8,both);
  const history=await operate(storage,{operation:'public_games',ranked:false});
  assert.equal(history.total,4); assert.equal(history.entries[0].kind,'challenge');
  assert.equal((await operate(storage,{operation:'public_games',ranked:true})).total,3);
  await assert.rejects(operate(storage,{operation:'public_games',ranked:true,limit:100}));
  assert.equal([...storage.values.keys()].filter(k=>k.startsWith('public:')).length,4);
});

test('arena entries are unique, consented, chronological, and select distinct recent opponents',async()=>{
  const storage = new Storage();
  const id = n=>`00000000-0000-0000-0000-${String(n).padStart(12,'0')}`;
  for (let n=1;n<=12;n++) {
    const machine={id:id(n),name:String(n),public_listing:n !== 12};
    await operate(storage,{operation:'put',kind:'machine',id:machine.id,data:machine});
    const data={kind:'arena',machine,created_at:`2026-10-28T12:00:${String(n).padStart(2,'0')}+00:00`,
      result:{total:273,rules_version:'pd-v1',suite_version:'arena-v1',
        matches:Array.from({length:10},()=>({rounds:Array(10).fill({})}))}};
    await operate(storage,{operation:'put',kind:'replay',id:id(n+20),data});
    await assert.rejects(operate(storage,{operation:'put',kind:'replay',id:id(n+40),data}));
  }
  const selected=await operate(storage,{operation:'arena_opponents',id:id(11)});
  assert.deepEqual(selected.map(m=>m.name),['10','9','8','7','6','5','4','3','2','1']);
  const page=await operate(storage,{operation:'arena_games',limit:2});
  assert.equal(page.total,11); assert.equal(page.entries[0].players[0].name,'11');
  assert.equal(page.entries[0].rank,undefined); assert.equal(page.next_offset,2);
  assert.equal((await operate(storage,{operation:'arena_entry',id:id(1)})).replay_id,id(21));
  assert.equal(await operate(storage,{operation:'arena_entry',id:id(99)}),null);
});


test('existing counts survive the daily limit increase',async()=>{
  const storage=new Storage();
  await storage.put({'daily:2026-10-28:generation':20,'lifetime:generation':20});
  const request={operation:'reserve',kind:'generation',limit:1000};
  const outcomes=await Promise.all(Array.from({length:90},()=>operate(storage,request,new Date('2026-10-28'))));
  assert.equal(outcomes.filter(Boolean).length,80);
  const status=await operate(storage,{operation:'status'});
  assert.equal(status.generations,100);
  assert.equal(status.reserved_micro_usd,1_000_000);
  assert.equal(status.budget_micro_usd,4_000_000);
});

test('generation changes preserve challenge limits',async()=>{
  const storage=new Storage();
  const request={operation:'reserve',kind:'challenge',limit:2000};
  await storage.put({'daily:2026-10-28:challenge':400,'lifetime:challenge':400});
  assert.equal(await operate(storage,request,new Date('2026-10-28')),false);
  await storage.put('lifetime:challenge',1600);
  assert.equal(await operate(storage,request,new Date('2026-10-29')),false);
});

test('build claims are atomic and machine recovery commits with the player',async()=>{
  const storage=new Storage(), id='00000000-0000-0000-0000-000000000099';
  const request={operation:'build_claim',id,fingerprint:'a'.repeat(64)};
  const claims=await Promise.all(Array.from({length:8},()=>operate(storage,request)));
  assert.equal(claims.filter(claim=>claim.created).length,1);
  await operate(storage,{operation:'build_progress',id,stage:'checking'});
  await operate(storage,{operation:'build_progress',id,stage:'generating'});
  assert.equal((await operate(storage,{operation:'build_status',id})).stage,'checking');
  const player='00000000-0000-0000-0000-000000000098';
  await operate(storage,{operation:'put',kind:'machine',id:player,data:{name:'@test'},request_id:id});
  await operate(storage,{operation:'build_progress',id,stage:'failed'});
  const job=await operate(storage,{operation:'build_status',id});
  assert.equal(job.stage,'complete');
  assert.equal(job.machine_id,player);
  assert.equal((await operate(storage,{operation:'get',kind:'machine',id:player})).name,'@test');
  assert.equal(await storage.get('lifetime:generation'),undefined);
});

test('public arena versions validate their own round counts',async()=>{
  const {publicEntry}=await import('../public-games.mjs');
  const data={kind:'arena',machine:{id:'x',name:'Test',public_listing:true},
    result:{suite_version:'arena-v2',rules_version:'pd-v1',total:1000,
      matches:Array.from({length:10},()=>({rounds:Array(20).fill({})}))}};
  assert.equal(publicEntry('r',data).rounds_per_match,20);
  data.result.suite_version='arena-v1';
  assert.equal(publicEntry('r',data),null);
  data.result.suite_version='arena-v2';
  data.result.total=1001;
  assert.equal(publicEntry('r',data),null);
});


test('result reset deletes only results and indexes and never repeats',async()=>{
  const storage=new Storage();
  storage.delete=async keys=>{
    let count=0;
    for (const key of keys) if(storage.values.delete(key)) count++;
    return count;
  };
  for (const prefix of ['replay:','public:','arena:']) {
    for(let n=0;n<260;n++) await storage.put(prefix+n,{saved:true});
  }
  const preserved={
    'machine:player':{name:'@player'},
    'build:reference':{stage:'complete',machine_id:'player'},
    'daily:2026-10-28:generation':42,
    'daily:2026-10-28:challenge':55,
    'lifetime:generation':87,
    'lifetime:challenge':99,
  };
  await storage.put(preserved);
  const first=await clearPreviousResults(storage);
  assert.equal(first.replays,260);
  assert.equal(first.public_entries,260);
  assert.equal(first.arena_entries,260);
  for(const [key,value] of Object.entries(preserved)) assert.deepEqual(await storage.get(key),value);
  assert.equal((await storage.list({prefix:'replay:'})).size,0);
  assert.equal((await storage.list({prefix:'public:'})).size,0);
  assert.equal((await storage.list({prefix:'arena:'})).size,0);
  await storage.put('replay:new',{saved:'after-reset'});
  assert.deepEqual(await clearPreviousResults(storage),first);
  assert.deepEqual(await storage.get('replay:new'),{saved:'after-reset'});
});

test('existing public summaries gain actual rules without rewriting results',async()=>{
  const storage=new Storage();
  await storage.put('public:old',{replay_id:'old',kind:'arena',suite_version:'arena-v2',
    players:[{id:'p',name:'@same'}],scores:[425]});
  await storage.put('machine:p',{id:'p',public_listing:true,strategy:'Betray first and last.'});
  const before=await storage.get('public:old');
  const page=await operate(storage,{operation:'arena_games'});
  assert.equal(page.entries[0].players[0].strategy,'Betray first and last.');
  assert.deepEqual(await storage.get('public:old'),before);
  await storage.put('machine:p',{id:'p',public_listing:false,strategy:'UNLISTED'});
  const hidden=await operate(storage,{operation:'arena_games'});
  assert.equal(hidden.entries[0].players[0].strategy,'');
});

test('arena ranks exclude old formats and resolve standing beyond the page',async()=>{
  const storage=new Storage();
  const ids=['00000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000002','00000000-0000-4000-8000-000000000003',
    '00000000-0000-4000-8000-000000000004'];
  for (const [index,id] of ids.entries()) {
    await storage.put('public:'+id,{replay_id:id,kind:'arena',
      suite_version:index===3?'arena-v1':'arena-v2',scores:[[564,564,425,900][index]],
      players:[{id,name:'@x',strategy:'Copy.'}]});
  }
  const request={operation:'arena_games',ranked:true,limit:1,player:ids[2]};
  const first=await operate(storage,request);
  assert.equal(first.total,3);
  assert.equal(first.entries[0].rank,1);
  assert.deepEqual(first.standing,{rank:3,total:3});
  assert.equal((await operate(storage,{...request,offset:1})).entries[0].rank,1);
  assert.equal((await operate(storage,{...request,offset:2})).entries[0].rank,3);
  assert.equal((await operate(storage,{...request,player:ids[3]})).standing,null);
  await assert.rejects(operate(storage,{...request,player:'invalid'}));
  await assert.rejects(operate(storage,{...request,ranked:false}));
});
