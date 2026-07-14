"""Compatibility wrapper for renamed Carbon recent-edits script.

Use Get_Carbon_Recent_Edits.py going forward.
"""

from Get_Carbon_Recent_Edits import main


if __name__ == "__main__":
    raise SystemExit(main())
