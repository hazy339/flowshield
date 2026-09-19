from __future__ import annotations

import branca.colormap as cm
import folium
from folium.features import GeoJsonTooltip
from folium.plugins import Fullscreen

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
    r = int(12 + t * 210)
    g = int(70 + (1 - t) * 90)
    b = int(160 + (1 - t) * 70)
    if t < 0.08:
        return "#1b3a4a"
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
        f'border:1px solid rgba(30,224,172,0.25);min-width:150px;">'
        f'<div style="font-weight:700;margin-bottom:6px;letter-spacing:0.04em;">{title}</div>{rows}</div>'
    )


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
        tiles="OpenStreetMap",
        control_scale=True,
    )
    fmap.fit_bounds(city.bounds)

    blocked_edges = blocked_edges or (result.blocked_edges if result else ())
    blocked = {(min(a, b), max(a, b)) for a, b in blocked_edges}
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
        elif color_mode == "Water depth" and water_row is not None:
            color = _depth_color(float(water_row[idx]))
        elif status_row is not None:
            color = RISK_COLORS[int(status_row[idx])]
        else:
            color = "#1ee0ac"
        return {
            "fillColor": color,
            "color": "#0b1220",
            "weight": 1.4,
            "fillOpacity": 0.72,
        }

    def highlight_fn(_feature):
        return {"weight": 3, "color": "#ffffff", "fillOpacity": 0.85}

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

    for canal in city.canal_polylines():
        blocked_seg = False
        for a, b in canal["edges"]:
            if (min(a, b), max(a, b)) in blocked:
                blocked_seg = True
                break
        color = "#e74c3c" if blocked_seg else "#4cc3ff"
        weight = 6 if blocked_seg else 3.5
        dash = "8, 8" if blocked_seg else None
        folium.PolyLine(
            locations=canal["coords"],
            color=color,
            weight=weight,
            opacity=0.9,
            dash_array=dash,
            tooltip=("BLOCKED · " if blocked_seg else "") + canal["name"],
        ).add_to(fmap)

    if color_mode == "Risk":
        legend = _legend_html(
            "Flood risk",
            [("Safe", RISK_COLORS[SAFE]), ("Warning", RISK_COLORS[WARNING]), ("Critical", RISK_COLORS[CRITICAL])],
        )
    elif color_mode == "Water depth":
        legend = _legend_html(
            "Water depth",
            [("0.0 m", "#1b3a4a"), ("0.4 m", "#2a6a9a"), ("0.8 m", "#3a80b0"), ("1.4 m+", "#de4a4a")],
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
