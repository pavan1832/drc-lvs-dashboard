# DRC/LVS Verification Dashboard

> Web-deployed IC physical verification tool — upload a layout JSON,
> run DRC/LVS, inspect violations, download sign-off reports.

The Project is Live at: https://pavan1832-drc-lvs-dashboard-app-zvogrg.streamlit.app/

---

## Project Structure

```
drc_lvs_dashboard/
│
├── app.py                      # Streamlit UI layer
│
├── python/
│   ├── main.py                 # CLI entry point (invoked via subprocess)
│   ├── drc_engine.py           # DRC rule-deck executor
│   ├── lvs_engine.py           # LVS netlist comparator
│   └── report_generator.py     # TXT + CSV report builder
│
├── tcl/
│   └── mock_drc_lvs.tcl        # TCL mock flow (tclsh)
│
├── .streamlit/
│   └── config.toml             # Dark theme + server config
│
├── sample_layout.json          # Pre-built test case (INVERTER_28NM)
├── requirements.txt
└── README.md
```

---

## Local Setup

### Prerequisites

| Tool       | Version   |
|------------|-----------|
| Python     | 3.11+     |
| pip        | latest    |
| tclsh      | any (optional — TCL phase is skipped gracefully if absent) |

### Install

```bash
cd drc_lvs_dashboard
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

Browser opens at **http://localhost:8501**

### CLI-only (engine without UI)

```bash
python python/main.py --layout sample_layout.json --outdir reports/
```

---

## Deploying to Streamlit Cloud

1. Push this folder to a **public GitHub repository**
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app**
4. Set:
   - Repository: `your-username/drc-lvs-dashboard`
   - Branch: `main`
   - Main file: `app.py`
5. Click **Deploy** — done.

> `tclsh` is not available on Streamlit Cloud; the TCL phase is skipped
> automatically and DRC/LVS results are unaffected.

---

## Deploying to Render

1. Create a **Web Service** on [render.com](https://render.com)
2. Connect your GitHub repo
3. Set:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4. Environment: Python 3.11

---

## Layout JSON Schema

```json
{
  "design_name": "INVERTER_28NM",
  "technology":  "mock_28nm",
  "top_cell":    "INV_X1",

  "layers": [
    {
      "name": "M1",
      "geometries": [
        { "x": 0.0, "y": 0.0, "width": 0.09, "spacing": 0.10 }
      ]
    }
  ],

  "nets": [
    { "name": "VDD", "connections": 4 },
    { "name": "OUT", "connections": 1 }
  ],

  "devices": [
    {
      "name": "MN0", "type": "NMOS",
      "schematic_width": 0.28,
      "layout_width":    0.28
    }
  ]
}
```

---

## How This Maps to Industry Flows

### Synopsys Custom Compiler / IC Validator

| Dashboard Layer         | ICV Equivalent                            |
|-------------------------|-------------------------------------------|
| `app.py` upload + run   | ICV GUI job submission                    |
| `python/main.py`        | `icv` binary / batch DRC run             |
| `drc_engine.py`         | `.drc` rule deck execution               |
| `lvs_engine.py`         | ICV-LVS netlist extraction + compare      |
| `summary_report.txt`    | ICV sign-off report / `.sum` file        |
| `drc_violations.csv`    | ICV DRC results database (ICVWB output)  |
| `tcl/mock_drc_lvs.tcl`  | ICV TCL run script / SVRF batch control  |

### Cadence Virtuoso / Pegasus

| Dashboard Layer         | Pegasus / Virtuoso Equivalent             |
|-------------------------|-------------------------------------------|
| `app.py`                | Virtuoso DRD / Constraint Manager UI     |
| DRC rule structs        | Pegasus `.rs` rule file (SKILL API)      |
| LVS comparator          | LVS `hcell` / Spectre netlist compare   |
| Report CSVs             | Pegasus violation viewer export          |

### Software Engineering Apprenticeship Alignment

| JD Requirement                  | This Project                            |
|---------------------------------|-----------------------------------------|
| Python scripting / automation   | Engine, subprocess orchestration        |
| Web application development     | Streamlit dashboard                     |
| EDA tool integration            | TCL invocation, ICV-style reporting     |
| Data handling (CSV/pandas)      | Violation table parsing + display       |
| Version-controlled deliverable  | Structured repo, clean module split     |
| Cross-platform deployment       | Works on Windows + Linux + cloud        |

---

## Sign-off Exit Codes

| Code | Meaning                              |
|------|--------------------------------------|
| `0`  | All checks pass — SIGN-OFF: PASS    |
| `1`  | One or more errors — SIGN-OFF: FAIL |
