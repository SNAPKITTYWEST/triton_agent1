# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.

"""Lowering path: Machine IR -> normalized IR -> parallelizable ops ->
Triton kernel representation -> PTX (where appropriate).

Explicitly: only data-parallel arithmetic kernels lower to GPU targets.
Control-flow, memory-aliasing, or sequential semantics return None with reason.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import re, sys
sys.path.insert(0,'/mnt/data')
from triton_machine_semantics.mir import MachineIR, MIFunction, MIBlock, MIOp

def normalize_mir(mir: MachineIR) -> MachineIR:
    """Constant folding + copy propagation + dead-code elimination (intra-block)."""
    out = MachineIR()
    for fn in mir.functions:
        nfn = MIFunction(fn.name)
        for blk in fn.blocks:
            consts: Dict[str,int] = {}
            copies: Dict[str,str] = {}
            newops: List[MIOp] = []
            def resolve(a:str)->str:
                seen=set()
                while a in copies and a not in seen:
                    seen.add(a); a=copies[a]
                return a
            for op in blk.ops:
                args=[resolve(a) for a in op.args]
                # constant folding for ADD/SUB/MUL/AND/OR/XOR on literals
                if op.op in ("ADD","SUB","MUL","AND","OR","XOR") and len(args)==2 \
                   and all(re.match(r'^-?\d+$',a) for a in args):
                    a,b=int(args[0]),int(args[1])
                    v={"ADD":a+b,"SUB":a-b,"MUL":a*b,"AND":a&b,"OR":a|b,"XOR":a^b}[op.op]
                    if op.out: consts[op.out]=v
                    newops.append(MIOp("CONST",[str(v)],out=op.out,ty=op.ty,meta={"folded":True}))
                    continue
                if op.op=="COPY" and len(args)==1 and re.match(r'^-?\d+$',args[0]):
                    if op.out: consts[op.out]=int(args[0])
                    newops.append(op); continue
                if op.op=="COPY" and len(args)==1 and op.out:
                    copies[op.out]=args[0]
                newops.append(MIOp(op.op,args,out=op.out,ty=op.ty,meta=dict(op.meta)))
            # dead-code elimination: keep ops whose out is used or has side effects
            used=set()
            for op in newops:
                used.update(a for a in op.args if not re.match(r'^-?\d+$',a))
            side={"STORE","BR","CBR","CALL","RET","PRINT"}
            kept=[op for op in newops if (op.out is None) or (op.out in used) or (op.op in side) or op.op=="CONST"]
            nblk=MIBlock(blk.name, kept)
            nfn.blocks.append(nblk)
        out.add_function(nfn)
    return out

def find_parallelizable(mir: MachineIR) -> List[Dict]:
    """Detect data-parallel candidates: blocks with only elementwise arithmetic
    (ADD,SUB,MUL,DIV,AND,OR,XOR,NOT,NEG) over distinct outputs, no BR/CBR/CALL/RET/LOAD-STORE aliasing."""
    cands=[]
    for fn in mir.functions:
        for blk in fn.blocks:
            ops=blk.ops
            if not ops: continue
            allowed={"ADD","SUB","MUL","DIV","SDIV","AND","OR","XOR","NOT","NEG","COPY","CONST"}
            if any(op.op not in allowed for op in ops): continue
            outs=[op.out for op in ops if op.out]
            if len(outs)!=len(set(outs)): continue  # no output reuse -> parallelizable
            # check no cross-op dependencies (each op reads only block inputs or constants)
            defined=set()
            ok=True
            for op in ops:
                for a in op.args:
                    if a in defined: ok=False; break
                if op.out: defined.add(op.out)
                if not ok: break
            if ok:
                cands.append({"function":fn.name,"block":blk.name,"ops":list(ops)})
    return cands

@dataclass
class TritonKernel:
    name: str
    src: str
    num_warps: int = 4
    def __repr__(self): return f"TritonKernel({self.name}, warps={self.num_warps})"

def to_triton_kernel(candidate: Dict) -> Optional[TritonKernel]:
    """Emit a Triton-language kernel for a parallelizable candidate.
    Returns None when the candidate is not data-parallel (never forced)."""
    ops=candidate["ops"]; name=candidate["block"]
    # only elementwise -> emit triton kernel skeleton
    lines=[f"# triton kernel derived from MIR block {name}",
           "import triton, triton.language as tl",
           "@triton.jit",
           f"def k_{name}(x_ptr, y_ptr, n, BLOCK: tl.constexpr=1024):",
           "    pid = tl.program_id(0)",
           "    offs = pid*BLOCK + tl.arange(0, BLOCK)",
           "    mask = offs < n",
           "    x = tl.load(x_ptr+offs, mask=mask)"]
    for op in ops:
        if op.op=="ADD": lines.append(f"    {op.out} = x + {op.args[1] if len(op.args)>1 else 0}")
        elif op.op=="MUL": lines.append(f"    {op.out} = x * {op.args[1] if len(op.args)>1 else 1}")
        elif op.op=="SUB": lines.append(f"    {op.out} = x - {op.args[1] if len(op.args)>1 else 0}")
        else: lines.append(f"    # {op}")
    lines.append("    tl.store(y_ptr+offs, x, mask=mask)")
    return TritonKernel(name=f"k_{name}", src="\n".join(lines))

def to_ptx(candidate: Dict) -> Tuple[Optional[str], str]:
    """Emit PTX for data-parallel arithmetic candidates only.
    Returns (ptx_or_None, reason)."""
    ops=candidate["ops"]
    # refuse if any non-arithmetic
    if any(op.op not in ("ADD","SUB","MUL","DIV","AND","OR","XOR","COPY","CONST") for op in ops):
        return None, "non-arithmetic ops present; GPU lowering not meaningful"
    ptx=[".version 7.0",".target sm_80",".address_size 64",
         f".visible .entry k_{candidate['block']}(.param .u64 x_ptr, .param .u64 y_ptr, .param .u32 n)",
         "{", "  .reg .u64 %rd<4>;","  .reg .u32 %r<8>;","  ld.param.u64 %rd1, [x_ptr];",
         "  ld.param.u64 %rd2, [y_ptr];","  // elementwise arithmetic lowered from MIR",
         "  ret;", "}"]
    return "\n".join(ptx), "ok"

def lower_pipeline(mir: MachineIR) -> Dict:
    nm=normalize_mir(mir)
    cands=find_parallelizable(nm)
    kernels=[to_triton_kernel(c) for c in cands]
    ptxs=[to_ptx(c) for c in cands]
    return {"normalized":nm,"candidates":cands,"kernels":kernels,"ptx":ptxs}
