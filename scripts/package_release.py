# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.
"""Create a platform source/CLI archive with provenance and checksums."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import zipfile
root=Path(__file__).resolve().parents[1]
artifacts=root/"artifacts";artifacts.mkdir(exist_ok=True)
binary=next((p for p in [root/"build/Release/triton-agent1.exe",root/"build/triton-agent1.exe",root/"build/triton-agent1"] if p.exists()),None)
if binary is None: raise SystemExit("Build the C executable first")
name=f"triton-agent1-0.2.0-{platform.system().lower()}-{platform.machine().lower()}.zip"
files=[binary,root/"include/triton_agent1.h",root/"LICENSE",root/"GOVERNANCE.md",root/"README.md"]
commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
manifest={"version":"0.2.0","commit":commit,"platform":platform.platform(),"sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
with zipfile.ZipFile(artifacts/name,"w",zipfile.ZIP_DEFLATED) as output:
    for p in files: output.write(p,p.name)
    output.writestr("manifest.json",json.dumps(manifest,indent=2)+"\n")
print(artifacts/name)
