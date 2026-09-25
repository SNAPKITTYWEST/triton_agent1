#!/usr/bin/env sh
# SPDX-License-Identifier: MPL-2.0
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cmake -S "$ROOT" -B "$ROOT/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$ROOT/build" --config Release
ctest --test-dir "$ROOT/build" -C Release --output-on-failure
