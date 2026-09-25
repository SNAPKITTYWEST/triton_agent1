# Commercial use and contact

TRITON-SLED is distributed under MPL-2.0 on a file-by-file basis.
Commercial use is permitted by that license. Distribution of covered source or
executables must follow its applicable terms. Read LICENSE for the controlling
text and https://www.mozilla.org/en-US/MPL/2.0/FAQ/ for Mozilla's explanation.

Commercial support, integration, and service enquiries:
[a.parr@belespritdaccord.uk](mailto:a.parr@belespritdaccord.uk).
No support contract, service entitlement, or alternative license is implied by
installation. Network administration remains governed separately by GOVERNANCE.md.

Contributors: Ahmad Ali Parr (ahmedparr@icloud.com), SNAPKITTYWEST
(ahmedparr93@gmail.com).

## Distribution channels

The Python wheel contains the machine-semantics implementation. The npm package
is a small Node command-line bridge to that Python implementation, not a separate
JavaScript compiler. Install Python 3.10+ and the Python package first. The Node
bridge requires Node 22+ and provides triton-semantics-node. TRITON_PYTHON can point
to the Python executable in a virtual environment. Arguments are passed directly
without a shell, and the Python exit status is preserved. Installation does not
run a download script, install Python, collect credentials, or contact a server.

Registry publication requires the project owner's authenticated PyPI and npm
accounts or configured trusted publishers. Local archives are not evidence of a
registry publication; verify the exact version on each registry after upload.
