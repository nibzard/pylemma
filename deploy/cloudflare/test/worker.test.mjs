import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

// Replace only the external container runtime. Exercise the actual Worker routes.
let source = await readFile(new URL('../worker.js',import.meta.url),'utf8');
source = source.replace("import { Container } from '@cloudflare/containers';",`
class Container {
  constructor(ctx,env) { this.ctx=ctx; this.env=env; this.starts=0; }
  async fetch() { this.starts++; return Response.json({forwarded:true}); }
}`);
for (const file of ['storage.mjs','trace-links.mjs']) {
  source=source.replace(`'./${file}'`,JSON.stringify(new URL('../'+file,import.meta.url).href));
}
const {Pylemma} = await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const id='00000000-0000-0000-0000-000000000001';
const replay='00000000-0000-0000-0000-000000000002';
const request=(path,body)=>new Request('https://example.test'+path,body ? {
  method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),
}:{});

test('stored arena retry bypasses exhausted quota and container startup',async()=>{
  const records=new Map([['arena:'+id,replay],['replay:'+replay,{kind:'arena',result:{total:273}}],
    ['lifetime:challenge',1600]]);
  const worker=new Pylemma({storage:{get:async key=>records.get(key)}},{});
  const response=await worker.fetch(request('/api/arena',{machine_id:id}));
  assert.equal(response.status,201);
  assert.equal((await response.json()).replay_id,replay);
  assert.equal(worker.starts,0);
});

test('arena reads and invalid requests never start the container',async()=>{
  const worker=new Pylemma({storage:{get:async()=>null,list:async()=>new Map()}},{});
  assert.equal((await worker.fetch(request('/api/arena'))).status,200);
  assert.equal((await worker.fetch(request('/api/arena?limit=51'))).status,422);
  assert.equal((await worker.fetch(request('/api/arena',{machine_id:'bad'}))).status,422);
  assert.equal((await worker.fetch(request('/api/events',{event:'unknown',replay_id:replay}))).status,422);
  assert.equal((await worker.fetch(request('/api/events',{event:'share_click',replay_id:replay}))).status,404);
  assert.equal(worker.starts,0);
});

test('new arena entry forwards only after validating the stored player',async()=>{
  const worker=new Pylemma({storage:{get:async key=>key === 'machine:'+id ? {id} : null}},{});
  const response=await worker.fetch(request('/api/arena',{machine_id:id}));
  assert.equal(response.status,200);
  assert.equal(worker.starts,1);
});

test('diagnostics correlate safe routes and reject extra browser fields',async(t)=>{
  const logs=[];
  t.mock.method(console,'log',line=>logs.push(JSON.parse(line)));
  const worker=new Pylemma({storage:{get:async()=>null,list:async()=>new Map()}},{VERSION_METADATA:{id:'release-test'}});
  const req=new Request('https://example.test/api/replays/'+id+'?secret=PRIVATE',{
    headers:{'X-Request-ID':id,'Authorization':'PRIVATE'}});
  const response=await worker.fetch(req);
  assert.equal(response.headers.get('X-Request-ID'),id);
  assert.equal(logs[0].request_id,id);
  assert.equal(logs[0].route,'/api/replays/{id}');
  assert.equal(logs[0].status,404);
  assert.equal(logs[0].version,'release-test');
  assert.ok(!JSON.stringify(logs).includes('PRIVATE'));
  const report={request_id:id,operation:'create',failure:'network',status:0};
  assert.equal((await worker.fetch(request('/api/diagnostics',report))).status,204);
  assert.ok(logs.some(row=>row.event === 'browser.failure' && row.failed_request_id === id && row.untrusted));
  assert.equal((await worker.fetch(request('/api/diagnostics',{...report,message:'PRIVATE'}))).status,422);
  assert.equal(worker.starts,0);
});

test('quota diagnostics distinguish rejection without starting a container',async(t)=>{
  const logs=[];
  t.mock.method(console,'log',line=>logs.push(JSON.parse(line)));
  const worker=new Pylemma({storage:{get:async key=>key === 'lifetime:challenge' ? 1600 : null}},{});
  const response=await worker.fetch(request('/api/challenges',{left:id,right:replay}));
  assert.equal(response.status,429);
  assert.equal(logs[0].outcome,'lifetime_quota');
  assert.equal(worker.starts,0);
});

test('failed diagnostic logging does not change the response',async(t)=>{
  t.mock.method(console,'log',()=>{throw new Error('log unavailable');});
  const worker=new Pylemma({storage:{list:async()=>new Map()}},{});
  assert.equal((await worker.fetch(request('/api/arena'))).status,200);
});

test('container lifecycle records exit codes without raw errors',async(t)=>{
  const logs=[];
  t.mock.method(console,'log',line=>logs.push(JSON.parse(line)));
  const worker=new Pylemma({storage:{}},{VERSION_METADATA:{id:'release-test'}});
  worker.onStart();
  worker.onStop({exitCode:137,reason:'exit'});
  const error=new Error('PRIVATE');
  assert.throws(()=>worker.onError(error),value=>value === error);
  assert.equal(logs[0].event,'container.started');
  assert.equal(logs[1].exit_code,137);
  assert.equal(logs[2].event,'container.error');
  assert.ok(logs.every(row=>row.version === 'release-test'));
  assert.ok(!JSON.stringify(logs).includes('PRIVATE'));
});

test('idle expiry preserves a request waiting for container startup',async(t)=>{
  t.mock.method(console,'log',()=>{});
  const worker=new Pylemma({storage:{get:async key=>key === 'machine:'+id ? {id} : null}},{});
  let release,start;
  const started=new Promise(resolve=>{start=resolve;});
  t.mock.method(Object.getPrototypeOf(Pylemma.prototype),'fetch',async()=>{
    start();
    return new Promise(resolve=>{release=()=>resolve(Response.json({forwarded:true}));});
  });
  let destroyed=0,renewed=0;
  worker.destroy=async()=>{destroyed++;};
  worker.renewActivityTimeout=()=>{renewed++;};
  const pending=worker.fetch(request('/api/arena',{machine_id:id}));
  await started;
  await worker.onActivityExpired();
  assert.equal(destroyed,0);
  assert.equal(renewed,1);
  release();
  assert.equal((await pending).status,200);
  await worker.onActivityExpired();
  assert.equal(destroyed,1);
});
