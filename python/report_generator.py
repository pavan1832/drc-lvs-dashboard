"""
Report Generator
Produces EDA-style summary TXT and CSV outputs mirroring
Synopsys IC Validator / Cadence Pegasus report formats.
"""

from __future__ import annotations
import csv
import io
import textwrap
from datetime import datetime
from typing import Any

from drc_engine import DRCViolation
from lvs_engine import LVSViolation


TOOL_VERSION = "mock_icv-2024.12"
PDK_VERSION  = "mock_28nm-v3.1"
DIVIDER      = "=" * 72


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Summary TXT ───────────────────────────────────────────────────────────────

def generate_summary_txt(
    layout_meta: dict[str, Any],
    drc_violations: list[DRCViolation],
    lvs_violations: list[LVSViolation],
) -> str:
    drc_errors   = [v for v in drc_violations if v.severity == "ERROR"]
    lvs_errors   = [v for v in lvs_violations if v.severity == "ERROR"]
    overall_pass = len(drc_errors) == 0 and len(lvs_errors) == 0
    status_str   = "PASS ✓" if overall_pass else "FAIL ✗"

    lines = [
        DIVIDER,
        "  DRC/LVS VERIFICATION SIGN-OFF REPORT",
        f"  Tool     : {TOOL_VERSION}",
        f"  PDK      : {PDK_VERSION}",
        f"  Run Date : {_timestamp()}",
        DIVIDER,
        "",
        "  DESIGN INFORMATION",
        f"  Design Name  : {layout_meta.get('design_name', 'UNKNOWN')}",
        f"  Cell View    : layout",
        f"  Technology   : {layout_meta.get('technology', PDK_VERSION)}",
        f"  Top Cell     : {layout_meta.get('top_cell', layout_meta.get('design_name', 'UNKNOWN'))}",
        "",
        DIVIDER,
        "  DRC SUMMARY",
        DIVIDER,
        f"  Total DRC violations : {len(drc_violations)}",
        f"    Errors             : {len(drc_errors)}",
        f"    Warnings           : {len(drc_violations) - len(drc_errors)}",
        f"  DRC Status           : {'CLEAN' if len(drc_errors) == 0 else 'VIOLATIONS FOUND'}",
        "",
        DIVIDER,
        "  LVS SUMMARY",
        DIVIDER,
        f"  Total LVS violations : {len(lvs_violations)}",
        f"    Errors             : {len(lvs_errors)}",
        f"    Warnings           : {len(lvs_violations) - len(lvs_errors)}",
        f"  LVS Status           : {'CLEAN' if len(lvs_errors) == 0 else 'VIOLATIONS FOUND'}",
        "",
        DIVIDER,
        f"  OVERALL SIGN-OFF STATUS : {status_str}",
        DIVIDER,
        "",
    ]

    if drc_violations:
        lines += ["  DRC VIOLATION DETAILS", ""]
        for v in drc_violations:
            lines.append(
                f"  [{v.severity:<7}] {v.rule:<12} | {v.layer:<10} | "
                f"({v.x:.4f}, {v.y:.4f}) | "
                f"measured={v.measured:.4f} required={v.required:.4f} µm"
            )
        lines.append("")

    if lvs_violations:
        lines += ["  LVS VIOLATION DETAILS", ""]
        for v in lvs_violations:
            lines.append(
                f"  [{v.severity:<7}] {v.error_type:<20} | "
                f"{v.net_or_device:<14} | "
                f"sch={v.schematic_val}  lay={v.layout_val}"
            )
        lines.append("")

    lines += [DIVIDER, "  END OF REPORT", DIVIDER]
    return "\n".join(lines)


# ── DRC CSV ───────────────────────────────────────────────────────────────────

def generate_drc_csv(violations: list[DRCViolation]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Severity", "Rule", "Description", "Layer",
        "X (µm)", "Y (µm)", "Measured (µm)", "Required (µm)"
    ])
    for v in violations:
        writer.writerow([
            v.severity, v.rule, v.description, v.layer,
            v.x, v.y, v.measured, v.required,
        ])
    return output.getvalue()


# ── LVS CSV ───────────────────────────────────────────────────────────────────

def generate_lvs_csv(violations: list[LVSViolation]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Severity", "Error Type", "Description",
        "Net / Device", "Schematic Value", "Layout Value"
    ])
    for v in violations:
        writer.writerow([
            v.severity, v.error_type, v.description,
            v.net_or_device, v.schematic_val, v.layout_val,
        ])
    return output.getvalue()
