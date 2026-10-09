#!/usr/bin/env python3
"""Resolve bundled package relative to this file, even from another project."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dev_records.cli import main
raise SystemExit(main())
