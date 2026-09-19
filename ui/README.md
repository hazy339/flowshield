# FLOWSHIELD UI

This folder contains the **UI-only** Streamlit dashboard file.

| File | Role |
| --- | --- |
| `dashboard_ui.py` | Full dashboard layout (header, scenarios, map, right panels, timeline) |

The live entrypoint used by Streamlit is still the project root file `app.py` (same content).

## Run the full app (UI + model + OSM)

From the project root:

```bash
py -3 -m pip install -r requirements.txt
py -3 -m streamlit run app.py
```

Backend math lives in `simulation/`. Map overlays use Folium + OpenStreetMap tiles.
