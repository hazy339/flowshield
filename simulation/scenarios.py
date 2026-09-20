from __future__ import annotations

from dataclasses import dataclass

from .city import City
from .model import SimConfig


@dataclass(frozen=True)
class ScenarioPreset:
    name: str
    description: str
    rainfall_mm_h: float
    duration_h: float
    fail_lowest: bool = False
    block_primary: bool = False


PRESETS: dict[str, ScenarioPreset] = {
    "Normal rainfall": ScenarioPreset(
        name="Normal rainfall",
        description="Seasonal monsoon pulse the drainage network is designed to handle.",
        rainfall_mm_h=16.0,
        duration_h=24.0,
    ),
    "Heavy rainfall": ScenarioPreset(
        name="Heavy rainfall",
        description="Extreme cloudburst across the selected Indian basin.",
        rainfall_mm_h=72.0,
        duration_h=24.0,
    ),
    "Drainage failure": ScenarioPreset(
        name="Drainage failure",
        description="Pumping stations fail in the lowest-lying district while rain stays heavy.",
        rainfall_mm_h=48.0,
        duration_h=24.0,
        fail_lowest=True,
    ),
    "Blocked drainage channel": ScenarioPreset(
        name="Blocked drainage channel",
        description="A primary river/drain link is blocked, trapping upstream runoff.",
        rainfall_mm_h=48.0,
        duration_h=24.0,
        block_primary=True,
    ),
    "Custom": ScenarioPreset(
        name="Custom",
        description="Configure rainfall, failures, and blockages manually.",
        rainfall_mm_h=40.0,
        duration_h=24.0,
    ),
}


def apply_preset(name: str, city: City | None = None) -> SimConfig:
    preset = PRESETS[name]
    failed: tuple[str, ...] = ()
    blocked: tuple[tuple[str, str], ...] = ()
    if city is not None:
        if preset.fail_lowest:
            failed = (city.lowest_district_id(),)
        if preset.block_primary:
            edge = city.primary_block_edge()
            if edge:
                blocked = (edge,)
    return SimConfig(
        rainfall_mm_h=preset.rainfall_mm_h,
        duration_h=preset.duration_h,
        failed_districts=failed,
        blocked_edges=blocked,
    )
