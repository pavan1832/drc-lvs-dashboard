#!/usr/bin/env python3
"""
main.py — DRC/LVS Verification CLI Entry Point

Usage:
    python main.py --layout <path_to_layout.json> [--outdir <output_dir>]

Mirrors the invocation pattern used by Synopsys IC Validator batch runs.
The Streamlit web layer calls this script via subprocess.
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path


# ── Resolve sibling modules whether run from project root or /python ──────────
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from drc_engine      import run_drc
from lvs_engine      import run_lvs
from report_generator import generate_summary_txt, generate_drc_csv, generate_lvs_csv


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Mock DRC/LVS Verification Engine (Synopsys/Cadence style)"
    )
    p.add_argument("--layout", required=True,
                   help="Path to layout JSON file")
    p.add_argument("--outdir", default=None,
                   help="Output directory for reports (default: same as layout)")
    return p.parse_args()


def load_layout(path: str) -> dict:
    layout_path = Path(path)
    if not layout_path.exists():
        print(f"[ERROR] Layout file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(layout_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON in layout file: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    args = parse_args()
    layout_path = Path(args.layout).resolve()
    out_dir     = Path(args.outdir).resolve() if args.outdir else layout_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO]  Loading layout  : {layout_path}")
    layout = load_layout(str(layout_path))
    design_name = layout.get("design_name", "UNKNOWN")
    technology  = layout.get("technology", "mock_28nm")
    print(f"[INFO]  Design          : {design_name}")
    print(f"[INFO]  Technology      : {technology}")

    # ── DRC ──────────────────────────────────────────────────────────────────
    print("[INFO]  Running DRC rule deck …")
    drc_viols = run_drc(layout)
    drc_errors = [v for v in drc_viols if v.severity == "ERROR"]
    print(f"[INFO]  DRC complete    : {len(drc_viols)} violation(s) "
          f"({len(drc_errors)} error(s))")

    # ── LVS ──────────────────────────────────────────────────────────────────
    print("[INFO]  Running LVS comparison …")
    lvs_viols = run_lvs(layout)
    lvs_errors = [v for v in lvs_viols if v.severity == "ERROR"]
    print(f"[INFO]  LVS complete    : {len(lvs_viols)} violation(s) "
          f"({len(lvs_errors)} error(s))")

    # ── Reports ───────────────────────────────────────────────────────────────
    summary_txt  = generate_summary_txt(layout, drc_viols, lvs_viols)
    drc_csv      = generate_drc_csv(drc_viols)
    lvs_csv      = generate_lvs_csv(lvs_viols)

    (out_dir / "summary_report.txt").write_text(summary_txt, encoding="utf-8")
    (out_dir / "drc_violations.csv").write_text(drc_csv,     encoding="utf-8")
    (out_dir / "lvs_violations.csv").write_text(lvs_csv,     encoding="utf-8")

    print(f"[INFO]  Reports written : {out_dir}")

    # ── Sign-off status (machine-parseable for Streamlit layer) ───────────────
    overall_pass = len(drc_errors) == 0 and len(lvs_errors) == 0
    status = "PASS" if overall_pass else "FAIL"
    print(f"[SIGNOFF] STATUS={status} DRC_VIOLS={len(drc_viols)} "
          f"LVS_VIOLS={len(lvs_viols)}")
    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
