# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 the Trust (see GOVERNANCE.md)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.
"""triton_machine_semantics: multi-frontend machine-semantics toolkit.

Pipeline: source specifications (SLEIGH / SLED / SSL-RTL / assembly /
microcode / Forth / OISC) -> tokens/AST -> P-code -> unified Machine IR
-> normalized IR -> data-parallel Triton/PTX lowering.
"""
__version__ = "0.1.0"
