# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
class CDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary=os.environ.get("TRITON_C_BINARY")
        if not cls.binary:raise unittest.SkipTest("Set TRITON_C_BINARY to enable compiled C CLI regression tests")
    def run_source(self,data):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"input";p.write_bytes(data)
            return subprocess.run([self.binary,"jovial",str(p)],capture_output=True,text=True)
    def test_valid_and_demo_label(self):
        r=self.run_source(b"VALUE := 1;");self.assertEqual(r.returncode,0);self.assertIn("fixed IR demonstration",r.stdout)
    def test_invalid_inputs_fail(self):
        for data in (b"@",b'"unfinished',b"9"*100,b"a\x00b",b"x"*1048577):
            with self.subTest(data=data[:20]):self.assertNotEqual(self.run_source(data).returncode,0)
    def test_unknown_dialect_and_version(self):
        self.assertNotEqual(subprocess.run([self.binary,"other","missing"],capture_output=True).returncode,0)
        self.assertIn("0.2.0",subprocess.check_output([self.binary,"--version"],text=True))
