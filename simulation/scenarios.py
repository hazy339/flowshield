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
    rain_duration_h: float | None = None
    drainage_scale: float = 1.0
    initial_scale: float = 1.0
    fail_lowest: bool = False
    block_primary: bool = False


PRESETS: dict[str, ScenarioPreset] = {
    "Normal rainfall": ScenarioPreset(
        name="Normal rainfall",
        description="Seasonal monsoon pulse the drainage network is designed to handle.",
        rainfall_mm_h=22.0,
        duration_h=24.0,
        rain_duration_h=6.0,
    ),
    "Heavy rainfall": ScenarioPreset(
        name="Heavy rainfall",
        description="Sustained cloudburst that overwhelms drains across the basin.",
        rainfall_mm_h=95.0,
        duration_h=24.0,
        rain_duration_h=12.0,
        initial_scale=1.25,
    ),
    "Extreme flood": ScenarioPreset(
        name="Extreme flood",
        description="Worst-case monsoon: intense rain, saturated ground, pump failure and a blocked channel.",
        rainfall_mm_h=140.0,
        duration_h=24.0,
        rain_duration_h=16.0,
        drainage_scale=0.55,
        initial_scale=1.6,
        fail_lowest=True,
        block_primary=True,
    ),
    "Drainage failure": ScenarioPreset(
        name="Drainage failure",
        description="Heavy rain while pumping fails in the lowest-lying district.",
        rainfall_mm_h=90.0,
        duration_h=24.0,
        rain_duration_h=12.0,
        drainage_scale=0.75,
        initial_scale=1.3,
        fail_lowest=True,
    ),
    "Blocked drainage channel": ScenarioPreset(
        name="Blocked drainage channel",
        description="Primary river/drain link blocked, trapping upstream runoff under heavy rain.",
        rainfall_mm_h=85.0,
        duration_h=24.0,
        rain_duration_h=12.0,
        initial_scale=1.35,
        block_primary=True,
    ),
    "Custom": ScenarioPreset(
        name="Custom",
        description="Configure rainfall, failures, and blockages manually.",
        rainfall_mm_h=70.0,
        duration_h=24.0,
        rain_duration_h=10.0,
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
    rain_h = preset.rain_duration_h if preset.rain_duration_h is not None else preset.duration_h
    return SimConfig(
        rainfall_mm_h=preset.rainfall_mm_h,
        duration_h=preset.duration_h,
        rain_duration_h=rain_h,
        drainage_scale=preset.drainage_scale,
        initial_scale=preset.initial_scale,
        failed_districts=failed,
        blocked_edges=blocked,
    )
