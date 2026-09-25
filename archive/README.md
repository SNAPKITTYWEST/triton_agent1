# Preserved incomplete input
triton_agent1_incomplete.c.txt is the original, incomplete standalone C source.
It ends inside a comment-scanning loop and is preserved unchanged, excluded from builds.
The active implementation is include/triton_agent1.h with csrc/triton_agent1_main.c.
The original smoke script is retained in examples/legacy_smoke.py for provenance.
The supported test entry point is python run_tests.py.
