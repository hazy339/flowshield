from __future__ import annotations

from datetime import timedelta

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from streamlit_folium import st_folium

from simulation.city import list_regions, load_city, resolve_region_query
from simulation.model import CRITICAL, SimConfig, SimulationResult, WARNING, run_simulation
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
            padding: 1.05rem 1.45rem 0.85rem !important;
            max-width: 100% !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--panel);
            border: 1px solid var(--line) !important;
            border-radius: 14px;
            padding: 0.35rem 0.55rem 0.55rem;
        }
        .fs-top {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0.2rem;
            margin: 0;
            padding: 1.05rem 0.1rem 0.1rem;
            min-height: 4.4rem;
        }
        .fs-main-gap {
            height: 1.45rem;
        }
        .fs-brand {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 0.28rem;
        }
        .fs-logo {
            font-size: 1.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            color: var(--text);
            line-height: 1.1;
        }
        .fs-logo span { color: var(--accent); }
        .fs-sub {
            color: var(--muted);
            font-size: 0.84rem;
            line-height: 1.3;
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
        .action-callout {
            margin-top: 0.75rem;
            padding: 0.55rem 0.65rem;
            border-radius: 10px;
            border: 1px solid;
        }
        .action-callout .action-kicker {
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }
        .action-callout .action-body {
            font-size: 0.84rem;
            color: #e8eef7;
            line-height: 1.35;
        }
        .alert-summary {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.65rem;
            margin: 0.35rem 0 0.75rem;
        }
        .alert-card {
            border-radius: 12px;
            border: 1px solid;
            padding: 0.7rem 0.8rem;
            background: rgba(11,18,32,0.72);
        }
        .alert-card.warn {
            border-color: rgba(245,166,35,0.55);
            box-shadow: inset 3px 0 0 #f5a623;
        }
        .alert-card.evac {
            border-color: rgba(231,76,60,0.65);
            box-shadow: inset 3px 0 0 #e74c3c;
            animation: fs-alert-pulse 1.8s ease-in-out infinite;
        }
        .alert-card .alert-kicker {
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }
        .alert-card.warn .alert-kicker { color: #f5a623; }
        .alert-card.evac .alert-kicker { color: #e74c3c; }
        .alert-card .alert-count {
            font-size: 1.55rem;
            font-weight: 800;
            color: var(--text);
            line-height: 1.15;
            margin: 0.2rem 0 0.15rem;
        }
        .alert-card .alert-count span {
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--muted);
            margin-left: 0.25rem;
        }
        .alert-card .alert-pop {
            font-size: 0.8rem;
            color: #c5d4e8;
        }
        .alert-card .alert-msg {
            font-size: 0.78rem;
            color: var(--muted);
            margin-top: 0.35rem;
            line-height: 1.35;
        }
        .alert-empty {
            color: var(--muted);
            font-size: 0.82rem;
            padding: 0.35rem 0.1rem 0.15rem;
        }
        @keyframes fs-alert-pulse {
            0%, 100% { box-shadow: inset 3px 0 0 #e74c3c, 0 0 0 0 rgba(231,76,60,0); }
            50% { box-shadow: inset 3px 0 0 #e74c3c, 0 0 0 4px rgba(231,76,60,0.12); }
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
            margin-bottom: 0.15rem;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--panel);
            padding: 0.65rem 0.85rem 0.55rem;
        }
        .t-clock {
            color: var(--accent);
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            font-size: 1.05rem;
            text-align: right;
            padding-top: 0.55rem;
            letter-spacing: 0.02em;
        }
        .fs-playback-label {
            color: var(--muted);
            font-size: 0.68rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            font-weight: 650;
            margin: 0 0 0.35rem;
        }
        div[data-testid="stVerticalBlock"]:has(.fs-playback-mark) button {
            min-height: 2.65rem !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            font-size: 0.92rem !important;
            letter-spacing: 0.02em;
            padding: 0.35rem 0.7rem !important;
        }
        div[data-testid="stVerticalBlock"]:has(.fs-playback-mark) div[data-testid="stSlider"] {
            padding-top: 0.15rem;
        }
        div[data-testid="stSlider"] label { color: var(--muted) !important; }
        button[kind="secondary"] {
            border: 1px solid var(--line) !important;
        }
        .fs-collapse-hint {
            color: var(--muted);
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            text-align: center;
            margin: 0.35rem 0 0.15rem;
        }
        /* Collapsed scenarios → settings rail (scoped to settings panel only) */
        div[data-testid="stHorizontalBlock"] > div:has(.fs-settings-mark),
        div[data-testid="column"]:has(.fs-settings-mark),
        [data-testid="stColumn"]:has(.fs-settings-mark) {
            flex: 0 0 4.85rem !important;
            min-width: 4.85rem !important;
            max-width: 5.1rem !important;
            width: 4.85rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-settings-mark) {
            padding: 0.5rem 0.3rem !important;
            min-width: 3.6rem !important;
            width: 100%;
            box-sizing: border-box;
            background: linear-gradient(180deg, rgba(21,29,46,0.98), rgba(11,18,32,0.95));
            border-color: rgba(30,224,172,0.28) !important;
            box-shadow: 0 8px 22px rgba(0,0,0,0.28);
            overflow: visible !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-settings-mark) button {
            background: rgba(30, 224, 172, 0.1) !important;
            border: 1px solid rgba(30, 224, 172, 0.45) !important;
            border-radius: 14px !important;
            color: #1ee0ac !important;
            font-size: 1.35rem !important;
            line-height: 1 !important;
            width: 2.85rem !important;
            min-width: 2.85rem !important;
            max-width: 2.85rem !important;
            height: 2.85rem !important;
            min-height: 2.85rem !important;
            padding: 0 !important;
            margin: 0 auto !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 0 0 1px rgba(30,224,172,0.08), 0 6px 18px rgba(30,224,172,0.12) !important;
            transition: background 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-settings-mark) button:hover {
            background: rgba(30, 224, 172, 0.2) !important;
            box-shadow: 0 0 0 1px rgba(30,224,172,0.2), 0 8px 22px rgba(30,224,172,0.22) !important;
            transform: translateY(-1px);
        }
        .fs-settings-caption {
            display: none;
        }
        /* Top search cluster — scoped to search panel only */
        .fs-search-chrome {
            display: none;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-search-mark) {
            background: rgba(11, 18, 32, 0.55);
            border: 1px solid rgba(30, 224, 172, 0.22) !important;
            border-radius: 16px;
            padding: 0.65rem 0.8rem !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04), 0 10px 28px rgba(0,0,0,0.22);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-search-mark) [data-testid="stTextInput"] input {
            background: rgba(8, 14, 24, 0.92) !important;
            border: 1px solid rgba(30, 224, 172, 0.38) !important;
            border-radius: 10px !important;
            color: var(--text) !important;
            min-height: 2.7rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-search-mark) [data-testid="stTextInput"] input:focus {
            border-color: rgba(30, 224, 172, 0.6) !important;
            box-shadow: 0 0 0 2px rgba(30, 224, 172, 0.15) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-search-mark) [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-district-mark) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background-color: rgba(8, 14, 24, 0.95) !important;
            border-color: rgba(30, 224, 172, 0.42) !important;
            border-radius: 10px !important;
            color: var(--text) !important;
            min-height: 2.7rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-search-mark) [data-testid="stSelectbox"] svg,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-district-mark) [data-testid="stSelectbox"] svg {
            fill: #1ee0ac !important;
            opacity: 1 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-search-mark) button[kind="primary"] {
            border-radius: 10px !important;
            min-height: 2.7rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.04em !important;
            text-transform: uppercase;
            font-size: 0.86rem !important;
            background: linear-gradient(180deg, #24ecc0, #16c49a) !important;
            color: #062018 !important;
            border: 0 !important;
            box-shadow: 0 6px 16px rgba(30, 224, 172, 0.25) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.fs-search-mark) button[kind="primary"]:hover {
            filter: brightness(1.05);
        }

        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.45rem;
            margin: 0.35rem 0 0.55rem;
        }
        .info-card {
            background: rgba(11,18,32,0.72);
            border: 1px solid rgba(30,224,172,0.14);
            border-radius: 10px;
            padding: 0.45rem 0.55rem;
        }
        .info-card .k {
            font-size: 0.66rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
        }
        .info-card .v {
            font-size: 0.98rem;
            font-weight: 750;
            color: var(--text);
            margin-top: 0.12rem;
        }
        .water-gauge {
            height: 10px;
            border-radius: 999px;
            background: rgba(255,255,255,0.08);
            overflow: hidden;
            margin: 0.35rem 0 0.55rem;
        }
        .water-gauge > span {
            display: block;
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #1ee0ac, #4cc3ff, #e74c3c);
        }
        .ew-row {
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            padding: 0.35rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 0.82rem;
        }
        .ew-row .k { color: var(--muted); }
        .ew-row .v { color: var(--text); font-weight: 700; }
        .src-legend-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.78rem;
            padding: 0.22rem 0;
            color: #c5d4e8;
        }
        .src-dot {
            width: 8px; height: 8px; border-radius: 50%;
            display: inline-block; margin-right: 0.4rem;
        }
        .move-chip {
            font-size: 0.78rem;
            color: #c5d4e8;
            padding: 0.2rem 0;
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


def district_action(status: int) -> tuple[str, str, str]:
    if status >= CRITICAL:
        return (
            "EVACUATE NOW",
            "Critical flooding. Leave the flood zone immediately and move to higher ground.",
            "#e74c3c",
        )
    if status >= WARNING:
        return (
            "DANGER ALERT",
            "District in danger. Prepare to evacuate, move valuables upstairs, and monitor the timeline.",
            "#f5a623",
        )
    return (
        "MONITORING",
        "Depth is below the warning threshold. Continue watching the playback for rising water.",
        "#1ee0ac",
    )


def alert_groups(city, result: SimulationResult, t_idx: int) -> tuple[list[dict], list[dict]]:
    danger: list[dict] = []
    evacuate: list[dict] = []
    for idx, name in enumerate(city.names):
        status = int(result.status[t_idx, idx])
        if status < WARNING:
            continue
        row = {
            "name": name,
            "depth": float(result.water[t_idx, idx]),
            "population": int(city.population[idx]),
            "eta": float(result.time_to_critical_h[idx]),
        }
        if status >= CRITICAL:
            evacuate.append(row)
        else:
            danger.append(row)
    danger.sort(key=lambda r: r["depth"], reverse=True)
    evacuate.sort(key=lambda r: r["depth"], reverse=True)
    return danger, evacuate


def render_alert_district_buttons(rows: list[dict], prefix: str) -> None:
    if not rows:
        st.markdown('<div class="alert-empty">None at this hour.</div>', unsafe_allow_html=True)
        return
    cols = st.columns(3)
    for i, row in enumerate(rows):
        label = f"{row['name']} · {row['depth']:.2f} m"
        with cols[i % 3]:
            if st.button(label, key=f"{prefix}_{row['name']}", width="stretch"):
                st.session_state.selected_region = row["name"]
                st.rerun()


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
    st.session_state.t_idx = 0
    st.session_state.playing = False
    st.session_state.seek_peak = False
    st.session_state.playback_tick = False


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
        "left_collapsed": False,
        "trace_active": False,
        "scenario_label": "Extreme Rainfall",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    # One-time migration from older short-storm defaults
    if st.session_state.get("haz_v2") != 4:
        st.session_state.haz_v2 = 4
        st.session_state.show_grid = False
        st.session_state.playing = False
        st.session_state.playback_tick = False
        # Keep radio label aligned with active preset after UI redesign
        pname = st.session_state.get("preset_name", "Extreme flood")
        if pname in PRESET_TO_SCENARIO:
            st.session_state.scenario_label = PRESET_TO_SCENARIO[pname]
        apply_preset_to_state(pname, get_city())
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
        st.session_state.t_idx = 0
        st.session_state.playing = False
        st.session_state.seek_peak = False
        st.session_state.playback_tick = False
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
    warn_m = float(result.config.warning_m)
    crit_m = float(result.config.critical_m)
    sources = water_source_breakdown(city, result, idx, t_idx)
    if status == 0:
        reasons.append(f"Depth is still below the warning threshold ({warn_m:.2f} m).")
        return reasons
    if result.config.rainfall_mm_h >= 40:
        reasons.append(f"High rainfall input ({result.config.rainfall_mm_h:.0f} mm/h).")
    if sources.get("Net inflow from neighbours", 0.0) > 0.05:
        reasons.append(
            f"Significant upstream inflow (~{sources['Net inflow from neighbours']:.2f} m depth-equivalent)."
        )
    if drain < max(14.0, result.config.rainfall_mm_h * 0.2):
        reasons.append(f"Drainage capacity insufficient ({drain:.0f} mm/h).")
    if elev <= sorted(city.elevation)[max(0, city.n // 3)]:
        reasons.append(f"Low elevation ({elev:.0f} m) promotes ponding.")
    if city.ids[idx] in result.failed_districts:
        reasons.append("Drainage pumps have failed in this district.")
    for a, b in result.blocked_edges:
        if city.ids[idx] in (a, b):
            reasons.append("A connected drainage channel is blocked, trapping runoff.")
            break
    if depth >= crit_m:
        reasons.append(f"Critical threshold crossed ({depth:.2f} m ≥ {crit_m:.2f} m).")
    elif depth >= warn_m:
        reasons.append(f"Warning threshold crossed ({depth:.2f} m ≥ {warn_m:.2f} m).")
    return reasons[:4]


PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(11,18,32,0.35)",
    font=dict(color="#c5d4e8", size=12),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)


def build_progression_figure(result: SimulationResult, t_idx: int, selected_idx: int, district_name: str):
    times = [float(t) for t in result.times_h]
    safe, warn, crit, mean_depth, sel_depth = [], [], [], [], []
    for t in range(result.n_steps):
        counts = result.counts_at(t)
        safe.append(counts["Safe"])
        warn.append(counts["Warning"])
        crit.append(counts["Critical"])
        mean_depth.append(float(result.water[t].mean()))
        sel_depth.append(float(result.water[t, selected_idx]))

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=times, y=safe, name="Safe districts", line=dict(color="#1ee0ac", width=2)),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=times, y=warn, name="Warning", line=dict(color="#f5a623", width=2)),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=times, y=crit, name="Critical", line=dict(color="#e74c3c", width=2.5)),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=mean_depth,
            name="Basin mean depth",
            line=dict(color="#7ec8ff", width=2, dash="dot"),
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=times,
            y=sel_depth,
            name=f"{district_name} depth",
            line=dict(color="#ffffff", width=2),
        ),
        secondary_y=True,
    )
    now_h = times[min(t_idx, len(times) - 1)]
    fig.add_vline(x=now_h, line_width=2, line_dash="dash", line_color="rgba(30,224,172,0.85)")
    fig.add_annotation(
        x=now_h,
        y=1.02,
        yref="paper",
        text="Now",
        showarrow=False,
        font=dict(color="#1ee0ac", size=11),
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(
            text="Flood progression over time",
            font=dict(size=14, color="#e8eef7"),
            pad=dict(b=14),
        ),
        height=340,
        hovermode="x unified",
        margin=dict(l=40, r=24, t=58, b=40),
    )
    fig.update_xaxes(title_text="Hours", gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_yaxes(
        title_text="Districts",
        secondary_y=False,
        gridcolor="rgba(255,255,255,0.06)",
        zeroline=False,
        rangemode="tozero",
    )
    fig.update_yaxes(
        title_text="Water depth (m)",
        secondary_y=True,
        gridcolor="rgba(255,255,255,0.03)",
        zeroline=False,
        rangemode="tozero",
    )
    return fig


def build_status_pie(result: SimulationResult, t_idx: int):
    counts = result.counts_at(t_idx)
    labels = ["Safe", "Warning", "Critical"]
    values = [counts["Safe"], counts["Warning"], counts["Critical"]]
    colors = ["#1ee0ac", "#f5a623", "#e74c3c"]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker=dict(colors=colors, line=dict(color="#0b1220", width=2)),
                textinfo="label+percent",
                hovertemplate="%{label}: %{value} districts<br>%{percent}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Basin hazard mix (now)", font=dict(size=14, color="#e8eef7")),
        height=320,
        showlegend=False,
        margin=dict(l=20, r=20, t=48, b=20),
    )
    return fig


def build_cause_pie(city, result: SimulationResult, idx: int, t_idx: int, district_name: str):
    sources = water_source_breakdown(city, result, idx, t_idx)
    cause_keys = [
        ("Rainfall accumulation", "#4cc3ff"),
        ("Initial ponding", "#9b8cff"),
        ("Net inflow from neighbours", "#f5a623"),
    ]
    labels = []
    values = []
    colors = []
    for key, color in cause_keys:
        val = float(sources.get(key, 0.0))
        if val > 1e-6:
            labels.append(key.replace(" accumulation", "").replace(" from neighbours", ""))
            values.append(val)
            colors.append(color)
    if not values:
        labels = ["No standing flood yet"]
        values = [1.0]
        colors = ["#3a465c"]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker=dict(colors=colors, line=dict(color="#0b1220", width=2)),
                textinfo="label+percent",
                hovertemplate="%{label}: %{value:.2f} m<br>%{percent}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=f"Flood causes · {district_name}", font=dict(size=14, color="#e8eef7")),
        height=320,
        showlegend=False,
        margin=dict(l=20, r=20, t=48, b=20),
    )
    return fig



SCENARIO_LABELS = [
    "Normal Rainfall",
    "Heavy Rainfall",
    "Extreme Rainfall",
    "Drainage Failure",
    "Blocked Channel",
]
SCENARIO_TO_PRESET = {
    "Normal Rainfall": "Normal rainfall",
    "Heavy Rainfall": "Heavy rainfall",
    "Extreme Rainfall": "Extreme flood",
    "Drainage Failure": "Drainage failure",
    "Blocked Channel": "Blocked drainage channel",
}
PRESET_TO_SCENARIO = {v: k for k, v in SCENARIO_TO_PRESET.items()}


def minutes_eta(target_h: float, now_h: float) -> str:
    if target_h != target_h:  # NaN
        return "Not reached"
    if now_h + 1e-9 >= target_h:
        return "Already reached"
    mins = max(0.0, (target_h - now_h) * 60.0)
    if mins < 1:
        return "< 1 min"
    return f"~{mins:.0f} min"


def warning_lead_minutes(ttw: float, ttc: float) -> str:
    if ttw != ttw or ttc != ttc:
        return "—"
    lead = max(0.0, (ttc - ttw) * 60.0)
    return f"{lead:.0f} min"


def build_water_level_chart(result: SimulationResult, idx: int, t_idx: int, name: str):
    times = [float(t) for t in result.times_h]
    depths = [float(result.water[t, idx]) for t in range(result.n_steps)]
    warn = float(result.config.warning_m)
    crit = float(result.config.critical_m)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=times, y=depths, name="W(t)", line=dict(color="#4cc3ff", width=2.4), fill="tozeroy",
                   fillcolor="rgba(76,195,255,0.12)")
    )
    fig.add_hline(y=warn, line_dash="dash", line_color="#f5a623", annotation_text="Warning", annotation_font_color="#f5a623")
    fig.add_hline(y=crit, line_dash="dash", line_color="#e74c3c", annotation_text="Critical", annotation_font_color="#e74c3c")
    now_h = times[min(t_idx, len(times) - 1)]
    fig.add_vline(x=now_h, line_width=1.5, line_dash="dot", line_color="rgba(30,224,172,0.85)")
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=220,
        margin=dict(l=36, r=12, t=28, b=32),
        title=dict(text=f"Water level · {name}", font=dict(size=12, color="#e8eef7")),
        showlegend=False,
    )
    fig.update_xaxes(title_text="Hours", gridcolor="rgba(255,255,255,0.06)", zeroline=False)
    fig.update_yaxes(title_text="m", gridcolor="rgba(255,255,255,0.06)", zeroline=False, rangemode="tozero")
    return fig


def build_sources_donut(city, result: SimulationResult, idx: int, t_idx: int):
    sources = water_source_breakdown(city, result, idx, t_idx)
    items = [
        ("Rainfall", float(sources["Rainfall accumulation"]), "#4cc3ff"),
        ("Upstream flow", float(sources["Net inflow from neighbours"]), "#f5a623"),
        ("Initial stored", float(sources["Initial ponding"]), "#9b8cff"),
    ]
    labels, values, colors = [], [], []
    for lab, val, col in items:
        if val > 1e-6:
            labels.append(lab)
            values.append(val)
            colors.append(col)
    if not values:
        labels, values, colors = ["No standing water"], [1.0], ["#3a465c"]
    total = sum(values) or 1.0
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.58,
                marker=dict(colors=colors, line=dict(color="#0b1220", width=2)),
                textinfo="none",
                hovertemplate="%{label}: %{value:.2f} m<br>%{percent}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=200,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        annotations=[
            dict(text="estimate", x=0.5, y=0.5, font=dict(size=11, color="#8ea0b8"), showarrow=False)
        ],
    )
    legend_rows = []
    for lab, val, col in zip(labels, values, colors):
        pct = 100.0 * val / total
        legend_rows.append((lab, f"{val:.2f} m · {pct:.0f}%", col))
    return fig, legend_rows


def movement_summary(result: SimulationResult, idx: int, t_idx: int) -> dict:
    rows = result.district_edge_flows(t_idx, idx)
    incoming = [r for r in rows if r["direction"] == "incoming" and r["magnitude_m3s"] > 1e-6]
    outgoing = [r for r in rows if r["direction"] == "outgoing" and r["magnitude_m3s"] > 1e-6]
    incoming.sort(key=lambda r: r["magnitude_m3s"], reverse=True)
    outgoing.sort(key=lambda r: r["magnitude_m3s"], reverse=True)
    return {
        "in_m3s": sum(r["magnitude_m3s"] for r in incoming),
        "out_m3s": sum(r["magnitude_m3s"] for r in outgoing),
        "from": incoming[:3],
        "to": outgoing[:3],
        "edges": {(r["edge"][0], r["edge"][1]) for r in incoming},
    }

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
top_l, top_r = st.columns((1.15, 1.85), gap="medium")
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
    with st.container(border=True):
        st.markdown('<div class="fs-search-mark"></div>', unsafe_allow_html=True)
        s1, s2, s3 = st.columns((2.2, 2.4, 1.5), gap="small")
        with s1:
            st.text_input(
                "Search",
                placeholder="City or state — Delhi, Kochi, Assam…",
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
            if st.button("Search", width="stretch", type="primary"):
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
# Apply playback advance BEFORE any widget bound to key "t_idx".
if st.session_state.pop("playback_tick", False) and st.session_state.playing:
    nxt = min(max_idx, int(st.session_state.t_idx) + int(st.session_state.play_speed or 1))
    st.session_state.t_idx = nxt
    if nxt >= max_idx:
        st.session_state.playing = False
st.session_state.t_idx = min(int(st.session_state.t_idx), max_idx)

t_idx = int(st.session_state.t_idx)
hours = float(result.times_h[t_idx])

st.markdown('<div class="fs-main-gap"></div>', unsafe_allow_html=True)

# ── Main layout: compact scenarios | map + timeline | region intelligence ─
left, center, right = st.columns((0.95, 2.55, 1.35), gap="medium")

with left:
    with st.container(border=True):
        st.markdown('<div class="panel-title">SCENARIO</div>', unsafe_allow_html=True)
        st.caption(f"{CITY.label}")
        scenario = st.radio(
            "Scenario",
            SCENARIO_LABELS,
            key="scenario_label",
            label_visibility="collapsed",
        )
        preset = SCENARIO_TO_PRESET[scenario]
        if preset != st.session_state.get("preset_name"):
            apply_preset_to_state(preset, CITY)
            st.session_state.preset_name = preset
            st.session_state.last_preset = preset
            st.session_state.cfg_key = None
            st.rerun()
        st.caption(PRESETS[preset].description)

        with st.expander("Advanced controls", expanded=False):
            st.slider("Rainfall intensity", 5.0, 180.0, step=1.0, key="rainfall", format="%.0f mm/hr")
            st.slider("Rain duration", 30.0, 1440.0, step=15.0, key="rain_duration_min", format="%.0f min")
            st.slider("Drainage capacity", 0.25, 2.0, step=0.05, key="drainage_scale", format="x%.2f")
            st.slider("Initial water level", 0.0, 2.0, step=0.05, key="initial_scale", format="x%.2f")
            st.slider("Sim duration", 60.0, 2880.0, step=30.0, key="sim_duration_min", format="%.0f min")
            st.multiselect("Drainage failure", CITY.names, key="failed_names")
            st.selectbox("Blocked channel", CHANNEL_LABELS, key="blocked_label")

        if st.button("Run simulation", type="primary", width="stretch"):
            st.session_state.cfg_key = None
            st.session_state.t_idx = 0
            st.session_state.playing = True
            st.session_state.seek_peak = False
            st.rerun()

with center:
    sel_name = st.session_state.selected_region
    sel_id = CITY.ids[CITY.names.index(sel_name)] if sel_name in CITY.names else None
    sel_idx_pre = CITY.names.index(sel_name) if sel_name in CITY.names else 0
    move_pre = movement_summary(result, sel_idx_pre, t_idx)
    highlight = move_pre["edges"] if st.session_state.get("trace_active") else None

    fmap = build_map(
        CITY,
        result,
        t_idx=t_idx,
        color_mode="Risk",
        blocked_edges=result.blocked_edges,
        show_grid=False,
        show_labels=True,
        selected_id=sel_id,
        highlight_edges=highlight,
    )
    map_state = st_folium(
        fmap,
        height=620,
        use_container_width=True,
        returned_objects=["last_object_clicked_popup", "last_object_clicked"],
        key=f"main-map-{CITY.region_id}-{st.session_state.cfg_key}-{sel_id}-{t_idx}-{bool(highlight)}",
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

    # Timeline — primary time control
    st.markdown('<div class="fs-playback-mark"></div>', unsafe_allow_html=True)
    st.markdown('<div class="bottom-bar">', unsafe_allow_html=True)
    p1, p2, p3 = st.columns((1.1, 1.1, 3.2), gap="small")
    with p1:
        play_label = "Pause" if st.session_state.playing else "Play"
        if st.button(play_label, width="stretch", type="primary", key="play_btn"):
            if st.session_state.t_idx >= max_idx and not st.session_state.playing:
                st.session_state.t_idx = 0
            st.session_state.playing = not st.session_state.playing
            st.rerun()
    with p2:
        if st.button("Reset", width="stretch", key="reset_btn"):
            st.session_state.playing = False
            st.session_state.t_idx = 0
            st.rerun()
    with p3:
        st.markdown(
            f'<div class="t-clock">{clock_label(float(result.times_h[int(st.session_state.t_idx)]))}</div>',
            unsafe_allow_html=True,
        )
    st.slider(
        "Timeline",
        min_value=0,
        max_value=max_idx,
        key="t_idx",
        label_visibility="collapsed",
    )
    st.caption(f"T+0 → T+{float(result.times_h[-1]):.1f} h")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    with st.container(border=True):
        st.markdown('<div class="panel-title">SELECTED REGION</div>', unsafe_allow_html=True)
        st.selectbox("Region", CITY.names, key="selected_region", label_visibility="collapsed")
        sel_idx = CITY.names.index(st.session_state.selected_region)
        status = int(result.status[t_idx, sel_idx])
        label = result.status_label(t_idx, sel_idx).upper()
        if label == "WARNING":
            label = "WARNING"
        depth = float(result.water[t_idx, sel_idx])
        color = STATUS_COLOR[status]
        ttw = float(result.time_to_warning_h[sel_idx])
        ttc = float(result.time_to_critical_h[sel_idx])
        warn_m = float(result.config.warning_m)
        crit_m = float(result.config.critical_m)
        drain = CITY.drainage_mm_h[sel_idx] * result.config.drainage_scale
        rain_here = float(result.config.rainfall_mm_h) * float(CITY.rainfall_factor[sel_idx])
        init_w = float(CITY.initial_water[sel_idx]) * float(result.config.initial_scale)
        gauge = min(100.0, 100.0 * depth / max(crit_m * 1.25, 0.01))

        st.markdown(
            f"""
            <div class="hazard-hero" style="border-color:{color}66;box-shadow:0 0 0 1px {color}22, 0 12px 28px rgba(0,0,0,0.35);">
              <div class="district-name">{st.session_state.selected_region}</div>
              <div class="place-line">{CITY.city_name}, {CITY.state_name}</div>
              <div style="font-size:0.7rem;letter-spacing:0.12em;color:var(--muted);margin-top:0.45rem;">FLOOD RISK</div>
              <div class="hazard-status" style="color:{color};">{label}</div>
              <div style="font-size:0.7rem;letter-spacing:0.12em;color:var(--muted);margin-top:0.55rem;">CURRENT WATER LEVEL</div>
              <div class="hazard-depth">{depth:.2f}<span>m</span></div>
              <div class="water-gauge"><span style="width:{gauge:.1f}%;background:{color};"></span></div>
              <div class="ew-row"><span class="k">Warning</span><span class="v">{warn_m:.2f} m</span></div>
              <div class="ew-row"><span class="k">Critical</span><span class="v">{crit_m:.2f} m</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="panel-title-sm">Early warning</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="ew-row"><span class="k">Time to warning</span><span class="v">{minutes_eta(ttw, hours)}</span></div>
            <div class="ew-row"><span class="k">Time to critical</span><span class="v">{minutes_eta(ttc, hours)}</span></div>
            <div class="ew-row"><span class="k">Warning lead time</span><span class="v">{warning_lead_minutes(ttw, ttc)}</span></div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="panel-title-sm">Current conditions</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="info-grid">
              <div class="info-card"><div class="k">Rainfall</div><div class="v">{rain_here:.0f} mm/h</div></div>
              <div class="info-card"><div class="k">Elevation</div><div class="v">{CITY.elevation[sel_idx]:.1f} m</div></div>
              <div class="info-card"><div class="k">Drainage</div><div class="v">{drain:.0f} mm/h</div></div>
              <div class="info-card"><div class="k">Initial water</div><div class="v">{init_w:.2f} m</div></div>
              <div class="info-card"><div class="k">Population</div><div class="v">{CITY.population[sel_idx]:,}</div></div>
              <div class="info-card"><div class="k">Timeline</div><div class="v">{clock_label(hours)}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="panel-title-sm">Why is this flooding?</div>', unsafe_allow_html=True)
        reasons = flooding_reasons(CITY, result, sel_idx, t_idx)[:4]
        for reason in reasons:
            st.markdown(f'<div class="why-item">• {reason}</div>', unsafe_allow_html=True)

        t1, t2 = st.columns(2, gap="small")
        with t1:
            trace_label = "Trace · ON" if st.session_state.trace_active else "Trace Water Source"
            if st.button(trace_label, width="stretch", key="trace_btn"):
                st.session_state.trace_active = not st.session_state.trace_active
                st.rerun()
        with t2:
            with st.popover("What-if Analysis"):
                counts = result.counts_at(t_idx)
                st.write(
                    f"At {clock_label(hours)}: **{counts['Critical']}** critical · "
                    f"**{counts['Warning']}** warning · affected **{result.affected_population(t_idx):,}**."
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

# ── Region hydrology (below map + sidebars) ───────────────────────────────
sel_idx = CITY.names.index(st.session_state.selected_region)
st.markdown('<div class="fs-main-gap"></div>', unsafe_allow_html=True)
with st.container(border=True):
    st.markdown(
        f'<div class="panel-title">REGION HYDROLOGY · {st.session_state.selected_region}</div>',
        unsafe_allow_html=True,
    )
    chart_l, chart_r = st.columns(2, gap="medium")
    with chart_l:
        st.markdown('<div class="panel-title-sm">Water level over time</div>', unsafe_allow_html=True)
        st.plotly_chart(
            build_water_level_chart(result, sel_idx, t_idx, st.session_state.selected_region),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with chart_r:
        st.markdown('<div class="panel-title-sm">Water sources</div>', unsafe_allow_html=True)
        st.caption("Model-derived contribution estimate at this hour")
        donut, legend_rows = build_sources_donut(CITY, result, sel_idx, t_idx)
        st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})
        for lab, meta, col in legend_rows:
            st.markdown(
                f'<div class="src-legend-row"><span><span class="src-dot" style="background:{col}"></span>{lab}</span><span>{meta}</span></div>',
                unsafe_allow_html=True,
            )

    move = movement_summary(result, sel_idx, t_idx)
    st.markdown('<div class="panel-title-sm">Water movement</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="info-grid">
          <div class="info-card"><div class="k">Incoming</div><div class="v">{move['in_m3s']:.1f} m³/s</div></div>
          <div class="info-card"><div class="k">Outgoing</div><div class="v">{move['out_m3s']:.1f} m³/s</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    move_cols = st.columns(2, gap="medium")
    with move_cols[0]:
        for r in move["from"]:
            st.markdown(
                f'<div class="move-chip">From: {r["neighbor_name"]} · {r["magnitude_m3s"]:.1f} m³/s</div>',
                unsafe_allow_html=True,
            )
        if not move["from"]:
            st.caption("No incoming neighbour flow at this hour.")
    with move_cols[1]:
        for r in move["to"]:
            st.markdown(
                f'<div class="move-chip">To: {r["neighbor_name"]} · {r["magnitude_m3s"]:.1f} m³/s</div>',
                unsafe_allow_html=True,
            )
        if not move["to"]:
            st.caption("No outgoing neighbour flow at this hour.")

with st.expander("Model equations", expanded=False):
    st.markdown(
        r"""
        At each step Δt:

        1. **Rain** · \(w \leftarrow w + R\cdot c\cdot f\cdot \Delta t\) while raining
        2. **Drain** · \(w \leftarrow \max(0,\, w - D\cdot s\cdot \Delta t - I\cdot \Delta t)\)
        3. **Flow** · \(H = z + w\), flux \(k\sqrt{|H|}\) (signed) along edges
        4. **Sea / river sink** on coastal / riverfront districts
        5. **Class** · Safe / Warning / Critical from depth thresholds
        """
    )



@st.fragment(run_every=timedelta(milliseconds=1100) if st.session_state.playing else None)
def _advance_playback() -> None:
    if not st.session_state.playing:
        return
    # Defer t_idx mutation to the next full run (before the timeline slider mounts).
    st.session_state.playback_tick = True
    st.rerun()


if st.session_state.playing:
    _advance_playback()
