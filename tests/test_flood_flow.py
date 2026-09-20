"""Validation tests A–G for FLOWSHIELD nonlinear flood-flow core."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation.city import load_city
from simulation.model import SimConfig, _apply_limited_transfers, nonlinear_flow_m3s, run_simulation


def _closed_cfg(**kwargs) -> SimConfig:
    base = dict(
        rainfall_mm_h=0.0,
        duration_h=2.0,
        dt_h=0.25,
        rain_duration_h=0.0,
        drainage_scale=0.0,
        initial_scale=1.0,
        runoff=0.0,
        infiltration_mm_h=0.0,
        coastal_sink=0.0,
        conductivity=450.0,
        canal_conductivity=450.0,
        max_transfer_frac=0.38,
    )
    base.update(kwargs)
    return SimConfig(**base)


def test_a_equal_hydraulic_surface() -> None:
    assert abs(nonlinear_flow_m3s(0.0, 450.0)) < 1e-15
    assert abs(nonlinear_flow_m3s(1e-12, 450.0)) < 1e-9
    print("PASS A - equal hydraulic surface => F=0")


def test_b_direction() -> None:
    f = nonlinear_flow_m3s(0.25, 450.0)
    assert f > 0, "eta_i > eta_j must give F_ij > 0 (i->j)"
    f_rev = nonlinear_flow_m3s(-0.25, 450.0)
    assert f_rev < 0, "eta_i < eta_j must give F_ij < 0 (j->i)"
    assert abs(f + f_rev) < 1e-12
    print("PASS B - flow direction follows head sign")


def test_c_nonlinear_scaling() -> None:
    k = 450.0
    h = 0.16
    f1 = nonlinear_flow_m3s(h, k)
    f4 = nonlinear_flow_m3s(4.0 * h, k)
    ratio = f4 / f1
    assert abs(ratio - 2.0) < 1e-9, f"expected F->2F when H->4H, got ratio={ratio}"
    print(f"PASS C - nonlinear scaling H->4H => F->2F (ratio={ratio:.12f})")


def test_d_blocked_connection() -> None:
    city = load_city("chennai")
    edge = city.primary_block_edge()
    assert edge is not None
    cfg = _closed_cfg(blocked_edges=(edge,), initial_scale=3.0, rainfall_mm_h=0.0)
    # Uneven water so head would drive flow if unblocked.
    result = run_simulation(city, cfg)
    i = city.index_of[edge[0]]
    j = city.index_of[edge[1]]
    a, b = (i, j) if i < j else (j, i)
    e_idx = result.flow_edge_indices.index((a, b))
    assert np.allclose(result.flow_m3s[:, e_idx], 0.0), "blocked edge must have zero flow"
    print(f"PASS D - blocked edge {edge} has F=0 for all timesteps")


def test_e_mass_conservation() -> None:
    city = load_city("chennai")
    cfg = _closed_cfg(duration_h=6.0, dt_h=0.25, initial_scale=2.5)
    result = run_simulation(city, cfg)
    volumes = [result.total_volume_m3(t) for t in range(result.n_steps)]
    v0 = volumes[0]
    drift = max(abs(v - v0) for v in volumes)
    rel = drift / max(v0, 1.0)
    assert rel < 1e-9, f"mass drift {drift=} {rel=} volumes[0]={v0} volumes[-1]={volumes[-1]}"
    print(f"PASS E - mass conservation |dV|_max={drift:.6e} m3 (rel={rel:.3e})")


def test_f_non_negative_water() -> None:
    city = load_city("chennai")
    cfg = SimConfig(
        rainfall_mm_h=90.0,
        duration_h=12.0,
        dt_h=0.25,
        rain_duration_h=8.0,
        drainage_scale=1.2,
        initial_scale=1.5,
        conductivity=450.0,
        canal_conductivity=1400.0,
        max_transfer_frac=0.38,
    )
    result = run_simulation(city, cfg)
    assert np.all(result.water >= -1e-12), "water depth must stay non-negative"
    print(f"PASS F - non-negative water (min={float(result.water.min()):.3e} m)")


def test_g_timestep_seconds() -> None:
    dt_h = 0.25
    dt_s = dt_h * 3600.0
    assert abs(dt_s - 900.0) < 1e-12

    # Two-region closed toy: verifies phi = F * dt_s updates depth via area.
    elev = np.array([10.0, 10.0])
    area = np.array([1.0e6, 2.0e6])
    water = np.array([0.80, 0.20])  # H = 0.60 m
    edges = [(0, 1, 450.0)]
    H = (elev[0] + water[0]) - (elev[1] + water[1])
    assert abs(H - 0.60) < 1e-12
    F_unconstrained = nonlinear_flow_m3s(H, 450.0)
    assert abs(F_unconstrained - 450.0 * math.sqrt(0.60)) < 1e-12

    new_w, F = _apply_limited_transfers(
        water=water,
        area=area,
        elev=elev,
        edges=edges,
        blocked=set(),
        dt_s=dt_s,
        max_transfer_frac=1.0,  # allow full transfer up to available volume
    )
    phi = F[0] * dt_s
    assert abs((new_w[0] - water[0]) * area[0] + phi) < 1e-6
    assert abs((new_w[1] - water[1]) * area[1] - phi) < 1e-6
    assert abs(phi / (F[0] * dt_h) - 3600.0) < 1e-9
    assert np.all(new_w >= -1e-12)
    print(f"PASS G - volumetric transfer uses dt_s={dt_s:g} s (F={F[0]:.4f} m3/s, phi={phi:.1f} m3)")


def main() -> None:
    city = load_city("chennai")
    print("Chennai districts:", list(enumerate(city.names)))
    print("Areas m2:", [round(a, 1) for a in city.area_m2])

    test_a_equal_hydraulic_surface()
    test_b_direction()
    test_c_nonlinear_scaling()
    test_d_blocked_connection()
    test_e_mass_conservation()
    test_f_non_negative_water()
    test_g_timestep_seconds()

    # Scenario sample for reporting flow magnitude range.
    cfg = SimConfig(
        rainfall_mm_h=80.0,
        duration_h=18.0,
        dt_h=0.25,
        rain_duration_h=10.0,
        drainage_scale=0.85,
        initial_scale=1.2,
        conductivity=450.0,
        canal_conductivity=1400.0,
    )
    result = run_simulation(city, cfg)
    flows = result.flow_m3s[1:]  # skip t=0 zeros
    fmin = float(np.min(flows))
    fmax = float(np.max(flows))
    amax = float(np.max(np.abs(flows)))
    print("---")
    print(f"Sample run flow_m3s min={fmin:.6g} max={fmax:.6g} |F|_max={amax:.6g}")
    print(f"Edges stored: {result.n_edges}")
    print("All validation tests passed.")


if __name__ == "__main__":
    main()
