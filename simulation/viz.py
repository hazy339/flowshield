from __future__ import annotations

import branca.colormap as cm
import folium
from folium.features import GeoJsonTooltip
from folium.plugins import Fullscreen, PolyLineTextPath

from .city import City
from .model import CRITICAL, SAFE, WARNING, SimulationResult

RISK_COLORS = {
    SAFE: "#1ee0ac",
    WARNING: "#f5a623",
    CRITICAL: "#e74c3c",
}
RISK_LABELS = {SAFE: "Safe", WARNING: "Warning", CRITICAL: "Critical"}


def _depth_color(depth: float, vmax: float = 1.4) -> str:
    t = max(0.0, min(1.0, depth / vmax))
    r = int(10 + t * 20)
    g = int(105 + t * 115)
    b = int(165 + t * 80)
    return f"#{r:02x}{g:02x}{b:02x}"


def _elev_color(elev: float, emin: float, emax: float) -> str:
    t = 0.0 if emax <= emin else (elev - emin) / (emax - emin)
    r = int(40 + t * 180)
    g = int(90 + t * 120)
    b = int(70 + (1 - t) * 40)
    return f"#{r:02x}{g:02x}{b:02x}"


def _legend_html(title: str, items: list[tuple[str, str]]) -> str:
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
        f'<span style="width:14px;height:14px;background:{color};display:inline-block;'
        f'border-radius:3px;border:1px solid rgba(255,255,255,0.25);"></span>'
        f'<span>{label}</span></div>'
        for label, color in items
    )
    return (
        f'<div style="position:fixed;bottom:24px;left:24px;z-index:9999;background:rgba(11,18,32,0.92);'
        f'color:#e8eef7;padding:10px 12px;border-radius:10px;font-size:12px;'
        f'border:1px solid rgba(30,224,172,0.25);min-width:150px;'
        f'"><div style="font-weight:700;margin-bottom:6px;letter-spacing:0.04em;">{title}</div>{rows}</div>'
    )


def _hazard_icon(status: int) -> folium.DivIcon:
    color = RISK_COLORS.get(status, RISK_COLORS[SAFE])
    opacity = 0.58 if status == SAFE else 0.9
    shadow = "none" if status == SAFE else "drop-shadow(0 0 10px rgba(255,255,255,0.7))"
    html = (
        '<div style="width:18px;height:18px;position:relative;'
        f'opacity:{opacity};filter:{shadow};">'
        f'<div style="width:14px;height:14px;background:{color};border:2px solid #fff;'
        'border-radius:50% 50% 50% 0;transform:rotate(-45deg);position:absolute;'
        'left:1px;top:1px;box-sizing:border-box;">'
        '<div style="width:4px;height:4px;border-radius:50%;background:rgba(11,18,32,0.55);'
        'position:absolute;left:3px;top:3px;"></div></div></div>'
    )
    return folium.DivIcon(html=html, icon_size=(18, 18), icon_anchor=(9, 18))


def build_map(
    city: City,
    result: SimulationResult | None = None,
    t_idx: int = 0,
    color_mode: str = "Risk",
    blocked_edges: tuple[tuple[str, str], ...] | None = None,
) -> folium.Map:
    fmap = folium.Map(
        location=list(city.center),
        zoom_start=11,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        control_scale=True,
    )
    fmap.fit_bounds(city.bounds)

    blocked_edges = blocked_edges or (result.blocked_edges if result else ())
    blocked = {
        (min(city.index_of[a], city.index_of[b]), max(city.index_of[a], city.index_of[b]))
        for a, b in blocked_edges
        if a in city.index_of and b in city.index_of
    }
    failed = set(result.failed_districts if result else ())

    emin = min(city.elevation)
    emax = max(city.elevation)
    water_row = result.water[t_idx] if result is not None else None
    status_row = result.status[t_idx] if result is not None else None

    def style_fn(feature):
        did = feature["properties"]["id"]
        idx = city.index_of[did]
        if color_mode == "Elevation":
            color = _elev_color(city.elevation[idx], emin, emax)
            fill_opacity = 0.28
        elif color_mode == "Water depth" and water_row is not None:
            color = _depth_color(float(water_row[idx]))
            fill_opacity = 0.34
        elif color_mode == "Risk":
            color = "#d9f0ff"
            fill_opacity = 0.0
        elif status_row is not None:
            color = RISK_COLORS[int(status_row[idx])]
            fill_opacity = 0.0
        else:
            color = "#1ee0ac"
            fill_opacity = 0.0
        return {
            "fillColor": color,
            "color": "#d9f0ff" if color_mode == "Risk" else "#8cc9dd",
            "weight": 0.7,
            "fillOpacity": fill_opacity,
        }

    def highlight_fn(_feature):
        return {"weight": 2, "color": "#ffffff", "fillOpacity": 0.18 if color_mode != "Risk" else 0.04}

    def popup_html(did: str) -> str:
        idx = city.index_of[did]
        name = city.names[idx]
        lines = [
            f"<b>{name}</b>",
            f"Elevation: {city.elevation[idx]:.0f} m",
            f"Drainage: {city.drainage_mm_h[idx]:.0f} mm/h",
            f"Population: {city.population[idx]:,}",
        ]
        if did in failed:
            lines.append("<span style='color:#e74c3c'>Drainage FAILED</span>")
        if water_row is not None and status_row is not None:
            depth = float(water_row[idx])
            label = RISK_LABELS[int(status_row[idx])]
            lines.append(f"Water depth: {depth:.2f} m")
            lines.append(f"Status: <b>{label}</b>")
            if result is not None:
                ttc = result.time_to_critical_h[idx]
                if ttc == ttc:
                    lines.append(f"Time to critical: {ttc:.1f} h")
                else:
                    lines.append("Time to critical: not reached")
        return "<br>".join(lines)

    for feat in city.geojson["features"]:
        did = feat["properties"]["id"]
        folium.GeoJson(
            feat,
            style_function=style_fn,
            highlight_function=highlight_fn,
            tooltip=GeoJsonTooltip(fields=["name"], aliases=["District"]),
            popup=folium.Popup(popup_html(did), max_width=260),
        ).add_to(fmap)

    if color_mode == "Risk" and status_row is not None:
        for idx, did in enumerate(city.ids):
            label = RISK_LABELS[int(status_row[idx])]
            lat, lon = city.centroids[did]
            folium.Marker(
                location=[lat, lon],
                icon=_hazard_icon(int(status_row[idx])),
                tooltip=f"{city.names[idx]}: {label}",
                popup=folium.Popup(popup_html(did), max_width=260),
            ).add_to(fmap)

    if result is not None and result.edge_defs and result.edge_flow.size:
        flow_row = result.edge_flow[t_idx]
        flow_values = [abs(float(value)) for value in flow_row]
        max_flow = max(flow_values, default=0.0)
        min_flow = max(1e-6, max_flow * 0.02)
        for edge_idx, (i, j) in enumerate(result.edge_defs):
            if edge_idx >= len(flow_row) or (min(i, j), max(i, j)) in blocked:
                continue
            flow = float(flow_row[edge_idx])
            magnitude = abs(flow)
            if magnitude < min_flow:
                continue
            start, end = (i, j) if flow >= 0.0 else (j, i)
            start_did, end_did = city.ids[start], city.ids[end]
            start_point = city.centroids[start_did]
            end_point = city.centroids[end_did]
            ratio = magnitude / max_flow if max_flow else 0.0
            flow_line = folium.PolyLine(
                locations=[start_point, end_point],
                color="#42d9ff",
                weight=1.5 + 5.0 * ratio**0.5,
                opacity=0.35 + 0.6 * ratio,
                tooltip=(
                    f"Flow: {city.names[start]} → {city.names[end]} · "
                    f"{magnitude:.3f} m³/s"
                ),
            ).add_to(fmap)
            PolyLineTextPath(
                flow_line,
                "▶",
                repeat=True,
                offset=7,
                attributes={"fill": "#b8f4ff", "font-size": "12"},
            ).add_to(fmap)

    for i, j in blocked:
        start_did, end_did = city.ids[i], city.ids[j]
        start_point = city.centroids[start_did]
        end_point = city.centroids[end_did]
        folium.PolyLine(
            locations=[start_point, end_point],
            color="#f06b6b",
            weight=2.5,
            opacity=0.75,
            dash_array="6, 8",
            tooltip=f"BLOCKED · {city.names[i]} – {city.names[j]}",
        ).add_to(fmap)

    if color_mode == "Risk":
        legend = _legend_html(
            "Flood risk",
            [("Safe", RISK_COLORS[SAFE]), ("Warning", RISK_COLORS[WARNING]), ("Critical", RISK_COLORS[CRITICAL])],
        )
    elif color_mode == "Water depth":
        legend = _legend_html(
            "Water depth",
            [("0.0 m", _depth_color(0.0)), ("0.4 m", _depth_color(0.4)), ("0.8 m", _depth_color(0.8)), ("1.4 m+", _depth_color(1.4))],
        )
    else:
        legend = _legend_html(
            "Elevation",
            [(f"{emin:.0f} m (low)", _elev_color(emin, emin, emax)), (f"{emax:.0f} m (high)", _elev_color(emax, emin, emax))],
        )
    fmap.get_root().html.add_child(folium.Element(legend))
    Fullscreen().add_to(fmap)

    if color_mode == "Elevation":
        colormap = cm.LinearColormap(["#285846", "#b4d25a"], vmin=emin, vmax=emax, caption="Elevation (m)")
        colormap.add_to(fmap)

    return fmap
