"""Transformations to unified Machine IR and P-code emission."""
from __future__ import annotations
import re, sys
sys.path.insert(0, '/mnt/data')
from triton_machine_semantics.sleigh_ast import ProcessorSpec, Constructor
from triton_machine_semantics.pcode import PcodeOp, Varnode
from triton_machine_semantics.mir import MachineIR, MIFunction, MIBlock, MIOp
from triton_machine_semantics.frontends import parse_rtl, rtl_to_mir, parse_microcode, microcode_to_mir, asm_to_mir, forth_to_mir

def _ty_of_size(n:int)->str: return {1:"i8",2:"i16",4:"i32",8:"i64"}.get(n,"i32")

def sleigh_to_pcode(spec: ProcessorSpec, ctor: Constructor, bindings: dict, base_addr: int) -> list:
    """Lower a decoded SLEIGH constructor's semantic actions to raw P-code ops.
    Documented subset: assignments of form `dst = src op src`, `*dst = src`, `dst = *src`,
    `goto target`, `if (c) goto t`, `call t`, `return`.
    Unknown statements lower to UNIMPLEMENTED (explicit, never silent)."""
    ops=[]; seq=0
    reg = lambda name, size=4: Varnode("register", abs(hash(name)) % 4096, size)
    # map operand names to varnodes via bindings where numeric
    def vn_for(tok: str) -> Varnode:
        tok=tok.strip()
        if re.match(r'^-?\d+$', tok) or re.match(r'^0x', tok):
            return Varnode("const", int(tok,0), 4)
        if tok in bindings and isinstance(bindings[tok], int):
            return Varnode("const", bindings[tok], 4)
        return Varnode("register", abs(hash(tok)) % 8192, 4)
    for s in ctor.semantics_ops:
        src=s["src"]
        m=re.match(r'if\s*\((.+)\)\s*goto\s+(\w+)', src, re.I)
        if m:
            cond=vn_for(m.group(1)); tgt=vn_for(m.group(2))
            ops.append(PcodeOp("CBRANCH",[tgt,cond],None,base_addr,seq)); seq+=1; continue
        m=re.match(r'goto\s+(\w+)', src, re.I)
        if m:
            ops.append(PcodeOp("BRANCH",[vn_for(m.group(1))],None,base_addr,seq)); seq+=1; continue
        m=re.match(r'return', src, re.I)
        if m:
            ops.append(PcodeOp("RETURN",[],None,base_addr,seq)); seq+=1; continue
        m=re.match(r'call\s+(\w+)', src, re.I)
        if m:
            ops.append(PcodeOp("CALL",[vn_for(m.group(1))],None,base_addr,seq)); seq+=1; continue
        m=re.match(r'\*(.+?)\s*=\s*(.+)', src)
        if m:
            ptr=vn_for(m.group(1)); val=vn_for(m.group(2))
            sp=Varnode("const", 0, 4)
            op=PcodeOp("STORE",[sp,ptr,val],None,base_addr,seq); op.store_space="ram"
            ops.append(op); seq+=1; continue
        m=re.match(r'(.+?)\s*=\s*\*(.+)', src)
        if m:
            dst=vn_for(m.group(1)); ptr=vn_for(m.group(2))
            sp=Varnode("const",0,4)
            op=PcodeOp("LOAD",[sp,ptr],dst,base_addr,seq); op.load_space="ram"
            ops.append(op); seq+=1; continue
        m=re.match(r'(.+?)\s*=\s*(.+?)\s*([+\-*/&|^])\s*(.+)', src)
        if m:
            dst,a,opd,b=m.group(1),m.group(2),m.group(3),m.group(4)
            mp={"+":"INT_ADD","-":"INT_SUB","*":"INT_MULT","&":"INT_AND","|":"INT_OR","^":"INT_XOR"}[opd]
            # '/' needs signedness; default unsigned
            if opd=="/": mp="INT_DIV"
            ops.append(PcodeOp(mp,[vn_for(a),vn_for(b)],vn_for(dst),base_addr,seq)); seq+=1; continue
        m=re.match(r'(.+?)\s*=\s*(.+)', src)
        if m:
            ops.append(PcodeOp("COPY",[vn_for(m.group(2))],vn_for(m.group(1)),base_addr,seq)); seq+=1; continue
        ops.append(PcodeOp("UNIMPLEMENTED",[],None,base_addr,seq)); seq+=1
    return ops

_P2M={"COPY":"COPY","INT_ADD":"ADD","INT_SUB":"SUB","INT_MULT":"MUL","INT_DIV":"DIV","INT_SDIV":"SDIV",
 "INT_REM":"REM","INT_SREM":"SREM","INT_AND":"AND","INT_OR":"OR","INT_XOR":"XOR","INT_NEGATE":"NOT",
 "INT_2COMP":"NEG","INT_LEFT":"SHL","INT_RIGHT":"LSHR","INT_SRIGHT":"ASHR","INT_EQUAL":"EQ",
 "INT_NOTEQUAL":"NE","INT_LESS":"ULT","INT_LESSEQUAL":"ULE","INT_SLESS":"SLT","INT_SLESSEQUAL":"SLE",
 "INT_ZEXT":"ZEXT","INT_SEXT":"SEXT","PIECE":"CONCAT","SUBPIECE":"EXTRACT","BRANCH":"BR","CBRANCH":"CBR",
 "CALL":"CALL","CALLIND":"CALL","RETURN":"RET","LOAD":"LOAD","STORE":"STORE","BOOL_AND":"AND",
 "BOOL_OR":"OR","BOOL_XOR":"XOR","BOOL_NEGATE":"NOT"}

def pcode_to_mir(ops_by_addr: dict, fname="pcode_main") -> MachineIR:
    mir=MachineIR(); fn=MIFunction(fname)
    def vname(v:Varnode)->str:
        if v.space=="const": return str(v.offset)
        return f"{v.space}_{v.offset}_{v.size}"
    for addr in sorted(ops_by_addr):
        blk=MIBlock(f"bb_{addr:x}")
        for op in ops_by_addr[addr]:
            mop=_P2M.get(op.opcode, "NOP")
            args=[vname(v) for v in op.inputs]
            out=vname(op.output) if op.output else None
            ty=_ty_of_size(op.output.size if op.output else (op.inputs[0].size if op.inputs else 4))
            blk.ops.append(MIOp(mop,args,out=out,ty=ty,meta={"pcode":op.opcode,"addr":addr}))
        fn.blocks.append(blk)
    mir.add_function(fn); return mir

def sleigh_to_mir(spec, decoded: list, fname="sleigh_main") -> MachineIR:
    """SLEIGH -> Machine IR via P-code."""
    ops_by_addr={}
    for d in decoded:
        ctor=d["ctor"]; addr=d["addr"]
        if ctor is None: continue
        ops_by_addr[addr]=sleigh_to_pcode(spec, ctor, d["bindings"], addr)
    return pcode_to_mir(ops_by_addr, fname)

def rtl_text_to_mir(text:str, fname="rtl_main")->MachineIR:
    return rtl_to_mir(parse_rtl(text), fname)
def microcode_text_to_mir(text:str, fname="ucode_main")->MachineIR:
    return microcode_to_mir(parse_microcode(text), fname)
def assembly_text_to_mir(text:str, fname="asm_main")->MachineIR:
    return asm_to_mir(text, fname)
