# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# Network administration authority is governed separately; see GOVERNANCE.md.

cc -std=c11 -Wall -Wextra -Wpedantic -O2 \
    triton_agent1_main.c \
    -o triton-agent1

./triton-agent1 jovial program.jov
./triton-agent1 cms2 program.cms
./triton-agent1 tacpol program.tac
