# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.
"""Bounded straight-line integer P-code interpreter. Unsupported ops raise."""
from .pcode import AddressSpace

def _signed(value,bits):
    return value-(1<<bits) if value&(1<<(bits-1)) else value

class PcodeMachine:
    def __init__(self,endian="little"):
        if endian not in ("little","big"): raise ValueError("invalid endian")
        self.endian=endian
        self.spaces={name:AddressSpace(name) for name in ("ram","register","unique")}
        self.program={}
    def load_program(self,program):
        if any(not isinstance(a,int) or a<0 for a in program): raise ValueError("invalid program address")
        self.program={a:list(ops) for a,ops in program.items()}
    def _read(self,v):
        if not 1<=v.size<=8: raise ValueError("varnode size must be 1..8")
        if v.space=="const": return v.offset&((1<<(8*v.size))-1)
        if v.space not in self.spaces: raise ValueError("unknown address space")
        return self.spaces[v.space].read(v.offset,v.size,self.endian)
    def run(self,start=0,trace=False,max_steps=100000):
        if max_steps<1: raise ValueError("max_steps must be positive")
        if start not in self.program: raise ValueError("start address not in program")
        steps=0; events=[]
        for address in sorted(a for a in self.program if a>=start):
            for op in self.program[address]:
                if steps>=max_steps: raise RuntimeError("P-code step limit exceeded")
                steps+=1
                if trace: events.append(repr(op))
                if op.opcode=="RETURN" and not op.inputs: return {"steps":steps,"trace":"\n".join(events)}
                arity={"COPY":1,"INT_ZEXT":1,"INT_SEXT":1,"INT_NEGATE":1,"INT_2COMP":1,"BOOL_NEGATE":1,
                       "INT_ADD":2,"INT_SUB":2,"INT_MULT":2,"INT_DIV":2,"INT_REM":2,"INT_SDIV":2,"INT_SREM":2,
                       "INT_AND":2,"INT_OR":2,"INT_XOR":2,"INT_LEFT":2,"INT_RIGHT":2,"INT_SRIGHT":2,
                       "INT_EQUAL":2,"INT_NOTEQUAL":2,"INT_LESS":2,"INT_LESSEQUAL":2,"INT_SLESS":2,"INT_SLESSEQUAL":2,
                       "BOOL_AND":2,"BOOL_OR":2,"BOOL_XOR":2,"LOAD":2,"STORE":3}
                if op.opcode not in arity: raise NotImplementedError(op.opcode)
                if len(op.inputs)!=arity[op.opcode]: raise ValueError("incorrect P-code arity")
                values=[self._read(v) for v in op.inputs]; a=values[0]; b=values[1] if len(values)>1 else 0
                bits=op.inputs[0].size*8; sa=_signed(a,bits)
                sb=_signed(b,op.inputs[1].size*8) if len(values)>1 else 0
                if op.opcode=="STORE":
                    space=getattr(op,"store_space","ram")
                    self.spaces[space].write(b,op.inputs[2].size,values[2],self.endian);continue
                if not op.output or op.output.space=="const" or op.output.space not in self.spaces or not 1<=op.output.size<=8: raise ValueError("invalid output")
                if op.opcode in ("INT_DIV","INT_REM","INT_SDIV","INT_SREM") and b==0: raise ZeroDivisionError("P-code division by zero")
                if op.opcode in ("INT_SDIV","INT_SREM"):
                    q=(abs(sa)//abs(sb))*(-1 if (sa<0)!=(sb<0) else 1)
                    value=q if op.opcode=="INT_SDIV" else sa-q*sb
                elif op.opcode=="LOAD": value=self.spaces[getattr(op,"load_space","ram")].read(b,op.output.size,self.endian)
                else:
                    funcs={"COPY":lambda:a,"INT_ZEXT":lambda:a,"INT_SEXT":lambda:sa,
                           "INT_NEGATE":lambda:~a,"INT_2COMP":lambda:-a,"BOOL_NEGATE":lambda:int(not a),
                           "INT_ADD":lambda:a+b,"INT_SUB":lambda:a-b,"INT_MULT":lambda:a*b,
                           "INT_DIV":lambda:a//b,"INT_REM":lambda:a%b,
                           "INT_AND":lambda:a&b,"INT_OR":lambda:a|b,"INT_XOR":lambda:a^b,
                           "INT_LEFT":lambda:a<<b if b<bits else 0,"INT_RIGHT":lambda:a>>b if b<bits else 0,
                           "INT_SRIGHT":lambda:sa>>min(b,bits),
                           "INT_EQUAL":lambda:int(a==b),"INT_NOTEQUAL":lambda:int(a!=b),
                           "INT_LESS":lambda:int(a<b),"INT_LESSEQUAL":lambda:int(a<=b),
                           "INT_SLESS":lambda:int(sa<sb),"INT_SLESSEQUAL":lambda:int(sa<=sb),
                           "BOOL_AND":lambda:int(bool(a) and bool(b)),"BOOL_OR":lambda:int(bool(a) or bool(b)),
                           "BOOL_XOR":lambda:int(bool(a)!=bool(b))}
                    value=funcs[op.opcode]()
                self.spaces[op.output.space].write(op.output.offset,op.output.size,value,self.endian)
        return {"steps":steps,"trace":"\n".join(events)}
