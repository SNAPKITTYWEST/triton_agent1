# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.
"""Conservative i32 elementwise lowering; unsupported blocks never emit kernels."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import re
from .mir import MachineIR, MIOp

_BINARY={"ADD":lambda a,b:a+b,"SUB":lambda a,b:a-b,"MUL":lambda a,b:a*b,
         "AND":lambda a,b:a&b,"OR":lambda a,b:a|b,"XOR":lambda a,b:a^b}
def normalize_mir(mir: MachineIR) -> MachineIR:
    """Fold literal integer arithmetic, preserving observable register writes.

    MIR does not declare live-outs, so deleting unused outputs or propagating
    register aliases across writes would be unsound. Neither is attempted.
    """
    out=deepcopy(mir)
    for fn in out.functions:
        for block in fn.blocks:
            for i,op in enumerate(block.ops):
                if op.op in _BINARY and len(op.args)==2 and re.fullmatch(r"i(8|16|32|64)",op.ty) and all(re.fullmatch(r"-?\d+",a) for a in op.args):
                    width=int(op.ty[1:])
                    value=_BINARY[op.op](*map(int,op.args))&((1<<width)-1)
                    block.ops[i]=MIOp("CONST",[str(value)],op.out,op.ty,{**op.meta,"folded":True})
    return out

def _reason(candidate):
    ops=candidate.get("ops",[])
    if len(ops)!=1: return "exactly one observable arithmetic write per block is required"
    op=ops[0]
    if op.op not in _BINARY or op.ty!="i32": return "only ADD/SUB/MUL/AND/OR/XOR on i32 are supported"
    if not op.out or len(op.args)!=2: return "one output and two operands are required"
    if not re.fullmatch(r"[A-Za-z_]\w*",op.args[0]) or not re.fullmatch(r"-?\d+",op.args[1]): return "expected an array input followed by an integer constant"
    if not re.fullmatch(r"[A-Za-z_]\w*",candidate.get("block","")): return "invalid kernel block identifier"
    return None

def find_parallelizable(mir):
    return [dict(function=fn.name,block=b.name,ops=list(b.ops))
            for fn in mir.functions for b in fn.blocks
            if not _reason(dict(block=b.name,ops=b.ops))]

@dataclass
class TritonKernel:
    name:str
    src:str
    num_warps:int=4

def to_triton_kernel(candidate):
    if _reason(candidate): return None
    op=candidate["ops"][0]; name="k_"+candidate["block"]; value=int(op.args[1])&0xffffffff
    symbol={"ADD":"+","SUB":"-","MUL":"*","AND":"&","OR":"|","XOR":"^"}[op.op]
    src=f"""import triton
import triton.language as tl

@triton.jit
def {name}(x_ptr, y_ptr, n, BLOCK: tl.constexpr = 256):
    offsets = tl.program_id(0) * BLOCK + tl.arange(0, BLOCK)
    mask = offsets < n
    x = tl.load(x_ptr + offsets, mask=mask, other=0).to(tl.uint32)
    scalar = tl.full((BLOCK,), {value}, tl.uint32)
    result = (x {symbol} scalar).to(tl.uint32)
    tl.store(y_ptr + offsets, result, mask=mask)
"""
    return TritonKernel(name,src)

def to_ptx(candidate):
    reason=_reason(candidate)
    if reason: return None,reason
    op=candidate["ops"][0]; name="k_"+candidate["block"]; value=int(op.args[1])&0xffffffff
    instr={"ADD":"add.u32","SUB":"sub.u32","MUL":"mul.lo.u32","AND":"and.b32","OR":"or.b32","XOR":"xor.b32"}[op.op]
    return f""".version 7.0
.target sm_80
.address_size 64
.visible .entry {name}(.param .u64 x_ptr, .param .u64 y_ptr, .param .u32 n)
{{
  .reg .pred %p;
  .reg .u32 %r<6>;
  .reg .u64 %rd<6>;
  ld.param.u64 %rd1, [x_ptr];
  ld.param.u64 %rd2, [y_ptr];
  ld.param.u32 %r0, [n];
  mov.u32 %r1, %tid.x;
  mov.u32 %r2, %ctaid.x;
  mov.u32 %r3, %ntid.x;
  mad.lo.u32 %r1, %r2, %r3, %r1;
  setp.ge.u32 %p, %r1, %r0;
  @%p bra DONE;
  mul.wide.u32 %rd3, %r1, 4;
  add.u64 %rd4, %rd1, %rd3;
  add.u64 %rd5, %rd2, %rd3;
  ld.global.u32 %r4, [%rd4];
  {instr} %r5, %r4, {value};
  st.global.u32 [%rd5], %r5;
DONE:
  ret;
}}
""","ok"

def lower_pipeline(mir):
    normalized=normalize_mir(mir); candidates=find_parallelizable(normalized)
    rejected=[{"function":fn.name,"block":b.name,"reason":_reason({"block":b.name,"ops":b.ops})}
              for fn in normalized.functions for b in fn.blocks if _reason({"block":b.name,"ops":b.ops})]
    return {"normalized":normalized,"candidates":candidates,
            "kernels":[to_triton_kernel(c) for c in candidates],
            "ptx":[to_ptx(c) for c in candidates],"rejected":rejected}
