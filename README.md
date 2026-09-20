# FLOWSHIELD

**Predict the flood. Protect the future.**

Flood simulation and early-warning dashboard for Indian city basins (Chennai, Mumbai, Delhi, Kolkata, Guwahati, Hyderabad, Bengaluru, plus high-risk basins such as Patna, Kochi, Surat, Visakhapatnam, Bhubaneswar, Srinagar, Alappuzha, Vadodara, and Mangaluru). Districts overlay Google Earth satellite imagery; water levels evolve from rainfall, terrain, drainage and channel flow.

## Demo flow

1. Choose a scenario (normal rain, heavy rain, drainage failure, or a blocked channel) or set rainfall yourself.
2. Run the simulation (it also updates automatically when inputs change).
3. Drag the **time slider** to watch flood progression on the map.
4. Read the early-warning panel: critical districts, time-to-critical, and estimated affected population.
5. Open **Compare scenarios** to contrast two runs side by side.

## Run locally

Python 3.10+ recommended.

```bash
cd flood
py -3 -m pip install -r requirements.txt
py -3 -m streamlit run app.py --server.port 8502
```

The dashboard opens at [http://localhost:8502](http://localhost:8502).

Map tiles use **Google Earth-style satellite / hybrid** imagery. An internet connection is needed for tiles to load.

## What the model uses

| Input | Role |
| --- | --- |
| Rainfall intensity (mm/h) | Water added each timestep, scaled by district exposure |
| Elevation | Water-surface height; flow moves downhill |
| Drainage capacity | Pumps/sewers that remove standing water |
| Neighbour + canal links | Movement between districts; canals conduct faster |
| Drainage failure | Sets selected districts' drainage to zero |
| Blocked channel | Sets a river/drain link conductivity to zero |
| Population | People living in Warning or Critical districts |

Thresholds: **Safe** &lt; 0.30 m, **Warning** 0.30–0.80 m, **Critical** ≥ 0.80 m.

## Project layout

```
app.py                      Streamlit dashboard
simulation/model.py         Hydrology engine and risk classification
simulation/city.py          District graph, canals, GeoJSON loader
simulation/scenarios.py     Normal / heavy / failure / blocked presets
simulation/viz.py           Google Earth satellite map overlays
data/districts.geojson      District polygons
data/district_attributes.csv Elevation, drainage, population, neighbours
```
