# Release procedure and readiness boundary

## Gate sequence
1. Confirm the exact repository and clean working tree.
2. Build the C11 driver and run CTest.
3. Run the Python regression suite with TRITON_C_BINARY set to that executable.
4. Build the wheel and sdist, then run scripts/check_wheel.py in a clean temporary environment.
5. Require the GitHub Actions matrix and Linux address/undefined sanitizer job to pass for the exact release commit.
6. Download the corresponding platform artifacts; create SHA256SUMS for every uploaded file.
7. Create an annotated version tag and publish the release with scope and limitations.

## Scope
Version 0.2.0 is a hardened subset/tooling release. It does not certify complete historical-language compilation, complete Ghidra semantics, a SLED runtime, distributed governance enforcement, or production GPU execution. The C driver lexes source then prints a clearly labeled fixed IR demonstration. Generated GPU code supports one i32 array/scalar arithmetic operation per block. The native P-code interpreter is a documented bounded straight-line integer subset and rejects control-flow operations it does not implement.

No GPU is available in the local verification environment. GPU code is emitted, checked structurally, and parsed as Python where applicable; an actual CUDA/Triton launch has not been validated. The TLA+ file is preserved as an unverified specification artifact; its theorem declarations are not proof results. These are explicit deployment boundaries, not passing tests.

## Rollback
Consumers should pin a release version and record the SHA256 of the downloaded artifact. To roll back, reinstall the previously approved version in a fresh virtual environment and restore the prior CLI binary. Do not overwrite tags or replace published assets silently. If an incorrect release is discovered, mark it in release notes, publish a corrective version, and keep the original checksums for traceability.

## Network governance
Code ownership or a successful build does not grant Trust administrative authority. GOVERNANCE.md remains separate from MPL-2.0. This release contains no network-admin or grant-signing service.
