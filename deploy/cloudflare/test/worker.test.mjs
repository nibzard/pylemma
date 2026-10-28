import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

// Replace only the external container runtime. Exercise the actual Worker routes.
let source = await readFile(new URL('../worker.js',import.meta.url),'utf8');
source = source.replace("import { Container } from '@cloudflare/containers';",`
class Container {
  constructor(ctx,env) { this.ctx=ctx; this.env=env; this.starts=0; }
  async startAndWaitForPorts() {}
  async fetch(request) { this.starts++; return this.forward ? this.forward(request) : Response.json({forwarded:true}); }
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

test('new arena entry forwards only after validating the stored player',async(t)=>{
  const logs=[];
  t.mock.method(console,'log',line=>logs.push(JSON.parse(line)));
  const worker=new Pylemma({storage:{get:async key=>key === 'machine:'+id ? {id} : null}},{});
  const response=await worker.fetch(request('/api/arena',{machine_id:id}));
  assert.equal(response.status,200);
  assert.equal(worker.starts,1);
  const ready=logs.find(row=>row.event === 'container.ready');
  assert.ok(ready);
  assert.equal(ready.request_id,response.headers.get('X-Request-ID'));
  assert.ok(ready.duration_ms >= 0);
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
  assert.equal(logs[2].failure,'other');
  assert.throws(()=>worker.onError(new Error('Container crashed while checking for ports PRIVATE')));
  assert.equal(logs[3].failure,'startup_exit');
  assert.throws(()=>worker.onError(new Error('Failed to verify port 8080 PRIVATE')));
  assert.equal(logs[4].failure,'port_deadline');
  assert.ok(logs.every(row=>row.version === 'release-test'));
  assert.ok(!JSON.stringify(logs).includes('PRIVATE'));
});

test('idle expiry preserves a request waiting for container startup',async(t)=>{
  t.mock.method(console,'log',()=>{});
  const worker=new Pylemma({storage:{get:async key=>key === 'machine:'+id ? {id} : null}},{});
  let release,start;
  const started=new Promise(resolve=>{start=resolve;});
  t.mock.method(Object.getPrototypeOf(Pylemma.prototype),'startAndWaitForPorts',async options=>{
    assert.equal(options.ports,8080);
    assert.equal(options.cancellationOptions.portReadyTimeoutMS,60000);
    assert.ok(options.cancellationOptions.abort instanceof AbortSignal);
    start();
    return new Promise(resolve=>{release=resolve;});
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


test('generation admission agrees with the new daily and lifetime limits',async(t)=>{
  t.mock.method(console,'log',()=>{});
  const day=new Date().toISOString().slice(0,10);
  const records=new Map([['daily:'+day+':generation',99],['lifetime:generation',99]]);
  const worker=new Pylemma({storage:{get:async key=>records.get(key)}},{});
  const input={name:'Test',strategy:'Cooperate',public_acknowledged:true};
  assert.equal(worker.envVars.PYLEMMA_DAILY_GENERATIONS,'100');
  assert.equal((await worker.fetch(request('/api/machines',input))).status,200);
  records.set('daily:'+day+':generation',100);
  assert.equal((await worker.fetch(request('/api/machines',input))).status,429);
  records.set('daily:'+day+':generation',0);
  records.set('lifetime:generation',400);
  assert.equal((await worker.fetch(request('/api/machines',input))).status,429);
  assert.equal(worker.starts,1);
});

test('lost build responses recover without starting again or checking quota',async()=>{
  const records=new Map();
  const storage={get:async key=>structuredClone(records.get(key)),
    put:async(key,value)=>records.set(key,structuredClone(value)),
    transaction:async fn=>fn(storage)};
  const waits=[];
  const worker=new Pylemma({storage,waitUntil:work=>waits.push(work)},{});
  const body={name:'@test',strategy:'Cooperate',public_acknowledged:true,preview:true};
  const make=(value=body)=>new Request('https://example.test/api/machines',{
    method:'POST',headers:{'Content-Type':'application/json','X-Request-ID':id},body:JSON.stringify(value)});
  await worker.fetch(make());
  assert.equal(worker.starts,1);
  // The simulated original transport returned without committing a machine.
  const pending=await worker.fetch(make());
  assert.equal(pending.status,202);
  assert.equal(worker.starts,1);
  const changed=await worker.fetch(make({...body,strategy:'Betray'}));
  assert.equal(changed.status,409);
  const job=records.get('build:'+id);
  records.set('build:'+id,{...job,stage:'complete',machine_id:replay});
  records.set('machine:'+replay,{id:replay,name:'@test'});
  records.set('lifetime:generation',400);
  const recovered=await worker.fetch(make());
  assert.equal(recovered.status,201);
  assert.equal((await recovered.json()).machine.id,replay);
  assert.equal(worker.starts,1);
  const status=await worker.fetch(request('/api/builds/'+id));
  const data=await status.json();
  assert.equal(data.stage,'complete');
  assert.equal(data.fingerprint,undefined);
  assert.equal(status.headers.get('Cache-Control'),'no-store');
  assert.ok(waits.length > 0);
});

test('interrupted builds keep their references and never restart automatically',async()=>{
  const worker=new Pylemma({storage:{get:async key=>key === 'build:'+id ?
    {stage:'generating',started_at:'2000-01-01T00:00:00Z'} : null}},{});
  const response=await worker.fetch(request('/api/builds/'+id));
  assert.equal((await response.json()).stage,'interrupted');
  assert.equal(worker.starts,0);
});

test('disconnect does not abort admitted work and saved builds wait for the execution slot',async()=>{
  const {operate}=await import('../storage.mjs');
  const records=new Map();
  const storage={get:async key=>structuredClone(records.get(key)),
    put:async(key,value)=>records.set(key,structuredClone(value)),
    transaction:async fn=>fn(storage)};
  const worker=new Pylemma({storage,waitUntil:()=>{}},{});
  let started,release;
  const admitted=new Promise(resolve=>{started=resolve;});
  const finish=new Promise(resolve=>{release=resolve;});
  let forwarded;
  worker.forward=async req=>{
    forwarded=req;
    await operate(storage,{operation:'put',kind:'machine',id:replay,
      data:{id:replay,name:'@saved'},request_id:id});
    started();
    await finish;
    return Response.json({machine:{id:replay,name:'@saved'}},{status:201});
  };
  const controller=new AbortController();
  const original=worker.fetch(new Request('https://example.test/api/machines',{
    method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json','X-Request-ID':id},
    body:JSON.stringify({name:'@saved',strategy:'Cooperate',preview:true,public_acknowledged:true})}));
  await admitted;
  controller.abort();
  assert.equal(forwarded.signal.aborted,false);
  const pending=await worker.fetch(request('/api/builds/'+id));
  assert.equal((await pending.json()).stage,'finishing');
  release();
  assert.equal((await original).status,201);
  const complete=await worker.fetch(request('/api/builds/'+id));
  assert.equal((await complete.json()).machine.id,replay);
  assert.equal(worker.starts,1);
});
