"""
Offline NumPy / Pandas / Matplotlib analysis helpers.

Satisfies the suggested stack for numerical computation and analysis
alongside the React visualization front end.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from simulation.city import load_city
from simulation.model import run_simulation
from simulation.scenarios import PRESETS, apply_preset

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "analysis" / "output"


def scenario_comparison_table(region_id: str = "chennai") -> pd.DataFrame:
    city = load_city(region_id)
    rows = []
    for name, preset in PRESETS.items():
        if name == "Custom":
            continue
        result = run_simulation(city, apply_preset(name, city))
        t = result.peak_hazard_index()
        rows.append(
            {
                "scenario": name,
                "rainfall_mm_h": preset.rainfall_mm_h,
                "peak_critical": result.counts_at(t)["Critical"],
                "peak_warning": result.counts_at(t)["Warning"],
                "affected_population": result.affected_population(t),
                "first_critical_h": result.first_critical_hour(),
            }
        )
    return pd.DataFrame(rows)


def plot_scenario_comparison(region_id: str = "chennai") -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    df = scenario_comparison_table(region_id)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(df))
    ax.bar([i - 0.2 for i in x], df["peak_critical"], width=0.4, label="Critical districts", color="#e74c3c")
    ax.bar([i + 0.2 for i in x], df["peak_warning"], width=0.4, label="Warning districts", color="#f5a623")
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["scenario"], rotation=20, ha="right")
    ax.set_ylabel("District count at peak hazard")
    ax.set_title(f"FLOWSHIELD scenario comparison · {region_id}")
    ax.legend()
    fig.tight_layout()
    path = OUT / f"{region_id}_scenario_comparison.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    csv_path = OUT / f"{region_id}_scenario_comparison.csv"
    df.to_csv(csv_path, index=False)
    return path


if __name__ == "__main__":
    out = plot_scenario_comparison("chennai")
    print(f"Wrote {out}")
