"""Compatibility wrapper for unified county recent-edits runner.

Use cli/Get_Recent_Edits.py with --county Piute for the shared implementation.

Example:
  python Get_Piute_Recent_Edits.py
    --update-features "Z:\Documents\gdb\PiuteCo_20260414.gdb\Roads_2026_April"
    --base-features "Z:\Documents\gdb\PiuteCo_20251020.gdb\Roads"
"""

import os
import runpy
import sys


if __name__ == "__main__":
    target = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "Get_Recent_Edits.py"))
    passthrough = sys.argv[1:]
    if "--county" not in passthrough:
        passthrough = ["--county", "Piute"] + passthrough
    sys.argv = [sys.argv[0]] + passthrough
    runpy.run_path(target, run_name="__main__")
