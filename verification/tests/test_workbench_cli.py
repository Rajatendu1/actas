"""Documented exit codes of the offline policy gate, run as an installed module."""
import json
import subprocess
import sys
from pathlib import Path

SAMPLES = Path(__file__).resolve().parent.parent / 'samples'


def run_gate(*args):
    return subprocess.run(
        [sys.executable, '-m', 'actas.workbench', *[str(a) for a in args]],
        capture_output=True, text=True)


def test_matching_pack_exits_zero():
    r = run_gate(SAMPLES / 'baseline.json')
    assert r.returncode == 0
    report = json.loads(r.stdout)
    assert report['matched'] == report['total']


def test_new_allowance_exits_one_with_report():
    r = run_gate(SAMPLES / 'candidate.json', SAMPLES / 'baseline.json')
    assert r.returncode == 1
    report = json.loads(r.stdout)
    assert report['newly_allowed'] == 1 and report['newly_denied'] == 0


def test_missing_file_exits_two_without_report():
    r = run_gate(SAMPLES / 'does-not-exist.json')
    assert r.returncode == 2
    assert r.stdout == ''
