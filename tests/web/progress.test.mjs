import {test} from 'node:test';
import assert from 'node:assert/strict';
import {requestStage,requestError} from '../../src/pylemma/web/static/progress.mjs';

test('progress follows actual request boundaries',()=>{
  assert.equal(requestStage('/api/machines','POST'),0);
  assert.equal(requestStage('/api/arena','POST'),1);
  assert.equal(requestStage('/api/challenges','POST'),1);
  assert.equal(requestStage('/api/replays/id','GET'),2);
  assert.equal(requestStage('/api/arena','GET'),null);
});
test('network failures explain how to recover without exposing browser errors',()=>{
  assert.match(requestError('/api/machines',0),/description is still here/);
  assert.match(requestError('/api/arena',0),/player is saved/);
  assert.match(requestError('/api/replays/id',0),/Reload this page/);
  assert.match(requestError('/api/machines',502),/connection/);
  assert.equal(requestError('/api/machines',429,'The quota is exhausted.'),'The quota is exhausted.');
  assert.match(requestError('/api/replays/id',404),/Check the link/);
});

test('browser reports omit URLs, descriptions, and raw exception text',async()=>{
  const {failureReport} = await import('../../src/pylemma/web/static/progress.mjs');
  assert.deepEqual(failureReport('/api/replays/private-id?secret=private','00000000-0000-0000-0000-000000000001','network',0),{
    request_id:'00000000-0000-0000-0000-000000000001',operation:'replay',failure:'network',status:0});
});
