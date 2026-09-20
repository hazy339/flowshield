"""FastAPI service exposing FLOWSHIELD NumPy simulations to the React UI."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from simulation.city import list_regions, load_city
from simulation.model import SimConfig, SimulationResult, run_simulation
from simulation.scenarios import PRESETS, apply_preset

app = FastAPI(
    title="FLOWSHIELD API",
    description="Python/NumPy flood simulation backend for the React dashboard.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCENARIO_UI = [
    ("Normal Rainfall", "Normal rainfall"),
    ("Heavy Rainfall", "Heavy rainfall"),
    ("Extreme Rainfall", "Extreme flood"),
    ("Drainage Failure", "Drainage failure"),
    ("Blocked Channel", "Blocked drainage channel"),
]


class SimulateRequest(BaseModel):
    region_id: str = "chennai"
    preset: str | None = "Extreme flood"
    rainfall_mm_h: float | None = None
    rain_duration_h: float | None = None
    duration_h: float | None = None
    drainage_scale: float | None = None
    initial_scale: float | None = None
    failed_districts: list[str] = Field(default_factory=list)
    blocked_edge: list[str] | None = None  # [id_a, id_b] or null


def _finite(x: float) -> float | None:
    if x != x or math.isinf(x):
        return None
    return float(x)


def _serialize_result(city, result: SimulationResult) -> dict[str, Any]:
    """Pack SimulationResult into JSON-friendly structures for React."""
    n = result.n_steps
    # Light downsample for faster browser transfer on long runs.
    step = 1 if n <= 120 else max(1, n // 96)
    indices = list(range(0, n, step))
    if indices[-1] != n - 1:
        indices.append(n - 1)

    water = result.water[indices]
    status = result.status[indices]
    flows = result.flow_m3s[indices]
    times = result.times_h[indices]

    districts = []
    for i, did in enumerate(result.district_ids):
        lat, lon = city.centroids[did]
        districts.append(
            {
                "id": did,
                "name": result.district_names[i],
                "lat": float(lat),
                "lon": float(lon),
                "elevation_m": float(result.elevation[i]),
                "drainage_mm_h": float(result.drainage_mm_h[i]),
                "population": int(result.population[i]),
                "coastal": bool(city.coastal[i]),
                "rainfall_factor": float(city.rainfall_factor[i]),
                "initial_water_m": float(city.initial_water[i]),
                "time_to_warning_h": _finite(float(result.time_to_warning_h[i])),
                "time_to_critical_h": _finite(float(result.time_to_critical_h[i])),
            }
        )

    canal_paths = []
    for canal in city.canals:
        districts_c = [d for d in canal.get("districts", []) if d in city.centroids]
        if len(districts_c) < 2:
            continue
        if canal.get("path"):
            coords = [[float(lat), float(lon)] for lat, lon in canal["path"]]
        else:
            coords = [[float(city.centroids[d][0]), float(city.centroids[d][1])] for d in districts_c]
        canal_paths.append(
            {
                "id": canal["id"],
                "name": canal["name"],
                "districts": districts_c,
                "coords": coords,
            }
        )

    counts = [result.counts_at(t) for t in indices]
    affected = [result.affected_population(t) for t in indices]

    return {
        "region_id": city.region_id,
        "city_name": city.city_name,
        "state_name": city.state_name,
        "label": city.label,
        "times_h": [float(t) for t in times],
        "warning_m": float(result.config.warning_m),
        "critical_m": float(result.config.critical_m),
        "rainfall_mm_h": float(result.config.rainfall_mm_h),
        "drainage_scale": float(result.config.drainage_scale),
        "districts": districts,
        "water": np.round(water, 4).tolist(),
        "status": status.astype(int).tolist(),
        "flow_edges": [list(e) for e in result.flow_edges],
        "flow_m3s": np.round(flows, 3).tolist(),
        "counts": counts,
        "affected_population": affected,
        "peak_hazard_index": int(
            min(range(len(indices)), key=lambda k: abs(indices[k] - result.peak_hazard_index()))
        ),
        "first_critical_hour": result.first_critical_hour(),
        "geojson": city.geojson,
        "canal_paths": canal_paths,
        "blockable_channels": [
            {"label": ch["label"], "edge": list(ch["edge"])} for ch in city.blockable_channels
        ],
        "failed_districts": list(result.failed_districts),
        "blocked_edges": [list(e) for e in result.blocked_edges],
        "config": {
            "rainfall_mm_h": float(result.config.rainfall_mm_h),
            "duration_h": float(result.config.duration_h),
            "rain_duration_h": float(result.config.rain_duration_h or result.config.duration_h),
            "drainage_scale": float(result.config.drainage_scale),
            "initial_scale": float(result.config.initial_scale),
            "runoff": float(result.config.runoff),
        },
    }


def _build_config(city, body: SimulateRequest) -> SimConfig:
    if body.preset and body.preset in PRESETS:
        cfg = apply_preset(body.preset, city)
    else:
        cfg = apply_preset("Custom", city)

    rainfall = body.rainfall_mm_h if body.rainfall_mm_h is not None else cfg.rainfall_mm_h
    rain_h = body.rain_duration_h if body.rain_duration_h is not None else cfg.rain_duration_h
    dur_h = body.duration_h if body.duration_h is not None else cfg.duration_h
    drain = body.drainage_scale if body.drainage_scale is not None else cfg.drainage_scale
    init = body.initial_scale if body.initial_scale is not None else cfg.initial_scale

    failed = tuple(body.failed_districts) if body.failed_districts else cfg.failed_districts
    blocked = cfg.blocked_edges
    if body.blocked_edge and len(body.blocked_edge) == 2:
        blocked = ((body.blocked_edge[0], body.blocked_edge[1]),)

    return SimConfig(
        rainfall_mm_h=float(rainfall),
        duration_h=float(dur_h),
        rain_duration_h=float(rain_h) if rain_h is not None else None,
        drainage_scale=float(drain),
        initial_scale=float(init),
        failed_districts=failed,
        blocked_edges=blocked,
        warning_m=cfg.warning_m,
        critical_m=cfg.critical_m,
        conductivity=cfg.conductivity,
        canal_conductivity=cfg.canal_conductivity,
        runoff=cfg.runoff,
        infiltration_mm_h=cfg.infiltration_mm_h,
        coastal_sink=cfg.coastal_sink,
        max_transfer_frac=cfg.max_transfer_frac,
        dt_h=cfg.dt_h,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "numpy"}


@app.get("/api/regions")
def regions() -> list[dict[str, str]]:
    return [
        {
            "id": r.id,
            "city": r.city,
            "state": r.state,
            "label": r.label,
            "description": r.description,
        }
        for r in list_regions()
    ]


@app.get("/api/scenarios")
def scenarios() -> list[dict[str, str]]:
    out = []
    for label, key in SCENARIO_UI:
        p = PRESETS[key]
        out.append({"label": label, "preset": key, "description": p.description})
    return out


@app.get("/api/regions/{region_id}")
def region_detail(region_id: str) -> dict[str, Any]:
    try:
        city = load_city(region_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "id": city.region_id,
        "label": city.label,
        "city_name": city.city_name,
        "state_name": city.state_name,
        "district_names": city.names,
        "district_ids": city.ids,
        "blockable_channels": [
            {"label": ch["label"], "edge": list(ch["edge"])} for ch in city.blockable_channels
        ],
        "geojson": city.geojson,
    }


@app.post("/api/simulate")
def simulate(body: SimulateRequest) -> dict[str, Any]:
    try:
        city = load_city(body.region_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    cfg = _build_config(city, body)
    result = run_simulation(city, cfg)
    return _serialize_result(city, result)
