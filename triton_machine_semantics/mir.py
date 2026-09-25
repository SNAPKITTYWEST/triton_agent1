# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.

"""Unified Machine IR (MIR): single SSA-ish IR fed by all front ends."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

MI_OPS = ["COPY","LOAD","STORE","ADD","SUB","MUL","DIV","SDIV","REM","SREM",
 "AND","OR","XOR","NOT","NEG","SHL","LSHR","ASHR","EQ","NE","ULT","ULE","SLT","SLE",
 "ZEXT","SEXT","CONCAT","EXTRACT","BR","CBR","CALL","RET","PHI","CONST","NOP","PRINT"]

@dataclass
class MIOp:
    op: str
    args: List[str] = field(default_factory=list)   # SSA value names or literals
    out: Optional[str] = None
    ty: str = "i32"     # i8,i16,i32,i64,f32,f64
    meta: Dict = field(default_factory=dict)
    def __repr__(self):
        o = f"{self.out} = " if self.out else ""
        return f"{o}{self.op}({', '.join(self.args)}) :{self.ty}"

@dataclass
class MIBlock:
    name: str
    ops: List[MIOp] = field(default_factory=list)

@dataclass
class MIFunction:
    name: str
    blocks: List[MIBlock] = field(default_factory=list)
    def all_ops(self):
        for b in self.blocks:
            yield from b.ops

@dataclass
class MachineIR:
    functions: List[MIFunction] = field(default_factory=list)
    def add_function(self, f: MIFunction):
        self.functions.append(f)
    def __repr__(self):
        s=[]
        for f in self.functions:
            s.append(f"func {f.name}:")
            for b in f.blocks:
                s.append(f" block {b.name}:")
                for op in b.ops: s.append(f"   {op}")
        return "\n".join(s)
