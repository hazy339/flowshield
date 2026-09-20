# FLOWSHIELD

**Predict the flood. Protect the future.**

Flood simulation and early-warning dashboard for Indian city basins. Built to the suggested stack:

| Layer | Choice |
| --- | --- |
| Mathematical modelling & numerical simulation | **Python** + **NumPy** (`simulation/`) |
| Numerical computation & analysis | **Pandas** + **Matplotlib** (`analysis/plots.py`) |
| Visualization | **React** (`web/`) and/or **Streamlit** (`app.py`) |

Districts overlay satellite imagery; water levels evolve from rainfall, terrain, drainage, and nonlinear channel flow.

## Demo flow

1. Pick a **study area**.
2. Choose a **scenario** (normal / heavy / extreme rain, drainage failure, blocked channel).
3. Watch the **map** and use the **timeline** (or Play) to step through the storm.
4. Select a district — flood risk, water depth, early-warning lead times.
5. Review hydrology charts (water level over time).

For a full spoken demo checklist, see [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Run — React + Python API (recommended for the suggested stack)

Terminal 1 — NumPy simulation API:

```bash
cd flood
py -3 -m pip install -r requirements.txt
py -3 -m uvicorn api.main:app --reload --port 8000
```

Terminal 2 — React dashboard:

```bash
cd flood/web
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Run — Streamlit (alternate visualization)

```bash
cd flood
py -3 -m streamlit run app.py --server.port 8502
```

Opens [http://localhost:8502](http://localhost:8502).

## Offline analysis (Pandas / Matplotlib)

```bash
py -3 -m analysis.plots
```

Writes scenario comparison CSV + PNG under `analysis/output/`.

## What the model uses

| Input | Role |
| --- | --- |
| Rainfall intensity (mm/h) | Water added each timestep, scaled by district exposure |
| Elevation | Water-surface height; flow moves downhill |
| Drainage capacity | Pumps/sewers that remove standing water |
| Neighbour + canal links | Volumetric transfer F = k√|H| along edges |
| Drainage failure | Sets selected districts' drainage to zero |
| Blocked channel | Sets a river/drain link conductivity to zero |
| Population | People living in Warning or Critical districts |

Thresholds: **Safe** &lt; 0.30 m, **Warning** 0.30–0.80 m, **Critical** ≥ 0.80 m.

## Project layout

```
simulation/                 Python/NumPy hydrology engine
api/main.py                 FastAPI bridge for the React app
web/                        React + Leaflet + Recharts UI
app.py                      Streamlit UI (same engine)
analysis/plots.py           Pandas/Matplotlib scenario reports
data/                       District GeoJSON + attributes
tests/                      Flood-flow checks
DEMO_SCRIPT.md              Demo narration
```

## Tests

```bash
py -3 -m pytest tests/ -q
```
