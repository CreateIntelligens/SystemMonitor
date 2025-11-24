#!/usr/bin/env python3
"""
Convenience entry point for the SystemMonitor CLI.
It ensures the backend package is on sys.path so users can call:
    python backend/cli.py <command>
"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from system_monitor.cli import main


if __name__ == "__main__":
    main()
