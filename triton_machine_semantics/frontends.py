# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.

"""Low-level front ends: assembly, RTL, microcode, Forth-style, OISC/URISC/MISC."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import re, sys
sys.path.insert(0, '/mnt/data')
from triton_machine_semantics.mir import MachineIR, MIFunction, MIBlock, MIOp

# ---------- Assembly ----------
def parse_asm(text: str) -> List[Tuple[str, List[str]]]:
    """Parse simple three-address assembly: OP dst, src1, src2 ; returns (op, args)."""
    out=[]
    for ln in text.splitlines():
        ln=re.sub(r'[;#].*$','',ln).strip()
        if not ln: continue
        m=re.match(r'(\w+)\s+(.*)', ln)
        if not m: continue
        op=m.group(1).upper(); args=[a.strip() for a in m.group(2).split(',') if a.strip()]
        out.append((op,args))
    return out

def asm_to_mir(text: str, fname="asm_main") -> MachineIR:
    mir=MachineIR(); fn=MIFunction(fname); blk=MIBlock("entry")
    ssa=0
    amap={"MOV":"COPY","ADD":"ADD","SUB":"SUB","MUL":"MUL","AND":"AND","OR":"OR","XOR":"XOR",
          "SHL":"SHL","SHR":"LSHR","SAR":"ASHR","LD":"LOAD","ST":"STORE","JMP":"BR","CJMP":"CBR","CALL":"CALL","RET":"RET"}
    for op,args in parse_asm(text):
        mop=amap.get(op, op)
        if mop in ("BR",): blk.ops.append(MIOp("BR",args,ty="i32"))
        elif mop=="RET": blk.ops.append(MIOp("RET",args,ty="i32"))
        else:
            out=args[0] if args and mop not in ("STORE","CBR","CALL") else None
            rest=args[1:] if out else args
            # map dst to ssa name
            blk.ops.append(MIOp(mop, rest, out=out, ty="i32"))
    fn.blocks.append(blk); mir.add_function(fn); return mir

# ---------- RTL ----------
@dataclass
class RTLStmt:
    dst: str; expr: str
def parse_rtl(text: str) -> List[RTLStmt]:
    out=[]
    for ln in text.splitlines():
        ln=ln.strip()
        if not ln or ln.startswith('#'): continue
        m=re.match(r'(.+?)\s*<--\s*(.+)', ln)
        if m: out.append(RTLStmt(m.group(1).strip(), m.group(2).strip()))
    return out

def rtl_to_mir(stmts: List[RTLStmt], fname="rtl_main") -> MachineIR:
    mir=MachineIR(); fn=MIFunction(fname); blk=MIBlock("entry")
    # map RTL operators to MI ops via simple pattern matching
    for s in stmts:
        e=s.expr
        m=re.match(r'(\w+)\s*([+\-*/&|^])\s*(\w+)', e)
        if m:
            a,opd,b=m.group(1),m.group(2),m.group(3)
            mp={"+":"ADD","-":"SUB","*":"MUL","&":"AND","|":"OR","^":"XOR"}[opd]
            blk.ops.append(MIOp(mp,[a,b],out=s.dst,ty="i32"))
        else:
            blk.ops.append(MIOp("COPY",[e],out=s.dst,ty="i32"))
    fn.blocks.append(blk); mir.add_function(fn); return mir

# ---------- Microcode ----------
@dataclass
class MicroOp:
    op: str; args: List[str] = field(default_factory=list)
def parse_microcode(text: str) -> List[MicroOp]:
    out=[]
    for ln in text.splitlines():
        ln=re.sub(r'#.*$','',ln).strip()
        if not ln: continue
        parts=ln.split()
        out.append(MicroOp(parts[0].upper(), parts[1:]))
    return out

def microcode_to_mir(ops: List[MicroOp], fname="ucode_main") -> MachineIR:
    mir=MachineIR(); fn=MIFunction(fname); blk=MIBlock("entry")
    mp={"ALU_ADD":"ADD","ALU_SUB":"SUB","REG_MOV":"COPY","MEM_RD":"LOAD","MEM_WR":"STORE","JUMP":"BR"}
    for mo in ops:
        blk.ops.append(MIOp(mp.get(mo.op, "NOP"), mo.args, ty="i32", meta={"ucode":mo.op}))
    fn.blocks.append(blk); mir.add_function(fn); return mir

# ---------- Forth-style ----------
class ForthMachine:
    """Executable Forth-style stack machine (public subset)."""
    def __init__(self):
        self.stack: List[int]=[]; self.rstack: List[int]=[]
        self.mem: Dict[int,int]={}; self.words: Dict[str,List[str]]={}
    def run(self, src: str):
        toks=src.split()
        i=0
        while i < len(toks):
            t=toks[i]
            if re.match(r'^-?\d+$', t): self.stack.append(int(t))
            elif t=='+': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(a+b)
            elif t=='-': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(a-b)
            elif t=='*': b=self.stack.pop(); a=self.stack.pop(); self.stack.append(a*b)
            elif t=='DUP': self.stack.append(self.stack[-1])
            elif t=='DROP': self.stack.pop()
            elif t=='SWAP': a=self.stack.pop(); b=self.stack.pop(); self.stack.extend([a,b])
            elif t=='@': a=self.stack.pop(); self.stack.append(self.mem.get(a,0))
            elif t=='!': a=self.stack.pop(); v=self.stack.pop(); self.mem[a]=v
            elif t==':': # word definition : NAME ... ;
                name=toks[i+1]; body=[]
                i+=2
                while toks[i]!=';': body.append(toks[i]); i+=1
                self.words[name]=body
            elif t in self.words:
                self.run(' '.join(self.words[t]))
            i+=1
        return list(self.stack)

def forth_to_mir(src: str, fname="forth_main") -> MachineIR:
    mir=MachineIR(); fn=MIFunction(fname); blk=MIBlock("entry")
    # each forth token becomes a stack-effect MI op (executable model)
    for t in src.split():
        blk.ops.append(MIOp("NOP",[t],ty="i32",meta={"forth":t}))
    fn.blocks.append(blk); mir.add_function(fn); return mir

# ---------- OISC / URISC / MISC descriptors ----------
OISC_DESC={"SUBLEQ": "single instruction: Mem[b]=Mem[b]-Mem[a]; if <=0 goto c",
           "ADDLEQ": "single instruction: Mem[b]=Mem[b]+Mem[a]; if <=0 goto c"}
URISC_DESC={"SUBLEQ-URISC": "SUBLEQ with reversed operands, 2-operand form",
            "MOVE": "single instruction: move with conditional branch"}
MISC_DESC={"MISC": "minimal instruction set: load, store, add, branch variants"}
