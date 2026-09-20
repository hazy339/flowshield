# FLOWSHIELD Web (React)

React visualization for the Python/NumPy flood engine.

Full install guide (clone, prerequisites, Windows/macOS/Linux): see the root [README.md](../README.md).

## Quick start (after cloning)

**Terminal 1** — from repo root:

```bash
py -3 -m pip install -r requirements.txt
py -3 -m uvicorn api.main:app --reload --port 8000
```

**Terminal 2** — from `web/`:

```bash
npm install
npm run dev
```

Open http://localhost:5173 (proxies `/api` → `:8000`).
