#!/usr/bin/env sh
# SPDX-License-Identifier: MPL-2.0
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec sh "$ROOT/scripts/build.sh" "$@"
