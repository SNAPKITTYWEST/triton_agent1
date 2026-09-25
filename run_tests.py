# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.

import sys; sys.path.insert(0,'/mnt/data')
from triton_machine_semantics.sleigh_parser import parse_sleigh
from triton_machine_semantics.sleigh_decoder import decode_all
from triton_machine_semantics.transforms import sleigh_to_pcode, pcode_to_mir, sleigh_to_mir
from triton_machine_semantics.pcode import PcodeOp, Varnode
from triton_machine_semantics.pcode_engine import PcodeMachine
from triton_machine_semantics import subleq
from triton_machine_semantics.frontends import asm_to_mir, rtl_to_mir, parse_rtl, forth_to_mir, ForthMachine
from triton_machine_semantics.lowering import lower_pipeline

print("=== SLEIGH parse/decode ===")
spec_text="""
define endian=little;
define space ram type=ram_space size=4 default;
define space register type=register_space size=4;
define register offset=0 size=4 [ R0 R1 R2 R3 ];
define token instr(16) [ op=(0,7) rd=(8,11) rs=(12,15) ];
:ADD rd, rs is op=0x1 & rd & rs { rd = rd + rs; }
:SUB rd, rs is op=0x2 & rd & rs { rd = rd - rs; }
"""
spec=parse_sleigh(spec_text)
print("spaces",list(spec.spaces),"regs",list(spec.registers),"ctors",len(spec.constructors))
code=bytes([0x01,0x12])  # op=1 little endian
dec=decode_all(spec, code)
for d in dec: print(d["disasm"], d["bindings"])

print("\n=== SLEIGH -> P-code -> engine ===")
ops_by_addr={}
for d in dec:
    if d["ctor"]:
        ops=sleigh_to_pcode(spec, d["ctor"], d["bindings"], d["addr"])
        ops_by_addr[d["addr"]]=ops
        for o in ops: print(o)
m=PcodeMachine(endian='little')
m.spaces['register'].write(0x10,4,100); m.spaces['register'].write(0x20,4,58)
# patch varnodes: use fixed offsets for rd/rs test
rA=Varnode('register',0x10,4); rB=Varnode('register',0x20,4); rC=Varnode('register',0x30,4)
ops={0:[PcodeOp('INT_ADD',[rA,rB],rC,0,0), PcodeOp('INT_SUB',[rA,rB],rC,0,1)]}
m.load_program({0:ops[0][:1]})
print(m.run(0,trace=True)["trace"][:200])

print("\n=== P-code differential: engine vs python ints ===")
ok=True
for a in [0,1,127,255,2**31-1]:
    for b in [0,1,2,100]:
        mm=PcodeMachine(); ra=Varnode('register',0,4); rb=Varnode('register',4,4); rc=Varnode('register',8,4)
        mm.load_program({0:[PcodeOp('COPY',[Varnode('const',a,4)],ra,0,0),PcodeOp('COPY',[Varnode('const',b,4)],rb,0,1),PcodeOp('INT_ADD',[ra,rb],rc,0,2)]})
        mm.run(0); got=mm.spaces['register'].read(8,4); exp=(a+b)&0xFFFFFFFF
        if got!=exp: ok=False; print("mismatch",a,b,got,exp)
print("arith differential:", "PASS" if ok else "FAIL")

print("\n=== SUBLEQ toolchain ===")
print(subleq.run_tests())

print("\n=== MIR transforms ===")
mir1=asm_to_mir("ADD R0, R1, R2\nSUB R3, R0, R1\n")
print(mir1)
mir2=rtl_to_mir(parse_rtl("r0 <-- r1 + r2\nr3 <-- r0 & r1"))
print(mir2)
fm=ForthMachine(); print("forth stack:", fm.run("3 4 + 2 *"))

print("\n=== Lowering ===")
lp=lower_pipeline(mir1)
print("candidates:", len(lp["candidates"]), "kernels:", len(lp["kernels"]))
for k in lp["kernels"]:
    if k: print(k.src[:300])
for ptx,reason in lp["ptx"]:
    print("PTX:", reason, str(ptx)[:120] if ptx else None)
print("\nALL EXECUTABLE TESTS COMPLETED")
