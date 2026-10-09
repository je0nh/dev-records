#!/usr/bin/env python3
"""Run subprocess CLI tests with standard-library line coverage (no dependencies)."""
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import trace

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='dev-records-coverage-') as directory:
    env = dict(os.environ, DEV_RECORDS_TRACE_DIR=directory)
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=root, env=env)
    combined = trace.CoverageResults()
    for file in Path(directory).glob('*.counts'):
        # Only counts produced by our subprocesses in this private temp directory.
        counts, called, callers = pickle.loads(file.read_bytes())
        counts = {key: count for key, count in counts.items()
                  if Path(key[0]).parent == root / 'dev_records'}
        combined.update(trace.CoverageResults(counts=counts))
    combined.write_results(show_missing=True, summary=True, coverdir=str(Path(directory) / 'combined'))
    sys.exit(result.returncode)
