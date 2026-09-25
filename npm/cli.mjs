#!/usr/bin/env node
// SPDX-License-Identifier: MPL-2.0
// Copyright (c) 2026 the Trust (see GOVERNANCE.md)
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. See https://mozilla.org/MPL/2.0/.
// Network administration authority is governed separately; see GOVERNANCE.md.
import { spawnSync } from 'node:child_process';
const python = process.env.TRITON_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const result = spawnSync(python, ['-m', 'triton_machine_semantics', ...process.argv.slice(2)], {
  stdio: 'inherit',
  shell: false
});
if (result.error) {
  console.error('Unable to start Python. Install Python 3.10+ and triton-machine-semantics with pip, or set TRITON_PYTHON to the Python executable.');
  console.error('Support: a.parr@belespritdaccord.uk');
  process.exitCode = 1;
} else {
  process.exitCode = result.status ?? 1;
}
