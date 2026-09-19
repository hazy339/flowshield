from __future__ import annotations

from dataclasses import dataclass

from .model import SimConfig


@dataclass(frozen=True)
class ScenarioPreset:
    name: str
    description: str
    rainfall_mm_h: float
    duration_h: float
    failed_districts: tuple[str, ...] = ()
    blocked_edges: tuple[tuple[str, str], ...] = ()


PRESETS: dict[str, ScenarioPreset] = {
    "Normal rainfall": ScenarioPreset(
        name="Normal rainfall",
        description="Seasonal monsoon pulse the drainage network is designed to handle.",
        rainfall_mm_h=16.0,
        duration_h=24.0,
    ),
    "Heavy rainfall": ScenarioPreset(
        name="Heavy rainfall",
        description="Extreme cloudburst across the Chennai basin.",
        rainfall_mm_h=72.0,
        duration_h=24.0,
    ),
    "Drainage failure": ScenarioPreset(
        name="Drainage failure",
        description="Pumping stations fail in low-lying Velachery while rain stays heavy.",
        rainfall_mm_h=48.0,
        duration_h=24.0,
        failed_districts=("velachery",),
    ),
    "Blocked drainage channel": ScenarioPreset(
        name="Blocked drainage channel",
        description="Velachery Drain is blocked, trapping runoff before it reaches Adyar.",
        rainfall_mm_h=48.0,
        duration_h=24.0,
        blocked_edges=(("velachery", "adyar"),),
    ),
    "Custom": ScenarioPreset(
        name="Custom",
        description="Configure rainfall, failures, and blockages manually.",
        rainfall_mm_h=40.0,
        duration_h=24.0,
    ),
}


def apply_preset(name: str) -> SimConfig:
    preset = PRESETS[name]
    return SimConfig(
        rainfall_mm_h=preset.rainfall_mm_h,
        duration_h=preset.duration_h,
        failed_districts=preset.failed_districts,
        blocked_edges=preset.blocked_edges,
    )
