# Hosted CSV acceptance oracle correction

Reviewed against source commit `65f18b6a09bba87f85c9866738e08931741c1164`
on 5 November 2026.

## Observed failure

[Research release run 42048802552](https://github.com/mohammadrezwankhan/helioforge-energy-lab/actions/runs/42048802552)
completed the hosted acceptance suite with 33 passing checks and one failing
check. The failing check covered the 59 study table CSV exports; only
`pilots-offgas` and `council-debate` differed. Their JSON exports, data row
counts, provenance, and record metadata all passed. The retained
`browser-evidence` artifact is ID `13427080057`, with SHA-256
`33d1557ae45c24890c91e332d9647a8496b786a04ccc186e673b16d935fcdcd2`.

Those two tables contain object-valued cells: sensor exceedances and structured
debate evidence. The application already preserves those objects as JSON in
CSV cells. Its existing `core.test.mjs` explicitly tests this behavior. The
acceptance oracle still used JavaScript's implicit object conversion, which
replaces each structured record with `[object Object]`. That lossy oracle
produced different CSV hashes despite correct downloaded values.

## Correction and retained checks

The browser-side expectation expression is now named so that regression tests
can execute the exact expression passed to Playwright. Its independent CSV
encoder serializes object cells as JSON and retains the existing recursive
comma-joined array representation, null/boolean/numeric conversion, quotation
escaping, and spreadsheet formula defenses.

The oracle still reads the source study data rather than calling the
application's CSV implementation. Full exported-byte SHA-256 comparisons,
all 59 studies, row counts, metadata, provenance, empty-table behavior,
series checks, JSON checks and memorandum checks remain enforced. Numerical
implementations, frozen study data, generated browser assets and product
export behavior are unchanged by this correction.

## Local regression evidence and hosted boundary

Before the correction, the new controls reproduced the exact two study hash
mismatches and rejected lossy object/array encoding. The scalar quoting and
formula-defense control already passed. After the correction, all five tests
pass, including comparison of all 59 unchanged application CSV exports with
the independent oracle. Expected fixture bytes are built with Python's CSV
writer from explicit cell text, independently of the JavaScript encoder.

Five mutation controls reject object placeholders, a changed sensor value, a
missing row, a missing provenance column and changed record metadata. A
guarded runtime prevents the oracle from calling application CSV helpers.
The release workflow now executes these controls before browser acceptance;
the existing hardened Python gate also discovers them.

These local results execute the exact browser expression in Node and inspect
the unchanged bundle. They are not a new Playwright browser run or a
production-deployment claim. Hosted acceptance must pass on the published
follow-up commit before this release check is reported as green.
