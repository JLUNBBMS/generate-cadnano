#!/usr/bin/env python3
"""Check the generation dependency. cadnano2 is optional for integration QA."""
from importlib.metadata import PackageNotFoundError, version
import sys

if sys.version_info < (3, 10):
    print("Generation requires Python >= 3.10")
    raise SystemExit(1)
try:
    import scadnano
    installed = version("scadnano")
except (ImportError, PackageNotFoundError):
    print("Missing scadnano; run: python -m pip install -r requirements.txt")
    raise SystemExit(1)
if installed != "0.20.1":
    print(f"Unverified scadnano version {installed}; install requirements.txt")
    raise SystemExit(1)
print("scadnano 0.20.1 installed; generation dependency OK")
