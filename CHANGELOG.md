# Changelog

## 0.2.0
- Organize C sources, public headers, Python package, specifications, scripts, tests, and examples into separate directories.
- Preserve the incomplete standalone C fragment in archive instead of compiling or deleting it.
- Add installable Python packaging, an installed CLI, CMake/CTest, and platform release artifacts.
- Repair the SSL module syntax error and remove machine-specific import paths.
- Implement missing bounded integer P-code and SUBLEQ execution modules with explicit unsupported-operation errors.
- Replace randomized register addresses with declared offsets and explicit Varnode bindings.
- Reject unknown decode constraints and truncated instructions, and repair division lowering.
- Preserve observable MIR writes and limit constant folding to wrapping fixed-width integer operations.
- Replace no-op GPU output with constrained elementwise Triton/PTX emitters that store the computed result.
- Bound Forth execution and reject unknown words, stack underflow, and malformed definitions.
- Validate C file size, embedded NUL input, numeric overflow, and IR operand IDs; release IR allocations.
- Add regression tests, isolated wheel installation checks, cross-platform CI, and sanitizer verification.
- Retain MPL-2.0 and Trust-controlled network governance without claiming those policies are a deployed authorization service.
