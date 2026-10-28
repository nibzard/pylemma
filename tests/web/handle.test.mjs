import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeHandle} from '../../src/pylemma/web/static/handle.mjs';

test('adds the handle prefix only when it is missing', () => {
  assert.equal(normalizeHandle('alice'), '@alice');
  assert.equal(normalizeHandle('@alice'), '@alice');
  assert.equal(normalizeHandle(normalizeHandle('alice')), '@alice');
});

test('trims surrounding spaces without turning empty input into a handle', () => {
  assert.equal(normalizeHandle(' alice '), '@alice');
  assert.equal(normalizeHandle(' @alice '), '@alice');
  assert.equal(normalizeHandle('   '), '');
  assert.equal(normalizeHandle(''), '');
});
