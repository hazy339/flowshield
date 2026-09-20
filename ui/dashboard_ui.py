from __future__ import annotations

from datetime import timedelta

import streamlit as st
from streamlit_folium import st_folium

from simulation.city import list_regions, load_city, resolve_region_query
from simulation.model import SimConfig, SimulationResult, run_simulation
from simulation.scenarios import PRESETS, apply_preset
from simulation.viz import build_map

st.set_page_config(
    page_title="FLOWSHIELD · Flood Early Warning",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

STATUS_COLOR = {0: "#1ee0ac", 1: "#f5a623", 2: "#e74c3c"}
REGION_LABELS = [info.label for info in list_regions()]
LABEL_TO_REGION = {info.label: info.id for info in list_regions()}


def get_city():
    rid = st.session_state.get("region_id", "chennai")
    cache_key = f"city_{rid}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = load_city(rid)
    return st.session_state[cache_key]


def channel_maps(city):
    labels = ["None"] + [ch["label"] for ch in city.blockable_channels]
    edges = {ch["label"]: ch["edge"] for ch in city.blockable_channels}
    return labels, edges


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #0b1220;
            --panel: #151d2e;
            --accent: #1ee0ac;
            --accent-dim: rgba(30, 224, 172, 0.22);
            --text: #e8eef7;
            --muted: #8ea0b8;
            --line: rgba(30, 224, 172, 0.18);
        }
        html, body, [data-testid="stAppViewContainer"] {
            background: var(--bg) !important;
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { display: none; }
        [data-testid="stSidebar"] { display: none; }
        .block-container {
            padding: 0.55rem 1.1rem 0.4rem !important;
            max-width: 100% !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--panel);
            border: 1px solid var(--line) !important;
            border-radius: 14px;
            padding: 0.15rem 0.35rem 0.45rem;
        }
        .fs-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 0.55rem;
            padding: 0.15rem 0.2rem;
        }
        .fs-brand {
            display: flex;
            align-items: baseline;
            gap: 0.75rem;
            flex-wrap: wrap;
        }
        .fs-logo {
            font-size: 1.35rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            color: var(--text);
        }
        .fs-logo span { color: var(--accent); }
        .fs-sub {
            color: var(--muted);
            font-size: 0.82rem;
        }
        .panel-title {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            color: var(--text);
            margin: 0.35rem 0 0.55rem;
        }
        .panel-title-sm {
            font-size: 0.9rem;
            font-weight: 650;
            color: var(--text);
            margin: 0.2rem 0 0.45rem;
        }
        .hint {
            color: var(--muted);
            font-size: 0.8rem;
            line-height: 1.35;
        }
        .region-chip {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 0.45rem 0.65rem;
            margin-bottom: 0.35rem;
            background: rgba(11, 18, 32, 0.55);
            font-size: 0.86rem;
        }
        .pill {
            display: inline-block;
            padding: 0.12rem 0.5rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }
        .hazard-hero {
            border-radius: 14px;
            padding: 0.85rem 0.9rem 0.95rem;
            margin: 0.15rem 0 0.55rem;
            border: 1px solid;
            background: linear-gradient(160deg, rgba(11,18,32,0.92), rgba(21,29,46,0.98));
        }
        .hazard-hero .district-name {
            font-size: 1.15rem;
            font-weight: 800;
            color: var(--text);
            letter-spacing: 0.01em;
            line-height: 1.2;
        }
        .hazard-hero .place-line {
            color: var(--muted);
            font-size: 0.78rem;
            margin: 0.2rem 0 0.7rem;
        }
        .hazard-status {
            font-size: 1.55rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            line-height: 1.1;
        }
        .hazard-depth {
            font-size: 2rem;
            font-weight: 800;
            font-variant-numeric: tabular-nums;
            color: var(--text);
            line-height: 1;
            margin-top: 0.35rem;
        }
        .hazard-depth span {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--muted);
            margin-left: 0.2rem;
        }
        .hazard-meta {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.45rem;
            margin-top: 0.75rem;
        }
        .hazard-meta .cell {
            background: rgba(11,18,32,0.65);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
            padding: 0.4rem 0.5rem;
        }
        .hazard-meta .k {
            font-size: 0.68rem;
            color: var(--muted);
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .hazard-meta .v {
            font-size: 0.92rem;
            font-weight: 700;
            color: var(--text);
            margin-top: 0.12rem;
        }
        .src-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.84rem;
            padding: 0.28rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            color: #c5d4e8;
        }
        .why-item {
            font-size: 0.82rem;
            color: #c5d4e8;
            margin: 0.25rem 0;
            padding-left: 0.2rem;
        }
        .map-shell {
            border: 1px solid var(--line);
            border-radius: 14px;
            overflow: hidden;
            background: #0a101c;
            min-height: 560px;
        }
        iframe[title="streamlit_folium.st_folium"] {
            border: 1px solid var(--line) !important;
            border-radius: 14px;
        }
        .bottom-bar {
            margin-top: 0.55rem;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--panel);
            padding: 0.55rem 0.8rem 0.35rem;
        }
        .t-clock {
            color: var(--accent);
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            font-size: 0.95rem;
            text-align: right;
            padding-top: 0.55rem;
        }
        div[data-testid="stSlider"] label { color: var(--muted) !important; }
        button[kind="secondary"] {
            border: 1px solid var(--line) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def eta_text(hours: float) -> str:
    if hours != hours:
        return "Not reached"
    h = int(hours)
    m = int(round((hours - h) * 60))
    if m == 60:
        h += 1
        m = 0
    return f"{hours:.1f} h (t+{h:02d}:{m:02d})"


def clock_label(hours: float) -> str:
    total_m = int(round(hours * 60))
    h, m = divmod(total_m, 60)
    return f"T+{h}h {m:02d}m"


def edge_label(blocked_label: str, channel_edge: dict) -> tuple[tuple[str, str], ...]:
    if blocked_label == "None" or blocked_label not in channel_edge:
        return ()
    return (channel_edge[blocked_label],)


def apply_preset_to_state(preset_name: str, city) -> None:
    cfg = apply_preset(preset_name, city)
    st.session_state.rainfall = float(cfg.rainfall_mm_h)
    rain_h = cfg.rain_duration_h if cfg.rain_duration_h is not None else cfg.duration_h
    st.session_state.rain_duration_min = float(min(1440.0, max(30.0, rain_h * 60.0)))
    st.session_state.sim_duration_min = float(min(2880.0, max(240.0, cfg.duration_h * 60.0)))
    st.session_state.drainage_scale = float(cfg.drainage_scale)
    st.session_state.initial_scale = float(cfg.initial_scale)
    st.session_state.failed_names = [city.name_of(did) for did in cfg.failed_districts]
    labels, edges = channel_maps(city)
    blocked = "None"
    if cfg.blocked_edges:
        target = {cfg.blocked_edges[0][0], cfg.blocked_edges[0][1]}
        for label, edge in edges.items():
            if {edge[0], edge[1]} == target:
                blocked = label
                break
    st.session_state.blocked_label = blocked if blocked in labels else "None"
    st.session_state.cfg_key = None
    st.session_state.playing = False
    st.session_state.seek_peak = True


def switch_region(region_id: str) -> None:
    st.session_state.region_id = region_id
    city = load_city(region_id)
    st.session_state[f"city_{region_id}"] = city
    st.session_state.selected_region = city.names[0]
    st.session_state.failed_names = []
    st.session_state.blocked_label = "None"
    st.session_state.cfg_key = None
    st.session_state.t_idx = 0
    st.session_state.playing = False
    apply_preset_to_state(st.session_state.get("preset_name", "Extreme flood"), city)


def init_state() -> None:
    defaults = {
        "region_id": "chennai",
        "preset_name": "Extreme flood",
        "rainfall": 140.0,
        "rain_duration_min": 960.0,
        "sim_duration_min": 1440.0,
        "drainage_scale": 0.55,
        "initial_scale": 1.6,
        "failed_names": [],
        "blocked_label": "None",
        "selected_region": "Velachery",
        "color_mode": "Risk",
        "playing": False,
        "play_speed": 1,
        "t_idx": 0,
        "last_preset": "Extreme flood",
        "search_query": "",
        "show_grid": False,
        "show_labels": True,
        "study_area_label": "Chennai, Tamil Nadu",
        "seek_peak": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if st.session_state.get("haz_v2") != 3:
        st.session_state.haz_v2 = 3
        st.session_state.show_grid = False
        apply_preset_to_state(st.session_state.get("preset_name", "Extreme flood"), get_city())
        st.session_state.initialized = True
    st.session_state.rain_duration_min = float(min(1440.0, max(30.0, st.session_state.rain_duration_min)))
    st.session_state.sim_duration_min = float(min(2880.0, max(60.0, st.session_state.sim_duration_min)))
    if "initialized" not in st.session_state or not st.session_state.initialized:
        apply_preset_to_state(st.session_state.preset_name, get_city())
        st.session_state.initialized = True


def current_config(city) -> SimConfig:
    rain_h = float(st.session_state.rain_duration_min) / 60.0
    sim_h = float(st.session_state.sim_duration_min) / 60.0
    name_to_id = dict(zip(city.names, city.ids))
    failed = tuple(name_to_id[name] for name in st.session_state.get("failed_names", []) if name in name_to_id)
    _, channel_edge = channel_maps(city)
    return SimConfig(
        rainfall_mm_h=float(st.session_state.rainfall),
        duration_h=sim_h,
        rain_duration_h=rain_h,
        drainage_scale=float(st.session_state.drainage_scale),
        initial_scale=float(st.session_state.initial_scale),
        failed_districts=failed,
        blocked_edges=edge_label(st.session_state.get("blocked_label", "None"), channel_edge),
    )


def ensure_result(city) -> SimulationResult:
    cfg = current_config(city)
    key = (
        city.region_id,
        cfg.rainfall_mm_h,
        cfg.duration_h,
        cfg.rain_duration_h,
        cfg.drainage_scale,
        cfg.initial_scale,
        cfg.failed_districts,
        cfg.blocked_edges,
    )
    if st.session_state.get("cfg_key") != key:
        st.session_state.result = run_simulation(city, cfg)
        st.session_state.cfg_key = key
        st.session_state.seek_peak = True
    if st.session_state.get("seek_peak"):
        st.session_state.t_idx = st.session_state.result.peak_hazard_index()
        st.session_state.seek_peak = False
    else:
        st.session_state.t_idx = min(int(st.session_state.get("t_idx", 0)), st.session_state.result.n_steps - 1)
    return st.session_state.result


def water_source_breakdown(city, result: SimulationResult, idx: int, t_idx: int) -> dict[str, float]:
    depth = float(result.water[t_idx, idx])
    rain_h = result.config.rain_duration_h or result.config.duration_h
    elapsed = float(result.times_h[t_idx])
    wet = min(elapsed, rain_h)
    rain_in = (result.config.rainfall_mm_h / 1000.0) * result.config.runoff * city.rainfall_factor[idx] * wet
    drain_out = (city.drainage_mm_h[idx] / 1000.0) * result.config.drainage_scale * elapsed
    if city.ids[idx] in result.failed_districts:
        drain_out = 0.0
    initial = city.initial_water[idx] * result.config.initial_scale
    residual = max(0.0, depth - max(0.0, rain_in + initial - drain_out))
    return {
        "Rainfall accumulation": max(0.0, rain_in),
        "Initial ponding": max(0.0, initial),
        "Net inflow from neighbours": max(0.0, residual),
        "Drainage removed": max(0.0, drain_out),
        "Standing depth now": depth,
    }


def flooding_reasons(city, result: SimulationResult, idx: int, t_idx: int) -> list[str]:
    reasons: list[str] = []
    status = int(result.status[t_idx, idx])
    depth = float(result.water[t_idx, idx])
    elev = city.elevation[idx]
    drain = city.drainage_mm_h[idx] * result.config.drainage_scale
    if status == 0:
        reasons.append("Depth is still below the warning threshold (0.30 m).")
        return reasons
    if elev <= sorted(city.elevation)[max(0, city.n // 3)]:
        reasons.append(f"Low elevation ({elev:.0f} m) lets water pond instead of draining downhill.")
    if drain < 14:
        reasons.append(f"Drainage capacity is limited ({drain:.0f} mm/h).")
    if city.ids[idx] in result.failed_districts:
        reasons.append("Drainage pumps have failed in this district.")
    for a, b in result.blocked_edges:
        if city.ids[idx] in (a, b):
            reasons.append("A connected drainage channel is blocked, trapping runoff.")
            break
    if result.config.rainfall_mm_h >= 40:
        reasons.append(f"Heavy rainfall ({result.config.rainfall_mm_h:.0f} mm/h) exceeds local removal rate.")
    if depth >= result.config.critical_m:
        reasons.append(f"Water depth has reached critical ({depth:.2f} m ≥ 0.80 m).")
    elif depth >= result.config.warning_m:
        reasons.append(f"Water depth is in warning range ({depth:.2f} m).")
    if not reasons:
        reasons.append("Click another district or advance the timeline to inspect drivers.")
    return reasons


inject_css()
init_state()
CITY = get_city()
CHANNEL_LABELS, _CHANNEL_EDGE = channel_maps(CITY)
if st.session_state.selected_region not in CITY.names:
    st.session_state.selected_region = CITY.names[0]
if st.session_state.blocked_label not in CHANNEL_LABELS:
    st.session_state.blocked_label = "None"
st.session_state.failed_names = [n for n in st.session_state.failed_names if n in CITY.names]

# ── Top bar ──────────────────────────────────────────────────────────────
top_l, top_r = st.columns((2.4, 1.6))
with top_l:
    st.markdown(
        f"""
        <div class="fs-top">
          <div class="fs-brand">
            <div class="fs-logo"><span>◆</span> FLOWSHIELD</div>
            <div class="fs-sub">{CITY.city_name}, {CITY.state_name} · India basins · Google Earth</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with top_r:
    s1, s2, s3 = st.columns((1.5, 1.5, 1.0))
    with s1:
        st.text_input(
            "Search",
            placeholder="Delhi, Mumbai, Chennai, Kolkata…",
            label_visibility="collapsed",
            key="search_query",
        )
    with s2:
        study = st.selectbox(
            "Study area",
            REGION_LABELS,
            label_visibility="collapsed",
            key="study_area_label",
        )
    with s3:
        if st.button("Go", width="stretch", type="primary"):
            rid = resolve_region_query(st.session_state.search_query)
            if not rid:
                rid = LABEL_TO_REGION.get(st.session_state.study_area_label)
            if rid and rid != st.session_state.region_id:
                switch_region(rid)
                st.session_state.study_area_label = load_city(rid).label
                st.rerun()
            else:
                st.session_state.t_idx = 0
                st.session_state.playing = False
                st.session_state.cfg_key = None

# Apply study-area dropdown changes immediately
_selected_rid = LABEL_TO_REGION.get(st.session_state.study_area_label)
if _selected_rid and _selected_rid != st.session_state.region_id:
    switch_region(_selected_rid)
    st.rerun()

CITY = get_city()
CHANNEL_LABELS, _CHANNEL_EDGE = channel_maps(CITY)
result = ensure_result(CITY)
max_idx = max(0, result.n_steps - 1)
st.session_state.t_idx = min(int(st.session_state.t_idx), max_idx)

t_idx = int(st.session_state.t_idx)
hours = float(result.times_h[t_idx])

# ── Main 3-column layout ─────────────────────────────────────────────────
left, center, right = st.columns((1.05, 2.35, 1.15), gap="small")

with left:
    with st.container(border=True):
        st.markdown('<div class="panel-title">SCENARIOS</div>', unsafe_allow_html=True)
        st.caption(f"{CITY.label} · {CITY.n} districts")
        preset = st.selectbox("Preset", list(PRESETS.keys()), key="preset_name", label_visibility="collapsed")
        if preset != st.session_state.last_preset:
            apply_preset_to_state(preset, CITY)
            st.session_state.last_preset = preset
            st.session_state.cfg_key = None
            st.rerun()
        st.caption(PRESETS[preset].description)

        st.slider("Rainfall intensity", 5.0, 180.0, step=1.0, key="rainfall", format="%.0f mm/hr")
        st.slider("Rain duration", 30.0, 1440.0, step=15.0, key="rain_duration_min", format="%.0f min")
        st.slider("Drainage capacity", 0.25, 2.0, step=0.05, key="drainage_scale", format="x%.2f")
        st.slider("Initial water level", 0.0, 2.0, step=0.05, key="initial_scale", format="x%.2f")
        st.slider("Sim duration", 60.0, 2880.0, step=30.0, key="sim_duration_min", format="%.0f min")

        with st.expander("Failures & blockages", expanded=False):
            st.multiselect("Drainage failure", CITY.names, key="failed_names")
            st.selectbox("Blocked channel", CHANNEL_LABELS, key="blocked_label")

        if st.button("Run simulation", type="primary", width="stretch"):
            st.session_state.cfg_key = None
            st.session_state.playing = False
            st.session_state.seek_peak = True
            st.rerun()

        with st.expander("Model equations", expanded=False):
            st.markdown(
                r"""
                At each step Δt:

                1. **Rain** · \(w \leftarrow w + R\cdot c\cdot f\cdot \Delta t\) while raining  
                2. **Drain** · \(w \leftarrow \max(0,\, w - D\cdot s\cdot \Delta t - I\cdot \Delta t)\)  
                3. **Flow** · \(H = z + w\), flux \(k(H_i-H_j)\Delta t\) along edges  
                4. **Sea / river sink** on coastal / riverfront districts  
                5. **Class** · Safe < 0.22 m · Warning · Critical ≥ 0.60 m
                """
            )

with center:
    m1, m2, m3 = st.columns([2.2, 1, 1])
    with m1:
        st.radio(
            "Pin colour",
            ["Risk", "Water depth", "Elevation"],
            horizontal=True,
            key="color_mode",
            label_visibility="collapsed",
        )
    with m2:
        st.checkbox("Grid lines", key="show_grid")
    with m3:
        st.checkbox("Hazard labels", key="show_labels")

    sel_name = st.session_state.selected_region
    sel_id = CITY.ids[CITY.names.index(sel_name)] if sel_name in CITY.names else None

    fmap = build_map(
        CITY,
        result,
        t_idx=t_idx,
        color_mode=st.session_state.color_mode,
        blocked_edges=result.blocked_edges,
        show_grid=bool(st.session_state.show_grid),
        show_labels=bool(st.session_state.show_labels),
        selected_id=sel_id,
    )
    map_state = st_folium(
        fmap,
        height=620,
        use_container_width=True,
        returned_objects=["last_object_clicked_popup", "last_object_clicked"],
        key=f"main-map-{CITY.region_id}-{st.session_state.color_mode}-{st.session_state.cfg_key}-{st.session_state.show_grid}-{st.session_state.show_labels}-{sel_id}-{t_idx}",
    )

    if map_state and map_state.get("last_object_clicked"):
        clicked = map_state["last_object_clicked"]
        if clicked and "lat" in clicked and "lng" in clicked:
            lat, lon = clicked["lat"], clicked["lng"]
            best = min(
                CITY.ids,
                key=lambda did: (CITY.centroids[did][0] - lat) ** 2 + (CITY.centroids[did][1] - lon) ** 2,
            )
            st.session_state.selected_region = CITY.name_of(best)

with right:
    with st.container(border=True):
        st.markdown('<div class="panel-title">SELECTED DISTRICT</div>', unsafe_allow_html=True)
        st.selectbox("Region", CITY.names, key="selected_region", label_visibility="collapsed")
        sel_idx = CITY.names.index(st.session_state.selected_region)
        status = int(result.status[t_idx, sel_idx])
        label = result.status_label(t_idx, sel_idx)
        depth = float(result.water[t_idx, sel_idx])
        color = STATUS_COLOR[status]
        ttc = float(result.time_to_critical_h[sel_idx])
        drain = CITY.drainage_mm_h[sel_idx] * result.config.drainage_scale
        st.markdown(
            f"""
            <div class="hazard-hero" style="border-color:{color}66;box-shadow:0 0 0 1px {color}22, 0 12px 28px rgba(0,0,0,0.35);">
              <div class="district-name">{st.session_state.selected_region}</div>
              <div class="place-line">{CITY.city_name}, {CITY.state_name}</div>
              <div class="hazard-status" style="color:{color};">{label}</div>
              <div class="hazard-depth">{depth:.2f}<span>m water</span></div>
              <div class="hazard-meta">
                <div class="cell"><div class="k">ETA to critical</div><div class="v" style="color:{color};">{eta_text(ttc)}</div></div>
                <div class="cell"><div class="k">Population</div><div class="v">{CITY.population[sel_idx]:,}</div></div>
                <div class="cell"><div class="k">Elevation</div><div class="v">{CITY.elevation[sel_idx]:.0f} m</div></div>
                <div class="cell"><div class="k">Drainage</div><div class="v">{drain:.0f} mm/h</div></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.container(border=True):
        st.markdown('<div class="panel-title-sm">Why this hazard</div>', unsafe_allow_html=True)
        reasons = flooding_reasons(CITY, result, sel_idx, t_idx)
        for reason in reasons:
            st.markdown(f'<div class="why-item">• {reason}</div>', unsafe_allow_html=True)

    with st.expander("Water source breakdown", expanded=False):
        sources = water_source_breakdown(CITY, result, sel_idx, t_idx)
        for name, value in sources.items():
            st.markdown(
                f'<div class="src-row"><span>{name}</span><span>{value:.2f} m</span></div>',
                unsafe_allow_html=True,
            )

    with st.expander("What-if analysis", expanded=False):
        counts = result.counts_at(t_idx)
        st.write(
            f"At {clock_label(hours)}: **{counts['Critical']}** critical · "
            f"**{counts['Warning']}** warning · affected **{result.affected_population(t_idx):,}** people."
        )
        cmp_names = [n for n in PRESETS if n != "Custom"]
        a = st.selectbox("Compare to preset", cmp_names, key="whatif_preset")
        other = run_simulation(CITY, apply_preset(a, CITY))
        oi = min(t_idx, other.n_steps - 1)
        first = other.first_critical_hour()
        st.caption(
            f"{a}: {other.counts_at(oi)['Critical']} critical · "
            f"affected {other.affected_population(oi):,} · "
            f"first critical {first if first is not None else '—'} h"
        )

# ── Bottom playback bar ──────────────────────────────────────────────────
st.markdown('<div class="bottom-bar">', unsafe_allow_html=True)
b1, b2, b3, b4 = st.columns((1.35, 1.1, 4.2, 0.9), gap="small")
with b1:
    cplay, creset = st.columns(2)
    with cplay:
        play_label = "Pause" if st.session_state.playing else "Play"
        if st.button(play_label, width="stretch", type="primary"):
            if st.session_state.t_idx >= max_idx and not st.session_state.playing:
                st.session_state.t_idx = 0
            st.session_state.playing = not st.session_state.playing
            st.rerun()
    with creset:
        if st.button("Reset", width="stretch"):
            st.session_state.playing = False
            st.session_state.t_idx = 0
            st.rerun()
with b2:
    speed = st.segmented_control(
        "SPEED",
        options=[1, 2, 4, 8],
        format_func=lambda x: f"{x}x",
        key="play_speed",
        label_visibility="collapsed",
    )
    if speed is None:
        st.session_state.play_speed = 1
with b3:
    st.slider(
        "Timeline",
        min_value=0,
        max_value=max_idx,
        key="t_idx",
        label_visibility="collapsed",
    )
with b4:
    st.markdown(
        f'<div class="t-clock">{clock_label(float(result.times_h[int(st.session_state.t_idx)]))}</div>',
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)


@st.fragment(run_every=timedelta(milliseconds=700) if st.session_state.playing else None)
def _advance_playback() -> None:
    if not st.session_state.playing:
        return
    res = st.session_state.get("result")
    if res is None:
        return
    cap = res.n_steps - 1
    nxt = min(cap, int(st.session_state.t_idx) + int(st.session_state.play_speed or 1))
    st.session_state.t_idx = nxt
    if nxt >= cap:
        st.session_state.playing = False
    st.rerun()


_advance_playback()
