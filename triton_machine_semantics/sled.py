# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.

"""SLED subset: fields, tokens, patterns, constructors for encode/decode."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import re

@dataclass
class SledField:
    name: str; msb: int; lsb: int
@dataclass
class SledToken:
    name: str; bits: int; fields: List[SledField] = field(default_factory=list)
@dataclass
class SledPattern:
    name: str; constraints: Dict[str,int] = field(default_factory=dict)
@dataclass
class SledConstructor:
    name: str; pattern: str; operands: List[str] = field(default_factory=list)
@dataclass
class SledSpec:
    tokens: Dict[str,SledToken] = field(default_factory=dict)
    patterns: Dict[str,SledPattern] = field(default_factory=dict)
    constructors: List[SledConstructor] = field(default_factory=list)

def parse_sled(text: str) -> SledSpec:
    spec = SledSpec()
    # tokens: token NAME(BITS) [ f=(msb,lsb), ... ]
    for m in re.finditer(r'token\s+(\w+)\s*\((\d+)\)\s*\[([^\]]*)\]', text, re.I):
        name, bits, body = m.group(1), int(m.group(2)), m.group(3)
        fs=[]
        for fm in re.finditer(r'(\w+)\s*=\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', body):
            fs.append(SledField(fm.group(1), int(fm.group(2)), int(fm.group(3))))
        spec.tokens[name]=SledToken(name,bits,fs)
    # patterns: pattern NAME is FIELD=val & ...
    for m in re.finditer(r'pattern\s+(\w+)\s+is\s+([^\n;]+)', text, re.I):
        name, body = m.group(1), m.group(2)
        cons={}
        for cm in re.finditer(r'(\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+)', body):
            v=cm.group(2); cons[cm.group(1)]=int(v,16) if v.startswith('0x') else int(v)
        spec.patterns[name]=SledPattern(name,cons)
    # constructors: constructor NAME(PAT, ops)
    for m in re.finditer(r'constructor\s+(\w+)\s*\(\s*(\w+)\s*((?:,\s*\w+\s*)*)\)', text, re.I):
        name, pat, ops = m.group(1), m.group(2), m.group(3)
        operands=[o.strip() for o in ops.split(',') if o.strip()]
        spec.constructors.append(SledConstructor(name,pat,operands))
    return spec

def sled_decode(spec: SledSpec, word: int) -> Optional[SledConstructor]:
    # find token fields
    fields: Dict[str,int]={}
    for t in spec.tokens.values():
        for f in t.fields:
            w=abs(f.msb-f.lsb)+1; lo=min(f.msb,f.lsb)
            fields[f.name]=(word>>lo)&((1<<w)-1)
    for c in spec.constructors:
        pat=spec.patterns.get(c.pattern)
        if pat is None: continue
        if all(fields.get(k)==v for k,v in pat.constraints.items()):
            return c
    return None
