"""
DRC Engine — Design Rule Check
Simulates a Synopsys IC Validator / Calibre DRC flow.
"""

from __future__ import annotations
import json
import random
from dataclasses import dataclass, field
from typing import Any


# ── Rule definitions (mock_28nm PDK) ─────────────────────────────────────────

DRC_RULES: list[dict[str, Any]] = [
    {"rule": "M1.W.1",  "description": "Metal-1 min width",             "min_val": 0.09, "unit": "µm"},
    {"rule": "M1.S.1",  "description": "Metal-1 min spacing",           "min_val": 0.10, "unit": "µm"},
    {"rule": "V1.EN.1", "description": "Via-1 enclosure by Metal-1",    "min_val": 0.04, "unit": "µm"},
    {"rule": "POLY.W",  "description": "Poly min width",                "min_val": 0.03, "unit": "µm"},
    {"rule": "DIFF.S",  "description": "Diffusion min spacing",         "min_val": 0.12, "unit": "µm"},
    {"rule": "NWELL.W", "description": "N-well min width",              "min_val": 0.30, "unit": "µm"},
    {"rule": "M2.W.1",  "description": "Metal-2 min width",             "min_val": 0.10, "unit": "µm"},
    {"rule": "M2.S.1",  "description": "Metal-2 min spacing",           "min_val": 0.10, "unit": "µm"},
    {"rule": "CONT.EN", "description": "Contact enclosure by diffusion","min_val": 0.04, "unit": "µm"},
    {"rule": "GC.OV",   "description": "Gate-cut overlap on poly",      "min_val": 0.02, "unit": "µm"},
]


@dataclass
class DRCViolation:
    rule: str
    description: str
    layer: str
    x: float
    y: float
    measured: float
    required: float
    severity: str   # ERROR | WARNING


def run_drc(layout: dict[str, Any]) -> list[DRCViolation]:
    """
    Execute DRC rule deck against a parsed layout JSON.
    Returns a list of DRCViolation objects.
    """
    violations: list[DRCViolation] = []
    layers: list[dict] = layout.get("layers", [])
    seed = hash(layout.get("design_name", "cell")) & 0xFFFF
    rng = random.Random(seed)

    for layer_obj in layers:
        layer_name: str = layer_obj.get("name", "UNKNOWN")
        geometries: list[dict] = layer_obj.get("geometries", [])

        for geo in geometries:
            width: float = geo.get("width", 0.0)
            spacing: float = geo.get("spacing", 0.0)
            x: float = geo.get("x", 0.0)
            y: float = geo.get("y", 0.0)

            for rule in DRC_RULES:
                # Width check
                if "W" in rule["rule"] and layer_name.upper() in rule["rule"].upper():
                    if width > 0 and width < rule["min_val"]:
                        violations.append(DRCViolation(
                            rule=rule["rule"],
                            description=rule["description"],
                            layer=layer_name,
                            x=round(x + rng.uniform(0, 0.5), 4),
                            y=round(y + rng.uniform(0, 0.5), 4),
                            measured=round(width, 4),
                            required=rule["min_val"],
                            severity="ERROR",
                        ))

                # Spacing check
                if "S" in rule["rule"] and layer_name.upper() in rule["rule"].upper():
                    if spacing > 0 and spacing < rule["min_val"]:
                        violations.append(DRCViolation(
                            rule=rule["rule"],
                            description=rule["description"],
                            layer=layer_name,
                            x=round(x + rng.uniform(0, 0.5), 4),
                            y=round(y + rng.uniform(0, 0.5), 4),
                            measured=round(spacing, 4),
                            required=rule["min_val"],
                            severity="ERROR",
                        ))

    # Inject warnings for realism
    if layers and rng.random() < 0.6:
        sample_rule = rng.choice(DRC_RULES)
        violations.append(DRCViolation(
            rule=sample_rule["rule"],
            description=f"{sample_rule['description']} — near-limit",
            layer="GENERIC",
            x=round(rng.uniform(0, 10), 4),
            y=round(rng.uniform(0, 10), 4),
            measured=round(sample_rule["min_val"] * 1.01, 4),
            required=sample_rule["min_val"],
            severity="WARNING",
        ))

    return violations
