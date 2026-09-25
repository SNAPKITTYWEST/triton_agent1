// SPDX-License-Identifier: MPL-2.0
// Copyright (c) 2026 the Trust (see GOVERNANCE.md)
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. See https://mozilla.org/MPL/2.0/.
// Network administration authority is governed separately; see GOVERNANCE.md.
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';
function run(args, extraEnv = {}) {
  return spawnSync(process.execPath, ['npm/cli.mjs', ...args], {
    encoding: 'utf8',
    env: { ...process.env, PYTHONPATH: resolve('src'), ...extraEnv }
  });
}
test('Python CLI bridge forwards arguments and output', () => {
  const result = run(['forth', '3 4 + 2 *']);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), '[14]');
});
test('bridge preserves CLI failure', () => {
  assert.notEqual(run(['not-a-command']).status, 0);
});
test('missing interpreter gives contact information', () => {
  const result = run(['--version'], { TRITON_PYTHON: resolve('missing-interpreter') });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /a\.parr@belespritdaccord\.uk/);
});
