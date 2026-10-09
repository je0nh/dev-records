"""Optional standard-library coverage wrapper for CLI subprocess tests."""
import os
from pathlib import Path
import runpy
import sys
import trace
import uuid

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.argv = ['dev-records', *sys.argv[1:]]
counts = Path(os.environ['DEV_RECORDS_TRACE_DIR']) / (uuid.uuid4().hex + '.counts')
tracer = trace.Trace(count=True, trace=False, outfile=str(counts), ignoredirs=[str(Path(sys.base_prefix).resolve())])
try:
    tracer.runfunc(runpy.run_module, 'dev_records', run_name='__main__')
finally:
    tracer.results().write_results(show_missing=True, coverdir=str(counts.parent / counts.stem))
