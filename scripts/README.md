# Scripts

`python3 scripts/check.py` runs Python syntax, unit and integration checks.
`node scripts/browser-check.cjs` runs the optional local-only browser suite;
see [testing](../docs/testing/V0_ACCEPTANCE.md) for its development dependencies.

`python3 scripts/build_demo.py` builds a portable ZIP from the committed `HEAD`
under ignored `dist/`. It requires Git only while building, never for launching
the extracted app. See [demo bundle](../docs/DEMO_BUNDLE.md).

The separately opted-in live voice harness is documented in
[live validation](../docs/testing/LIVE_VOICE.md). It is excluded from demo bundles
and is never called by the default suite or CI. The two planned overnight paid
attempts are exhausted; do not reset its ledger or run additional paid inference.
