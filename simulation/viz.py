from __future__ import annotations

import folium
from branca.element import MacroElement, Template
from folium.features import DivIcon
from folium.plugins import Fullscreen

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
                    weight: 0.8,
                    opacity: 0.35,
                    dashArray: '4,6',
                    interactive: false
                };
                var labelStyle =
                    'color:#fff;font-size:10px;font-weight:600;' +
                    'text-shadow:0 0 3px #000;opacity:0.85;white-space:nowrap;';

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


def _pin_html(color: str, selected: bool = False) -> str:
    size = 18 if selected else 14
    ring = "3px solid #ffffff" if selected else "2px solid rgba(255,255,255,0.92)"
    glow = f"0 0 0 4px {color}55" if selected else f"0 0 8px {color}88"
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50% 50% 50% 0;'
        f'transform:rotate(-45deg);background:{color};border:{ring};'
        f'box-shadow:{glow};margin:0 auto;"></div>'
    )


def _add_grid(fmap: folium.Map, _city: City) -> None:
    """Draw lat/lon grid lines across the entire visible map (updates on pan/zoom)."""
    fmap.get_root().html.add_child(
        folium.Element(
            "<style>.fs-graticule-label,.fs-district-pin{background:transparent!important;border:0!important;}</style>"
        )
    )
    fmap.add_child(_ViewportGraticule())


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
    """District / city name pointers colour-coded by hazard (or elev / depth)."""
    emin = min(city.elevation)
    emax = max(city.elevation)
    water_row = result.water[t_idx] if result is not None else None
    status_row = result.status[t_idx] if result is not None else None

    pins = folium.FeatureGroup(name="District pointers", show=True)

    # City / state title
    folium.Marker(
        location=list(city.center),
        tooltip=f"{city.city_name}, {city.state_name}",
        popup=folium.Popup(
            f"<b>{city.city_name}</b><br>{city.state_name}<br>Districts: {city.n}",
            max_width=220,
        ),
        icon=DivIcon(
            icon_size=(220, 40),
            icon_anchor=(110, 48),
            class_name="fs-district-pin",
            html=(
                f'<div style="background:rgba(11,18,32,0.88);color:#1ee0ac;'
                f'border:1px solid rgba(30,224,172,0.5);border-radius:8px;'
                f'padding:5px 12px;font-size:12px;font-weight:700;text-align:center;'
                f'white-space:nowrap;box-shadow:0 2px 10px rgba(0,0,0,0.45);">'
                f'{city.city_name} · {city.state_name}</div>'
            ),
        ),
    ).add_to(pins)

    for did, (lat, lon) in city.centroids.items():
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

        pin_size = 36 if selected else 28
        folium.Marker(
            location=[lat, lon],
            tooltip=tip,
            popup=folium.Popup("<br>".join(lines), max_width=260),
            icon=DivIcon(
                icon_size=(pin_size, pin_size + 8),
                icon_anchor=(pin_size // 2, pin_size + 4),
                class_name="fs-district-pin",
                html=_pin_html(color, selected=selected),
            ),
        ).add_to(pins)

        if show_names:
            label_color = color if color_mode == "Risk" else "#ffffff"
            weight = 800 if selected else 700
            folium.Marker(
                location=[lat, lon],
                icon=DivIcon(
                    icon_size=(140, 20),
                    icon_anchor=(70, -6),
                    class_name="fs-district-pin",
                    html=(
                        f'<div style="color:{label_color};font-size:{"12px" if selected else "11px"};'
                        f'font-weight:{weight};text-align:center;white-space:nowrap;'
                        f'text-shadow:0 1px 3px #000,0 0 6px #000;pointer-events:none;">{name}</div>'
                    ),
                ),
            ).add_to(pins)

    pins.add_to(fmap)


def build_map(
    city: City,
    result: SimulationResult | None = None,
    t_idx: int = 0,
    color_mode: str = "Risk",
    blocked_edges: tuple[tuple[str, str], ...] | None = None,
    show_grid: bool = True,
    show_labels: bool = True,
    selected_id: str | None = None,  # highlighted district pin
) -> folium.Map:
    fmap = folium.Map(
        location=list(city.center),
        zoom_start=11,
        tiles=None,
        control_scale=True,
    )
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Earth Satellite",
        overlay=False,
        control=True,
        max_zoom=20,
    ).add_to(fmap)
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Earth Hybrid",
        overlay=False,
        control=True,
        max_zoom=20,
    ).add_to(fmap)
    fmap.fit_bounds(city.bounds)

    if show_grid:
        _add_grid(fmap, city)
    else:
        fmap.get_root().html.add_child(
            folium.Element(
                "<style>.fs-district-pin{background:transparent!important;border:0!important;}</style>"
            )
        )

    blocked_edges = blocked_edges or (result.blocked_edges if result else ())
    blocked = {(min(a, b), max(a, b)) for a, b in blocked_edges}
    failed = set(result.failed_districts if result else ())
    emin = min(city.elevation)
    emax = max(city.elevation)

    canals = folium.FeatureGroup(name="Drainage channels", show=True)
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
        ).add_to(canals)
    canals.add_to(fmap)

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
            "Pointer hazard",
            [("Safe", RISK_COLORS[SAFE]), ("Warning", RISK_COLORS[WARNING]), ("Critical", RISK_COLORS[CRITICAL])],
        )
    elif color_mode == "Water depth":
        legend = _legend_html(
            "Pointer depth",
            [("0.0 m", "#1b3a4a"), ("0.4 m", "#2a6a9a"), ("0.8 m", "#3a80b0"), ("1.4 m+", "#de4a4a")],
        )
    else:
        legend = _legend_html(
            "Pointer elevation",
            [(f"{emin:.0f} m (low)", _elev_color(emin, emin, emax)), (f"{emax:.0f} m (high)", _elev_color(emax, emin, emax))],
        )
    fmap.get_root().html.add_child(folium.Element(legend))
    Fullscreen().add_to(fmap)
    folium.LayerControl(position="topright", collapsed=True).add_to(fmap)

    return fmap
