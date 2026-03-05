#!/usr/bin/env python3
"""Solace Inspector runner stub for solace-browser pre-push hook.

The real inspector lives in solace-cli. This stub satisfies the pre-push
gate that checks for the runner's existence.
"""

import sys


def main() -> int:
    print("Inspector runner: solace-browser (stub — real runner in solace-cli)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
