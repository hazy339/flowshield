# FLOWSHIELD

**Predict the flood. Protect the future.**

Flood simulation and early-warning dashboard for Indian city basins (Chennai, Mumbai, Delhi, Kolkata, Guwahati, Hyderabad, Bengaluru, plus high-risk basins such as Patna, Kochi, Surat, Visakhapatnam, Bhubaneswar, Srinagar, Alappuzha, Vadodara, and Mangaluru). Districts overlay Google Earth satellite imagery; water levels evolve from rainfall, terrain, drainage, and nonlinear channel flow.

## Demo flow

1. Pick a **study area** in the top bar (or search city / state).
2. Choose a **scenario** on the left (normal / heavy / extreme rain, drainage failure, blocked channel) or open Advanced controls.
3. Watch the **map** and drag the **timeline** (or press Play) to step through the storm.
4. Click a district — the right panel shows flood risk, water depth, early-warning lead times, and why it is flooding.
5. Scroll below the map for **Region hydrology**: water level over time, water sources, and neighbour movement.
6. Use **Trace Water Source** / **What-if Analysis** on the selected-region panel when you need a deeper look.

For a full spoken demo (requirements → features, video checklist), see [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Run locally

Python 3.10+ recommended.

```bash
cd flood
py -3 -m pip install -r requirements.txt
py -3 -m streamlit run app.py --server.port 8502
```

The dashboard opens at [http://localhost:8502](http://localhost:8502).

Map tiles use **Google Earth-style satellite / hybrid** imagery. An internet connection is needed for tiles to load.

> Localhost is only on your machine. Teammates need the repo cloned and the same `streamlit run` command (or a shared host), not your `localhost` URL.

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

## Map visuals

- Flood fill is clipped to **district land polygons** (not painted over open ocean).
- Animated dotted **river flow** follows approximate canal corridors, clipped **inland of the coast** so lines do not continue into the sea.
- Risk pins and district labels sit on the satellite basemap; GIS clutter toggles are removed from the main layout.

## Project layout

```
app.py                      Streamlit dashboard (map-first UI)
simulation/model.py         Hydrology engine and risk classification
simulation/city.py          District graph, canals, GeoJSON loader
simulation/scenarios.py     Normal / heavy / failure / blocked presets
simulation/viz.py           Satellite map, land flood fill, river AntPaths
data/districts.geojson      District polygons
data/district_attributes.csv Elevation, drainage, population, neighbours
ui/dashboard_ui.py          Mirror of the root dashboard
tests/                      Flood-flow and related checks
```

## Tests

```bash
py -3 -m pytest tests/ -q
```
