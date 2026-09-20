# FLOWSHIELD UI

`dashboard_ui.py` mirrors the root Streamlit dashboard (`app.py`). Prefer running `app.py` from the repo root.

## Layout

- **Top bar** — brand, study-area search / selector
- **Left** — scenario presets + advanced controls
- **Center** — Google Earth map + playback timeline
- **Right** — selected-region hazard, early warning, conditions
- **Below** — region hydrology (water level, sources, movement)

## India study areas

Chennai, Mumbai, Delhi, Kolkata, Guwahati, Hyderabad, Bengaluru, Patna, Kochi, Surat, Visakhapatnam, Bhubaneswar, Srinagar, Alappuzha, Vadodara, Mangaluru.

## Run

From the repo root:

```bash
py -3 -m pip install -r requirements.txt
py -3 -m streamlit run app.py --server.port 8502
```

Dashboard: [http://localhost:8502](http://localhost:8502)

Map: Google Earth satellite, land-clipped flood fill, inland river flow paths, district risk labels.
