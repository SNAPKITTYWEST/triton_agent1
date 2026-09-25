<div align="center">

<img src="assets/logo.svg" alt="TRITON-SLED" width="620"/>

# TRITON-SLED

**A multi-frontend machine-semantics toolkit: from processor specifications to a unified IR to data-parallel GPU lowering.**

[![License: MPL-2.0](https://img.shields.io/badge/License-MPL--2.0-brightgreen.svg)](LICENSE)
[![Governance: Trust](https://img.shields.io/badge/Governance-Trust%20Controlled-8b5cf6.svg)](GOVERNANCE.md)
[![Language: C11](https://img.shields.io/badge/C-C11-00599C.svg?logo=c)](include/triton_agent1.h)
[![Language: Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](src/triton_machine_semantics/)
[![Spec: SLED](https://img.shields.io/badge/DSL-SLED-06b6d4.svg)](specs/sled/)
[![Model: SLEIGH%20%2F%20P--code](https://img.shields.io/badge/Model-SLEIGH%20%2F%20P--code-f59e0b.svg)](src/triton_machine_semantics/pcode.py)
[![Formal: TLA%2B](https://img.shields.io/badge/Formal-TLA%2B-2563eb.svg)](specs/sled/core.tla)
[![CI](https://github.com/SNAPKITTYWEST/triton_agent1/actions/workflows/ci.yml/badge.svg)](https://github.com/SNAPKITTYWEST/triton_agent1/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/SNAPKITTYWEST/triton_agent1)](https://github.com/SNAPKITTYWEST/triton_agent1/releases)
[![Status: Executable%20Core](https://img.shields.io/badge/Status-Executable%20Core-16a34a.svg)](run_tests.py)

<sub>authors · <b>ahmedparr93@gmail.com</b> · <b>SNAPKITTYWEST</b></sub>

</div>

---

## Release 0.2.0 support boundary

This release hardens and packages the existing machine-semantics toolkit.
It is suitable for the documented local parsing, integer interpretation, and
source-generation workflows after validation against your inputs. It is not a
complete production compiler or an untrusted-code sandbox.

| Area | Delivered behavior | Boundary |
|---|---|---|
| C11 | Lexer diagnostics, IR builders, command-line demo | Fixed demonstration IR; no full source compiler |
| Python | Installable package, CLI, bounded integer/Forth/SUBLEQ execution | Documented subsets only |
| GPU | Single-operation i32 Triton/PTX source generation | No device validation in CI |
| SLED/TLA+ | Original research artifacts preserved | No runtime or verified proof supplied |
| Governance | MPL notices and Trust charter preserved | No network authorization service |

## Table of contents

- [What this is](#what-this-is)
- [Design principles](#design-principles)
- [Repository layout](#repository-layout)
- [The pipeline at a glance](#the-pipeline-at-a-glance)
- [Component 1 — the C11 compiler core (`triton_agent1`)](#component-1--the-c11-compiler-core-triton_agent1)
- [Component 2 — the machine-semantics package](#component-2--the-machine-semantics-package)
  - [SLEIGH frontend](#sleigh-frontend)
  - [SLED frontend](#sled-frontend)
  - [SSL / RTL frontend](#ssl--rtl-frontend)
  - [The low-level frontends](#the-low-level-frontends)
  - [P-code: the semantic backbone](#p-code-the-semantic-backbone)
  - [Machine IR (MIR)](#machine-ir-mir)
  - [Lowering to Triton and PTX](#lowering-to-triton-and-ptx)
- [Component 3 — the SLED language](#component-3--the-sled-language)
- [Component 4 — the TLA+ specification](#component-4--the-tla-specification)
- [Getting started](#getting-started)
- [Worked examples](#worked-examples)
- [Testing and verification](#testing-and-verification)
- [Extending TRITON-SLED](#extending-triton-sled)
- [Design decisions and non-goals](#design-decisions-and-non-goals)
- [Licensing and governance](#licensing-and-governance)
- [Provenance](#provenance)
- [Authors](#authors)

---

## What this is

TRITON-SLED is a **machine-semantics toolkit**. It takes descriptions of how a
processor — real, historical, or invented — behaves, and turns those
descriptions into something executable, analyzable, and, where the shape of the
computation permits, lowerable to a GPU.

The word "machine semantics" is doing a lot of work here, so it is worth being
precise about it. A great deal of software concerns itself with *syntax*: what a
program looks like, how it is written, how it parses. TRITON-SLED is concerned
with *semantics*: what a program **means** when a machine runs it. When you say
`ADD R0, R1, R2`, what actually happens? Which storage locations are read? Which
are written? What is the width of the arithmetic? What are the side effects on
flags, on the program counter, on memory? Machine semantics is the discipline of
answering those questions formally enough that a computer can answer them for
you.

This matters in a surprising number of places. It matters in **decompilation and
binary analysis**, where you have bytes and you want to recover meaning. It
matters in **retargetable compilation**, where you want to describe a new target
once and get a working toolchain. It matters in **emulation**, where you want to
run one machine's code on another. It matters in **formal verification**, where
you want to prove that a transformation preserves behavior. And it matters in
**high-performance computing**, where you want to recognize when a chunk of
generic computation is secretly a data-parallel kernel that a GPU could run
thousands of times faster.

TRITON-SLED is built around a single conviction: all of these use cases want the
*same* intermediate representation of meaning. If you can get from any input
language into a common, well-defined semantic core, you get every downstream
capability for free. That common core, in this project, is **P-code** (a
register-transfer semantic model in the tradition of the SLEIGH/Ghidra
ecosystem) feeding a **unified Machine IR (MIR)**. Everything upstream is a
frontend; everything downstream is a consumer.

The name is a portmanteau. **TRITON** is the parallel-kernel and lowering
ambition — the trident that reaches toward GPU targets. **SLED** is the
specification language at the front of the pipeline (and a nod to the classic
"Specification Language for Encoding and Decoding" lineage of machine
descriptions). Together they name the arc this repository draws: from a formal
description of a machine, all the way down to code a modern accelerator can run.

---

## Design principles

TRITON-SLED holds itself to a small number of principles, and they explain most
of the choices you will find in the code.

**1. Evidence before claims.** The release includes executable Python subsets,
a C lexer/IR demonstration, and separately identified research specifications.
The SLED language artifacts have no included execution runtime. Generated GPU
source is inspected by tests but is not GPU-validated in the release matrix.
Unsupported backend operations are rejected explicitly.

**2. Documented subsets, never invented history.** Several of the input
languages TRITON-SLED accepts are historical or based on published
specifications. The parsers implement a **documented public subset** of each,
and they say so in their module docstrings. The project deliberately does not
fabricate undocumented syntax to look more complete than it is. A parser that
handles a clean, real subset is worth more than one that hallucinates a language.

**3. Fail closed, and fail loud.** When the P-code lowering meets a statement it
does not understand, it emits an explicit `UNIMPLEMENTED` opcode — a marker you
can search for, count, and act on — rather than dropping the statement. When the
GPU lowering meets computation that is not data-parallel, it returns `None`
*with a reason string*, never a broken kernel. Silence is the enemy of
correctness.

**4. Separation of frontends.** Each source language gets its own module. No
frontend is quietly treated as another. This keeps the semantics of, say,
JOVIAL distinct from the semantics of CMS-2, even though they share the same
downstream IR. Contamination between frontends is a category of bug this layout
makes structurally hard to introduce.

**5. Verification has a boundary.** Regression tests and C sanitizers exercise the shipped implementations. The inherited TLA+ model is an unverified research artifact; theorem declarations are not proof results.

---

## Repository layout

    triton_agent1/
    ├── csrc/                 C command-line driver
    ├── include/              C11 header library
    ├── src/triton_machine_semantics/
    │   ├── cli.py            Installed command-line interface
    │   ├── pcode_engine.py   Bounded integer interpreter
    │   ├── subleq.py         Assembler and bounded interpreter
    │   └── ...               Parsers, IR, transforms, source emitters
    ├── tests/                Regression and C CLI tests
    ├── examples/             Small inputs and historical smoke script
    ├── specs/sled/           Preserved SLED and TLA+ specifications
    ├── archive/              Original unfinished C source, preserved as text
    ├── scripts/              Build, wheel validation, release packaging
    ├── docs/                 Release procedure
    ├── assets/               Original project logo
    ├── .github/workflows/    Cross-platform builds and sanitizer checks
    ├── CMakeLists.txt        C build and CTest registration
    ├── pyproject.toml        Installable Python distribution
    ├── run_tests.py          Development test entry point
    ├── LICENSE              MPL-2.0
    └── GOVERNANCE.md        Separate Trust governance policy

---

## The pipeline at a glance

```
   ┌──────────────────────────────────────────────────────────────┐
   │                          FRONTENDS                             │
   │  SLEIGH   SLED   SSL/RTL   Assembly   Microcode   Forth  OISC  │
   └───────┬──────┬──────┬─────────┬───────────┬─────────┬────┬────┘
           │      │      │         │           │         │    │
           ▼      ▼      ▼         ▼           ▼         ▼    ▼
        ┌─────────────────────────────────────────────────────┐
        │          tokens / AST / field bindings               │
        └───────────────────────┬─────────────────────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │        P-CODE          │  ← semantic backbone
                     │  varnodes + opcodes    │
                     └───────────┬───────────┘
                                 ▼
                     ┌───────────────────────┐
                     │    MACHINE IR (MIR)    │  ← single unified IR
                     └───────────┬───────────┘
                                 ▼
                 ┌───────────────────────────────┐
                 │  normalize (integer folding)     │
                 └───────────────┬───────────────┘
                                 ▼
                 ┌───────────────────────────────┐
                 │  find data-parallel candidates │
                 └───────────────┬───────────────┘
                                 ▼
                     ┌───────────┴───────────┐
                     ▼                       ▼
              ┌────────────┐          ┌────────────┐
              │  TRITON    │          │    PTX      │
              │  kernel    │          │  (sm_80)    │
              └────────────┘          └────────────┘
```

This diagram describes the architectural direction. The supported executable paths and their restrictions are listed below; Forth execution and SUBLEQ execution are separate interpreters, not complete GPU compilation paths.

---

## Component 1 — the C11 compiler core (`triton_agent1`)

The C side of TRITON-SLED is a **self-contained C11 compiler infrastructure**
with no external dependencies. It establishes the classic front-half of a
compiler — source → lexer → tokens → AST → symbols → IR — for three historical
systems-programming languages: **JOVIAL**, **CMS-2**, and **TACPOL**.

The design is deliberately a **header-library plus driver**. `triton_agent1.h`
contains the full infrastructure: a checked memory layer (`ta_malloc`,
`ta_calloc`, `ta_realloc`, `ta_strdup`, all of which abort loudly on
exhaustion), a source-location model, a diagnostics engine with note / warning /
error / fatal severities, a token model with a growable token vector, a complete
recursive lexer, an arena-friendly AST with a tagged-union node type, a type
system, a symbol table, and a small SSA-flavored IR with a text dumper.
`triton_agent1_main.c` is the thin executable driver that reads a file, runs the
lexer, prints diagnostics, and dumps a **fixed 12 + 30 demonstration IR**. It does not parse the input into that IR or implement full JOVIAL, CMS-2, or TACPOL compilation.

Three things are worth calling out about this component.

First, the **diagnostics are real**. When the lexer meets a byte it cannot
classify, it does not skip it — it records `unrecognized character 0x..` at a
precise line and column, increments the error count, and emits a `TOK_UNKNOWN`
so the caller can decide what to do. Unterminated string literals are reported
the same way. This is the "fail loud" principle expressed in C.

Second, the **frontends are separated by construction**. The header defines
distinct `TA_JovialCompiler`, `TA_CMS2Compiler`, and `TA_TACPOLCompiler` state
types, each with its own diagnostics, tokens, symbols, and IR module. They share
the lexer and IR machinery but not their identity. This is the same
"no frontend is silently another frontend" rule the Python side follows.

Third, the **IR is genuinely an IR**. It has basic blocks, typed SSA values, an
opcode set spanning arithmetic, comparison, control flow, calls, and memory, and
a builder API (`ir_const_i64`, `ir_binary`, …). The driver validates the whole
pipeline by constructing a small IR module and dumping it, so a successful run
checks the lexer and IR builder independently; it does not prove source-to-IR compilation.

Build it:

```sh
cc -std=c11 -O2 -Wall -Wextra -pedantic \
   -Iinclude csrc/triton_agent1_main.c -o triton-agent1
```

Run it:

```sh
./triton-agent1 jovial source.jov
./triton-agent1 cms2  source.cms
./triton-agent1 tacpol source.tac
```

There is also a built-in test build. Compiling `triton_agent1.h` with
`-DTRITON_AGENT1_TEST` produces a standalone tokenizer self-test that lexes a
sample expression and prints every token with its kind and location.

---

## Component 2 — the machine-semantics package

This is the heart of TRITON-SLED: an importable Python package that carries
computation all the way from a machine description to a GPU kernel. Import it as
`triton_machine_semantics`.

### SLEIGH frontend

The SLEIGH frontend implements a documented public subset of the SLEIGH
processor-specification language — the same family of language Ghidra uses to
describe instruction sets.

`sleigh_parser.py` recognizes `define endian`, `define space`,
`define register`, `define token` (with bit-field lists), `define context`,
`macro` definitions with balanced-brace bodies, and constructor lines of the
canonical form:

```
:MNEMONIC operands is pattern { semantics }
```

It parses each of these into the AST defined in `sleigh_ast.py` — `SpaceDef`,
`RegisterDef`, `FieldDef`, `TokenDef`, `PatternConstraint`, `Constructor`,
`MacroDef`, all gathered under a `ProcessorSpec`. Sensible implicit spaces
(`ram`, `register`, `unique`, `const`) are supplied if the specification does
not, matching the conventional model.

`sleigh_decoder.py` then does the real work: given a `ProcessorSpec` and raw
bytes, it reads a token-sized word (honoring endianness), extracts every field
by mask and shift, and walks the constructor list to find one whose pattern
constraints all hold. It returns the matching constructor, the field bindings,
a rendered disassembly string, and the instruction size. `decode_all` iterates
this across a byte buffer to disassemble a whole stream, emitting a `.word`
fallback for anything undecodable — again, fail loud, never silent.

### SLED frontend

`sled.py` is a compact, self-contained encode/decode model in the SLED tradition
("Specification Language for Encoding and Decoding"). It parses `token`,
`pattern`, and `constructor` declarations and provides `sled_decode`, which
matches a machine word against pattern constraints to recover the constructor.
Where the SLEIGH frontend is oriented toward rich disassembly, the SLED frontend
is the minimal, auditable kernel of the same idea.

### SSL / RTL frontend

`ssl_semantics.py` handles semantic descriptions in the SSL/RTL style — a
reconstructable subset of the UQBT register-transfer model, where an instruction
is a set of effects of the form `location := expression`. It parses
`instr NAME { ... }` blocks into `SSLInstr` objects carrying ordered
`RTLEffect`s, and lowers them to generic three-address pseudo-ops. This is the
most declarative of the frontends: it describes *what changes*, and leaves the
*how* to the common lowering.

### The low-level frontends

`frontends.py` gathers the machine-adjacent input languages, each with a parser
and an MIR lowering:

- **Assembly** — a simple three-address form (`OP dst, src1, src2`) with a
  documented opcode map (`MOV`→`COPY`, `ADD`→`ADD`, `LD`→`LOAD`, `JMP`→`BR`, …).
- **RTL** — line-oriented register transfers using `<--`, with operator
  recognition that turns `r1 + r2` into an `ADD` MIR op.
- **Microcode** — whitespace-delimited micro-operations (`ALU_ADD`, `REG_MOV`,
  `MEM_RD`, …) mapped to MIR.
- **Forth-style** — and this one is genuinely *executable*. `ForthMachine` is a
  bounded stack machine: literals push, `+ - *` compute, `DUP DROP SWAP` shuffle,
  `@ !` read and write memory, and `: NAME ... ;` defines new words that then run
  through an iterative dispatcher with an instruction budget. Forth-to-MIR is explicitly unsupported and produces an UNIMPLEMENTED marker.
- **OISC / URISC / MISC** — descriptor tables for one-instruction and
  minimal-instruction computers (SUBLEQ, ADDLEQ, and friends), documenting the
  single-instruction semantics that make these architectures Turing-complete.

### P-code: the semantic backbone

`pcode.py` is where all meaning converges. It defines the P-code **opcode set** —
copies, loads and stores, the full integer arithmetic and comparison family
(signed and unsigned), boolean ops, an extensive floating-point set, conversions,
and the SSA-style meta-ops (`MULTIEQUAL`, `INDIRECT`, `PIECE`, `SUBPIECE`,
`CAST`, `PTRADD`, `PTRSUB`) — plus `POPCOUNT`, `LZCOUNT`, and more.

It defines **varnodes** — the `(space, offset, size)` triples that are P-code's
universal notion of a storage location — as frozen, hashable values. And it
defines **address spaces** with real byte-addressable backing store and
endian-aware multi-byte reads and writes, so a P-code program has somewhere to
actually keep its state.

Crucially, `PcodeOp` **validates its opcode on construction**. You cannot build a
P-code operation with a misspelled or nonexistent opcode; the constructor raises
immediately. The semantic core refuses to hold nonsense.

### Machine IR (MIR)

`mir.py` defines the single unified IR that every frontend targets. It is
deliberately small and readable: a typed operation (`MIOp` with an op name,
argument list, optional output, a width type like `i8`/`i32`/`f64`, and a
metadata dict), grouped into basic blocks, grouped into functions, grouped into a
`MachineIR` module with a clean text representation. The metadata dict is the
quiet hero — it carries provenance (which P-code op, which microcode op, which
Forth token) down through the pipeline, so nothing loses its origin.

`transforms.py` connects SLEIGH to this IR through P-code. `sleigh_to_pcode`
lowers a decoded constructor's semantic statements — assignments, dereferencing
loads and stores, `goto`, conditional `goto`, `call`, `return` — into raw P-code,
and emits `UNIMPLEMENTED` for anything outside the documented subset.
`pcode_to_mir` then maps P-code opcodes to MIR opcodes through an explicit table.
The composition, `sleigh_to_mir`, takes you from processor spec plus bytes to a
full MIR module.

### Lowering to Triton and PTX

`lowering.py` is the TRITON in TRITON-SLED. It runs in stages:

1. **normalize_mir** folds literal integer ADD, SUB, MUL, AND, OR, and XOR
   with width-specific wrapping. It preserves writes. Copy propagation and
   dead-code elimination are intentionally absent because MIR has no live-out contract.
2. **find_parallelizable** accepts one i32 arithmetic write per block, with
   an array input followed by an integer constant. Two-array operations,
   dependent sequences, branches, loads/stores, floats, and reductions are rejected.
3. **to_triton_kernel** emits masked input loads, the actual operation, and
   masked output stores. Input/output buffers must contain 32-bit integer elements.
4. **to_ptx** emits the same operation with explicit indexing, bounds checking,
   global loads/stores, PTX 7.0 and an sm_80 target.

The lower_pipeline result includes normalized, candidates, kernels, ptx, and
rejected entries. Every rejected entry gives its function, block, and reason.
These are source generators. The release does not establish GPU compilation,
device execution, throughput, or equivalence on actual accelerator hardware.

---

## Component 3 — the SLED language

The `specs/sled/` directory contains a small, purpose-built functional language —
**SLED** — and, strikingly, a lexer and parser for SLED **written in SLED
itself**. These are preserved design artifacts; this repository does not ship a compiler or runtime that executes them.

The language has algebraic data types (`enum` and tagged `type` unions), records,
generics (`List<T>`, `Option<T>`, `Result<T,E>`, `Map<K,V>`), pattern matching,
and first-class functions. `core.sled` is the prelude — the `Option`/`Result`/
`List`/`Map`/`Pair` vocabulary every other module builds on. `token.sled` and
`lexer.sled` tokenize SLED source; `ast.sled` and `parser.sled` build the tree;
`value.sled`, `graph.sled`, and `state.sled` provide the runtime model,
including a property-graph of nodes and edges and a full `RuntimeState`.

The two top-level programs describe the **TRITON pipeline** as a SLED program.
`triton-sled.core.sled` lays out the ten-stage flow — pre-assessment,
reconnaissance, threat modeling, vulnerability correlation, path modeling,
controlled-emulation model, result validation, risk analysis, recommendation,
report — as a monotone promotion chain, with a matching inversion chain that
walks the tree back destination-first, and a set of emitted models.
`triton-sled.full.sled` is the fully annotated version carrying the complete
project metadata.

---

## Component 4 — the TLA+ specification

The inherited specs/sled/core.tla describes promotion through evidence, findings,
risk, decisions, recommendations, and reports. It contains named invariants and
theorem statements. **No TLC run or machine-checked proof is claimed for 0.2.0.**

The model needs review of next-state variable constraints, finite model
configuration, and the distinction between safety invariants and eventual
progress before verification results can be published. Keeping the original
model preserves provenance; including a theorem declaration is not evidence
that its statement holds. This model also does not verify the C or Python code.

---

## Getting started

Requirements: Python 3.10 or newer for the toolkit. Building the C demo additionally
requires CMake 3.20 or newer and a C11 compiler. Python runtime dependencies are
empty; setuptools and wheel are build-time dependencies.

    git clone https://github.com/SNAPKITTYWEST/triton_agent1.git
    cd triton_agent1
    python -m venv .venv

Activate with .venv/Scripts/Activate.ps1 on Windows PowerShell, or
source .venv/bin/activate on POSIX shells, then install:

    python -m pip install .
    triton-semantics --version
    triton-semantics forth "3 4 + 2 *"
    triton-semantics decode examples/minimal.slaspec 0100
    triton-semantics lower examples/elementwise.asm --format ptx

The Forth example prints [14]. The lower command writes generated source to
standard output; redirect it to a file if desired. Use --format triton or
--format mir for the other outputs.

Build and check the C program:

    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
    cmake --build build --config Release
    ctest --test-dir build -C Release --output-on-failure

On Windows with Visual Studio, the executable is build/Release/triton-agent1.exe.
Single-configuration Unix generators place it at build/triton-agent1. MinGW on
Windows places it at build/triton-agent1.exe. Pass jovial, cms2, or tacpol followed
by examples/program.txt. Each invocation performs lexical validation and emits
the same explicitly labeled fixed IR demonstration.

For Python development use python -m pip install -e .; production installations
should use a versioned wheel in a dedicated environment. Do not put repository
directories into application sys.path. The source layout prevents accidental
imports from hiding broken package installations.

---

## Worked examples

**Disassemble bytes against a SLEIGH spec:**

```python
spec = parse_sleigh("""
    define endian=little;
    define space ram type=ram_space size=4 default;
    define register offset=0 size=4 [ R0 R1 R2 R3 ];
    define token instr(16) [ op=(0,7) rd=(8,11) rs=(12,15) ];
    :ADD rd, rs is op=0x1 & rd & rs { rd = rd + rs; }
    :SUB rd, rs is op=0x2 & rd & rs { rd = rd - rs; }
""")

for insn in decode_all(spec, bytes([0x01, 0x12])):
    print(insn["disasm"], insn["bindings"])
```

**Run the Forth stack machine:**

```python
from triton_machine_semantics.frontends import ForthMachine
print(ForthMachine().run("3 4 + 2 *"))     # -> [14]
```

**Lower assembly to a GPU candidate:**

```python
from triton_machine_semantics.frontends import asm_to_mir
from triton_machine_semantics.lowering import lower_pipeline

mir = asm_to_mir("ADD output, input, 7\n")
result = lower_pipeline(mir)
print(len(result["candidates"]), "parallel candidate(s)")
for kernel in result["kernels"]:
    if kernel:
        print(kernel.src)
```

---

## Testing and verification

Run python run_tests.py. Set TRITON_C_BINARY to the absolute path of the built
C executable to include its subprocess tests. Without it the C test class is
reported as skipped; that is not a complete release check.

The suite includes 25 tests: parsing and decoder boundaries, declared register
offsets, cross-process hash-seed determinism, integer execution, signed division,
memory endianness, execution budgets, Forth errors, SUBLEQ, normalization
regressions, source generation, CLI errors, and malformed C input. Integer
arithmetic includes 960 reproducible randomized differential cases across four
widths. The tests compare results and failures rather than merely printing them.

CTest independently runs three dialect smoke cases and one rejected-input case.
CI runs the Python and C tests on Linux, Windows, and macOS with Python 3.10 and
3.13. A separate Linux Clang job uses AddressSanitizer, UndefinedBehaviorSanitizer,
and leak detection. The workflow also builds a wheel and source distribution,
installs the wheel into a new environment away from the source tree, and verifies
the installed command.

    python -m pip install build
    python -m build
    python scripts/check_wheel.py

A passing test suite establishes the checked cases, not arbitrary-input safety,
complete historical language compatibility, GPU execution, or formal proof.
Inspect the workflow associated with the exact release commit for current
results. See docs/RELEASE.md for promotion and rollback procedures.

---

## Extending TRITON-SLED

The architecture is designed to be extended at the edges without disturbing the
core.

**Adding a frontend** means writing a parser that produces MIR (or P-code, if
your language has genuine machine semantics). Follow the pattern in
`frontends.py`: parse to a small typed representation, then walk it emitting
`MIOp`s with useful metadata. Your language inherits normalization and GPU
lowering the moment it reaches MIR.

**Adding an optimization** means adding a pass over MIR alongside
`normalize_mir`. Passes are plain functions from `MachineIR` to `MachineIR`;
compose them however you like.

**Adding a backend** means writing a consumer of MIR (or of the parallel
candidates) alongside `to_triton_kernel` and `to_ptx`. The candidate structure
already isolates exactly the blocks a data-parallel backend can accept.

**Adding a C dialect** means adding a `TA_*Compiler` state type and keyword set
in `triton_agent1.h`, keeping it separate from the existing three.

---

## Design decisions and non-goals

A few things TRITON-SLED deliberately does **not** try to be.

It is **not a drop-in replacement** for Ghidra's SLEIGH engine, the full UQBT/SSL
toolchain, or a production Triton compiler. It implements documented, auditable
subsets of those ideas, chosen so the whole pipeline stays comprehensible and
the supported implementation stays reviewable.

It is **not a syntax museum.** The historical languages it names are represented
by real, working subsets, not by fabricated grammars assembled to look complete.

It does **not** force computation onto the GPU. The lowering pipeline is
conservative on purpose: it lowers only what is genuinely data-parallel, and it
tells you in words why it declined everything else.

These are features, not omissions. A smaller thing that is entirely true is more
useful than a larger thing that is partly invented.

---

## Licensing and governance

TRITON-SLED is **copyleft**, licensed under the **Mozilla Public License,
Version 2.0**, which applies **on a file-by-file basis**. The full text is in
[`LICENSE`](LICENSE), and every source file carries an SPDX header and a short
notice pointing here.

MPL-2.0 is a *weak* copyleft: modifications to an MPL-covered file must be shared
under the MPL, but you may combine those files with independently-licensed files
in a larger work, and each file keeps its own license. That boundary is exactly
what this project wants — the semantic core stays open and improvements flow
back, while integrators keep flexibility at the edges.

Governance is a **separate layer** from the code license, and this is important.
Possessing the source grants you every right the MPL grants — to run, study,
modify, and redistribute covered files — and **nothing more**. It does **not**
grant any administrative authority over a governed TRITON-SLED network. As
[`GOVERNANCE.md`](GOVERNANCE.md) sets out, only **the Trust** may grant
network-admin, node-admin, signing, admission/revocation, or governance-policy
authority, every grant must carry a full authorization record and a valid
signature, and the charter requires **fail-closed** authorization: no valid grant means no authority. This toolkit does not implement a network administration or grant-verification service. Copyright in the code is
held by the Trust. Read the license and the governance charter together: one
governs the code, the other governs the network.

---

## Provenance

The material in this repository was assembled from source contributed by the
authors. The C11 core, the machine-semantics package, the SLED language, and the
TLA+ specification were integrated into a single tree, licensed under MPL-2.0,
and organized as documented above.

---


## Release installation and operations

Download versioned assets from the GitHub Releases page. Platform ZIP names
identify operating system and architecture; do not run a binary for a different
architecture. The Python wheel is platform-independent and contains no compiled
extension. Install it with python -m pip install followed by the wheel path.
The source distribution contains the Python sources and development artifacts
needed to rebuild the package and C demonstration.

Each platform archive contains the executable, header, README, license,
governance charter, and a manifest recording the Git commit and SHA-256 hashes.
SHA256SUMS on the release records hashes of the downloadable assets. Compare
downloaded hashes before installation: PowerShell provides Get-FileHash with
-Algorithm SHA256; Linux provides sha256sum; macOS provides shasum -a 256.
Checksums detect corruption or mismatch; they are not detached publisher signatures.

Run --version after installation and retain the release tag and asset hash in
your deployment record. Install into a new environment before replacing a
working installation. For rollback, recreate the environment with the previous
approved wheel or restore the previous platform archive. No database migrations,
background service, network listener, or account credentials are required.

The default tools operate on local files. Do not send secrets in example inputs
or commit proprietary machine specifications unintentionally. Execution step
budgets limit interpreter work but do not provide process isolation or an overall
memory quota. Use an OS-level isolated process with resource limits when handling
untrusted or exceptionally large inputs. The C file reader enforces a 1 MiB limit
and rejects embedded NUL bytes; these checks do not turn it into a complete
adversarial-input sandbox.

### Migrating from the original flat checkout

C consumers must change their include search path to include/. The C executable
entry point is now csrc/triton_agent1_main.c. The original incomplete standalone
C file is preserved byte-for-byte under archive/ as text and is excluded from
compilation. Python consumers should install the distribution instead of
importing a root-level folder. Import names remain triton_machine_semantics.

Specification paths now begin with specs/sled/. The root build.sh delegates to
scripts/build.sh. The root run_tests.py is the supported regression entry point;
the old print-based smoke harness is preserved at examples/legacy_smoke.py as a
historical artifact and is not a release gate.

Behavior has intentionally tightened. Unknown execution operations raise errors.
Numeric decoder fields are input literals; use explicit Varnode bindings when
they identify output storage. Register addresses come from declarations, not
process-dependent hashes. Unsupported GPU blocks appear in rejected results and
cause the lower CLI to exit unsuccessfully. Consumers that previously accepted
empty kernels or silently discarded instructions must handle these errors.

### Execution model and error handling

PcodeMachine executes a straight-line sequence in deterministic order. Values
are read from byte-addressed register, unique, or RAM spaces, and constants are
immediate values. Output writes wrap to the varnode width. Supported varnode
widths are one through eight bytes. Signed division truncates toward zero, and
division by zero fails. The broad opcode vocabulary in pcode.py is a data model;
it is larger than the executable subset in pcode_engine.py. Branches, calls,
floating-point operations, and SSA merge operations are not implemented there.

Use the max_steps argument for interpreter budgets. A budget error, malformed
varnode, unknown operation, or invalid memory-space access should terminate the
current operation rather than be treated as a valid zero result. Forth definitions
run through an iterative dispatcher, so recursive definitions consume the budget
rather than the Python call stack. SUBLEQ validates memory addresses and halts
when its program counter becomes negative.

The SLEIGH decoder currently handles one token of one through 64 bits.
Constraints on unknown fields cannot match. Truncated trailing instruction data
raises an error. A .word fallback indicates undecoded data, not valid semantics;
the semantic lowering rejects unknown instructions. These parsers are compact
subsets and are not a replacement for a full SLEIGH grammar validator.

### GPU source contract

A supported block contains exactly one ADD, SUB, MUL, AND, OR, or XOR write on
i32, with an array input and a decimal integer constant. Arithmetic is represented
as 32-bit bit patterns with modulo wrapping. The output array must have capacity
for n elements, and the input must provide at least n elements. Generated code
does not allocate device memory, launch kernels, synchronize streams, or validate
host-side pointer ownership. Those remain responsibilities of the caller.

The Triton source takes x_ptr, y_ptr, n, and a compile-time BLOCK parameter.
The PTX entry takes two 64-bit device pointers and a 32-bit element count.
Both compute an element index, check bounds, load the input, apply the operation,
and store the result. Launch configuration must cover the requested elements
without overflowing 32-bit index arithmetic. Separate output storage is the
recommended contract; arbitrary partially overlapping arrays are unsupported.

Before deploying generated code on a GPU, assemble or compile it with the target
toolchain and compare device output against a CPU reference across zero length,
partial blocks, large values, negative constants, and overflow. Record GPU model,
driver, compiler version, launch dimensions, and test seeds. Release CI checks
source structure and Python syntax, not those device requirements. No benchmark
or accelerator speedup is claimed.

### Contributing and maintaining a release

Keep semantic fixes separate from layout-only changes where practical. Add a
regression case that would fail before the fix, and make the expected bit width,
endianness, and error behavior explicit. Preserve license headers and author
attribution. New frontend operations must either have defined lowering semantics
or remain visibly unsupported; a NOP is not an acceptable placeholder for an
operation with effects.

Before a release, check a clean source checkout, all matrix jobs, sanitizer
results, and isolated wheel installation. Publish artifacts from the same commit
as the release tag. Never retarget a published tag to different code. If a defect
is discovered, publish a corrected version and identify the affected behavior
in the changelog. See CHANGELOG.md and docs/RELEASE.md.

### Primary technical references

- [Ghidra SLEIGH reference](https://ghidra.re/ghidra_docs/languages/html/sleigh_ref.html)
- [Ghidra P-code operation reference](https://ghidra.re/ghidra_docs/languages/html/pcodedescription.html)
- [NVIDIA PTX ISA reference](https://docs.nvidia.com/cuda/archive/12.2.1/parallel-thread-execution/)

These references describe the source models and target instruction language.
They do not certify compatibility or verification of this implementation.

## Authors

<div align="center">

| Author | Contact |
|---|---|
| **Ahmad Ali Parr** | `ahmedparr93@gmail.com` |
| **SNAPKITTYWEST** | Sovereign Kernel Project |

<sub>© 2026 the Trust · Licensed under MPL-2.0 · Network authority governed separately, see GOVERNANCE.md</sub>

</div>
