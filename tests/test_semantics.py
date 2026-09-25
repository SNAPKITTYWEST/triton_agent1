# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.
import ast
import contextlib
import importlib
import io
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from triton_machine_semantics.sleigh_parser import parse_sleigh
from triton_machine_semantics.sleigh_decoder import decode_all,decode_one
from triton_machine_semantics.transforms import sleigh_to_pcode,pcode_to_mir
from triton_machine_semantics.pcode import PcodeOp,Varnode,AddressSpace
from triton_machine_semantics.pcode_engine import PcodeMachine
from triton_machine_semantics.frontends import asm_to_mir,parse_rtl,rtl_to_mir,ForthMachine,parse_microcode,microcode_to_mir
from triton_machine_semantics.lowering import normalize_mir,lower_pipeline,to_ptx,to_triton_kernel
from triton_machine_semantics import subleq
from triton_machine_semantics.cli import main

ROOT=Path(__file__).resolve().parents[1]
SPEC=(ROOT/"examples/minimal.slaspec").read_text()
class SemanticsTests(unittest.TestCase):
    def test_all_modules_import(self):
        for f in (ROOT/"src/triton_machine_semantics").glob("*.py"):
            if f.stem not in ("__main__",): importlib.import_module("triton_machine_semantics."+f.stem)
    def test_decode_and_actual_register_offsets(self):
        spec=parse_sleigh(SPEC);decoded=decode_all(spec,b"\x01\x12")
        self.assertEqual(decoded[0]["ctor"].mnemonic,"ADD")
        ops=sleigh_to_pcode(spec,decoded[0]["ctor"],decoded[0]["bindings"],0)
        self.assertEqual(ops[0].output,Varnode("register",0,4))
        m=PcodeMachine();m.spaces["register"].write(0,4,7);m.spaces["register"].write(4,4,9);m.load_program({0:ops});m.run()
        self.assertEqual(m.spaces["register"].read(0,4),16)
    def test_register_holes_have_register_width(self):
        spec=parse_sleigh("define register offset=0 size=4 [ R0 _ R2 ];")
        self.assertEqual(spec.registers["R2"].offset,8)
    def test_unknown_pattern_does_not_match(self):
        spec=parse_sleigh(SPEC.replace("op=1","missing=1"))
        self.assertIsNone(decode_one(spec,b"\x01\x12")[0])
    def test_truncated_instruction_rejected(self):
        with self.assertRaises(ValueError):decode_all(parse_sleigh(SPEC),b"\x01")
    def test_invalid_token_width(self):
        for spec in ("define token x(0) [ a=(0,0) ];","define token x(8) [ a=(0,8) ];"):
            with self.assertRaises(ValueError):parse_sleigh(spec)
    def test_unresolved_operands_rejected(self):
        spec=parse_sleigh(SPEC.replace("R0 = R0 + R1","rd = rd + rs"))
        d=decode_all(spec,b"\x01\x12")[0]
        with self.assertRaises(ValueError):sleigh_to_pcode(spec,d["ctor"],d["bindings"],0)
    def test_division_transform(self):
        spec=parse_sleigh(SPEC.replace("R0 + R1","R0 / R1"));d=decode_all(spec,b"\x01\x12")[0]
        self.assertEqual(sleigh_to_pcode(spec,d["ctor"],d["bindings"],0)[0].opcode,"INT_DIV")
        self.assertEqual(rtl_to_mir(parse_rtl("r0 <-- r1 / r2")).functions[0].blocks[0].ops[0].op,"DIV")
    def test_unknown_pcode_is_not_nop(self):
        mir=pcode_to_mir({0:[PcodeOp("UNIMPLEMENTED")]})
        self.assertEqual(mir.functions[0].blocks[0].ops[0].op,"UNIMPLEMENTED")
        m=PcodeMachine();m.load_program({0:[PcodeOp("UNIMPLEMENTED")]})
        with self.assertRaises(NotImplementedError):m.run()
    def test_wrapping_arithmetic_differential(self):
        randomizer=random.Random(2026)
        for size in (1,2,4,8):
            mask=(1<<(size*8))-1
            for opcode,fn in (("INT_ADD",lambda a,b:a+b),("INT_SUB",lambda a,b:a-b),("INT_MULT",lambda a,b:a*b)):
                for _ in range(80):
                    a,b=randomizer.getrandbits(size*8),randomizer.getrandbits(size*8)
                    m=PcodeMachine();m.load_program({0:[PcodeOp(opcode,[Varnode("const",a,size),Varnode("const",b,size)],Varnode("register",0,size))]});m.run()
                    self.assertEqual(m.spaces["register"].read(0,size),fn(a,b)&mask)
    def test_signed_division_truncates_toward_zero(self):
        for op,expected in (("INT_SDIV",-2),("INT_SREM",-1)):
            m=PcodeMachine();m.load_program({0:[PcodeOp(op,[Varnode("const",-7,4),Varnode("const",3,4)],Varnode("register",0,4))]});m.run()
            self.assertEqual(m.spaces["register"].read(0,4),expected&0xffffffff)
    def test_zero_division_and_step_budget(self):
        m=PcodeMachine();m.load_program({0:[PcodeOp("INT_DIV",[Varnode("const",1,4),Varnode("const",0,4)],Varnode("register",0,4))]})
        with self.assertRaises(ZeroDivisionError):m.run()
        m.load_program({0:[PcodeOp("COPY",[Varnode("const",1,4)],Varnode("register",0,4))]*2})
        with self.assertRaises(RuntimeError):m.run(max_steps=1)
    def test_address_space_endian_and_wrap(self):
        space=AddressSpace("ram",size=1);space.write(255,2,0x1234,"big")
        self.assertEqual(space.read(255,2,"big"),0x1234);self.assertEqual(space.read_byte(0),0x34)
    def test_load_store(self):
        for endian in ("little","big"):
            m=PcodeMachine(endian);m.load_program({0:[PcodeOp("STORE",[Varnode("const",0,4),Varnode("const",100,4),Varnode("const",0x12345678,4)]),PcodeOp("LOAD",[Varnode("const",0,4),Varnode("const",100,4)],Varnode("register",0,4))]});m.run()
            self.assertEqual(m.spaces["register"].read(0,4,endian),0x12345678)
    def test_forth_and_errors(self):
        self.assertEqual(ForthMachine().run(": twice DUP + ; 7 twice"),[14])
        for code in ("+","BOGUS",": broken 1"):
            with self.assertRaises(ValueError):ForthMachine().run(code)
        with self.assertRaises(RuntimeError):ForthMachine().run(": loop loop ; loop",max_steps=30)
    def test_subleq_and_bounds(self):
        result=subleq.run(subleq.assemble("a b -1\na: 5\nb: 3"))
        self.assertEqual(result["memory"][4],-2)
        with self.assertRaises(RuntimeError):subleq.run([0,0,0],max_steps=10)
        with self.assertRaises(ValueError):subleq.run([99,0,-1])
        with self.assertRaises(ValueError):subleq.assemble("unknown")
    def test_normalization_preserves_liveouts_and_aliases(self):
        mir=asm_to_mir("MOV a, b\nADD b, c, 1\nADD out, a, 1")
        normalized=normalize_mir(mir)
        self.assertEqual(len(normalized.functions[0].blocks[0].ops),3)
        self.assertEqual(normalized.functions[0].blocks[0].ops[2].args[0],"a")
        self.assertEqual(len(lower_pipeline(asm_to_mir("ADD out, x, 7"))["kernels"]),1)
    def test_constant_folding_wraps(self):
        result=normalize_mir(asm_to_mir("ADD out, 4294967295, 1"))
        self.assertEqual(result.functions[0].blocks[0].ops[0].args,["0"])
    def test_gpu_output_and_fail_closed(self):
        for opname in ("ADD","SUB","MUL","AND","OR","XOR"):
            result=lower_pipeline(asm_to_mir(f"{opname} output, input, 7"))
            kernel=result["kernels"][0];ast.parse(kernel.src)
            self.assertIn("tl.store(y_ptr + offsets, result",kernel.src)
            ptx=result["ptx"][0][0];self.assertIn("ld.global.u32",ptx);self.assertIn("st.global.u32",ptx);self.assertIn("@%p bra DONE",ptx)
        for src in ("ADD a, b, c","DIV a, b, 2","ADD a, b, 1\nSUB c, a, 1","RET"):
            result=lower_pipeline(asm_to_mir(src));self.assertFalse(result["kernels"]);self.assertTrue(result["rejected"])
    def test_unknown_microcode_explicit(self):
        mir=microcode_to_mir(parse_microcode("MYSTERY x"))
        self.assertEqual(mir.functions[0].blocks[0].ops[0].op,"UNIMPLEMENTED")
    def test_cli_success_and_refusal(self):
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(main(["forth","3 4 +"]),0)
        with tempfile.TemporaryDirectory() as folder:
            f=Path(folder)/"input.asm";f.write_text("DIV out, x, 2")
            with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(main(["lower",str(f)]),2)
    def test_register_mapping_is_process_deterministic(self):
        code="from triton_machine_semantics.sleigh_parser import parse_sleigh;from triton_machine_semantics.transforms import sleigh_to_pcode;s=parse_sleigh("+repr(SPEC)+");print(sleigh_to_pcode(s,s.constructors[0],{},0))"
        outputs=[]
        for seed in ("1","99"):
            env={**os.environ,"PYTHONHASHSEED":seed,"PYTHONPATH":str(ROOT/"src")}
            outputs.append(subprocess.check_output([sys.executable,"-c",code],env=env,text=True))
        self.assertEqual(*outputs)
