#!/bin/sh
# New recovery suite only. Requires installed source and verification deps.
set -eu
cd "$(dirname "$0")/.."
python verification/scripts/check_original.py
python -m pytest verification/tests -q
python verification/check_integration.py
python verification/scripts/check_process.py
python verification/scripts/check_browser.py
