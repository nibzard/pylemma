import {test} from 'node:test';
import assert from 'node:assert/strict';
import {buildPlayer} from '../../src/pylemma/web/static/build.mjs';

test('recovers a lost response with one submission and actual stages',async()=>{
  let posts=0, polls=0, clock=0;
  const stages=[], reference='reference';
  const fetcher=async(path,options)=>{
    if (path === '/api/machines') { posts++; assert.equal(options.headers['X-Request-ID'],reference); throw new Error('lost'); }
    assert.equal(path,'/api/builds/reference');
    polls++;
    return Response.json(polls === 1 ? {stage:'checking'} : {stage:'complete',machine:{id:'saved'}});
  };
  const result=await buildPlayer({name:'@x'},{requestId:reference,fetcher,
    onStage:stage=>stages.push(stage),delay:async()=>{clock+=1000;},now:()=>clock});
  assert.equal(result.machine.id,'saved');
  assert.equal(posts,1);
  assert.deepEqual(stages,['connecting','checking','complete']);
});

test('resuming a build never submits or consumes another generation',async()=>{
  const result=await buildPlayer({},{
    requestId:'saved',start:false,fetcher:async path=>{
      assert.equal(path,'/api/builds/saved');
      return Response.json({stage:'complete',machine:{id:'saved'}});
    },
  });
  assert.equal(result.machine.id,'saved');
});

test('uncertain builds retain recovery while confirmed failures allow a new attempt',async()=>{
  for (const stage of ['failed','interrupted']) {
    await assert.rejects(buildPlayer({},{
      requestId:'saved',start:false,
      fetcher:async()=>Response.json({stage,detail:'Build stopped.'}),
    }), error=>error.recoverable === (stage === 'interrupted') && error.message.includes('saved'));
  }
});

test('poll timeout preserves the reference without resubmitting',async()=>{
  let clock=0, posts=0;
  await assert.rejects(buildPlayer({},{
    requestId:'saved',timeoutMs:2,now:()=>clock,delay:async()=>{clock+=3;},
    fetcher:async path=>{
      if (path === '/api/machines') {posts++; throw new Error('offline');}
      return Response.json({}, {status:404});
    },
  }),error=>error.recoverable && error.message.includes('saved'));
  assert.equal(posts,1);
});
