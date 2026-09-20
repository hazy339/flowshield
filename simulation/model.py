from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .city import City

SAFE, WARNING, CRITICAL = 0, 1, 2
STATUS_LABELS = {SAFE: "Safe", WARNING: "Warning", CRITICAL: "Critical"}


def classify_depth(depth_m: float, warning_m: float, critical_m: float) -> int:
    if depth_m >= critical_m:
        return CRITICAL
    if depth_m >= warning_m:
        return WARNING
    return SAFE


@dataclass
class SimConfig:
    rainfall_mm_h: float
    duration_h: float
    dt_h: float = 0.25
    rain_duration_h: float | None = None
    drainage_scale: float = 1.0
    initial_scale: float = 1.0
    failed_districts: tuple[str, ...] = ()
    blocked_edges: tuple[tuple[str, str], ...] = ()
    conductivity: float = 0.16
    canal_conductivity: float = 0.48
    warning_m: float = 0.22
    critical_m: float = 0.60
    runoff: float = 0.92
    infiltration_mm_h: float = 0.6
    coastal_sink: float = 0.035
    max_transfer_frac: float = 0.38


@dataclass
class SimulationResult:
    times_h: np.ndarray
    water: np.ndarray
    status: np.ndarray
    time_to_warning_h: np.ndarray
    time_to_critical_h: np.ndarray
    peak_water: np.ndarray
    peak_status: np.ndarray
    config: SimConfig
    district_ids: list[str]
    district_names: list[str]
    population: np.ndarray
    elevation: np.ndarray
    drainage_mm_h: np.ndarray
    failed_districts: tuple[str, ...] = ()
    blocked_edges: tuple[tuple[str, str], ...] = ()
    labels: dict[int, str] = field(default_factory=lambda: dict(STATUS_LABELS))

    @property
    def n_steps(self) -> int:
        return int(self.water.shape[0])

    def status_label(self, t_idx: int, district_idx: int) -> str:
        return STATUS_LABELS[int(self.status[t_idx, district_idx])]

    def counts_at(self, t_idx: int) -> dict[str, int]:
        row = self.status[t_idx]
        return {
            "Safe": int(np.sum(row == SAFE)),
            "Warning": int(np.sum(row == WARNING)),
            "Critical": int(np.sum(row == CRITICAL)),
        }

    def affected_population(self, t_idx: int, min_status: int = WARNING) -> int:
        mask = self.status[t_idx] >= min_status
        return int(np.sum(self.population[mask]))

    def critical_population(self, t_idx: int) -> int:
        return self.affected_population(t_idx, CRITICAL)

    def peak_affected_population(self, min_status: int = WARNING) -> int:
        worst = int(np.argmax([self.affected_population(t, min_status) for t in range(self.n_steps)]))
        return self.affected_population(worst, min_status)

    def first_critical_hour(self) -> float | None:
        finite = self.time_to_critical_h[np.isfinite(self.time_to_critical_h)]
        if finite.size == 0:
            return None
        return float(np.min(finite))

    def peak_hazard_index(self) -> int:
        """Timeline index with the most severe map-wide flooding."""
        best_t = 0
        best_score = (-1.0, -1.0, -1.0)
        for t in range(self.n_steps):
            row = self.status[t]
            score = (
                float(np.sum(row == CRITICAL)),
                float(np.sum(row == WARNING)),
                float(np.mean(self.water[t])),
            )
            if score > best_score:
                best_score = score
                best_t = t
        return best_t


def _blocked_set(city: City, blocked_edges: tuple[tuple[str, str], ...]) -> set[tuple[int, int]]:
    blocked: set[tuple[int, int]] = set()
    for a, b in blocked_edges:
        if a not in city.index_of or b not in city.index_of:
            continue
        i, j = city.index_of[a], city.index_of[b]
        blocked.add((min(i, j), max(i, j)))
    return blocked


def _edge_list(city: City, blocked: set[tuple[int, int]], cfg: SimConfig) -> list[tuple[int, int, float]]:
    canal = { (min(i, j), max(i, j)) for i, j in city.canal_edges }
    edges: dict[tuple[int, int], float] = {}
    for i, neigh in enumerate(city.neighbors):
        for j in neigh:
            key = (min(i, j), max(i, j))
            edges[key] = cfg.conductivity
    for key in canal:
        edges[key] = cfg.canal_conductivity
    return [(i, j, k) for (i, j), k in edges.items() if (i, j) not in blocked]


def run_simulation(city: City, cfg: SimConfig) -> SimulationResult:
    n = city.n
    steps = max(2, int(round(cfg.duration_h / cfg.dt_h)) + 1)
    times = np.linspace(0.0, cfg.duration_h, steps)
    dt = cfg.dt_h

    elev = np.asarray(city.elevation, dtype=float)
    drain_cap = np.asarray(city.drainage_mm_h, dtype=float) / 1000.0 * max(0.0, cfg.drainage_scale)
    rain_factor = np.asarray(city.rainfall_factor, dtype=float)
    coastal = np.asarray(city.coastal, dtype=float)
    failed = np.zeros(n, dtype=float)
    for did in cfg.failed_districts:
        if did in city.index_of:
            failed[city.index_of[did]] = 1.0

    blocked = _blocked_set(city, cfg.blocked_edges)
    edges = _edge_list(city, blocked, cfg)

    water = np.zeros((steps, n), dtype=float)
    water[0] = np.asarray(city.initial_water, dtype=float) * max(0.0, cfg.initial_scale)

    rain_m_h = (cfg.rainfall_mm_h / 1000.0) * cfg.runoff * rain_factor
    infil_m_h = cfg.infiltration_mm_h / 1000.0
    rain_until = cfg.duration_h if cfg.rain_duration_h is None else min(cfg.duration_h, max(0.0, cfg.rain_duration_h))

    w = water[0].copy()
    for t in range(1, steps):
        if times[t] <= rain_until + 1e-9:
            w = w + rain_m_h * dt
        drain = drain_cap * (1.0 - failed) * dt
        w = np.maximum(0.0, w - drain - infil_m_h * dt)

        surface = elev + w
        transfer = np.zeros(n, dtype=float)
        for i, j, k in edges:
            H = surface[i] - surface[j]
            if H > 0:
                flux = k * np.sqrt(H) * dt
                flux = min(flux, w[i] * cfg.max_transfer_frac)
            elif H < 0:
                flux = -k * np.sqrt(-H) * dt
                flux = max(flux, -w[j] * cfg.max_transfer_frac)
            else:
                flux = 0.0
            transfer[i] -= flux
            transfer[j] += flux
        w = np.maximum(0.0, w + transfer)

        sea_out = cfg.coastal_sink * np.maximum(w, 0.0) * coastal * dt
        w = np.maximum(0.0, w - sea_out)
        water[t] = w

    status = np.zeros_like(water, dtype=int)
    status[water >= cfg.warning_m] = WARNING
    status[water >= cfg.critical_m] = CRITICAL

    ttw = np.full(n, np.nan)
    ttc = np.full(n, np.nan)
    for i in range(n):
        warn_hits = np.where(status[:, i] >= WARNING)[0]
        crit_hits = np.where(status[:, i] >= CRITICAL)[0]
        if warn_hits.size:
            ttw[i] = times[warn_hits[0]]
        if crit_hits.size:
            ttc[i] = times[crit_hits[0]]

    peak_water = np.max(water, axis=0)
    peak_status = np.max(status, axis=0)

    return SimulationResult(
        times_h=times,
        water=water,
        status=status,
        time_to_warning_h=ttw,
        time_to_critical_h=ttc,
        peak_water=peak_water,
        peak_status=peak_status,
        config=cfg,
        district_ids=list(city.ids),
        district_names=list(city.names),
        population=np.asarray(city.population, dtype=int),
        elevation=elev,
        drainage_mm_h=np.asarray(city.drainage_mm_h, dtype=float),
        failed_districts=cfg.failed_districts,
        blocked_edges=cfg.blocked_edges,
    )
