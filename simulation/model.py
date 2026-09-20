from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .city import City

SAFE, WARNING, CRITICAL = 0, 1, 2
STATUS_LABELS = {SAFE: "Safe", WARNING: "Warning", CRITICAL: "Critical"}

# Head difference [m] below this is treated as hydraulically flat (negligible flow).
HEAD_EPS_M = 1e-9


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
    # Effective conductance k_ij for F = k * sqrt(|H|)  [m^{5/2}/s]
    conductivity: float = 450.0
    canal_conductivity: float = 1400.0
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
    area_m2: np.ndarray
    # Undirected edges as (id_i, id_j) with index_i < index_j; F>0 means i→j.
    flow_edges: list[tuple[str, str]]
    flow_edge_indices: list[tuple[int, int]]
    # Signed volumetric flow [m³/s], shape (n_steps, n_edges). flow[0]=0.
    flow_m3s: np.ndarray
    failed_districts: tuple[str, ...] = ()
    blocked_edges: tuple[tuple[str, str], ...] = ()
    labels: dict[int, str] = field(default_factory=lambda: dict(STATUS_LABELS))

    @property
    def n_steps(self) -> int:
        return int(self.water.shape[0])

    @property
    def n_edges(self) -> int:
        return len(self.flow_edges)

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

    def total_volume_m3(self, t_idx: int) -> float:
        return float(np.sum(self.area_m2 * self.water[t_idx]))

    def district_edge_flows(self, t_idx: int, district_idx: int) -> list[dict]:
        """Signed flows touching a district at t_idx (positive = outgoing)."""
        rows: list[dict] = []
        flows = self.flow_m3s[t_idx]
        for e, ((i, j), (id_i, id_j)) in enumerate(zip(self.flow_edge_indices, self.flow_edges)):
            f = float(flows[e])
            if i == district_idx:
                rows.append(
                    {
                        "edge": (id_i, id_j),
                        "neighbor_idx": j,
                        "neighbor_id": id_j,
                        "neighbor_name": self.district_names[j],
                        "signed_m3s": f,
                        "direction": "outgoing" if f > 0 else ("incoming" if f < 0 else "none"),
                        "magnitude_m3s": abs(f),
                    }
                )
            elif j == district_idx:
                # Stored F>0 is i→j; from j's view outgoing is -F.
                signed = -f
                rows.append(
                    {
                        "edge": (id_i, id_j),
                        "neighbor_idx": i,
                        "neighbor_id": id_i,
                        "neighbor_name": self.district_names[i],
                        "signed_m3s": signed,
                        "direction": "outgoing" if signed > 0 else ("incoming" if signed < 0 else "none"),
                        "magnitude_m3s": abs(signed),
                    }
                )
        return rows


def nonlinear_flow_m3s(head_m: float, k: float) -> float:
    """
    Signed volumetric flow F [m³/s] for head H = η_i − η_j.

    F = k * sqrt(max(H, 0)) with sign(H): positive ⇒ i→j.
    """
    if head_m > HEAD_EPS_M:
        return float(k * np.sqrt(head_m))
    if head_m < -HEAD_EPS_M:
        return float(-k * np.sqrt(-head_m))
    return 0.0


def _blocked_set(city: City, blocked_edges: tuple[tuple[str, str], ...]) -> set[tuple[int, int]]:
    blocked: set[tuple[int, int]] = set()
    for a, b in blocked_edges:
        if a not in city.index_of or b not in city.index_of:
            continue
        i, j = city.index_of[a], city.index_of[b]
        blocked.add((min(i, j), max(i, j)))
    return blocked


def _undirected_edge_list(city: City, cfg: SimConfig) -> list[tuple[int, int, float]]:
    """One undirected edge per neighbour pair; canal edges get higher conductance."""
    canal = {(min(i, j), max(i, j)) for i, j in city.canal_edges}
    edges: dict[tuple[int, int], float] = {}
    for i, neigh in enumerate(city.neighbors):
        for j in neigh:
            if i >= j:
                continue
            edges[(i, j)] = cfg.conductivity
    # Neighbour lists are not always symmetric — also ingest reverse mentions.
    for i, neigh in enumerate(city.neighbors):
        for j in neigh:
            key = (min(i, j), max(i, j))
            edges.setdefault(key, cfg.conductivity)
    for key in canal:
        edges[key] = cfg.canal_conductivity
    return [(i, j, k) for (i, j), k in sorted(edges.items())]


def _apply_limited_transfers(
    *,
    water: np.ndarray,
    area: np.ndarray,
    elev: np.ndarray,
    edges: list[tuple[int, int, float]],
    blocked: set[tuple[int, int]],
    dt_s: float,
    max_transfer_frac: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Simultaneous nonlinear volume transfer for one timestep.

    Returns (new_water_depth, signed_flow_m3s per edge).
    """
    n = water.shape[0]
    n_edges = len(edges)
    eta = elev + water
    F = np.zeros(n_edges, dtype=float)
    phi = np.zeros(n_edges, dtype=float)

    for e, (i, j, k) in enumerate(edges):
        if (i, j) in blocked:
            continue
        F[e] = nonlinear_flow_m3s(float(eta[i] - eta[j]), k)
        phi[e] = F[e] * dt_s

    # Per-source remaining transferable volume this step (simultaneous).
    avail = np.maximum(0.0, water) * area * max(0.0, max_transfer_frac)
    out_demand = np.zeros(n, dtype=float)
    for e, (i, j, _) in enumerate(edges):
        if phi[e] > 0.0:
            out_demand[i] += phi[e]
        elif phi[e] < 0.0:
            out_demand[j] += -phi[e]

    scale = np.ones(n, dtype=float)
    for i in range(n):
        if out_demand[i] > avail[i] > 0.0:
            scale[i] = avail[i] / out_demand[i]
        elif out_demand[i] > 0.0 and avail[i] <= 0.0:
            scale[i] = 0.0

    for e, (i, j, _) in enumerate(edges):
        if phi[e] > 0.0:
            phi[e] *= scale[i]
        elif phi[e] < 0.0:
            phi[e] *= scale[j]
        F[e] = phi[e] / dt_s if dt_s > 0.0 else 0.0

    dV = np.zeros(n, dtype=float)
    for e, (i, j, _) in enumerate(edges):
        dV[i] -= phi[e]
        dV[j] += phi[e]

    new_w = np.maximum(0.0, water + dV / area)
    return new_w, F


def run_simulation(city: City, cfg: SimConfig) -> SimulationResult:
    n = city.n
    steps = max(2, int(round(cfg.duration_h / cfg.dt_h)) + 1)
    times = np.linspace(0.0, cfg.duration_h, steps)
    dt_h = float(cfg.dt_h)
    dt_s = dt_h * 3600.0

    elev = np.asarray(city.elevation, dtype=float)
    area = np.asarray(city.area_m2, dtype=float)
    if area.shape[0] != n:
        raise ValueError("city.area_m2 length must match number of districts")
    area = np.maximum(area, 1.0)

    # Depth rates [m/s] so ΔW = R·Δt_s / D·Δt_s with SI seconds.
    rain_factor = np.asarray(city.rainfall_factor, dtype=float)
    rain_m_s = (cfg.rainfall_mm_h / 1000.0) * cfg.runoff * rain_factor / 3600.0
    drain_m_s = np.asarray(city.drainage_mm_h, dtype=float) / 1000.0 * max(0.0, cfg.drainage_scale) / 3600.0
    infil_m_s = (cfg.infiltration_mm_h / 1000.0) / 3600.0
    coastal = np.asarray(city.coastal, dtype=float)
    # coastal_sink is fractional depth removal per hour → per second
    coastal_s = max(0.0, cfg.coastal_sink) / 3600.0

    failed = np.zeros(n, dtype=float)
    for did in cfg.failed_districts:
        if did in city.index_of:
            failed[city.index_of[did]] = 1.0

    blocked = _blocked_set(city, cfg.blocked_edges)
    edges = _undirected_edge_list(city, cfg)
    n_edges = len(edges)
    flow_edge_indices = [(i, j) for i, j, _ in edges]
    flow_edges = [(city.ids[i], city.ids[j]) for i, j, _ in edges]

    water = np.zeros((steps, n), dtype=float)
    flow_m3s = np.zeros((steps, n_edges), dtype=float)
    water[0] = np.asarray(city.initial_water, dtype=float) * max(0.0, cfg.initial_scale)

    rain_until = cfg.duration_h if cfg.rain_duration_h is None else min(cfg.duration_h, max(0.0, cfg.rain_duration_h))

    w = water[0].copy()
    for t in range(1, steps):
        # Rainfall / drainage / infiltration on depth (seconds-consistent).
        if times[t] <= rain_until + 1e-9:
            w = w + rain_m_s * dt_s
        drain = drain_m_s * (1.0 - failed) * dt_s
        w = np.maximum(0.0, w - drain - infil_m_s * dt_s)

        w, F = _apply_limited_transfers(
            water=w,
            area=area,
            elev=elev,
            edges=edges,
            blocked=blocked,
            dt_s=dt_s,
            max_transfer_frac=cfg.max_transfer_frac,
        )
        flow_m3s[t] = F

        sea_out = coastal_s * np.maximum(w, 0.0) * coastal * dt_s
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
        area_m2=area,
        flow_edges=flow_edges,
        flow_edge_indices=flow_edge_indices,
        flow_m3s=flow_m3s,
        failed_districts=cfg.failed_districts,
        blocked_edges=cfg.blocked_edges,
    )
