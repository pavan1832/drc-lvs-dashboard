"""
app.py — DRC/LVS Verification Dashboard
========================================
Web UI layer built on Streamlit.
Business logic is intentionally isolated in python/main.py (the engine).
This layer is responsible ONLY for:
  - File upload / user interaction
  - Subprocess orchestration
  - Report display and download
"""

from __future__ import annotations
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Path resolution ────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent.resolve()
ENGINE    = ROOT / "python" / "main.py"
TCL_SCRIPT = ROOT / "tcl" / "mock_drc_lvs.tcl"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
  
    page_title="DRC/LVS Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (industrial / EDA aesthetic) ────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
  }
  code, pre, .stCodeBlock, .monospace {
    font-family: 'JetBrains Mono', monospace !important;
  }

  /* Dark industrial palette */
  .stApp {
    background: #0d1117;
    color: #e6edf3;
  }

  .main-header {
    background: linear-gradient(135deg, #0f2942 0%, #0d1f36 50%, #061020 100%);
    border: 1px solid #1e3a5f;
    border-left: 4px solid #00d4ff;
    padding: 1.5rem 2rem;
    border-radius: 4px;
    margin-bottom: 1.5rem;
  }
  .main-header h1 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    color: #00d4ff;
    margin: 0;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .main-header .subtitle {
    color: #7d9ab5;
    font-size: 0.85rem;
    margin-top: 0.3rem;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.05em;
  }

  .metric-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 1.2rem 1.4rem;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
  }
  .metric-label {
    font-size: 0.72rem;
    color: #7d9ab5;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
  }
  .metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #e6edf3;
  }
  .metric-value.violation { color: #f85149; }
  .metric-value.clean     { color: #3fb950; }

  .status-pass {
    background: linear-gradient(135deg, #0d2818, #0a1f12);
    border: 2px solid #3fb950;
    border-radius: 8px;
    padding: 1.5rem;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #3fb950;
    letter-spacing: 0.15em;
    text-shadow: 0 0 20px rgba(63,185,80,0.4);
  }
  .status-fail {
    background: linear-gradient(135deg, #2d0f0f, #200a0a);
    border: 2px solid #f85149;
    border-radius: 8px;
    padding: 1.5rem;
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #f85149;
    letter-spacing: 0.15em;
    text-shadow: 0 0 20px rgba(248,81,73,0.4);
  }

  .section-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #7d9ab5;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    border-bottom: 1px solid #21262d;
    padding-bottom: 0.5rem;
    margin: 1.5rem 0 1rem 0;
  }

  .log-block {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #8b949e;
    max-height: 250px;
    overflow-y: auto;
    white-space: pre-wrap;
  }
  .log-info  { color: #58a6ff; }
  .log-error { color: #f85149; }
  .log-warn  { color: #d29922; }
  .log-signoff { color: #3fb950; font-weight: 700; }

  .stButton > button {
    background: linear-gradient(135deg, #1e3a5f, #0f2942);
    color: #00d4ff;
    border: 1px solid #1e4a7a;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    letter-spacing: 0.05em;
    padding: 0.5rem 1.5rem;
    width: 100%;
    transition: all 0.2s;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #1e4a7a, #1e3a5f);
    border-color: #00d4ff;
    color: #ffffff;
    box-shadow: 0 0 12px rgba(0,212,255,0.3);
  }

  .stDownloadButton > button {
    background: #161b22;
    color: #8b949e;
    border: 1px solid #30363d;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    border-radius: 4px;
  }

  .stAlert {
    font-family: 'IBM Plex Sans', sans-serif;
  }

  /* Style dataframes */
  .stDataFrame {
    border: 1px solid #21262d !important;
    border-radius: 4px;
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #21262d;
  }

  .sidebar-section {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #7d9ab5;
  }
  .sidebar-section h4 {
    color: #58a6ff;
    margin: 0 0 0.7rem 0;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .sidebar-section p {
    margin: 0.2rem 0;
    line-height: 1.6;
  }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════════

def _parse_stdout(stdout: str) -> dict:
    """Extract sign-off fields from the engine's [SIGNOFF] line."""
    result = {"status": None, "drc_viols": 0, "lvs_viols": 0}
    for line in stdout.splitlines():
        if "[SIGNOFF]" in line:
            m = re.search(r"STATUS=(\w+)\s+DRC_VIOLS=(\d+)\s+LVS_VIOLS=(\d+)", line)
            if m:
                result["status"]    = m.group(1)
                result["drc_viols"] = int(m.group(2))
                result["lvs_viols"] = int(m.group(3))
    return result


def _run_engine(layout_path: Path, out_dir: Path) -> tuple[int, str, str]:
    """
    Invoke python/main.py via subprocess.
    Returns (returncode, stdout, stderr).
    """
    cmd = [
        sys.executable,
        str(ENGINE),
        "--layout", str(layout_path),
        "--outdir", str(out_dir),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr


def _run_tcl(design_name: str, technology: str) -> tuple[int, str]:
    """
    Invoke the TCL mock engine via tclsh (if available).
    Returns (returncode, stdout).
    """
    tclsh = shutil.which("tclsh")
    if not tclsh:
        return -1, "[WARN]  tclsh not found — TCL phase skipped.\n"
    try:
        proc = subprocess.run(
            [tclsh, str(TCL_SCRIPT), design_name, technology],
            capture_output=True, text=True, timeout=30,
        )
        return proc.returncode, proc.stdout + proc.stderr
    except Exception as exc:
        return -1, f"[WARN]  TCL invocation failed: {exc}\n"


def _colorise_log(raw: str) -> str:
    """Wrap log lines in coloured spans for HTML rendering."""
    lines = []
    for line in raw.splitlines():
        if "[SIGNOFF]" in line:
            lines.append(f'<span class="log-signoff">{line}</span>')
        elif "[ERROR]" in line or "[error]" in line.lower():
            lines.append(f'<span class="log-error">{line}</span>')
        elif "[WARN]" in line:
            lines.append(f'<span class="log-warn">{line}</span>')
        else:
            lines.append(f'<span class="log-info">{line}</span>')
    return "\n".join(lines)


def _load_csv_safe(path: Path) -> pd.DataFrame | None:
    if path.exists() and path.stat().st_size > 0:
        try:
            return pd.read_csv(path)
        except Exception:
            return None
    return None


def _sample_layout_json() -> str:
    """Return a realistic sample layout JSON for demo purposes."""
    sample = {
        "design_name": "INVERTER_28NM",
        "technology": "mock_28nm",
        "top_cell": "INV_X1",
        "layers": [
            {
                "name": "M1",
                "geometries": [
                    {"x": 0.0,  "y": 0.0,  "width": 0.07, "spacing": 0.08},
                    {"x": 0.5,  "y": 0.0,  "width": 0.12, "spacing": 0.15},
                ]
            },
            {
                "name": "POLY",
                "geometries": [
                    {"x": 0.2,  "y": 0.1,  "width": 0.025, "spacing": 0.05},
                ]
            },
            {
                "name": "DIFF",
                "geometries": [
                    {"x": 0.0,  "y": 0.3,  "width": 0.20,  "spacing": 0.10},
                ]
            },
        ],
        "nets": [
            {"name": "VDD",  "connections": 4},
            {"name": "VSS",  "connections": 3},
            {"name": "IN",   "connections": 2},
            {"name": "OUT",  "connections": 1},   # will trigger NET_OPEN
        ],
        "devices": [
            {
                "name": "MN0",
                "type": "NMOS",
                "schematic_width": 0.28,
                "layout_width":    0.30,           # W mismatch → LVS FAIL
            },
            {
                "name": "MP0",
                "type": "PMOS",
                "schematic_width": 0.56,
                "layout_width":    0.56,
            },
        ],
    }
    return json.dumps(sample, indent=2)


# ════════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ════════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div class="sidebar-section">
      <h4>⚙ Tool Info</h4>
      <p>Engine  : mock_icv-2024.12</p>
      <p>PDK     : mock_28nm-v3.1</p>
      <p>Mode    : DRC + LVS</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="sidebar-section">
      <h4>📦 Sample Layout</h4>
      <p>Download a pre-built JSON to try the tool immediately.</p>
    </div>
    """, unsafe_allow_html=True)

    st.download_button(
        label="⬇  Download sample_layout.json",
        data=_sample_layout_json(),
        file_name="sample_layout.json",
        mime="application/json",
    )

    st.markdown("""
    <div class="sidebar-section">
      <h4>ℹ Layout JSON Schema</h4>
      <p><b>design_name</b>  : string</p>
      <p><b>technology</b>   : string</p>
      <p><b>layers[]</b>     : name, geometries</p>
      <p>  geometry: x, y, width, spacing</p>
      <p><b>nets[]</b>       : name, connections</p>
      <p><b>devices[]</b>    : name, type, schematic_width, layout_width</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="sidebar-section">
      <h4>🔗 Architecture</h4>
      <p>UI      → Streamlit (app.py)</p>
      <p>Engine  → Python subprocess</p>
      <p>TCL     → tclsh mock flow</p>
      <p>Reports → TXT + CSV</p>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  MAIN PANEL
# ════════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
  <h1>🔬 DRC / LVS Verification Dashboard</h1>
  <div class="subtitle">
    mock_icv-2024.12 &nbsp;·&nbsp; mock_28nm &nbsp;·&nbsp;
    Synopsys Custom Compiler / Cadence Virtuoso Compatible Flow
  </div>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">01 — LAYOUT UPLOAD</div>', unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Upload layout JSON (GDS-derived / OpenAccess export)",
    type=["json"],
    help="JSON must contain: design_name, technology, layers, nets, devices",
)

if uploaded:
    try:
        layout_preview = json.loads(uploaded.getvalue())
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.success(
                f"✓  Loaded: **{layout_preview.get('design_name', 'UNKNOWN')}** "
                f"| Technology: `{layout_preview.get('technology', '—')}`"
            )
        with col_b:
            st.info(f"{uploaded.size / 1024:.1f} KB")
    except json.JSONDecodeError:
        st.error("❌  File is not valid JSON. Please check your layout export.")
        st.stop()

    # ── Run button ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">02 — RUN VERIFICATION</div>', unsafe_allow_html=True)

    run_col, _ = st.columns([1, 2])
    with run_col:
        run_clicked = st.button("▶  Run DRC / LVS", use_container_width=True)

    if run_clicked:
        with tempfile.TemporaryDirectory(prefix="drc_lvs_") as tmpdir:
            tmp = Path(tmpdir)
            layout_file = tmp / "layout.json"
            layout_file.write_bytes(uploaded.getvalue())

            # ── TCL phase (cosmetic, EDA realism) ─────────────────────────────
            design_name = layout_preview.get("design_name", "UNKNOWN")
            technology  = layout_preview.get("technology", "mock_28nm")

            with st.spinner("Running TCL mock engine (tclsh) …"):
                tcl_rc, tcl_log = _run_tcl(design_name, technology)

            # ── Python engine ──────────────────────────────────────────────────
            with st.spinner("Running Python DRC/LVS engine …"):
                t0 = time.time()
                rc, stdout, stderr = _run_engine(layout_file, tmp)
                elapsed = time.time() - t0

            # ── Parse results ──────────────────────────────────────────────────
            parsed = _parse_stdout(stdout)
            status     = parsed["status"]
            drc_viols  = parsed["drc_viols"]
            lvs_viols  = parsed["lvs_viols"]

            if status is None and rc != 0:
                st.error(
                    "**Engine failed to produce a sign-off result.**\n\n"
                    f"```\n{stderr or stdout}\n```"
                )
                st.stop()

            # ════════════════════════════════════════════════════════════════
            #  RESULTS PANEL
            # ════════════════════════════════════════════════════════════════
            st.markdown('<div class="section-header">03 — VERIFICATION RESULTS</div>',
                        unsafe_allow_html=True)

            # Sign-off status banner
            if status == "PASS":
                st.markdown(
                    '<div class="status-pass">✓ &nbsp; SIGN-OFF : PASS</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="status-fail">✗ &nbsp; SIGN-OFF : FAIL</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Metric row
            m1, m2, m3, m4, m5 = st.columns(5)
            with m1:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-label">Design</div>
                  <div class="metric-value" style="font-size:1rem">{design_name}</div>
                </div>""", unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-label">Technology</div>
                  <div class="metric-value" style="font-size:1rem">{technology}</div>
                </div>""", unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-label">DRC Violations</div>
                  <div class="metric-value {'violation' if drc_viols else 'clean'}">{drc_viols}</div>
                </div>""", unsafe_allow_html=True)
            with m4:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-label">LVS Violations</div>
                  <div class="metric-value {'violation' if lvs_viols else 'clean'}">{lvs_viols}</div>
                </div>""", unsafe_allow_html=True)
            with m5:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-label">Runtime</div>
                  <div class="metric-value" style="font-size:1.1rem">{elapsed:.2f}s</div>
                </div>""", unsafe_allow_html=True)

            # ── Violation tables ───────────────────────────────────────────────
            st.markdown('<div class="section-header">04 — VIOLATION TABLES</div>',
                        unsafe_allow_html=True)

            drc_tab, lvs_tab = st.tabs(["🔴  DRC Violations", "🟠  LVS Violations"])

            drc_df = _load_csv_safe(tmp / "drc_violations.csv")
            with drc_tab:
                if drc_df is not None and not drc_df.empty:
                    err_mask = drc_df.get("Severity", pd.Series()) == "ERROR"
                    st.caption(
                        f"{len(drc_df)} total &nbsp;|&nbsp; "
                        f"{err_mask.sum()} errors &nbsp;|&nbsp; "
                        f"{(~err_mask).sum()} warnings"
                    )
                    st.dataframe(
                        drc_df.style.apply(
                            lambda row: [
                                "color: #f85149" if row.get("Severity") == "ERROR"
                                else "color: #d29922"
                                for _ in row
                            ],
                            axis=1,
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.success("✓ No DRC violations — rule deck passed cleanly.")

            lvs_df = _load_csv_safe(tmp / "lvs_violations.csv")
            with lvs_tab:
                if lvs_df is not None and not lvs_df.empty:
                    err_mask = lvs_df.get("Severity", pd.Series()) == "ERROR"
                    st.caption(
                        f"{len(lvs_df)} total &nbsp;|&nbsp; "
                        f"{err_mask.sum()} errors &nbsp;|&nbsp; "
                        f"{(~err_mask).sum()} warnings"
                    )
                    st.dataframe(
                        lvs_df.style.apply(
                            lambda row: [
                                "color: #f85149" if row.get("Severity") == "ERROR"
                                else "color: #d29922"
                                for _ in row
                            ],
                            axis=1,
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.success("✓ LVS clean — layout matches schematic netlist.")

            # ── Downloads ──────────────────────────────────────────────────────
            st.markdown('<div class="section-header">05 — REPORT DOWNLOADS</div>',
                        unsafe_allow_html=True)

            dl1, dl2, dl3 = st.columns(3)

            summary_path = tmp / "summary_report.txt"
            if summary_path.exists():
                with dl1:
                    st.download_button(
                        label="📄  summary_report.txt",
                        data=summary_path.read_bytes(),
                        file_name="summary_report.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )

            drc_csv_path = tmp / "drc_violations.csv"
            if drc_csv_path.exists():
                with dl2:
                    st.download_button(
                        label="📊  drc_violations.csv",
                        data=drc_csv_path.read_bytes(),
                        file_name="drc_violations.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

            lvs_csv_path = tmp / "lvs_violations.csv"
            if lvs_csv_path.exists():
                with dl3:
                    st.download_button(
                        label="📊  lvs_violations.csv",
                        data=lvs_csv_path.read_bytes(),
                        file_name="lvs_violations.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

            # ── Engine logs ────────────────────────────────────────────────────
            with st.expander("🔧 Engine Logs (Python + TCL)", expanded=False):
                combined = (tcl_log or "") + "\n" + stdout + (f"\n[STDERR]\n{stderr}" if stderr else "")
                st.markdown(
                    f'<div class="log-block">{_colorise_log(combined)}</div>',
                    unsafe_allow_html=True,
                )

else:
    # ── Empty state ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="
      background: #161b22;
      border: 1px dashed #30363d;
      border-radius: 8px;
      padding: 3rem;
      text-align: center;
      margin-top: 1rem;
      font-family: 'JetBrains Mono', monospace;
    ">
      <div style="font-size: 3rem; margin-bottom: 1rem;">🔬</div>
      <div style="color: #58a6ff; font-size: 1rem; letter-spacing: 0.05em;">
        AWAITING LAYOUT INPUT
      </div>
      <div style="color: #484f58; font-size: 0.78rem; margin-top: 0.8rem; line-height: 1.8;">
        Upload a layout JSON file to begin DRC/LVS verification.<br>
        Use the sidebar to download a sample layout for demonstration.
      </div>
    </div>
    """, unsafe_allow_html=True)
