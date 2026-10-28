import { Container } from '@cloudflare/containers';
import { operate, validId, DAILY_GENERATIONS, DAILY_CHALLENGES, MAX_GENERATIONS, MAX_CHALLENGES } from './storage.mjs';
import { inspectLink } from './trace-links.mjs';

export class Pylemma extends Container {
  defaultPort = 8080;
  sleepAfter = '5m';
  envVars;
  busy = false;
  activeBuildId = null;
  constructor(ctx, env) {
    super(ctx, env);
    this.envVars = {
      PYLEMMA_RELEASE: env.VERSION_METADATA?.id || 'unknown',
      OPENAI_API_KEY: env.OPENAI_API_KEY,
      LOGFIRE_TOKEN: env.LOGFIRE_TOKEN,
      LOGFIRE_BASE_URL: env.LOGFIRE_BASE_URL,
      PYLEMMA_LOGFIRE_PROJECT_URL: env.LOGFIRE_PROJECT_URL,
      PYLEMMA_DAILY_GENERATIONS: String(DAILY_GENERATIONS),
      PYLEMMA_STORE_URL: 'https://pylemma.aor.fyi',
      PYLEMMA_STORE_TOKEN: env.STORE_TOKEN,
    };
  }
  onStart() {
    diagnosticLog({event:'container.started',version:this.env.VERSION_METADATA?.id || 'unknown'});
  }
  onStop({exitCode,reason}) {
    diagnosticLog({event:'container.stopped',exit_code:Number.isInteger(exitCode) ? exitCode : null,
      reason:['exit','signal'].includes(reason) ? reason : 'other',
      version:this.env.VERSION_METADATA?.id || 'unknown'});
  }
  onError(error) {
    const message=error instanceof Error ? error.message : typeof error === 'string' ? error : '';
    const failure=message.includes('crashed while checking for ports') ? 'startup_exit' :
      message.startsWith('Failed to verify port ') ? 'port_deadline' : 'other';
    diagnosticLog({event:'container.error',failure,version:this.env.VERSION_METADATA?.id || 'unknown'});
    throw error;
  }
  async onActivityExpired() {
    // The SDK counts in-flight requests only after startup finishes.
    if (this.busy) {
      diagnosticLog({event:'container.idle_deferred',version:this.env.VERSION_METADATA?.id || 'unknown'});
      this.renewActivityTimeout();
      return;
    }
    diagnosticLog({event:"container.idle_shutdown",version:this.env.VERSION_METADATA?.id || "unknown"});
    await this.destroy();
  }
  async fetch(request) {
    const supplied = request.headers.get('X-Request-ID');
    const requestId = validId(supplied) ? supplied.toLowerCase() : crypto.randomUUID();
    const headers = new Headers(request.headers);
    headers.set('X-Request-ID',requestId);
    request = new Request(request,{headers});
    const start = Date.now();
    let response;
    let outcome;
    try {
      const work = this.handleRequest(request);
      // Preserve a bounded build even if its browser connection closes.
      if (new URL(request.url).pathname === '/api/machines' && request.method === 'POST') {
        this.ctx.waitUntil?.(work.catch(()=>{}));
      }
      response = await work;
    }
    catch {
      outcome = 'unhandled_error';
      response = Response.json({detail:'The game server could not respond. Try again shortly.'},{status:503});
    }
    outcome ||= response.headers.get('X-Game-Outcome') || (response.status >= 400 ? 'rejected' : 'completed');
    diagnosticLog({event:'game.request',request_id:requestId,
      route:diagnosticRoute(new URL(request.url).pathname),
      method:['GET','POST'].includes(request.method) ? request.method : 'OTHER',
      status:response.status,outcome,duration_ms:Date.now()-start,
      version:this.env.VERSION_METADATA?.id || 'unknown'});
    const responseHeaders = new Headers(response.headers);
    responseHeaders.set('X-Request-ID',requestId);
    return new Response(response.body,{status:response.status,headers:responseHeaders});
  }
  async handleRequest(request) {
    const path = new URL(request.url).pathname;
    const buildMatch = path.match(/^\/api\/builds\/([^/]+)$/);
    if (request.method === 'GET' && buildMatch) {
      if (!validId(buildMatch[1])) return Response.json({detail:'Invalid reference.'},{status:422});
      const job=await operate(this.ctx.storage,{operation:'build_status',id:buildMatch[1]});
      return job ? await buildStatus(this.ctx.storage,job,false,this.activeBuildId === buildMatch[1]) : Response.json({detail:'Build not found.'},{status:404});
    }
    if (path === '/_store') {
      if (request.headers.get('Authorization') !== `Bearer ${this.env.STORE_TOKEN}`) {
        return Response.json({detail:'Not found.'}, {status:404});
      }
      try {
        const input = await request.json();
        const result = await operate(this.ctx.storage, input);
        if (input.operation === 'build_progress' && result) {
          diagnosticLog({event:'build.progress',request_id:input.id,stage:input.stage});
        }
        if (input.operation === 'put' && input.kind === 'machine' && validId(input.request_id)) {
          diagnosticLog({event:'build.saved',request_id:input.request_id,machine_id:input.id});
        }
        return Response.json(result, {status:result === null ? 404 : 200});
      } catch {
        return Response.json({detail:'Storage operation failed.'}, {status:400});
      }
    }
    if (request.method === 'GET' && ['/api/leaderboard','/api/games','/api/arena'].includes(path)) {
      const query = new URL(request.url).searchParams;
      const offset = Number(query.get('offset') ?? 0);
      const limit = Number(query.get('limit') ?? 20);
      try {
        return Response.json(await operate(this.ctx.storage, {
          operation:path === '/api/arena' ? 'arena_games' : 'public_games', ranked:path === '/api/leaderboard', offset, limit,
        }));
      } catch {
        return Response.json({detail:'Use a valid page with between 1 and 50 games.'}, {status:422});
      }
    }
    const match = path.match(/^\/api\/(machines|replays)\/([^/]+)$/);
    if (request.method === 'GET' && match) {
      if (!validId(match[2])) return Response.json({detail:'Invalid identifier.'}, {status:422});
      const kind = match[1] === 'machines' ? 'machine' : 'replay';
      let result = await operate(this.ctx.storage, {operation:'get', kind, id:match[2]});
      if (result && kind === 'replay') {
        let reviewed = {};
        try { reviewed = JSON.parse(this.env.LOGFIRE_PUBLIC_TRACES || '{}'); } catch {}
        result = inspectLink(result, this.env.LOGFIRE_PROJECT_URL, reviewed || {});
      }
      return Response.json(result ?? {detail:'Record not found.'}, {status:result ? 200 : 404});
    }
    if (path === '/api/diagnostics' && request.method === 'POST') {
      let input;
      try { input = await request.json(); } catch { return new Response(null,{status:422}); }
      if (!validBrowserFailure(input)) return new Response(null,{status:422});
      diagnosticLog({event:'browser.failure',failed_request_id:input.request_id,
        operation:input.operation,failure:input.failure,status:input.status,untrusted:true,
        version:this.env.VERSION_METADATA?.id || 'unknown'});
      return new Response(null,{status:204});
    }
    if (request.method !== 'POST' || !['/api/machines','/api/challenges','/api/tournaments','/api/arena','/api/events'].includes(path)) {
      return Response.json({detail:'Not found.'}, {status:404});
    }
    if (path === '/api/events') {
      let input;
      try { input = await request.json(); } catch { return new Response(null,{status:422}); }
      if (!input || !['inspection_click','example_inspection_click','share_click'].includes(input.event) ||
          !validId(input.replay_id) || Object.keys(input).some(k=>!['event','replay_id'].includes(k))) {
        return new Response(null,{status:422});
      }
      if (!await this.ctx.storage.get('replay:'+input.replay_id)) return new Response(null,{status:404});
      // Worker logs preserve the funnel without starting a container for a click.
      diagnosticLog({event:input.event,replay_id:input.replay_id});
      return new Response(null,{status:204});
    }
    if (path === '/api/arena') {
      let input;
      try { input = await request.clone().json(); } catch { return new Response(null,{status:422}); }
      if (!input || !validId(input.machine_id) ||
          (input.referral != null && !validId(input.referral)) ||
          Object.keys(input).some(k=>!['machine_id','referral'].includes(k))) {
        return Response.json({detail:'Supply a player identifier.'},{status:422});
      }
      const saved = await operate(this.ctx.storage,{operation:'arena_entry',id:input.machine_id});
      if (saved) return Response.json(saved,{status:201,headers:{'X-Game-Outcome':'saved_entry'}});
    }
    let buildInput, fingerprint, buildId;
    if (path === '/api/machines') {
      try { buildInput=await request.clone().json(); } catch { /* Normal validation below. */ }
      if (buildInput?.preview === true) {
        buildId=request.headers.get('X-Request-ID');
        fingerprint=await inputFingerprint(buildInput);
        const existing=await operate(this.ctx.storage,{operation:'build_status',id:buildId});
        if (existing) {
          if (existing.fingerprint !== fingerprint) return Response.json({detail:'This reference belongs to a different build.'},{status:409});
          return buildStatus(this.ctx.storage,existing,true,this.activeBuildId === buildId);
        }
      }
    }
    const lifetime = await this.ctx.storage.get(path === '/api/machines' ?
      'lifetime:generation' : 'lifetime:challenge') || 0;
    if (lifetime >= (path === '/api/machines' ? MAX_GENERATIONS : MAX_CHALLENGES)) {
      return Response.json({detail:'The demonstration allowance is exhausted.'}, {status:429,headers:{'X-Game-Outcome':'lifetime_quota'}});
    }
    const kind = path === '/api/machines' ? 'generation' : 'challenge';
    const daily = await this.ctx.storage.get(`daily:${new Date().toISOString().slice(0,10)}:${kind}`) || 0;
    if (daily >= (kind === 'generation' ? DAILY_GENERATIONS : DAILY_CHALLENGES)) {
      return Response.json({detail:'The daily demonstration quota is exhausted.'}, {status:429,headers:{'X-Game-Outcome':'daily_quota'}});
    }
    if (this.busy) return Response.json({detail:'Another operation is running. Try again shortly.'}, {status:429,headers:{'X-Game-Outcome':'busy'}});
    let input;
    try { input = await request.clone().json(); } catch {
      return Response.json({detail:'Invalid request.'}, {status:422});
    }
    if (!input || typeof input !== 'object' || Array.isArray(input)) {
      return Response.json({detail:'Invalid request.'}, {status:422});
    }
    if (kind === 'generation') {
      if (typeof input.name !== 'string' || !input.name.trim() || input.name.length > 60 ||
          typeof input.strategy !== 'string' || !input.strategy.trim() || input.strategy.length > 1000 ||
          input.public_acknowledged !== true || (input.preview !== undefined && typeof input.preview !== 'boolean') ||
          (input.public_listing !== undefined && typeof input.public_listing !== 'boolean') || Object.keys(input).some(k=>!['name','strategy','public_acknowledged','preview','public_listing'].includes(k))) {
        return Response.json({detail:'Supply a name, strategy, and public record acknowledgement.'}, {status:422});
      }
    } else if (['/api/tournaments','/api/arena'].includes(path)) {
      if (!validId(input.machine_id) || Object.keys(input).some(k=>!['machine_id',...(path === '/api/arena' ? ['referral'] : [])].includes(k))) {
        return Response.json({detail:'Supply a player identifier.'}, {status:422});
      }
      if (!await this.ctx.storage.get('machine:'+input.machine_id)) {
        return Response.json({detail:'Player not found.'}, {status:404});
      }
    } else {
      if (!validId(input.left) || !validId(input.right) || (input.referral != null && !validId(input.referral)) || Object.keys(input).some(k=>!['left','right','referral'].includes(k))) {
        return Response.json({detail:'Supply two machine identifiers.'}, {status:422});
      }
      if (!await this.ctx.storage.get('machine:'+input.left) || !await this.ctx.storage.get('machine:'+input.right)) {
        return Response.json({detail:'Machine not found.'}, {status:404});
      }
    }
    // Recheck after asynchronous reads; only one execution may enter.
    if (this.busy) return Response.json({detail:'Another operation is running. Try again shortly.'},{status:429});
    this.busy = true;
    this.activeBuildId = buildId || null;
    try {
      if (buildId) {
        const claim=await operate(this.ctx.storage,{operation:'build_claim',id:buildId,fingerprint});
        if (!claim.created) {
          if (claim.job.fingerprint !== fingerprint) return Response.json({detail:'This reference belongs to a different build.'},{status:409});
          return buildStatus(this.ctx.storage,claim.job,true);
        }
        diagnosticLog({event:'build.started',request_id:buildId});
        request=new Request(request.url,{method:'POST',headers:request.headers,body:JSON.stringify(buildInput)});
      }
      // Record startup separately from application execution.
      const readyStart = Date.now();
      diagnosticLog({event:'container.wait',request_id:request.headers.get('X-Request-ID'),
        port_ready_timeout_ms:60000,version:this.env.VERSION_METADATA?.id || 'unknown'});
      await this.startAndWaitForPorts({ports:this.defaultPort,
        cancellationOptions:{abort:buildId ? undefined : request.signal,portReadyTimeoutMS:60000}});
      diagnosticLog({event:"container.ready",request_id:request.headers.get("X-Request-ID"),
        duration_ms:Date.now()-readyStart,version:this.env.VERSION_METADATA?.id || "unknown"});
      const response = await super.fetch(request);
      if (buildId && !response.ok) await operate(this.ctx.storage,{operation:'build_progress',id:buildId,stage:'failed'});
      if (!(response.headers.get('Content-Type') || '').includes('application/json')) {
        await response.body?.cancel();
        if (buildId) await operate(this.ctx.storage,{operation:'build_progress',id:buildId,stage:'failed'});
        return Response.json({detail:'The game server is starting. Try again shortly.'}, {status:503,headers:{'X-Game-Outcome':'invalid_container_response'}});
      }
      return response;
    } catch {
      // An unknown transport outcome stays recoverable. Never repeat generation.
      return Response.json({detail:'The game server connection was interrupted. Try again shortly.'},
        {status:503,headers:{'X-Game-Outcome':'container_connection'}});
    }
    finally { this.busy = false; this.activeBuildId = null; }
  }
}

export function diagnosticLog(record) {
  try { console.log(JSON.stringify(record)); } catch { /* Diagnostics never change results. */ }
}

export function diagnosticRoute(path) {
  if (/^\/api\/(machines|replays|builds)\/[^/]+$/.test(path)) return path.split('/').slice(0,3).join('/')+'/{id}';
  return ['/api/machines','/api/arena','/api/challenges','/api/tournaments','/api/events',
    '/api/diagnostics','/api/leaderboard','/api/games','/_store'].includes(path) ? path : 'unmatched';
}
export function validBrowserFailure(input) {
  return input && typeof input === 'object' && !Array.isArray(input) &&
    Object.keys(input).length === 4 && validId(input.request_id) &&
    ['create','arena','challenge','tournament','replay','read'].includes(input.operation) &&
    ['network','http','invalid_response'].includes(input.failure) &&
    Number.isInteger(input.status) && input.status >= 0 && input.status <= 599;
}

async function limitedBody(request, maxBytes) {
  const reader = request.body?.getReader();
  if (!reader) return new Uint8Array();
  const chunks = []; let total = 0;
  for (;;) {
    const {done, value} = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > maxBytes) { await reader.cancel(); return null; }
    chunks.push(value);
  }
  const result = new Uint8Array(total); let offset = 0;
  for (const chunk of chunks) { result.set(chunk,offset); offset += chunk.length; }
  return result;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let response;
    if (url.pathname.startsWith('/api/') || url.pathname === '/_store') {
      if (request.method === 'POST') {
        const maxBytes = url.pathname === '/_store' ? 420_000 : 8_192;
        const body = await limitedBody(request, maxBytes);
        if (body === null) return Response.json({detail:'Request too large.'}, {status:413});
        request = new Request(request, {body});
      }
      response = await env.GAME.getByName('public-v1').fetch(request);
    } else if (url.pathname === '/health') {
      response = Response.json({status:'ok'});
    } else if (request.method === 'GET' || request.method === 'HEAD') {
      if (url.pathname.startsWith('/static/')) url.pathname = url.pathname.slice(7);
      response = await env.ASSETS.fetch(new Request(url, request));
    } else response = new Response('Not found', {status:404});
    const headers = new Headers(response.headers);
    headers.set('X-Content-Type-Options','nosniff');
    headers.set('Referrer-Policy','same-origin');
    headers.set('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
    if (url.pathname.startsWith('/api/') || url.pathname === '/_store') headers.set('Cache-Control','no-store');
    return new Response(response.body, {status:response.status, headers});
  }
};


async function inputFingerprint(input) {
  const normalized={name:input.name,strategy:input.strategy,
    public_acknowledged:input.public_acknowledged,public_listing:input.public_listing ?? false,
    preview:input.preview};
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(normalized)));
  return [...new Uint8Array(digest)].map(byte=>byte.toString(16).padStart(2,'0')).join('');
}

async function buildStatus(storage,job,posting=false,finishing=false) {
  const headers={'Cache-Control':'no-store','X-Game-Outcome':job.stage === 'complete' ? 'build_complete' : 'build_pending'};
  if (job.stage === 'complete' && finishing) {
    headers['X-Game-Outcome']='build_pending';
    return Response.json({stage:'finishing'},{status:posting ? 202 : 200,headers});
  }
  if (job.stage === 'complete') {
    const machine=await operate(storage,{operation:'get',kind:'machine',id:job.machine_id});
    return Response.json({stage:'complete',machine},{status:posting ? 201 : 200,headers});
  }
  const stale=Date.now()-Date.parse(job.started_at) > 180000;
  const stage=job.stage === 'failed' ? 'failed' : stale ? 'interrupted' : job.stage;
  if (['failed','interrupted'].includes(stage)) headers['X-Game-Outcome']='build_'+stage;
  const detail=stage === 'failed' ? 'The build failed. Your description is saved. You can start a new attempt.' :
    stage === 'interrupted' ? 'This build has not completed. Keep its reference to check again. No automatic retry was made.' : undefined;
  return Response.json({stage,detail},{status:posting ? 202 : 200,headers});
}
