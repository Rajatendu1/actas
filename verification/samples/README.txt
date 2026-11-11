Actas first-integration review evidence
Captured November 11, 2026, approximately 08:49-08:50 IST.
Source: the live Actas workbench , displayed version 0.14.1.

Actual Chrome downloads: actas-policy-pack.json and actas-policy-comparison.json.
baseline.json and candidate.json are extracted reusable inputs.
intent-matched-comparison.json is a subsequent live API response with the same
fictitious candidate cases except outside-policy.expect_allowed changed to true.
It matches 8/8 expectations but still reports one newly allowed request.
No tokens, credentials, personal data or private configuration were supplied.

These files establish the live export and permission-change interpretation leg
only. Fresh install, offline CLI parity and CI execution were NOT completed:
the private original source archive was unavailable. This evidence package is
not application source, a source reconstruction, or proof of adoption/security.

Original source recovery anchor: actas-0.14.1.tar.gz, transferred November 10
2026 at 15:56 IST; expected SHA256
267ce423cefadfb5109a5afaa5e6e3f6d9fc905a1db9ae9e04d7883563883a21.
Recover original bytes before resuming install/CLI/CI work.
