import { test } from 'node:test';
import assert from 'node:assert/strict';
import { inspectLink } from '../trace-links.mjs';
const trace='01a18279f80e04757e90f2b753321bc4';
const project='https://logfire-eu.pydantic.dev/nibzard/starter-project/';
const publicUrl='https://logfire-eu.pydantic.dev/public-trace/example';

test('account links filter the exact trace and apply the game time window',()=>{
  const data={trace_id:trace,created_at:'2026-10-28T12:26:35+00:00'};
  const result=inspectLink(data,project);
  assert.equal(result.logfire_access,'account');
  const url=new URL(result.logfire_url);
  assert.equal(url.searchParams.get('q'),`trace_id='${trace}'`);
  assert.equal(url.searchParams.get('since'),'2026-10-28T11:26:35.000Z');
  assert.equal(url.searchParams.get('until'),'2026-10-28T13:26:35.000Z');
  assert.equal(data.logfire_url,undefined);
});
test('only a reviewed reference produces a public access label',()=>{
  assert.equal(inspectLink({trace_id:trace},project,{[trace]:publicUrl}).logfire_access,'public');
  const result=inspectLink({trace_id:trace,public_trace_url:publicUrl},project);
  assert.equal(result.logfire_url,publicUrl);
  assert.equal(result.logfire_access,'public');
  assert.equal(inspectLink({trace_id:trace,public_trace_url:'javascript:alert(1)'},project).logfire_access,'account');
});
test('invalid configuration and absent trace identifiers do not create links',()=>{
  for (const url of ['javascript:alert(1)','https://example.com/a/b',project+'?token=secret',
    'https://logfire-eu.pydantic.dev:443/a/b',project+'\n',project+'%20']) {
    assert.equal(inspectLink({trace_id:trace},url).logfire_access,'unavailable');
  }
  assert.equal(inspectLink({},project).logfire_url,null);
  assert.equal(inspectLink({trace_id:"' OR true"},project).logfire_url,null);
});
test('preserves a verified span highlight while rejecting extra parameters',()=>{
  const url='https://logfire-eu.pydantic.dev/public-trace/44e57f30-c25a-47fe-b85f-5db1d0604010?spanId=4ed36f7dff63d8fe';
  assert.equal(inspectLink({trace_id:trace},project,{[trace]:url}).logfire_url,url);
  assert.equal(inspectLink({trace_id:trace},project,{[trace]:url}).logfire_access,'public');
  for (const suffix of ['&redirect=https://example.com','&spanId=0000000000000000','#fragment']) {
    assert.equal(inspectLink({trace_id:trace},project,{[trace]:url+suffix}).logfire_access,'account');
  }
});
