#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--phase-three-dir",
        required=True,
        help="Path to a PHASE_THREE directory (containing runs/...)",
    )
    args = ap.parse_args()

    phase_three_dir = os.path.abspath(str(args.phase_three_dir))
    runs_root = os.path.join(phase_three_dir, "runs")
    if not os.path.isdir(runs_root):
        print(f"Expected runs/ under: {phase_three_dir}", file=sys.stderr)
        return 2

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    from phase3_patterns import write_phase3_reports  # local import

    out = write_phase3_reports(phase_three_dir)
    print("Wrote:")
    for k, v in out.items():
        print(f"- {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

