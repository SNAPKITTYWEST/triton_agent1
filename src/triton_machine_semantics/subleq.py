# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.
"""Bounded SUBLEQ integer machine and two-pass integer/label assembler."""
def assemble(source):
    labels={}; tokens=[]
    for line in source.splitlines():
        for token in line.split("#",1)[0].split():
            if token.endswith(":"):
                name=token[:-1]
                if not name.isidentifier() or name in labels: raise ValueError("invalid or duplicate label")
                labels[name]=len(tokens)
            else: tokens.append(token)
    result=[]
    for token in tokens:
        if token in labels: result.append(labels[token])
        else:
            try: result.append(int(token,0))
            except ValueError as exc: raise ValueError(f"unknown label or integer: {token}") from exc
    return result

def run(program,*,pc=0,max_steps=100000):
    memory=list(program)
    if not all(isinstance(v,int) for v in memory) or max_steps<1: raise ValueError("invalid program or budget")
    steps=0
    while pc>=0:
        if steps>=max_steps: raise RuntimeError("SUBLEQ step limit exceeded")
        if pc+2>=len(memory): raise ValueError("truncated SUBLEQ instruction")
        a,b,c=memory[pc:pc+3]
        if not 0<=a<len(memory) or not 0<=b<len(memory): raise ValueError("invalid SUBLEQ memory address")
        memory[b]-=memory[a];pc=c if memory[b]<=0 else pc+3;steps+=1
    return {"memory":memory,"pc":pc,"steps":steps}

def run_tests():
    result=run(assemble("start: a b -1\na: 5\nb: 3"))
    if result["memory"][4]!=-2: raise AssertionError("SUBLEQ subtraction")
    return {"passed":1}
