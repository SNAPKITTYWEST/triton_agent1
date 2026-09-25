# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.

"""P-code data model: opcodes, varnodes, address spaces. Public spec subset."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict

OPCODES = [
 "UNIMPLEMENTED","COPY","LOAD","STORE","BRANCH","CBRANCH","BRANCHIND",
 "CALL","CALLIND","CALLOTHER","RETURN",
 "INT_EQUAL","INT_NOTEQUAL","INT_SLESS","INT_SLESSEQUAL","INT_LESS","INT_LESSEQUAL",
 "INT_ZEXT","INT_SEXT","INT_ADD","INT_SUB","INT_CARRY","INT_SCARRY","INT_SBORROW",
 "INT_2COMP","INT_NEGATE","INT_XOR","INT_AND","INT_OR","INT_LEFT","INT_RIGHT","INT_SRIGHT",
 "INT_MULT","INT_DIV","INT_REM","INT_SDIV","INT_SREM",
 "BOOL_NEGATE","BOOL_XOR","BOOL_AND","BOOL_OR",
 "FLOAT_EQUAL","FLOAT_NOTEQUAL","FLOAT_LESS","FLOAT_LESSEQUAL",
 "FLOAT_ADD","FLOAT_SUB","FLOAT_MULT","FLOAT_DIV","FLOAT_NEG","FLOAT_ABS","FLOAT_SQRT","FLOAT_NAN",
 "INT2FLOAT","FLOAT2FLOAT","TRUNC","CEIL","FLOOR","ROUND",
 "MULTIEQUAL","INDIRECT","PIECE","SUBPIECE","CAST","PTRADD","PTRSUB",
 "POPCOUNT","LZCOUNT","CPOOLREF","NEW",
]
OPCODE_SET = set(OPCODES)

@dataclass
class AddressSpace:
    name: str
    stype: str = "ram_space"
    size: int = 4  # bytes needed to encode an offset (address width)
    wordsize: int = 1
    default: bool = False
    _data: Dict[int, int] = field(default_factory=dict, repr=False)
    def read_byte(self, offset: int) -> int:
        return self._data.get(offset & ((1 << (self.size*8))-1), 0)
    def write_byte(self, offset: int, val: int):
        mask = (1 << (self.size*8))-1
        self._data[offset & mask] = val & 0xFF
    def read(self, offset: int, size: int, endian: str = "little") -> int:
        bs = bytes(self.read_byte(offset+i) for i in range(size))
        return int.from_bytes(bs, endian)
    def write(self, offset: int, size: int, val: int, endian: str = "little"):
        bs = (val & ((1<<(size*8))-1)).to_bytes(size, endian)
        for i,b in enumerate(bs):
            self.write_byte(offset+i, b)

@dataclass(frozen=True)
class Varnode:
    space: str
    offset: int
    size: int
    def __repr__(self):
        return f"{self.space}[0x{self.offset:x}]:{self.size}"

@dataclass
class PcodeOp:
    opcode: str
    inputs: List[Varnode] = field(default_factory=list)
    output: Optional[Varnode] = None
    seq_addr: int = 0
    seq_num: int = 0
    def __post_init__(self):
        if self.opcode not in OPCODE_SET:
            raise ValueError(f"unknown pcode opcode {self.opcode}")
    def __repr__(self):
        ins = ",".join(repr(v) for v in self.inputs)
        out = f"{self.output} = " if self.output else ""
        return f"{out}{self.opcode}({ins}) @{self.seq_addr:04x}:{self.seq_num}"
