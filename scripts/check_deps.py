#!/usr/bin/env python3
"""Check that scadnano is installed and report its version."""
import sys
from importlib.metadata import version, PackageNotFoundError

# Required: scadnano
try:
    import scadnano
    try:
        ver = version("scadnano")
    except PackageNotFoundError:
        ver = "unknown"
    print(f"scadnano {ver} installed")
except ImportError:
    print("scadnano NOT installed — run: pip install scadnano")
    sys.exit(1)
