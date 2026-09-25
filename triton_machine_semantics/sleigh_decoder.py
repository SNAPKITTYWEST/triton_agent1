# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.

"""SLEIGH instruction decoder: bytes -> constructor + field bindings + disassembly."""
from __future__ import annotations
from typing import Tuple, Dict, Optional, List
from .sleigh_ast import ProcessorSpec, Constructor

def _extract_fields(word: int, bits: int, spec: ProcessorSpec) -> Dict[str,int]:
    out = {}
    # collect fields from all tokens (assume single token layout for this subset)
    for t in spec.tokens.values():
        for f in t.fields:
            width = abs(f.msb - f.lsb) + 1
            lo = min(f.msb, f.lsb)
            mask = (1 << width) - 1
            out[f.name] = (word >> lo) & mask
    return out

def decode_one(spec: ProcessorSpec, code: bytes, addr: int = 0) -> Tuple[Optional[Constructor], Dict[str,int], str, int]:
    """Decode a single instruction. Returns (ctor, bindings, disassembly, size)."""
    # determine token size: use first token bits else 16
    tbits = 16
    if spec.tokens:
        tbits = next(iter(spec.tokens.values())).bits
    tbytes = (tbits + 7)//8
    if len(code) < tbytes:
        return None, {}, "<truncated>", 0
    chunk = code[:tbytes]
    word = int.from_bytes(chunk, spec.endian)
    fields = _extract_fields(word, tbits, spec)
    for ctor in spec.constructors:
        ok = True
        for pc in ctor.pattern:
            if pc.field not in fields:
                # unknown field name: treat as literal mnemonic constraint skip
                # only fail if it had a value and field missing and name looks like a field
                if pc.value is not None:
                    # check registers/operands: ignore
                    pass
                continue
            if pc.value is not None and fields[pc.field] != pc.value:
                ok = False; break
        if ok:
            # build disassembly by substituting operand field values
            dis = ctor.mnemonic
            if ctor.operands:
                ops = []
                for op in ctor.operands:
                    if op in fields:
                        ops.append(f"{op}=0x{fields[op]:x}")
                    else:
                        ops.append(op)
                dis += " " + ", ".join(ops)
            return ctor, fields, dis, tbytes
    return None, fields, ".word 0x%x" % word, tbytes

def decode_all(spec: ProcessorSpec, code: bytes, base_addr: int = 0):
    out = []
    off = 0
    while off < len(code):
        ctor, bindings, dis, sz = decode_one(spec, code[off:], base_addr+off)
        if sz == 0:
            break
        out.append({"addr": base_addr+off, "ctor": ctor, "bindings": bindings,
                    "disasm": dis, "size": sz})
        off += sz
    return out
