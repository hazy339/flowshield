# FLOWSHIELD Web (React)

React visualization front end for the Python/NumPy flood engine.

## Stack (as suggested)

| Layer | Tech |
| --- | --- |
| Mathematical modelling | Python + NumPy (`simulation/`) |
| Analysis | Pandas + Matplotlib (`analysis/plots.py`) |
| Visualization | **React** (this app) — Streamlit (`app.py`) remains available |

## Run

Terminal 1 — API:

```bash
py -3 -m pip install -r requirements.txt
py -3 -m uvicorn api.main:app --reload --port 8000
```

Terminal 2 — React:

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173 (Vite proxies `/api` → `:8000`).
