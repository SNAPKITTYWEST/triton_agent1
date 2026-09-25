"""SLEIGH AST nodes: processor specification abstract syntax tree."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class SpaceDef:
    name: str
    stype: str
    size: int
    wordsize: int = 1
    default: bool = False

@dataclass
class RegisterDef:
    name: str
    offset: int
    size: int
    space: str = "register"

@dataclass
class FieldDef:
    name: str
    msb: int
    lsb: int
    signed: bool = False

@dataclass
class TokenDef:
    name: str
    bits: int
    fields: List[FieldDef] = field(default_factory=list)

@dataclass
class ContextDef:
    name: str
    bits: Tuple[int,int] = (0,0)

@dataclass
class PatternConstraint:
    field: str
    value: Optional[int] = None       # None means "field must be present / any"
    subfield: Optional[str] = None

@dataclass
class Constructor:
    mnemonic: str
    operands: List[str] = field(default_factory=list)
    pattern: List[PatternConstraint] = field(default_factory=list)
    display: str = ""
    semantics_src: str = ""
    semantics_ops: List[dict] = field(default_factory=list)  # parsed semantic actions

@dataclass
class MacroDef:
    name: str
    params: List[str] = field(default_factory=list)
    body: str = ""

@dataclass
class ProcessorSpec:
    endian: str = "little"
    spaces: Dict[str, SpaceDef] = field(default_factory=dict)
    registers: Dict[str, RegisterDef] = field(default_factory=dict)
    tokens: Dict[str, TokenDef] = field(default_factory=dict)
    contexts: Dict[str, ContextDef] = field(default_factory=dict)
    constructors: List[Constructor] = field(default_factory=list)
    macros: Dict[str, MacroDef] = field(default_factory=dict)
    alignment: int = 1
