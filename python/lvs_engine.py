"""
LVS Engine — Layout vs. Schematic
Simulates a Synopsys StarRC / Calibre LVS netlisting and comparison flow.
"""

from __future__ import annotations
import hashlib
import random
from dataclasses import dataclass
from typing import Any

# ── LVS error taxonomy (mirrors Calibre LVS output categories) ───────────────

LVS_ERROR_TYPES = [
    ("NET_OPEN",          "Net open — missing connection between nodes"),
    ("NET_SHORT",         "Net short — unintended connection detected"),
    ("DEVICE_MISMATCH",   "Device mismatch — W/L ratio does not match schematic"),
    ("MISSING_DEVICE",    "Missing device — element in schematic absent from layout"),
    ("EXTRA_DEVICE",      "Extra device — layout element has no schematic counterpart"),
    ("PORT_MISMATCH",     "Port mismatch — pin name or direction inconsistency"),
    ("PARAM_MISMATCH",    "Parameter mismatch — device parameter outside tolerance"),
    ("FLOATING_NODE",     "Floating node — net with no drive or load"),
]


@dataclass
class LVSViolation:
    error_type: str
    description: str
    net_or_device: str
    schematic_val: str
    layout_val: str
    severity: str   # ERROR | WARNING


def _extract_net_names(layout: dict[str, Any]) -> list[str]:
    nets = layout.get("nets", [])
    if nets:
        return [n.get("name", f"net_{i}") for i, n in enumerate(nets)]
    # Synthesise plausible net names from layer data
    return ["VDD", "VSS", "CLK", "D", "Q", "A", "B", "Z", "NET_001", "NET_002"]


def run_lvs(layout: dict[str, Any]) -> list[LVSViolation]:
    """
    Execute LVS comparison between extracted layout netlist and reference schematic.
    Returns a list of LVSViolation objects.
    """
    violations: list[LVSViolation] = []
    seed = (int(hashlib.md5(layout.get("design_name", "cell").encode()).hexdigest(), 16) ^ 0xA5A5) & 0xFFFF
    rng = random.Random(seed)

    net_names = _extract_net_names(layout)
    devices = layout.get("devices", [])

    # ── Check explicitly defined nets ────────────────────────────────────────
    for net in layout.get("nets", []):
        net_name = net.get("name", "UNNAMED")
        connections = net.get("connections", 0)

        if connections == 0:
            violations.append(LVSViolation(
                error_type="FLOATING_NODE",
                description=f"Net '{net_name}' has no connections",
                net_or_device=net_name,
                schematic_val=">0 connections",
                layout_val="0",
                severity="ERROR",
            ))
        elif connections == 1:
            violations.append(LVSViolation(
                error_type="NET_OPEN",
                description=f"Net '{net_name}' is open (single terminal)",
                net_or_device=net_name,
                schematic_val="≥2 connections",
                layout_val="1",
                severity="ERROR",
            ))

    # ── Check explicitly defined devices ─────────────────────────────────────
    for dev in devices:
        dev_name = dev.get("name", "UNKNOWN")
        sch_w = dev.get("schematic_width", 0.0)
        lay_w = dev.get("layout_width", 0.0)
        tolerance = 0.01  # 1% tolerance

        if sch_w > 0 and abs(sch_w - lay_w) / sch_w > tolerance:
            violations.append(LVSViolation(
                error_type="DEVICE_MISMATCH",
                description=f"W mismatch on device '{dev_name}'",
                net_or_device=dev_name,
                schematic_val=f"{sch_w:.4f} µm",
                layout_val=f"{lay_w:.4f} µm",
                severity="ERROR",
            ))

    # ── Probabilistic fault injection for realism ─────────────────────────────
    fault_count = rng.randint(0, 3)
    for _ in range(fault_count):
        etype, edesc = rng.choice(LVS_ERROR_TYPES)
        net = rng.choice(net_names)
        violations.append(LVSViolation(
            error_type=etype,
            description=edesc,
            net_or_device=net,
            schematic_val=rng.choice(["1", "W=0.28µm", "NMOS", "VDD"]),
            layout_val=rng.choice(["0", "W=0.30µm", "PMOS", "UNDRIVEN"]),
            severity="ERROR" if rng.random() > 0.3 else "WARNING",
        ))

    return violations
