import { Container } from '@cloudflare/containers';
import { operate, validId } from './storage.mjs';

export class Pylemma extends Container {
  defaultPort = 8080;
  sleepAfter = '30s';
  envVars;
  busy = false;
  constructor(ctx, env) {
    super(ctx, env);
    this.envVars = {
      OPENAI_API_KEY: env.OPENAI_API_KEY,
      LOGFIRE_TOKEN: env.LOGFIRE_TOKEN,
      LOGFIRE_BASE_URL: env.LOGFIRE_BASE_URL,
      PYLEMMA_DAILY_GENERATIONS: '20',
      PYLEMMA_STORE_URL: 'https://pylemma.aor.fyi',
      PYLEMMA_STORE_TOKEN: env.STORE_TOKEN,
    };
  }
  async onActivityExpired() {
    await this.destroy();
  }
  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (path === '/_store') {
      if (request.headers.get('Authorization') !== `Bearer ${this.env.STORE_TOKEN}`) {
        return Response.json({detail:'Not found.'}, {status:404});
      }
      try {
        const input = await request.json();
        const result = await operate(this.ctx.storage, input);
        return Response.json(result, {status:result === null ? 404 : 200});
      } catch {
        return Response.json({detail:'Storage operation failed.'}, {status:400});
      }
    }
    const match = path.match(/^\/api\/(machines|replays)\/([^/]+)$/);
    if (request.method === 'GET' && match) {
      if (!validId(match[2])) return Response.json({detail:'Invalid identifier.'}, {status:422});
      const kind = match[1] === 'machines' ? 'machine' : 'replay';
      const result = await operate(this.ctx.storage, {operation:'get', kind, id:match[2]});
      return Response.json(result ?? {detail:'Record not found.'}, {status:result ? 200 : 404});
    }
    if (request.method !== 'POST' || !['/api/machines','/api/challenges','/api/tournaments'].includes(path)) {
      return Response.json({detail:'Not found.'}, {status:404});
    }
    const lifetime = await this.ctx.storage.get(path === '/api/machines' ?
      'lifetime:generation' : 'lifetime:challenge') || 0;
    if (lifetime >= (path === '/api/machines' ? 80 : 1600)) {
      return Response.json({detail:'The demonstration allowance is exhausted.'}, {status:429});
    }
    const kind = path === '/api/machines' ? 'generation' : 'challenge';
    const daily = await this.ctx.storage.get(`daily:${new Date().toISOString().slice(0,10)}:${kind}`) || 0;
    if (daily >= (kind === 'generation' ? 20 : 400)) {
      return Response.json({detail:'The daily demonstration quota is exhausted.'}, {status:429});
    }
    if (this.busy) return Response.json({detail:'Another operation is running. Try again shortly.'}, {status:429});
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
          input.public_acknowledged !== true || (input.preview !== undefined && typeof input.preview !== 'boolean') || Object.keys(input).some(k=>!['name','strategy','public_acknowledged','preview'].includes(k))) {
        return Response.json({detail:'Supply a name, strategy, and public record acknowledgement.'}, {status:422});
      }
    } else if (path === '/api/tournaments') {
      if (!validId(input.machine_id) || Object.keys(input).some(k=>k !== 'machine_id')) {
        return Response.json({detail:'Supply a player identifier.'}, {status:422});
      }
      if (!await this.ctx.storage.get('machine:'+input.machine_id)) {
        return Response.json({detail:'Player not found.'}, {status:404});
      }
    } else {
      if (!validId(input.left) || !validId(input.right) || Object.keys(input).some(k=>!['left','right'].includes(k))) {
        return Response.json({detail:'Supply two machine identifiers.'}, {status:422});
      }
      if (!await this.ctx.storage.get('machine:'+input.left) || !await this.ctx.storage.get('machine:'+input.right)) {
        return Response.json({detail:'Machine not found.'}, {status:404});
      }
    }
    this.busy = true;
    try {
      const response = await super.fetch(request);
      if (!(response.headers.get('Content-Type') || '').includes('application/json')) {
        await response.body?.cancel();
        return Response.json({detail:'The game server is starting. Try again shortly.'}, {status:503});
      }
      return response;
    }
    finally { this.busy = false; }
  }
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
        const maxBytes = url.pathname === '/_store' ? 120_000 : 8_192;
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
