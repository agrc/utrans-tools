"""Compatibility wrapper for renamed Utah recent-edits script.

Use Get_Utah_Recent_Edits.py going forward.
"""

from Get_Utah_Recent_Edits import main


if __name__ == "__main__":
    raise SystemExit(main())
