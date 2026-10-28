import { test } from 'node:test';
import assert from 'node:assert/strict';
import { operate, MAX_GENERATIONS, validId } from '../storage.mjs';

class Storage {
  values = new Map();
  pending = Promise.resolve();
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
  const request = {operation:'reserve',kind:'generation',limit:20};
  const outcomes = await Promise.all(Array.from({length:30},()=>operate(storage,request,new Date('2026-10-28'))));
  assert.equal(outcomes.filter(Boolean).length,20);
  for (let day=29; day<=31; day++) {
    for(let i=0;i<20;i++) assert.equal(await operate(storage,request,new Date(`2026-10-${day}`)),true);
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
