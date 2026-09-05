"""Frozen Flick helper entry. Bundles its own Python; friends never install one."""

from __future__ import annotations

import multiprocessing
import sys


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--update" in args:
        from app.update import check_and_apply

        result = check_and_apply()
        return 0 if result.ok else 1
    from app.pastehost import main as paste_main

    return paste_main()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
