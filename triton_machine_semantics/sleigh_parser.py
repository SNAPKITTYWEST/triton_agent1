"""SLEIGH-compatible parser. Handles a documented public subset:
   define endian, define space, define register, define token, define context,
   macro definitions, and constructor lines of the form
     :MNEMONIC operands is pattern [ semantics ]
"""
from __future__ import annotations
import re
from .sleigh_ast import (ProcessorSpec, SpaceDef, RegisterDef, TokenDef, FieldDef,
                         ContextDef, PatternConstraint, Constructor, MacroDef)

_re_endian = re.compile(r'define\s+endian\s*=\s*(little|big)\s*;', re.I)
_re_space = re.compile(r'define\s+space\s+(\w+)\s+type\s*=\s*(\w+)\s+size\s*=\s*(\d+)([^;]*);', re.I)
_re_register = re.compile(r'define\s+register\s+offset\s*=\s*(\d+)\s+size\s*=\s*(\d+)\s*\[\s*([^\]]*)\]', re.I)
_re_token_head = re.compile(r'define\s+token\s+(\w+)\s*\((\d+)\)', re.I)
_re_context = re.compile(r'define\s+context\s+(\w+)', re.I)
_re_macro = re.compile(r'macro\s+(\w+)\s*\(([^)]*)\)\s*\{', re.I)

def _parse_fields(body: str):
    fields = []
    # fields like: op=(0,7) or op=0,7  inside token definition list
    for m in re.finditer(r'(\w+)\s*=\s*\(?\s*(\d+)\s*,\s*(\d+)\s*\)?', body):
        fields.append(FieldDef(name=m.group(1), msb=int(m.group(2)), lsb=int(m.group(3))))
    return fields

def _parse_pattern(pat: str):
    cons = []
    parts = [p.strip() for p in pat.split('&')]
    for p in parts:
        if not p:
            continue
        m = re.match(r'(\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+)', p)
        if m:
            fname = m.group(1); v = m.group(2)
            val = int(v, 16) if v.lower().startswith('0x') else int(v)
            cons.append(PatternConstraint(field=fname, value=val))
        else:
            m2 = re.match(r'(\w+)$', p)
            if m2:
                cons.append(PatternConstraint(field=m2.group(1), value=None))
    return cons

def _parse_semantics(sem: str):
    ops = []
    # split on ';' keep non-empty
    for stmt in [s.strip() for s in sem.split(';')]:
        if not stmt:
            continue
        ops.append({"src": stmt})
    return ops

def parse_sleigh(text: str) -> ProcessorSpec:
    spec = ProcessorSpec()
    # strip comments (# and // and /* */)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    lines = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#') or ln.startswith('//'):
            continue
        lines.append(ln)
    buf = "\n".join(lines)

    m = _re_endian.search(buf)
    if m:
        spec.endian = m.group(1).lower()

    for m in _re_space.finditer(buf):
        name, stype, size, rest = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        default = 'default' in rest.lower()
        wm = re.search(r'wordsize\s*=\s*(\d+)', rest, re.I)
        ws = int(wm.group(1)) if wm else 1
        spec.spaces[name] = SpaceDef(name=name, stype=stype, size=size, wordsize=ws, default=default)
    if "ram" not in spec.spaces:
        spec.spaces["ram"] = SpaceDef(name="ram", stype="ram_space", size=4, default=True)
    if "register" not in spec.spaces:
        spec.spaces["register"] = SpaceDef(name="register", stype="register_space", size=4)
    # unique/const are implicit
    spec.spaces.setdefault("unique", SpaceDef(name="unique", stype="unique_space", size=4))
    spec.spaces.setdefault("const", SpaceDef(name="const", stype="const_space", size=4))

    for m in _re_register.finditer(buf):
        offset, size, names = int(m.group(1)), int(m.group(2)), m.group(3)
        cur = offset
        for tok in names.split():
            tok=tok.strip().strip(',')
            if not tok or tok=='_':
                cur += 1
                continue
            spec.registers[tok] = RegisterDef(name=tok, offset=cur, size=size)
            cur += size

    # tokens: find define token ... [ ... ]
    for m in _re_token_head.finditer(buf):
        tname, bits = m.group(1), int(m.group(2))
        # find bracketed field list after head
        start = buf.find('[', m.end())
        end = buf.find(']', start)
        fbody = buf[start+1:end] if start!=-1 and end!=-1 else ""
        # token fields may also appear as separate "define field" lines; support both
        tdef = TokenDef(name=tname, bits=bits, fields=_parse_fields(fbody))
        spec.tokens[tname] = tdef

    for m in _re_context.finditer(buf):
        spec.contexts[m.group(1)] = ContextDef(name=m.group(1))

    # macros: capture balanced braces simply
    for m in _re_macro.finditer(buf):
        name, params = m.group(1), [p.strip() for p in m.group(2).split(',') if p.strip()]
        depth=1; i=m.end(); body=""
        while i < len(buf) and depth>0:
            c=buf[i]
            if c=='{': depth+=1
            elif c=='}': depth-=1
            if depth>0: body+=c
            i+=1
        spec.macros[name]=MacroDef(name=name, params=params, body=body)

    # constructors: :MNEM operands is pattern { semantics }  (semantics braces or brackets)
    ctor_re = re.compile(r':\s*(\w+)\s*([^:\n]*?)\s+is\s+([^\{\[]+?)\s*[\{\[]\s*(.*?)\s*[\}\]]', re.S)
    for m in ctor_re.finditer(buf):
        mnem = m.group(1)
        ops_raw = m.group(2).strip()
        pat_raw = m.group(3).strip()
        sem_raw = m.group(4).strip()
        operands = [o.strip().strip(',') for o in ops_raw.split(',') if o.strip()] if ops_raw else []
        # display: mnemonic + operands
        display = mnem + (" " + ", ".join(operands) if operands else "")
        spec.constructors.append(Constructor(
            mnemonic=mnem, operands=operands,
            pattern=_parse_pattern(pat_raw),
            display=display, semantics_src=sem_raw,
            semantics_ops=_parse_semantics(sem_raw)))
    return spec
