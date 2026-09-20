# FLOWSHIELD

**Predict the flood. Protect the future.**

Flood simulation and early-warning dashboard for Indian city basins. Built to the suggested stack:

| Layer | Choice |
| --- | --- |
| Mathematical modelling & numerical simulation | **Python** + **NumPy** (`simulation/`) |
| Numerical computation & analysis | **Pandas** + **Matplotlib** (`analysis/plots.py`) |
| Visualization | **React** (`web/`) and/or **Streamlit** (`app.py`) |

Districts overlay satellite imagery; water levels evolve from rainfall, terrain, drainage, and nonlinear channel flow.

**Repo:** https://github.com/hazy339/flowshield

---

## Install on any computer

Each teammate runs FLOWSHIELD **on their own machine**. Your `localhost` URL is not reachable by others — they must clone and start the app locally (or you deploy to a shared host).

### 1. Prerequisites

Install these once:

| Tool | Version | Check |
| --- | --- | --- |
| [Git](https://git-scm.com/downloads) | any recent | `git --version` |
| [Python](https://www.python.org/downloads/) | **3.10+** (3.11–3.13 OK) | `python --version` or `py -3 --version` |
| [Node.js](https://nodejs.org/) (LTS) | **18+** (20 LTS recommended) | `node --version` and `npm --version` |

On Windows, tick **“Add python.exe to PATH”** during Python setup.  
Internet is required the first time (packages + map tiles).

### 2. Clone the repository

```bash
git clone https://github.com/hazy339/flowshield.git
cd flowshield
```

### 3. Python dependencies

From the **repo root** (`flowshield/`):

**Windows**
```bash
py -3 -m pip install -r requirements.txt
```

**macOS / Linux**
```bash
python3 -m pip install -r requirements.txt
```

Optional virtual environment (recommended):

```bash
# Windows
py -3 -m venv .venv
.\.venv\Scripts\activate
py -3 -m pip install -r requirements.txt

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

---

## Option A — React + API (recommended)

You need **two terminals**, both started from the cloned repo.

### Terminal 1 — simulation API (port 8000)

```bash
cd flowshield
py -3 -m uvicorn api.main:app --reload --port 8000
```

macOS / Linux: use `python3 -m uvicorn ...` if `py` is not available.

Leave this running. You should see `Uvicorn running on http://127.0.0.1:8000`.

### Terminal 2 — React UI (port 5173)

```bash
cd flowshield/web
npm install
npm run dev
```

Open **http://localhost:5173** in a browser.

Vite proxies `/api` to the backend on port 8000, so both must be running.

### Stop

In each terminal: `Ctrl+C`.

---

## Option B — Streamlit only (simpler, one process)

If you only need a quick demo without Node.js:

```bash
cd flowshield
py -3 -m pip install -r requirements.txt
py -3 -m streamlit run app.py --server.port 8502
```

Open **http://localhost:8502**.

---

## Quick verify

| Check | Expected |
| --- | --- |
| API health | http://127.0.0.1:8000/api/health → `{"status":"ok",...}` |
| React UI | http://localhost:5173 loads FLOWSHIELD |
| Streamlit | http://localhost:8502 loads FLOWSHIELD |
| Tests | `py -3 -m pytest tests/ -q` |

Offline scenario charts (Pandas / Matplotlib):

```bash
py -3 -m analysis.plots
```

Output goes to `analysis/output/`.

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `ERR_CONNECTION_REFUSED` on `:5173` | Start `npm run dev` in `web/` — nothing is listening otherwise |
| React loads but simulation fails | Start the API on `:8000` first |
| `py` / `python` not found | Reinstall Python with PATH enabled, or use `python3` |
| `npm` not found | Install Node.js LTS and reopen the terminal |
| Port already in use | Change port: `uvicorn ... --port 8001` and set Vite proxy, or free the port |
| Map tiles blank | Need internet (Google satellite tiles) |
| Old UI after `git pull` | Restart API + `npm run dev`; hard-refresh the browser |

---

## Sharing with teammates

1. Push your latest work to GitHub (already on `main` if you pulled recently).
2. Teammates: `git clone` (or `git pull`) → follow **Install** + **Option A** or **B** above.
3. Do **not** send `http://localhost:...` as a team URL — that only works on the computer that started the server.

To let others use **your** running instance without cloning, you would need a cloud host (e.g. API on Render/Railway + React on Vercel/Netlify). Local install is the default for this project.

---

## Demo flow

1. Pick a **study area**.
2. Choose a **scenario** (normal / heavy / extreme rain, drainage failure, blocked channel).
3. Watch the **map** and use the **timeline** (or Play).
4. Select a district — risk, depth, early-warning lead times.
5. Scroll to **Region hydrology** — water level, sources pie, movement.

Full spoken checklist: [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## What the model uses

| Input | Role |
| --- | --- |
| Rainfall intensity (mm/h) | Water added each timestep, scaled by district exposure |
| Elevation | Water-surface height; flow moves downhill |
| Drainage capacity | Pumps/sewers that remove standing water |
| Neighbour + canal links | Volumetric transfer F = k√\|H\| along edges |
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
