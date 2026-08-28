"""Compatibility wrapper for add-only attribute rule behavior.

For new deployments, use deploy_ar.py directly.
"""

from __future__ import annotations

import sys

from deploy_ar import main as deploy_main


def main() -> None:
	argv = sys.argv[1:]
	if "--mode" in argv:
		raise RuntimeError("new_ar.py does not accept --mode. Use deploy_ar.py for mode selection.")
	deploy_main(["--mode", "add", *argv])


if __name__ == "__main__":
	main()
