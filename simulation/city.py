from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


CANALS: list[dict] = [
    {
        "id": "cooum",
        "name": "Cooum River",
        "districts": ["ambattur", "anna_nagar", "perambur", "tondiarpet"],
        "sea": [80.325, 13.15],
    },
    {
        "id": "adyar_river",
        "name": "Adyar River",
        "districts": ["pallavaram", "guindy", "adyar"],
        "sea": [80.325, 12.995],
    },
    {
        "id": "buckingham",
        "name": "Buckingham Canal",
        "districts": ["tondiarpet", "mylapore", "adyar", "sholinganallur"],
        "sea": None,
    },
    {
        "id": "south_canal",
        "name": "Velachery Drain",
        "districts": ["tambaram", "velachery", "adyar"],
        "sea": None,
    },
]

BLOCKABLE_CHANNELS: list[dict] = [
    {
        "id": "velachery_adyar",
        "label": "Velachery Drain (Velachery – Adyar)",
        "edge": ("velachery", "adyar"),
        "canal_id": "south_canal",
    },
    {
        "id": "guindy_adyar",
        "label": "Adyar River (Guindy – Adyar)",
        "edge": ("guindy", "adyar"),
        "canal_id": "adyar_river",
    },
    {
        "id": "anna_perambur",
        "label": "Cooum River (Anna Nagar – Perambur)",
        "edge": ("anna_nagar", "perambur"),
        "canal_id": "cooum",
    },
    {
        "id": "mylapore_adyar",
        "label": "Buckingham Canal (Mylapore – Adyar)",
        "edge": ("mylapore", "adyar"),
        "canal_id": "buckingham",
    },
]


def _polygon_centroid(ring: list[list[float]]) -> tuple[float, float]:
    xs = [p[0] for p in ring[:-1]]
    ys = [p[1] for p in ring[:-1]]
    return (sum(ys) / len(ys), sum(xs) / len(xs))


EARTH_RADIUS_M = 6_371_000.0


def _polygon_area_m2(geometry: dict) -> float:
    geom_type = geometry.get("type")
    if geom_type == "Polygon":
        rings = geometry.get("coordinates", [])
        total = 0.0
        for ring in rings:
            if len(ring) < 4:
                continue
            lat0, lon0 = _polygon_centroid(ring)
            projected: list[tuple[float, float]] = []
            for lon, lat in ring[:-1]:
                x = EARTH_RADIUS_M * math.radians(lon - lon0) * math.cos(math.radians(lat0))
                y = EARTH_RADIUS_M * math.radians(lat - lat0)
                projected.append((x, y))

            area = 0.0
            for i in range(len(projected)):
                x1, y1 = projected[i]
                x2, y2 = projected[(i + 1) % len(projected)]
                area += x1 * y2 - x2 * y1
            total += abs(area / 2.0)
        return total
    if geom_type == "MultiPolygon":
        polygons = geometry.get("coordinates", [])
        return sum(_polygon_area_m2({"type": "Polygon", "coordinates": polygon}) for polygon in polygons)
    return 0.0


@dataclass
class City:
    ids: list[str]
    names: list[str]
    elevation: list[float]
    drainage_mm_h: list[float]
    initial_water: list[float]
    population: list[int]
    rainfall_factor: list[float]
    coastal: list[bool]
    neighbors: list[list[int]]
    canal_edges: list[tuple[int, int]]
    geojson: dict
    centroids: dict[str, tuple[float, float]]
    area_m2: list[float] = field(default_factory=list)
    index_of: dict[str, int] = field(default_factory=dict)
    center: tuple[float, float] = (13.04, 80.22)
    bounds: list[list[float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.index_of = {did: i for i, did in enumerate(self.ids)}
        lats = [lat for lat, _ in self.centroids.values()]
        lons = [lon for _, lon in self.centroids.values()]
        self.center = (sum(lats) / len(lats), sum(lons) / len(lons))
        self.bounds = [
            [min(lats) - 0.02, min(lons) - 0.03],
            [max(lats) + 0.02, max(lons) + 0.03],
        ]

    @property
    def n(self) -> int:
        return len(self.ids)

    def name_of(self, district_id: str) -> str:
        return self.names[self.index_of[district_id]]

    def canal_polylines(self) -> list[dict]:
        lines = []
        for canal in CANALS:
            coords: list[list[float]] = []
            for did in canal["districts"]:
                lat, lon = self.centroids[did]
                coords.append([lat, lon])
            if canal.get("sea"):
                lon, lat = canal["sea"]
                coords.append([lat, lon])
            lines.append(
                {
                    "id": canal["id"],
                    "name": canal["name"],
                    "coords": coords,
                    "edges": list(zip(canal["districts"], canal["districts"][1:])),
                }
            )
        return lines


def load_city(data_dir: Path | None = None) -> City:
    data_dir = data_dir or DATA_DIR
    geojson = json.loads((data_dir / "districts.geojson").read_text(encoding="utf-8"))

    centroids: dict[str, tuple[float, float]] = {}
    for feat in geojson["features"]:
        did = feat["properties"]["id"]
        ring = feat["geometry"]["coordinates"][0]
        centroids[did] = _polygon_centroid(ring)

    rows: dict[str, dict] = {}
    with (data_dir / "district_attributes.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows[row["id"]] = row

    ids = [feat["properties"]["id"] for feat in geojson["features"]]
    index_of = {did: i for i, did in enumerate(ids)}

    names = []
    elevation = []
    drainage = []
    initial = []
    population = []
    rain_factor = []
    coastal = []
    neighbors: list[list[int]] = []

    for did in ids:
        row = rows[did]
        names.append(row["name"])
        elevation.append(float(row["elevation_m"]))
        drainage.append(float(row["drainage_mm_h"]))
        initial.append(float(row["initial_water_m"]))
        population.append(int(row["population"]))
        rain_factor.append(float(row["rainfall_factor"]))
        coastal.append(row["is_coastal"] == "1")
        neigh = [index_of[n] for n in row["neighbors"].split(";") if n]
        neighbors.append(neigh)

    canal_edges: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for canal in CANALS:
        for a, b in zip(canal["districts"], canal["districts"][1:]):
            i, j = index_of[a], index_of[b]
            key = (min(i, j), max(i, j))
            if key not in seen:
                seen.add(key)
                canal_edges.append(key)

    area_m2 = [_polygon_area_m2(feature["geometry"]) for feature in geojson["features"]]

    return City(
        ids=ids,
        names=names,
        elevation=elevation,
        drainage_mm_h=drainage,
        initial_water=initial,
        population=population,
        rainfall_factor=rain_factor,
        coastal=coastal,
        neighbors=neighbors,
        canal_edges=canal_edges,
        geojson=geojson,
        centroids=centroids,
        area_m2=area_m2,
    )
