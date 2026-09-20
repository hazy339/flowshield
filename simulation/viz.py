from __future__ import annotations

import hashlib
import math

import numpy as np
import folium
from branca.element import MacroElement, Template
from folium.features import DivIcon
from folium.plugins import AntPath, Fullscreen

from .city import City
from .model import CRITICAL, SAFE, WARNING, SimulationResult


class _ViewportGraticule(MacroElement):
    """Leaflet lat/lon grid covering the full current map viewport."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        (function() {
            var map = {{ this._parent.get_name() }};
            var gridLayer = L.layerGroup().addTo(map);
            var labelPane = map.createPane('graticuleLabels');
            labelPane.style.zIndex = 450;
            labelPane.style.pointerEvents = 'none';

            function niceStep(span, target) {
                var raw = Math.max(span / Math.max(target, 1), 1e-9);
                var exp = Math.floor(Math.log10(raw));
                var base = Math.pow(10, exp);
                var candidates = [1, 2, 5, 10];
                for (var i = 0; i < candidates.length; i++) {
                    var step = candidates[i] * base;
                    if (step >= raw) return step;
                }
                return 10 * base;
            }

            function formatDeg(v, step) {
                var digits = step >= 1 ? 0 : (step >= 0.1 ? 1 : 2);
                return v.toFixed(digits) + '°';
            }

            function drawGrid() {
                gridLayer.clearLayers();
                var b = map.getBounds().pad(0.05);
                var south = b.getSouth(), north = b.getNorth();
                var west = b.getWest(), east = b.getEast();
                var latStep = niceStep(north - south, 8);
                var lonStep = niceStep(east - west, 8);
                var style = {
                    color: '#ffffff',
                    weight: 0.6,
                    opacity: 0.18,
                    dashArray: '2,8',
                    interactive: false
                };
                var labelStyle =
                    'color:rgba(255,255,255,0.55);font-size:9px;font-weight:500;' +
                    'text-shadow:0 0 4px #000;white-space:nowrap;';

                var lat0 = Math.floor(south / latStep) * latStep;
                for (var lat = lat0; lat <= north + 1e-9; lat += latStep) {
                    L.polyline([[lat, west], [lat, east]], style).addTo(gridLayer);
                    L.marker([lat, west], {
                        interactive: false,
                        pane: 'graticuleLabels',
                        icon: L.divIcon({
                            className: 'fs-graticule-label',
                            html: '<div style=\"' + labelStyle + '\">' + formatDeg(lat, latStep) + '</div>',
                            iconSize: [70, 16],
                            iconAnchor: [0, 8]
                        })
                    }).addTo(gridLayer);
                }

                var lon0 = Math.floor(west / lonStep) * lonStep;
                for (var lon = lon0; lon <= east + 1e-9; lon += lonStep) {
                    L.polyline([[south, lon], [north, lon]], style).addTo(gridLayer);
                    L.marker([south, lon], {
                        interactive: false,
                        pane: 'graticuleLabels',
                        icon: L.divIcon({
                            className: 'fs-graticule-label',
                            html: '<div style=\"' + labelStyle + 'text-align:center;\">' +
                                  formatDeg(lon, lonStep) + '</div>',
                            iconSize: [70, 16],
                            iconAnchor: [35, 0]
                        })
                    }).addTo(gridLayer);
                }
            }

            map.on('moveend zoomend', drawGrid);
            drawGrid();
        })();
        {% endmacro %}
        """
    )


RISK_COLORS = {
    SAFE: "#1ee0ac",
    WARNING: "#f5a623",
    CRITICAL: "#e74c3c",
}
RISK_LABELS = {SAFE: "Safe", WARNING: "Warning", CRITICAL: "Critical"}


def _depth_color(depth: float, vmax: float = 0.9) -> str:
    t = max(0.0, min(1.0, depth / vmax))
    t = t**0.75
    r = int(20 + t * 220)
    g = int(90 + (1 - t) * 80)
    b = int(170 + (1 - t) * 50)
    if t < 0.05:
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
        f'<span style="width:10px;height:10px;background:{color};display:inline-block;'
        f'border-radius:50%;box-shadow:0 0 8px {color}88;"></span>'
        f'<span>{label}</span></div>'
        for label, color in items
    )
    return (
        f'<div style="position:fixed;bottom:20px;left:20px;z-index:9999;'
        f'background:rgba(8,14,24,0.78);backdrop-filter:blur(8px);'
        f'color:#e8eef7;padding:10px 12px;border-radius:12px;font-size:11px;'
        f'border:1px solid rgba(255,255,255,0.1);min-width:120px;'
        f'box-shadow:0 8px 24px rgba(0,0,0,0.35);">'
        f'<div style="font-weight:650;margin-bottom:6px;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:#8ea0b8;font-size:10px;">{title}</div>{rows}</div>'
    )


def _pointer_color(
    *,
    color_mode: str,
    elev: float,
    emin: float,
    emax: float,
    depth: float | None,
    status: int | None,
) -> str:
    if color_mode == "Elevation":
        return _elev_color(elev, emin, emax)
    if color_mode == "Water depth" and depth is not None:
        return _depth_color(depth)
    if status is not None:
        return RISK_COLORS[int(status)]
    return RISK_COLORS[SAFE]


def _map_chrome_css() -> str:
    return """
    <style>
      .fs-district-pin, .fs-graticule-label, .fs-map-label {
        background: transparent !important;
        border: 0 !important;
      }
      .fs-city-badge {
        position: fixed;
        top: 18px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9998;
        pointer-events: none;
        background: rgba(8,14,24,0.78);
        backdrop-filter: blur(10px);
        color: #e8eef7;
        border: 1px solid rgba(30,224,172,0.35);
        border-radius: 999px;
        padding: 7px 16px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.04em;
        box-shadow: 0 8px 28px rgba(0,0,0,0.4);
        white-space: nowrap;
      }
      .fs-city-badge span { color: #1ee0ac; }
      @keyframes fs-pulse {
        0% { box-shadow: 0 0 0 0 rgba(231,76,60,0.65); }
        70% { box-shadow: 0 0 0 18px rgba(231,76,60,0); }
        100% { box-shadow: 0 0 0 0 rgba(231,76,60,0); }
      }
      @keyframes fs-pulse-warn {
        0% { box-shadow: 0 0 0 0 rgba(245,166,35,0.55); }
        70% { box-shadow: 0 0 0 14px rgba(245,166,35,0); }
        100% { box-shadow: 0 0 0 0 rgba(245,166,35,0); }
      }
      .fs-pulse-dot {
        animation: fs-pulse 1.5s ease-out infinite;
      }
      .fs-pulse-warn {
        animation: fs-pulse-warn 2s ease-out infinite;
      }
    </style>
    """


def _stable_signed(seed: str) -> float:
    """Deterministic value in [-1, 1] from an edge id (stable across frames)."""
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0


def _cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    n: int = 16,
) -> list[list[float]]:
    pts: list[list[float]] = []
    for i in range(n + 1):
        t = i / n
        u = 1.0 - t
        lat = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        lon = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append([lat, lon])
    return pts


def _curved_flow_coords(
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
    edge_key: str,
) -> list[list[float]]:
    """
    Smooth Bezier visual path between existing edge endpoints.
    Curvature is deterministic per edge — not a new network connection.
    """
    dlat = lat_b - lat_a
    dlon = lon_b - lon_a
    length = math.hypot(dlat, dlon) or 1e-9
    plat, plon = -dlon / length, dlat / length
    s1 = _stable_signed(edge_key + "|bend")
    s2 = _stable_signed(edge_key + "|twist")
    amp1 = (0.14 + 0.12 * abs(s1)) * length
    amp2 = (0.10 + 0.10 * abs(s2)) * length
    sign = 1.0 if s1 >= 0 else -1.0
    c1 = (
        lat_a + dlat * 0.32 + plat * amp1 * sign,
        lon_a + dlon * 0.32 + plon * amp1 * sign,
    )
    c2 = (
        lat_a + dlat * 0.68 - plat * amp2 * sign * 0.85,
        lon_a + dlon * 0.68 - plon * amp2 * sign * 0.85,
    )
    return _cubic_bezier((lat_a, lon_a), c1, c2, (lat_b, lon_b), n=18)


def _flow_style(magnitude: float, f_ref: float) -> dict:
    """Thin organic channel styling: most flows 2-4 px, strongest ~5-7 px."""
    if f_ref <= 0:
        intensity = 0.35
    else:
        intensity = max(0.0, min(1.0, (magnitude / f_ref) ** 0.75))
    weight = 1.8 + 4.6 * intensity
    opacity = 0.28 + 0.42 * intensity
    delay = int(1100 - 700 * intensity)
    return {
        "weight": min(6.8, weight),
        "opacity": min(0.72, opacity),
        "delay": max(320, delay),
        "intensity": intensity,
        "glow_weight": min(10.0, weight + 2.8),
        "glow_opacity": 0.08 + 0.12 * intensity,
    }


def _add_flood_surface(
    fmap: folium.Map,
    city: City,
    result: SimulationResult | None,
    t_idx: int,
) -> None:
    """Soft circular inundation blobs — not rectangular blue tiles."""
    outlines = folium.FeatureGroup(name="District outlines", show=True)
    flood = folium.FeatureGroup(name="Flood surface", show=True)

    for feat in city.geojson["features"]:
        folium.GeoJson(
            feat,
            style_function=lambda _f: {
                "fillColor": "#ffffff",
                "color": "#ffffff",
                "weight": 0.8,
                "fillOpacity": 0.02,
                "opacity": 0.16,
                "dashArray": "2, 7",
            },
            interactive=False,
        ).add_to(outlines)
    outlines.add_to(fmap)

    if result is None:
        flood.add_to(fmap)
        return

    t = min(max(0, t_idx), result.n_steps - 1)
    warning_m = float(result.config.warning_m)
    critical_m = float(result.config.critical_m)

    for did, (lat, lon) in city.centroids.items():
        idx = city.index_of[did]
        depth = float(result.water[t, idx])
        status = int(result.status[t, idx])
        if depth < 0.05 and status < WARNING:
            continue
        t_depth = max(0.0, min(1.0, depth / max(critical_m * 1.4, 0.4))) ** 0.7
        if status >= CRITICAL or depth >= critical_m:
            base_r = 520 + 2100 * t_depth
            color = "#4db8ff"
            fill = "#1a8cff"
            op = 0.16 + 0.18 * t_depth
        elif status >= WARNING or depth >= warning_m:
            base_r = 420 + 1600 * t_depth
            color = "#6ecfff"
            fill = "#2aa9ff"
            op = 0.12 + 0.14 * t_depth
        else:
            base_r = 320 + 900 * t_depth
            color = "#8ad9ff"
            fill = "#3ec7ff"
            op = 0.07 + 0.10 * t_depth

        name = city.names[idx]
        for scale, op_mul in ((1.35, 0.35), (1.0, 0.7), (0.55, 1.0)):
            folium.Circle(
                location=[lat, lon],
                radius=base_r * scale,
                color=color,
                weight=0,
                fill=True,
                fill_color=fill,
                fill_opacity=op * op_mul,
                opacity=0,
                tooltip=f"{name} · {depth:.2f} m water" if scale == 1.0 else None,
            ).add_to(flood)

    flood.add_to(fmap)


def _add_simulated_flows(
    fmap: folium.Map,
    city: City,
    result: SimulationResult | None,
    t_idx: int,
    blocked: set[tuple[str, str]],
    selected_id: str | None,
) -> None:
    """Curved visual interpolation of existing F_ij edges — not new/fake paths."""
    glow_group = folium.FeatureGroup(name="Flow glow", show=True)
    flow_group = folium.FeatureGroup(name="Flood flow", show=True)
    blocked_group = folium.FeatureGroup(name="Blocked channels", show=True)

    drawn_blocked: set[tuple[str, str]] = set()
    for a, b in blocked:
        key = (a, b) if a <= b else (b, a)
        if key in drawn_blocked or a not in city.centroids or b not in city.centroids:
            continue
        drawn_blocked.add(key)
        lat_a, lon_a = city.centroids[a]
        lat_b, lon_b = city.centroids[b]
        curve = _curved_flow_coords(lat_a, lon_a, lat_b, lon_b, f"blocked|{key[0]}|{key[1]}")
        folium.PolyLine(
            locations=curve,
            color="#ff6b5a",
            weight=2.6,
            opacity=0.7,
            dash_array="5, 9",
            tooltip=f"BLOCKED · {city.name_of(a)} – {city.name_of(b)}",
        ).add_to(blocked_group)

    if result is None or result.n_edges == 0:
        glow_group.add_to(fmap)
        flow_group.add_to(fmap)
        blocked_group.add_to(fmap)
        return

    t = min(max(0, t_idx), result.n_steps - 1)
    flows = result.flow_m3s[t]
    abs_flows = np.abs(flows)
    positive = abs_flows[abs_flows > 1e-6]
    f_ref = float(np.percentile(positive, 88)) if positive.size else 0.0
    if f_ref <= 0 and positive.size:
        f_ref = float(np.max(positive))
    f_min = 0.012 * f_ref if f_ref > 0 else 1e-3

    sel_idx = city.index_of.get(selected_id) if selected_id else None
    order = sorted(range(len(flows)), key=lambda ei: abs(float(flows[ei])))

    for e in order:
        (i, j) = result.flow_edge_indices[e]
        id_i, id_j = result.flow_edges[e]
        key = (id_i, id_j) if id_i <= id_j else (id_j, id_i)
        if key in drawn_blocked or (id_i, id_j) in blocked or (id_j, id_i) in blocked:
            continue
        f = float(flows[e])
        mag = abs(f)
        if mag < f_min:
            continue

        lat_i, lon_i = city.centroids[id_i]
        lat_j, lon_j = city.centroids[id_j]
        edge_seed = f"{id_i}|{id_j}"
        if f >= 0:
            curve = _curved_flow_coords(lat_i, lon_i, lat_j, lon_j, edge_seed)
            src_name, dst_name = result.district_names[i], result.district_names[j]
        else:
            curve = _curved_flow_coords(lat_j, lon_j, lat_i, lon_i, edge_seed)
            src_name, dst_name = result.district_names[j], result.district_names[i]

        style = _flow_style(mag, f_ref)
        touches_sel = sel_idx is not None and sel_idx in (i, j)
        color = "#6ecfff" if not touches_sel else "#a8eaff"
        pulse = "#d7f6ff"
        weight = style["weight"] + (0.6 if touches_sel else 0.0)
        opacity = min(0.78, style["opacity"] + (0.08 if touches_sel else 0.0))

        folium.PolyLine(
            locations=curve,
            color="#3dbfff",
            weight=style["glow_weight"],
            opacity=style["glow_opacity"],
            line_cap="round",
            line_join="round",
            interactive=False,
        ).add_to(glow_group)

        tip = f"{src_name} -> {dst_name} · {mag:.1f} m3/s"
        AntPath(
            locations=curve,
            color=color,
            weight=weight,
            opacity=opacity,
            delay=style["delay"],
            dash_array=[7, 18],
            pulse_color=pulse,
            hardwareAcceleration=True,
            tooltip=tip,
        ).add_to(flow_group)

    glow_group.add_to(fmap)
    flow_group.add_to(fmap)
    blocked_group.add_to(fmap)


def _label_anchor(i: int, selected: bool) -> tuple[int, int]:
    if selected:
        return (70, 28)
    pattern = (
        (70, 22),
        (8, 10),
        (132, 10),
        (70, -4),
        (0, 18),
        (140, 18),
        (20, -2),
        (120, -2),
    )
    return pattern[i % len(pattern)]


def _add_grid(fmap: folium.Map, _city: City) -> None:
    fmap.add_child(_ViewportGraticule())


def _add_basin_outlines(fmap: folium.Map, city: City) -> None:
    """Faint district footprints when no simulation result is available."""
    _add_flood_surface(fmap, city, None, 0)


def _marker_html(
    *,
    color: str,
    status: int | None,
    selected: bool,
    name: str | None,
    depth: float | None,
) -> str:
    core = 13 if selected else (12 if status == CRITICAL else 10 if status == WARNING else 7)
    halo = 0
    if status == CRITICAL:
        halo = 38 if selected else 32
    elif status == WARNING:
        halo = 30 if selected else 24
    elif selected:
        halo = 22

    if status == CRITICAL:
        pulse_cls = "fs-pulse-dot"
    elif status == WARNING:
        pulse_cls = "fs-pulse-warn"
    else:
        pulse_cls = ""

    halo_html = ""
    if halo:
        halo_html = (
            f'<div style="position:absolute;left:50%;top:50%;width:{halo}px;height:{halo}px;'
            f'margin:{-halo / 2}px 0 0 {-halo / 2}px;border-radius:50%;'
            f'background:{color}44;border:1px solid {color}88;'
            f'box-shadow:0 0 18px {color}66;"></div>'
        )

    label_html = ""
    if name:
        depth_bit = (
            f'<div style="opacity:0.9;font-size:9px;font-weight:700;color:#9ad9ff;">{depth:.2f} m</div>'
            if depth is not None
            else ""
        )
        label_html = (
            f'<div style="position:absolute;left:50%;top:100%;transform:translate(-50%,6px);'
            f'min-width:72px;text-align:center;pointer-events:none;">'
            f'<div style="display:inline-block;background:rgba(8,14,24,0.88);'
            f'border:1px solid {color}99;border-radius:8px;padding:3px 8px;'
            f'color:#f2f6fb;font-size:10px;font-weight:700;letter-spacing:0.02em;'
            f'box-shadow:0 4px 16px rgba(0,0,0,0.45), 0 0 12px {color}44;white-space:nowrap;">'
            f'{name}{depth_bit}</div></div>'
        )

    return (
        f'<div style="position:relative;width:44px;height:44px;">'
        f"{halo_html}"
        f'<div class="{pulse_cls}" style="position:absolute;left:50%;top:50%;'
        f"width:{core}px;height:{core}px;margin:{-core / 2}px 0 0 {-core / 2}px;"
        f"border-radius:50%;background:{color};border:2px solid rgba(255,255,255,0.95);"
        f'box-shadow:0 0 16px {color}dd, 0 0 28px {color}66;"></div>'
        f"{label_html}</div>"
    )


def _add_hazard_pointers(
    fmap: folium.Map,
    city: City,
    *,
    result: SimulationResult | None,
    t_idx: int,
    color_mode: str,
    selected_id: str | None,
    failed: set[str],
    show_names: bool,
) -> None:
    """Sparse hazard markers: soft halos + labels only where they matter."""
    emin = min(city.elevation)
    emax = max(city.elevation)
    water_row = result.water[t_idx] if result is not None else None
    status_row = result.status[t_idx] if result is not None else None

    fmap.get_root().html.add_child(
        folium.Element(f'<div class="fs-city-badge">{city.city_name} <span>·</span> {city.state_name}</div>')
    )

    pins = folium.FeatureGroup(name="Hazard markers", show=True)
    ordered = sorted(
        city.centroids.items(),
        key=lambda item: int(status_row[city.index_of[item[0]]]) if status_row is not None else 0,
    )

    for draw_i, (did, (lat, lon)) in enumerate(ordered):
        idx = city.index_of[did]
        name = city.names[idx]
        depth = float(water_row[idx]) if water_row is not None else None
        status = int(status_row[idx]) if status_row is not None else None
        color = _pointer_color(
            color_mode=color_mode,
            elev=city.elevation[idx],
            emin=emin,
            emax=emax,
            depth=depth,
            status=status,
        )
        selected = did == selected_id
        risk_label = RISK_LABELS.get(status, "—") if status is not None else "—"

        show_label = selected or (show_names and status is not None and status >= WARNING)
        label_name = name if show_label else None
        label_depth = depth if show_label and depth is not None and status and status >= WARNING else None

        lines = [
            f"<b>{name}</b>",
            f"{city.city_name}, {city.state_name}",
            f"Elevation: {city.elevation[idx]:.0f} m",
            f"Drainage: {city.drainage_mm_h[idx]:.0f} mm/h",
            f"Population: {city.population[idx]:,}",
        ]
        if did in failed:
            lines.append("<span style='color:#e74c3c'>Drainage FAILED</span>")
        if depth is not None and status is not None:
            lines.append(f"Water depth: {depth:.2f} m")
            lines.append(f"Status: <b style='color:{color}'>{risk_label}</b>")
            if result is not None:
                ttc = result.time_to_critical_h[idx]
                if ttc == ttc:
                    lines.append(f"Time to critical: {ttc:.1f} h")
                else:
                    lines.append("Time to critical: not reached")

        tip = f"{name} · {risk_label}"
        if depth is not None:
            tip += f" · {depth:.2f} m"

        ax, ay = _label_anchor(draw_i, selected)
        folium.Marker(
            location=[lat, lon],
            tooltip=folium.Tooltip(tip, sticky=True),
            popup=folium.Popup("<br>".join(lines), max_width=260),
            icon=DivIcon(
                icon_size=(140, 70),
                icon_anchor=(ax, ay),
                class_name="fs-map-label",
                html=_marker_html(
                    color=color,
                    status=status,
                    selected=selected,
                    name=label_name,
                    depth=label_depth,
                ),
            ),
            z_index_offset=1000 if selected else (400 if status == CRITICAL else 200 if status == WARNING else 0),
        ).add_to(pins)

    pins.add_to(fmap)


def build_map(
    city: City,
    result: SimulationResult | None = None,
    t_idx: int = 0,
    color_mode: str = "Risk",
    blocked_edges: tuple[tuple[str, str], ...] | None = None,
    show_grid: bool = False,
    show_labels: bool = True,
    selected_id: str | None = None,
) -> folium.Map:
    fmap = folium.Map(
        location=list(city.center),
        zoom_start=11,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Earth Hybrid",
        overlay=False,
        control=True,
        max_zoom=20,
    ).add_to(fmap)
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Earth Satellite",
        overlay=False,
        control=True,
        max_zoom=20,
    ).add_to(fmap)

    south, west = city.bounds[0]
    north, east = city.bounds[1]
    pad_lat = (north - south) * 0.18
    pad_lon = (east - west) * 0.18
    fmap.fit_bounds([[south - pad_lat, west - pad_lon], [north + pad_lat, east + pad_lon]])

    fmap.get_root().html.add_child(folium.Element(_map_chrome_css()))

    if show_grid:
        _add_grid(fmap, city)

    _add_flood_surface(fmap, city, result, t_idx)

    blocked_edges = blocked_edges or (result.blocked_edges if result else ())
    blocked = {(min(a, b), max(a, b)) for a, b in blocked_edges}
    failed = set(result.failed_districts if result else ())
    emin = min(city.elevation)
    emax = max(city.elevation)

    _add_simulated_flows(
        fmap,
        city,
        result,
        t_idx,
        blocked=blocked,
        selected_id=selected_id,
    )

    _add_hazard_pointers(
        fmap,
        city,
        result=result,
        t_idx=t_idx,
        color_mode=color_mode,
        selected_id=selected_id,
        failed=failed,
        show_names=show_labels,
    )

    if color_mode == "Risk":
        legend = _legend_html(
            "Hazard & flood",
            [
                ("Safe", RISK_COLORS[SAFE]),
                ("Warning", RISK_COLORS[WARNING]),
                ("Critical", RISK_COLORS[CRITICAL]),
                ("Flood water", "#2aa9ff"),
                ("Active flow", "#5ad2ff"),
            ],
        )
    elif color_mode == "Water depth":
        legend = _legend_html(
            "Depth",
            [("Low", "#1b3a4a"), ("Rising", "#2a6a9a"), ("High", "#de4a4a"), ("Active flow", "#5ad2ff")],
        )
    else:
        legend = _legend_html(
            "Elevation",
            [(f"{emin:.0f} m", _elev_color(emin, emin, emax)), (f"{emax:.0f} m", _elev_color(emax, emin, emax))],
        )
    fmap.get_root().html.add_child(folium.Element(legend))
    Fullscreen().add_to(fmap)
    folium.LayerControl(position="topright", collapsed=True).add_to(fmap)

    return fmap
