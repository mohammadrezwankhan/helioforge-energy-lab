# Acceptance server request boundary

The full main-branch CodeQL run `42079757929` at
`c9cdfe65714e874006289c2f8d92d4b59a42c435` reported four
`py/path-injection` flows and one `py/http-response-splitting` flow in
`scripts/serve-acceptance.py`. Its Python artifact `13439504117` has SHA-256
`21c9117d9c0e7f3392e0f9da87f17609c8148e965c1f3fec8074e1f8019d3679`.

The original containment check preceded the directory `index.html` append.
A synthetic HTTP regression demonstrated that both directory aliases could
therefore read an index symlink outside the approved generated site. The
Content-Type finding traced request-derived filenames into MIME selection;
the regression does not claim a demonstrated header-injection exploit.

The server now snapshots completed generated files before listening. Each
request selects immutable bytes and a predetermined MIME value by route key;
it does not construct filesystem paths or read files. Snapshot construction
omits file and directory symlinks, control-character names and private metadata
routes. Directory index aliases remain generated from the actual inventory.
GET, HEAD, exact CSP, deterministic gzip, ETag, length, cache, noindex and TLS
behavior are retained. Importing the module no longer parses arguments or
starts a listener.

The actual main-run browser artifact `13441235315` has SHA-256
`fa8060f271b7a93d48f08e73dd88d7eb397830b7a59cd867d6420c757c29f653`.
Its export contains 364 files totaling 42,118,307 bytes. Snapshot startup rejects
inventories exceeding 4,096 entries or 128 MiB of loaded payload. The fixed MIME
map covers every suffix in this export; unrecognized extensions use
`application/octet-stream`. All 362 public files and 21 additional index aliases
were exercised over real local HTTP with exact bytes, MIME, CSP, lengths and
ETags compared to the original export. The largest file's gzip representation
also matched exactly. TLS was checked with an ephemeral local test certificate,
normal certificate verification and an untrusted-certificate negative control.

The generated export must remain stable during startup: its producer must
finish before this laboratory server loads it. The snapshot is not a filesystem
sandbox against a concurrent local writer during construction. Subsequent file
changes cannot affect its frozen routes. The payload bound does not claim to
bound all concurrent HTTP response buffers. This remains a loopback acceptance
tool, not a publicly deployable server.

`scripts/test_serve_acceptance.py` contains real HTTP regressions for the escape,
post-start mutation, absence of request-time file reads, traversal, symlinks,
private files, control characters, response semantics, import safety and startup
limits. Existing quality configuration already includes all scripts in lint,
strict types, tests and source analysis. No application calculations, fixtures,
tolerances, scanner rules, query scope or existing tests were changed.

The CodeQL push filter additionally names
`codex/helio-acceptance-server-20261105` so the repair receives full analysis before
merge. All other triggers, permissions, pinned actions, languages and the existing
fail-closed SARIF gate remain unchanged. Local checks are supporting evidence;
the new branch's hosted full CodeQL and original checks remain required.
