# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.
"""Installed CLI; errors use exit code 2 and stderr."""
import argparse
import json
import sys
from pathlib import Path
from . import __version__
from .frontends import asm_to_mir,ForthMachine
from .lowering import lower_pipeline
from .sleigh_parser import parse_sleigh
from .sleigh_decoder import decode_all

def main(argv=None):
    parser=argparse.ArgumentParser(prog="triton-semantics")
    parser.add_argument("--version",action="version",version=__version__)
    commands=parser.add_subparsers(dest="command",required=True)
    lower=commands.add_parser("lower");lower.add_argument("source",type=Path);lower.add_argument("--format",choices=("triton","ptx","mir"),default="triton")
    decode=commands.add_parser("decode");decode.add_argument("spec",type=Path);decode.add_argument("hex_bytes")
    forth=commands.add_parser("forth");forth.add_argument("program")
    args=parser.parse_args(argv)
    try:
        if args.command=="forth": print(json.dumps(ForthMachine().run(args.program)));return 0
        if args.command=="decode":
            result=decode_all(parse_sleigh(args.spec.read_text(encoding="utf-8")),bytes.fromhex(args.hex_bytes))
            if any(x["ctor"] is None for x in result): raise ValueError("unknown instruction")
            print(json.dumps([{k:v for k,v in x.items() if k!="ctor"} for x in result],indent=2));return 0
        result=lower_pipeline(asm_to_mir(args.source.read_text(encoding="utf-8")))
        if args.format=="mir": print(result["normalized"]);return 0
        if result["rejected"] or not result["candidates"]: raise ValueError("unsupported GPU lowering: "+json.dumps(result["rejected"]))
        for item in (result["kernels"] if args.format=="triton" else result["ptx"]): print(item.src if args.format=="triton" else item[0])
        return 0
    except (OSError,ValueError,NotImplementedError,RuntimeError) as error:
        print(f"error: {error}",file=sys.stderr);return 2
if __name__=="__main__": raise SystemExit(main())
