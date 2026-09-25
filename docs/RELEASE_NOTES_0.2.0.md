# TRITON-SLED 0.2.0 — packaged machine-semantics toolkit

This release organizes the project into C sources, headers, an installable Python
package, tests, examples, specifications, and an archive of the unfinished C
fragment. It repairs the missing interpreters, integer/register handling,
normalization, source emission, and error paths.

## Getting started

Install the Python wheel with python -m pip install followed by its path, then
run triton-semantics forth "3 4 + 2 *". The result is [14].
Choose a native ZIP matching your OS and architecture for the C lexer/IR demo.
Read README.md for commands, migration notes, supported operations, and limits.

Assets include the wheel, source distribution, native platform archives, and
SHA256SUMS. Native archives include license, governance, contributor information,
and a commit/hash manifest.

## Validation and scope

Release gates cover 25 regression tests, four CTest cases, isolated wheel
installation, Linux/Windows/macOS on Python 3.10 and 3.13, and Linux Clang
address/undefined-behavior sanitizers. Check the linked release commit's workflow.
GPU execution and TLA+ proofs are not verified. The C executable produces fixed
demonstration IR; this is not a full historical-language compiler.

## Copyleft, contact, and contributors

MPL-2.0 applies file by file. Preserve source license notices. Trust network
administration remains a separate governance layer described in GOVERNANCE.md.

Contact: a.parr@belespritdaccord.uk
Contributors: Ahmad Ali Parr (ahmedparr@icloud.com), SNAPKITTYWEST
(ahmedparr93@gmail.com).
