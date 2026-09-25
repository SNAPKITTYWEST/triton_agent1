# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.
"""Install and smoke-test the built wheel away from source paths."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv
root=Path(__file__).resolve().parents[1]
wheel=next((root/"dist").glob("*.whl"))
with tempfile.TemporaryDirectory() as folder:
    envroot=Path(folder)/"env";venv.EnvBuilder(with_pip=True).create(envroot)
    binary=envroot/("Scripts/python.exe" if os.name=="nt" else "bin/python")
    env={k:v for k,v in os.environ.items() if k!="PYTHONPATH"}
    subprocess.run([str(binary),"-m","pip","install","--no-deps",str(wheel)],check=True,env=env,cwd=folder)
    subprocess.run([str(binary),"-I","-c","import triton_machine_semantics as p; assert p.__version__ == '0.2.0'; from triton_machine_semantics.ssl_semantics import parse_ssl"],check=True,env=env,cwd=folder)
    result=subprocess.check_output([str(binary),"-I","-m","triton_machine_semantics","forth","3 4 + 2 *"],env=env,cwd=folder,text=True)
    assert result.strip()=="[14]",result
print("Isolated wheel install and CLI passed.")
