'use strict';

// These tests reject input before Playwright loads. No browser or provider calls.
const assert = require('node:assert/strict');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const test = require('node:test');

const script = path.resolve(__dirname, '../scripts/live-voice-check.cjs');
const token = 'synthetic-capability-fixture-12345';
const marker = 'SYNTHETIC_PRIVATE_MARKER_DO_NOT_ECHO';
const validShape = {base: 'http://127.0.0.1:12345', token, mode: 'smoke'};

function rejected(input, expected = 'invalid_input') {
  const child = spawnSync(process.execPath, [script], {
    input, encoding: 'utf8', timeout: 5000, maxBuffer: 16 * 1024,
    env: {}, // Never inherit keys, Playwright debug flags or NODE_OPTIONS.
  });
  assert.equal(child.error, undefined);
  assert.equal(child.signal, null);
  assert.equal(child.status, 1);
  assert.equal(child.stderr, '');
  assert.equal(child.stdout.trim().split('\n').length, 1);
  assert.ok(!child.stdout.includes(token));
  assert.ok(!child.stdout.includes(marker));
  const result = JSON.parse(child.stdout);
  assert.deepEqual(result, {
    provider_hangup_ack: false,
    ok: false, mode: 'smoke', phase: 'input', error_code: expected,
    cleanup: true, browser_cleanup: true,
  });
}

test('missing stdin returns one sanitized result', () => rejected('', 'missing_input'));

test('malformed and oversized input never echo contents', () => {
  for (const value of ['\n', marker + '\n', '{"secret":"' + marker + '"\n', 'x'.repeat(4097) + '\n']) {
    rejected(value);
  }
});

test('only the exact object shape and supported mode are accepted', () => {
  for (const value of [null, [], 42, marker, {}, {base: validShape.base},
    {...validShape, extra: marker}, {...validShape, mode: marker},
    {...validShape, base: [validShape.base]}, {...validShape, base: 12345}]) {
    rejected(JSON.stringify(value) + '\n');
  }
});

test('URL validation rejects external hosts and ambiguous local destinations', () => {
  for (const base of [
    'https://example.invalid/' + marker,
    'https://127.0.0.1:12345',
    'http://localhost:12345',
    'http://127.0.0.1',
    'http://user:synthetic@127.0.0.1:12345',
    'http://127.0.0.1:12345/private',
    'http://127.0.0.1:12345?secret=' + marker,
    'http://127.0.0.1:12345#' + marker,
    marker,
  ]) rejected(JSON.stringify({...validShape, base}) + '\n');
});

test('capability validation rejects missing, short, long and unsafe tokens', () => {
  for (const invalid of [null, 42, '', 'short', 's'.repeat(257), marker + ' ', marker + '\n']) {
    rejected(JSON.stringify({...validShape, token: invalid}) + '\n');
  }
});
