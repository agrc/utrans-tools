"""Compatibility wrapper for renamed Beaver recent-edits script.

Use Get_Beaver_Recent_Edits.py going forward.
"""

import os
import runpy


if __name__ == "__main__":
    target = os.path.join(os.path.dirname(__file__), "Get_Beaver_Recent_Edits.py")
    runpy.run_path(target, run_name="__main__")
