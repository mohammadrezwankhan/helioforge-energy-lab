# Standalone production-audit integration — 20 October 2026

The 13 supplied HF-RUN patches were checksum-verified and replayed in order at
deployed revision `79619841db052115db0af90c4dda6b768e03a1b2`, then integrated with
main at `712c15e9fb4a946bb7f6eb767959f6740e699325`. The newer XML security fixes,
lesson documentation and animation gallery are preserved. Generated files were
rebuilt from the integrated Python and TypeScript source.

The changes correct runtime canonical/provenance metadata, both broken study
references, lesson progress and storage-failure/reset handling, exact slider
defaults, comparison Pin state, annual-policy flow accounting, monthly import
peaks, complete frozen hybrid coverage, and the mobile Export evidence name.

The public boundary remains 36 architectures and 36 lessons, with 19 numerical
and 17 study-only architectures: 285 numerical pairs, 349 applicable study-only
pairs, and 230 inapplicable pairs. Edited inputs hide stale results; new
calculations require the separate local Python API.

## Local evidence

Windows, Python 3.12.14, Node 24.20.0, npm 11.19.0, pytest 9.1.1 and Ruff 0.17.1:

| Check | Observed result |
| --- | --- |
| Original audited base | 579 Python and 141 frontend tests passed |
| Patched audited base | 587 Python and 171 frontend tests passed |
| Integrated source | 613 Python and 171 frontend tests passed |
| Added artifact-verifier regressions | 11 passed; roundoff, type and nonfinite regressions failed the initial exact-comparison implementation |
| Original numerical bugs | Four focused tests failed the original engines; patched complete suites passed |
| Typecheck/build, generated-data arithmetic, preview/domain/collection checks | Passed |
| Engineering-film release checks | Three tests passed |
| npm audit at moderate threshold | Zero vulnerabilities reported |
| Native Chromium, direct local HTTP (no bridge) | All six suites passed: 18 smoke, 14 hybrid, 18 workspace, 24 study and 10 completion checks; twelve accessibility scans returned no violations |

Desktop and mobile screenshots were inspected. Browser evidence was produced in
a separate checkout so it cannot overwrite historical source evidence. These
checks are not a complete assistive-technology or scientific calibration audit.

## Integration repairs

The first Windows publication build rejected engineering-film files after Git
converted LF to CRLF. The release-media subtree now disables text conversion,
preserving the bytes covered by its existing size/SHA-256 manifest.

The first Linux CI browser job exposed platform-dependent floating-point results
in the generated hybrid bundle. `scripts/check-hybrid-assets.py` now compares all
committed cases against fresh model outputs, accepting only `1e-12` relative or
absolute numerical result roundoff. Inputs, identifiers, metadata, field/series
structure, catalogue/matrix records and browser/JSON agreement remain exact.
Every stored dataset digest must still match its own complete content. Changed
inputs, material results, nonfinite values and corrupt digests are rejected.
The checker reports the actual numerical difference; CI then builds its own
platform's results. No generated numerical value is hand-edited.

A separate read-only source review found no blocking defect. One minor test
improvement remains: the provenance fetch mock could also assert URL/options;
the current implementation already uses a same-origin URL and omitted credentials.

## Reproduction and publication

Run `python scripts/check-hybrid-assets.py`, the complete Python tests and Ruff,
then the web typecheck/build/tests. Run the six `scripts/browser-*.py` gates
against a loopback API with external AI disabled. The supplied audit package
also provides independent generated-data and effective-CSP verification scripts.

[Integration PR and CI](https://github.com/mohammadrezwankhan/helioforge-energy-lab/pull/22)
retain the remote matrix and merge evidence. Publication must build `app.json`
from the final public merge revision, compute a fresh runtime SHA-256, update
the dedicated host's existing CSP hash allowlists while retaining its scoped
film-frame exception, and verify actual live bytes/headers plus browser hydration.
The local test results above do not themselves assert that deployment succeeded.
