# FLOWSHIELD — Demo & Feature Script

**Tagline:** Predict the flood. Protect the future.

Use this as the **spoken narration + on-screen checklist** for the prototype demo video.

**Suggested length:** 4–6 minutes  
**Run:** `py -3 -m streamlit run app.py --server.port 8502` → http://localhost:8502

---

## 1. Opening (15–20 s)

**Say:**

> A city receives rainfall over time. Water does not rise evenly — it depends on rainfall intensity, drainage capacity, terrain, and how water moves between connected regions. FLOWSHIELD is a flood simulation and early-warning dashboard that models those interactions, shows how flooding progresses, and warns which regions may become vulnerable.

**Show:** Brand header **FLOWSHIELD**, study area (e.g. Chennai), satellite map.

---

## 2. Requirements → Features map

| Requirement | Where it appears in FLOWSHIELD |
| --- | --- |
| Configure rainfall intensity | Left **Scenario** presets, or **Advanced controls → Rainfall intensity** |
| City as connected regions | District graph on the map; neighbour + canal links in the model |
| Water accumulation & movement | Simulation engine + dotted **river flow** animation + **Water movement** panel |
| Drainage capacity & terrain | Advanced: drainage scale; elevation drives downhill flow (`η = z + w`) |
| Simulate water levels over time | Timeline / **Play**; depth labels on districts |
| Classify Safe / Warning / Critical | Risk pins & selected-region **FLOOD RISK** status |
| Time-based flood progression | Map fill + playback slider |
| Identify critical regions | Red critical pins; What-if counts |
| Estimated time to critical | Right panel **Early warning → Time to critical** |
| **Bonus:** Normal / heavy rain | Scenarios: Normal / Heavy / Extreme Rainfall |
| **Bonus:** Drainage failure | Scenario **Drainage Failure** (+ district multi-select) |
| **Bonus:** Blocked channel | Scenario **Blocked Channel** (+ channel select) |
| **Bonus:** Compare scenarios | **What-if Analysis** popover |
| **Bonus:** Affected population | What-if summary + model population on Warning/Critical |
| **Bonus:** Interactive time slider | Center timeline under the map |

**Deliverable arc (must be visible in the video):**

`Rainfall & terrain input → Water-level simulation → Flood progression → Risk classification → Early warning output`

---

## 3. Demo narration (follow in order)

### Act A — Rainfall & terrain input (~45 s)

**Do:**

1. Top bar: keep **Chennai, Tamil Nadu** (or switch city once to show multi-basin support).
2. Left panel: select **Heavy Rainfall**, then **Extreme Rainfall**.
3. Open **Advanced controls** briefly — show rainfall (mm/h), rain duration, drainage capacity, initial water, sim duration.

**Say:**

> Users configure the storm. Presets cover normal rain, heavy rain, and extreme flood. Advanced controls expose rainfall intensity, how long it rains, drainage capacity, and initial water levels. Terrain is built into each district’s elevation, so water-surface height is elevation plus standing water. Regions are connected through neighbourhood links and canals — a connected city graph, not a single tank.

**Close** Advanced controls.

---

### Act B — Water-level simulation (~40 s)

**Do:**

1. Click **Run simulation** (or wait for auto-update after scenario change).
2. Click a low inland district, then a coastal one (e.g. **Velachery** → **Adyar**).
3. Glance at right panel **Current water level** and **Current conditions** (rainfall, elevation, drainage).

**Say:**

> The model steps through time: rain adds water, drainage removes it, and nonlinear channel flow moves volume between districts based on head difference. Depth updates every timestep. Selecting a region shows live depth, local rainfall factor, elevation, and drainage — the same inputs the engine uses.

---

### Act C — Flood progression (time visualization) (~50 s)

**Do:**

1. Drag the **timeline** from T+0 toward mid-storm, or press **Play**.
2. Point at land flood fill and depth labels changing.
3. Point at dotted **river flow** along canals (inland corridors, not open sea).
4. Scroll to **Region hydrology**: **Water level over time**, **Water sources**, **Water movement**.

**Say:**

> The interactive time slider — a bonus requirement — lets us scrub flood progression. The map shows how inundation spreads. Animated flow along river corridors shows inflow and outflow between regions. Below the map, charts explain water level over time, where the water is coming from, and movement to and from neighbouring districts.

**Optional:** press **Pause**, then **Reset**, then Play again once.

---

### Act D — Risk classification (~40 s)

**Do:**

1. Stop on a frame with mixed pins (green / amber / red).
2. Select a **Critical** district (red).
3. Read **FLOOD RISK** and thresholds (Warning / Critical lines on the water-level chart).

**Say:**

> Every region is classified as Safe, Warning, or Critical from water depth. In FLOWSHIELD: Safe below 0.30 metres, Warning from 0.30 to 0.80 metres, and Critical at 0.80 metres and above. Critical districts are highlighted so responders can see which areas have already crossed the danger line.

---

### Act E — Early warning output (~45 s)

**Do:**

1. On the same district, show **Early warning**: time to warning, time to critical, warning lead time.
2. Show **Why is this flooding?**
3. Open **What-if Analysis** — read critical/warning counts and **affected population**; compare to another preset.
4. Optionally toggle **Trace Water Source**.

**Say:**

> Early warning is not only the current class — it is lead time. The panel estimates time to warning and time to critical for the selected region, plus how much warning lead time remains before critical. We also explain drivers: heavy rain, weak drainage, upstream inflow, or low elevation. What-if analysis compares scenarios and reports estimated affected population in warning and critical zones — another bonus requirement.

---

### Act F — Bonus scenarios pack (~40 s)

**Do (quick cuts):**

1. **Normal Rainfall** — map stays mostly safe; say “baseline conditions.”
2. **Drainage Failure** — show Advanced failures / preset; depths rise faster.
3. **Blocked Channel** — blocked link styled on the map; flooding redistributes.
4. Return to **Extreme Rainfall** for the closing frame.

**Say:**

> Bonus scenarios are built in: normal rainfall, heavy and extreme storms, drainage failure, and a blocked drainage channel. Comparing them shows how the same city responds under different failures — exactly what planners need beyond a single static map.

---

## 4. Closing (15–20 s)

**Do:** Wide shot of map + early-warning panel + timeline.

**Say:**

> FLOWSHIELD takes rainfall and terrain inputs, simulates water levels over time, visualizes flood progression, classifies risk, and delivers early-warning lead times and population impact. Predict the flood. Protect the future.

**End card (optional on-screen text):**

```
FLOWSHIELD
Rainfall & terrain → Simulation → Progression → Risk → Early warning
Prototype demo · Streamlit + NumPy
```

---

## 5. Tech stack (if judges ask)

| Layer | Choice |
| --- | --- |
| Numerical simulation | Python, NumPy |
| Hydrology model | `simulation/model.py` — rain, drain, nonlinear flow \(F = k\sqrt{\|H\|}\), risk classes |
| City graph / canals | `simulation/city.py` + GeoJSON districts |
| Scenarios | `simulation/scenarios.py` |
| Visualization | Streamlit, Folium / Google satellite tiles, Plotly charts |
| Entry point | `app.py` |

---

## 6. One-page checklist (record with this open)

- [ ] Tagline + problem stated  
- [ ] Rainfall configured (preset or Advanced)  
- [ ] Connected regions / canals mentioned  
- [ ] Simulation run; depth changes  
- [ ] Timeline / Play used  
- [ ] Safe / Warning / Critical shown  
- [ ] Critical district identified  
- [ ] Time to critical shown  
- [ ] Normal + heavy (or extreme) shown  
- [ ] Drainage failure **or** blocked channel shown  
- [ ] Scenario compare / affected population (What-if)  
- [ ] Closing deliverable sentence  

---

## 7. Short “elevator” version (60–90 s)

If time is tight, say only this while scrubbing the UI:

> FLOWSHIELD models an Indian city as connected districts. We set rainfall, drainage, and terrain; the engine simulates water over time with flow between regions. The map and time slider show flood progression. Districts are classed Safe, Warning, or Critical. The early-warning panel gives time to critical and affected population. Presets cover normal rain, heavy rain, drainage failure, and blocked channels — and What-if compares scenarios. That’s rainfall input to early-warning output in one dashboard.
