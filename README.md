# Actas: recovered source and new maintenance baseline

The original 0.14.1 application source has been recovered from its authorized
Vercel deployment. The guided policy workbench HTML and runtime configuration remain
unchanged recovered inputs. Twenty-eight of 31 recovered files remain byte-identical.
The current guide pointer and two lab input-validation modules are documented
maintenance edits in `REPOSITORY-CURATION.json`. `ORIGINAL-MANIFEST.json` retains
the original provider content IDs, SHA256 digests and sizes. This remains the
recovered 0.14.1 maintenance line, not the lost full development archive.

The lab rejects duplicate JSON fields, overly nested JSON and non-boolean
`bind_final` values with a client error. Normal fictional lab controls and valid
request behavior are unchanged.

This is not the lost full development archive. Its original tests, verification
scripts, target hash lock and operational/threat documents were excluded from
deployment and have not been recovered. The historical 295-test result must not
be presented as a result of this package. The original runtime README is retained in the private recovery archive. The
repository replaces that outdated development guide with a pointer to this
README. Use the commands below for this recovered baseline.

## Run and verify locally

Tested on Linux x86_64 with Python 3.10 and Chrome 156. A newly recorded fixed-version dependency resolution is supplied for this
recovery target. It has no wheel hashes and is not the lost hash-locked
installation; `verification/requirements-linux-py310-recovery.txt` records the dependency versions used.
Chrome must be available at `/usr/bin/google-chrome`, or set `CHROME_BIN` to its executable. The browser check uses a
fresh temporary profile and loopback servers only. No signed-in browser,
provider account, real token, API key or model call is needed.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r verification/requirements-linux-py310-recovery.txt
python -m pip install --no-build-isolation --no-deps -e ./source
sh verification/run_all.sh
```

Run the fictional application separately:

```sh
python -m uvicorn actas.app:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/`. Use non-sensitive examples only. The workbench
checks the supplied policy cases, not all possible requests or token security.
The issuer/lab is fictional and not a production authorization service.

## Offline policy gate

Export a policy pack from the workbench. Compare an edited candidate with the
saved baseline without the website:

```sh
python -m actas.workbench candidate.json baseline.json > comparison.json
```

Exit 0 means no supplied-case decision changed and candidate expectations match.
Exit 1 means a decision changed or an expectation mismatched. Exit 2 means invalid
input or a file error. A new allowance still returns 1 even if its expected
result was changed to Allow. A CI shell must preserve that nonzero status, for
example with `set -e`, rather than treating a JSON report as a successful gate.
The GitHub verification workflow runs on main pushes and pull requests, with
a read-only repository token and no deployment step. It installs the recorded
Python 3.10 dependencies and checksum-checked Chrome 156, then runs this gate.
Merge safeguards are configured separately; a workflow file alone cannot
prevent an untested merge.

## What the new checks establish

- Boundary regressions cover scope/audience/depth/lifetime combinations, strict
  input shapes, malformed JWT headers/claims, signature/issuer/audience/expiry,
  actor/client identity and holder-bound child exchange/resource proof behavior.
- Real-process checks stop the writer, back up encrypted SQLite, refuse a wrong
  passphrase/overwrite, remove the original location, restore/restart, and check
  retained keys/audit/revocations/replay. Offline rotation keeps newly retired
  old-created keys for overlap. A separate resource process fetches public JWKS
  and revocation state. All fixtures are fictional and temporary.
- Browser checks run actual unchanged recovered HTML on desktop and 390px,
  including custom cases, 9/8/9 intent versus permission comparison, real file
  export/reimport, duplicate input rejection, and delayed file/HTTP responses
  retaining newer drafts. Screenshots are local recovery evidence, not live
  production screenshots or independent user research.
- Integration checks reproduce exact downloaded live reports offline and run
  a real minimal local shell gate that fails on changed permissions.

These are new post-recovery checks, not restored originals, an audit, protocol
conformance certification, or equivalent coverage of the lost development suite.
In particular, exhaustive malformed-input/property coverage, external witnesses,
multi-instance replay/revocation consistency, a new fixed-target hash lock and
complete previous operations guidance remain outside this baseline. Browser
coverage is Chrome only, not screen-reader/cross-browser certification.

A restored old snapshot omits later revocations/proof use. No reconciliation,
RPO/RTO or compromise-response guarantee is implemented. Stop every writer
before snapshot/rotation; the CLI acknowledgement is not process detection.
Public demo issuer keys are throwaway. Do not replace real identity or consent
systems with this application. A source change alone does not promote a hosted deployment.

## Recovery provenance

Recovered November 11, 2026 from retained Vercel deployment inputs.
The provider content IDs and original digests are recorded in
`ORIGINAL-MANIFEST.json`; the documented README replacement and lab input-validation edits are exceptions
when checking that original manifest. `REPOSITORY-CURATION.json` records their hashes.

The immutable recovered archive SHA256 is
`5c013a488ad7b11e771f7604e70f8a4c43afa432a720d7e5b43ee17dbd3dd7bd`.
The lost full archive expected SHA256 is
`267ce423cefadfb5109a5afaa5e6e3f6d9fc905a1db9ae9e04d7883563883a21`.
They are different artifacts. The exact original runtime archive is preserved
separately from this repository baseline.

The full local maintenance-candidate gate passed on November 11, 2026. See
`verification/CLEAN-CHECKOUT-RESULTS.txt`. The test-client dependency emits a
Starlette/httpx deprecation warning. That warning is not a failed assertion,
but the dependency pair will need review before a future dependency update.
The workflow does not configure Vercel, provider secrets or automatic
production deployment.
