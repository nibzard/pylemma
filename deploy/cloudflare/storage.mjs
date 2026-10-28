import { publicEntry, publicPage } from './public-games.mjs';

/** Persist records and reserve allowances before external work starts. */
export const BUDGET_MICRO_USD = 4_000_000;
export const RESERVATION_MICRO_USD = 10_000;
export const MAX_GENERATIONS = BUDGET_MICRO_USD / RESERVATION_MICRO_USD;
export const DAILY_GENERATIONS = 100;
export const DAILY_CHALLENGES = 400;
export const MAX_CHALLENGES = 1600;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const validId = id => typeof id === 'string' && UUID.test(id);

export async function operate(storage, input, now = new Date()) {
  if (input.operation === 'build_status') {
    if (!validId(input.id)) throw new Error('Invalid build identifier.');
    return await storage.get('build:'+input.id) ?? null;
  }
  if (input.operation === 'build_claim') {
    if (!validId(input.id) || !/^[a-f0-9]{64}$/.test(input.fingerprint || '')) throw new Error('Invalid build.');
    return storage.transaction(async tx => {
      const key='build:'+input.id;
      const existing=await tx.get(key);
      if (existing) return {created:false,job:existing};
      const job={fingerprint:input.fingerprint,stage:'starting',started_at:now.toISOString(),updated_at:now.toISOString()};
      await tx.put(key,job);
      return {created:true,job};
    });
  }
  if (input.operation === 'build_progress') {
    if (!validId(input.id) || !['starting','generating','checking','saving','failed'].includes(input.stage)) throw new Error('Invalid build stage.');
    return storage.transaction(async tx => {
      const key='build:'+input.id, job=await tx.get(key);
      if (!job || job.stage === 'complete' || job.stage === 'failed') return false;
      const order=['starting','generating','checking','saving','failed'];
      if (order.indexOf(input.stage) < order.indexOf(job.stage)) return false;
      await tx.put(key,{...job,stage:input.stage,updated_at:now.toISOString()});
      return true;
    });
  }
  if (input.operation === 'arena_entry') {
    if (!validId(input.id)) throw new Error('Invalid identifier.');
    const replayId = await storage.get('arena:'+input.id);
    return replayId ? {replay_id:replayId, ...await storage.get('replay:'+replayId)} : null;
  }
  if (input.operation === 'arena_opponents') {
    if (!validId(input.id)) throw new Error('Invalid identifier.');
    const entries = await storage.list({prefix:'public:'});
    const rows = publicPage([...entries.values()],false,0,entries.size).entries;
    const selected = new Map();
    for (const row of rows) for (const player of row.players) {
      if (player.id === input.id || selected.has(player.id)) continue;
      const machine = await storage.get('machine:'+player.id);
      if (machine?.public_listing === true) selected.set(player.id,machine);
      if (selected.size === 10) return [...selected.values()];
    }
    return [...selected.values()];
  }
  if (input.operation === 'arena_games') {
    const {offset=0,limit=20} = input;
    if (!Number.isInteger(offset) || offset < 0 || offset > 100000 ||
        !Number.isInteger(limit) || limit < 1 || limit > 50) throw new Error('Invalid page.');
    const entries = await storage.list({prefix:'public:'});
    return publicPage([...entries.values()].filter(row=>row.kind === 'arena'),false,offset,limit);
  }
  if (input.operation === 'public_games') {
    const {ranked, offset=0, limit=20} = input;
    if (typeof ranked !== 'boolean' || !Number.isInteger(offset) || offset < 0 || offset > 100000 ||
        !Number.isInteger(limit) || limit < 1 || limit > 50) throw new Error('Invalid page.');
    const entries = await storage.list({prefix:'public:'});
    return publicPage([...entries.values()], ranked, offset, limit);
  }
  if (input.operation === 'status') {
    const generations = await storage.get('lifetime:generation') || 0;
    const challenges = await storage.get('lifetime:challenge') || 0;
    return {generations, challenges, reserved_micro_usd:generations * RESERVATION_MICRO_USD,
      budget_micro_usd:BUDGET_MICRO_USD,
      result_reset:await storage.get("maintenance:results-reset-2026-10-28") ?? null};
  }
  if (input.operation === 'reserve') {
    if (!['generation', 'challenge'].includes(input.kind) ||
        !Number.isInteger(input.limit) || input.limit < 1) throw new Error('Invalid reservation.');
    const dailyLimit = Math.min(input.limit, input.kind === 'generation' ? DAILY_GENERATIONS : DAILY_CHALLENGES);
    const lifetimeLimit = input.kind === 'generation' ? MAX_GENERATIONS : MAX_CHALLENGES;
    return storage.transaction(async tx => {
      const key = `daily:${now.toISOString().slice(0,10)}:${input.kind}`;
      const daily = await tx.get(key) || 0;
      const lifetimeKey = `lifetime:${input.kind}`;
      const lifetime = await tx.get(lifetimeKey) || 0;
      if (daily >= dailyLimit || lifetime >= lifetimeLimit) return false;
      await tx.put({[key]: daily + 1, [lifetimeKey]: lifetime + 1});
      return true;
    });
  }
  if (!['machine', 'replay'].includes(input.kind) || !validId(input.id)) throw new Error('Invalid record.');
  const key = `${input.kind}:${input.id}`;
  if (input.operation === 'get') return await storage.get(key) ?? null;
  if (input.operation === 'put') {
    if (!input.data || typeof input.data !== 'object') throw new Error('Invalid data.');
    if (JSON.stringify(input.data).length > 400_000) throw new Error('Record too large.');
    return storage.transaction(async tx => {
      if (await tx.get(key)) throw new Error('Record already exists.');
      if (input.kind === 'replay' && input.data.kind === 'arena') {
        const machineId = input.data.machine?.id;
        if (!validId(machineId)) throw new Error('Invalid arena player.');
        if (await tx.get('arena:'+machineId)) throw new Error('Arena entry already exists.');
        await tx.put('arena:'+machineId,input.id);
      }
      await tx.put(key, input.data);
      if (input.kind === 'machine' && validId(input.request_id)) {
        const buildKey='build:'+input.request_id, job=await tx.get(buildKey);
        if (job && job.stage !== 'complete') {
          await tx.put(buildKey,{...job,stage:'complete',machine_id:input.id,updated_at:now.toISOString()});
        }
      }
      if (input.kind === 'replay') {
        const summary = publicEntry(input.id, input.data);
        if (summary) await tx.put('public:'+input.id, summary);
      }
      return true;
    });
  }
  throw new Error('Unknown operation.');
}

/** One-time operator-requested reset. Never delete players or spending records. */
export async function clearPreviousResults(storage) {
  const marker='maintenance:results-reset-2026-10-28';
  return storage.transaction(async tx=>{
    const completed=await tx.get(marker);
    if (completed) return completed;
    const removed={replays:0,public_entries:0,arena_entries:0};
    for (const [prefix,label] of [['replay:','replays'],['public:','public_entries'],['arena:','arena_entries']]) {
      for (;;) {
        const entries=await tx.list({prefix,limit:128});
        if (!entries.size) break;
        const keys=[...entries.keys()];
        await tx.delete(keys);
        removed[label]+=keys.length;
      }
    }
    const result={...removed,completed_at:new Date().toISOString()};
    await tx.put(marker,result);
    return result;
  });
}
