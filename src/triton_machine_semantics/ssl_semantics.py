# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.

"""SSL-style semantic descriptions: parse RTL-like assignments into effect lists.
Publicly reconstructable subset based on UQBT RTL model: location := expression.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
import re

@dataclass
class RTLEffect:
    location: str
    expr: str

@dataclass
class SSLInstr:
    name: str
    effects: List[RTLEffect] = field(default_factory=list)

def parse_ssl(text: str) -> List[SSLInstr]:
    """Parse lines like:  instr ADD { r[rd] := r[rs1] + r[rs2]; pc := pc + 4; }"""
    out=[]
    for m in re.finditer(r'instr\s+(\w+)\s*\{(.*?)\}', text, re.S|re.I):
        name, body = m.group(1), m.group(2)
        effs=[]
        for stmt in body.split(';'):
            stmt=stmt.strip()
            if not stmt: continue
            mm=re.match(r'(.+?)\s*:=\s*(.+)', stmt)
            if mm:
                effs.append(RTLEffect(mm.group(1).strip(), mm.group(2).strip()))
        out.append(SSLInstr(name,effs))
    return out

def ssl_to_pcode_like(instr: SSLInstr) -> List[Dict]:
    """Lower SSL effects to generic three-address pseudo-ops (documented mapping)."""
    ops=[]
    for e in instr.effects:
        ops.append({"dst": e.location, "expr": e.expr})
    return ops
