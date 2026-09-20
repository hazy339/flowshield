from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


@dataclass(frozen=True)
class RegionInfo:
    id: str
    city: str
    state: str
    label: str
    description: str


REGION_CATALOG: dict[str, RegionInfo] = {
    "chennai": RegionInfo("chennai", "Chennai", "Tamil Nadu", "Chennai, Tamil Nadu", "Coastal basin · Cooum / Adyar"),
    "mumbai": RegionInfo("mumbai", "Mumbai", "Maharashtra", "Mumbai, Maharashtra", "Coastal megacity · Mithi River"),
    "delhi": RegionInfo("delhi", "Delhi", "Delhi NCT", "Delhi, NCT", "Yamuna floodplain · inland drains"),
    "kolkata": RegionInfo("kolkata", "Kolkata", "West Bengal", "Kolkata, West Bengal", "Hooghly delta · canal system"),
    "guwahati": RegionInfo("guwahati", "Guwahati", "Assam", "Guwahati, Assam", "Brahmaputra corridor"),
    "hyderabad": RegionInfo("hyderabad", "Hyderabad", "Telangana", "Hyderabad, Telangana", "Musi / lake basin"),
    "bengaluru": RegionInfo("bengaluru", "Bengaluru", "Karnataka", "Bengaluru, Karnataka", "Vrishabhavathi / lake chain"),
    "patna": RegionInfo("patna", "Patna", "Bihar", "Patna, Bihar", "Ganga floodplain · chronic monsoon inundation"),
    "kochi": RegionInfo("kochi", "Kochi", "Kerala", "Kochi, Kerala", "Backwaters · coastal monsoon surge"),
    "surat": RegionInfo("surat", "Surat", "Gujarat", "Surat, Gujarat", "Tapi estuary · tidal / river floods"),
    "visakhapatnam": RegionInfo(
        "visakhapatnam", "Visakhapatnam", "Andhra Pradesh", "Visakhapatnam, Andhra Pradesh", "Bay of Bengal cyclone coast"
    ),
    "bhubaneswar": RegionInfo(
        "bhubaneswar", "Bhubaneswar", "Odisha", "Bhubaneswar, Odisha", "Mahanadi delta · cyclone / Daya basin"
    ),
    "srinagar": RegionInfo("srinagar", "Srinagar", "Jammu & Kashmir", "Srinagar, J&K", "Jhelum floodplain · valley inundation"),
    "alappuzha": RegionInfo(
        "alappuzha", "Alappuzha", "Kerala", "Alappuzha, Kerala", "Kuttanad below sea level · extreme flood risk"
    ),
    "vadodara": RegionInfo("vadodara", "Vadodara", "Gujarat", "Vadodara, Gujarat", "Vishwamitri corridor · flash floods"),
    "mangaluru": RegionInfo("mangaluru", "Mangaluru", "Karnataka", "Mangaluru, Karnataka", "West coast monsoon · Netravati"),
}


def list_regions() -> list[RegionInfo]:
    return list(REGION_CATALOG.values())


def resolve_region_query(query: str) -> str | None:
    q = (query or "").strip().lower()
    if not q:
        return None
    for rid, info in REGION_CATALOG.items():
        hay = f"{info.city} {info.state} {info.label} {rid}".lower()
        if q in hay or info.city.lower().startswith(q) or rid.startswith(q):
            return rid
    aliases = {
        "madras": "chennai",
        "bombay": "mumbai",
        "calcutta": "kolkata",
        "bangalore": "bengaluru",
        "blr": "bengaluru",
        "ncr": "delhi",
        "new delhi": "delhi",
        "assam": "guwahati",
        "west bengal": "kolkata",
        "tamil nadu": "chennai",
        "maharashtra": "mumbai",
        "karnataka": "bengaluru",
        "telangana": "hyderabad",
        "bihar": "patna",
        "kerala": "kochi",
        "cochin": "kochi",
        "gujarat": "surat",
        "vizag": "visakhapatnam",
        "visakhapatnam": "visakhapatnam",
        "andhra": "visakhapatnam",
        "andhra pradesh": "visakhapatnam",
        "odisha": "bhubaneswar",
        "orissa": "bhubaneswar",
        "bbsr": "bhubaneswar",
        "jammu": "srinagar",
        "kashmir": "srinagar",
        "j&k": "srinagar",
        "alleppey": "alappuzha",
        "kuttanad": "alappuzha",
        "baroda": "vadodara",
        "mangalore": "mangaluru",
    }
    for key, rid in aliases.items():
        if key in q or q in key:
            return rid
    return None


def _polygon_centroid(ring: list[list[float]]) -> tuple[float, float]:
    xs = [p[0] for p in ring[:-1]]
    ys = [p[1] for p in ring[:-1]]
    return (sum(ys) / len(ys), sum(xs) / len(xs))


def _cell_polygon(lon0: float, lat0: float, lon1: float, lat1: float) -> list[list[float]]:
    return [[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]


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
    canals: list[dict] = field(default_factory=list)
    blockable_channels: list[dict] = field(default_factory=list)
    region_id: str = "chennai"
    city_name: str = "Chennai"
    state_name: str = "Tamil Nadu"
    index_of: dict[str, int] = field(default_factory=dict)
    center: tuple[float, float] = (13.04, 80.22)
    bounds: list[list[float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.index_of = {did: i for i, did in enumerate(self.ids)}
        lats = [lat for lat, _ in self.centroids.values()]
        lons = [lon for _, lon in self.centroids.values()]
        self.center = (sum(lats) / len(lats), sum(lons) / len(lons))
        self.bounds = [
            [min(lats) - 0.03, min(lons) - 0.04],
            [max(lats) + 0.03, max(lons) + 0.04],
        ]

    @property
    def n(self) -> int:
        return len(self.ids)

    @property
    def label(self) -> str:
        return f"{self.city_name}, {self.state_name}"

    def name_of(self, district_id: str) -> str:
        return self.names[self.index_of[district_id]]

    def lowest_district_id(self) -> str:
        return self.ids[min(range(self.n), key=lambda i: self.elevation[i])]

    def primary_block_edge(self) -> tuple[str, str] | None:
        if not self.blockable_channels:
            return None
        return self.blockable_channels[0]["edge"]

    def canal_polylines(self) -> list[dict]:
        lines = []
        for canal in self.canals:
            coords: list[list[float]] = []
            for did in canal["districts"]:
                if did not in self.centroids:
                    continue
                lat, lon = self.centroids[did]
                coords.append([lat, lon])
            if canal.get("sea") and coords:
                lon, lat = canal["sea"]
                coords.append([lat, lon])
            if len(coords) < 2:
                continue
            lines.append(
                {
                    "id": canal["id"],
                    "name": canal["name"],
                    "coords": coords,
                    "edges": list(zip(canal["districts"], canal["districts"][1:])),
                }
            )
        return lines


CHENNAI_CANALS = [
    {"id": "cooum", "name": "Cooum River", "districts": ["ambattur", "anna_nagar", "perambur", "tondiarpet"], "sea": [80.325, 13.15]},
    {"id": "adyar_river", "name": "Adyar River", "districts": ["pallavaram", "guindy", "adyar"], "sea": [80.325, 12.995]},
    {"id": "buckingham", "name": "Buckingham Canal", "districts": ["tondiarpet", "mylapore", "adyar", "sholinganallur"], "sea": None},
    {"id": "south_canal", "name": "Velachery Drain", "districts": ["tambaram", "velachery", "adyar"], "sea": None},
]

CHENNAI_BLOCKABLE = [
    {"id": "velachery_adyar", "label": "Velachery Drain (Velachery – Adyar)", "edge": ("velachery", "adyar"), "canal_id": "south_canal"},
    {"id": "guindy_adyar", "label": "Adyar River (Guindy – Adyar)", "edge": ("guindy", "adyar"), "canal_id": "adyar_river"},
    {"id": "anna_perambur", "label": "Cooum River (Anna Nagar – Perambur)", "edge": ("anna_nagar", "perambur"), "canal_id": "cooum"},
    {"id": "mylapore_adyar", "label": "Buckingham Canal (Mylapore – Adyar)", "edge": ("mylapore", "adyar"), "canal_id": "buckingham"},
]

CANALS = CHENNAI_CANALS
BLOCKABLE_CHANNELS = CHENNAI_BLOCKABLE


def _build_city_from_tables(
    *,
    region_id: str,
    city_name: str,
    state_name: str,
    geojson: dict,
    rows: dict[str, dict],
    canals: list[dict],
    blockable: list[dict],
) -> City:
    centroids: dict[str, tuple[float, float]] = {}
    for feat in geojson["features"]:
        did = feat["properties"]["id"]
        ring = feat["geometry"]["coordinates"][0]
        centroids[did] = _polygon_centroid(ring)

    ids = [feat["properties"]["id"] for feat in geojson["features"]]
    index_of = {did: i for i, did in enumerate(ids)}

    names, elevation, drainage, initial, population, rain_factor, coastal, neighbors = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for did in ids:
        row = rows[did]
        names.append(row["name"])
        elevation.append(float(row["elevation_m"]))
        drainage.append(float(row["drainage_mm_h"]))
        initial.append(float(row["initial_water_m"]))
        population.append(int(row["population"]))
        rain_factor.append(float(row["rainfall_factor"]))
        coastal.append(str(row["is_coastal"]) in {"1", "True", "true"})
        neigh = [index_of[n] for n in str(row["neighbors"]).split(";") if n and n in index_of]
        neighbors.append(neigh)

    canal_edges: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for canal in canals:
        for a, b in zip(canal["districts"], canal["districts"][1:]):
            if a not in index_of or b not in index_of:
                continue
            i, j = index_of[a], index_of[b]
            key = (min(i, j), max(i, j))
            if key not in seen:
                seen.add(key)
                canal_edges.append(key)

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
        canals=canals,
        blockable_channels=blockable,
        region_id=region_id,
        city_name=city_name,
        state_name=state_name,
    )


def _load_chennai(data_dir: Path) -> City:
    geojson = json.loads((data_dir / "districts.geojson").read_text(encoding="utf-8"))
    rows: dict[str, dict] = {}
    with (data_dir / "district_attributes.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows[row["id"]] = row
    info = REGION_CATALOG["chennai"]
    return _build_city_from_tables(
        region_id="chennai",
        city_name=info.city,
        state_name=info.state,
        geojson=geojson,
        rows=rows,
        canals=CHENNAI_CANALS,
        blockable=CHENNAI_BLOCKABLE,
    )


def _grid_city(
    *,
    region_id: str,
    city_name: str,
    state_name: str,
    origin_lon: float,
    origin_lat: float,
    cell_w: float,
    cell_h: float,
    cells: list[dict],
    canals: list[dict],
    blockable: list[dict],
) -> City:
    features = []
    rows: dict[str, dict] = {}
    id_by_rc = {(c["row"], c["col"]): c["id"] for c in cells}

    for cell in cells:
        r, c = cell["row"], cell["col"]
        lon0 = origin_lon + c * cell_w
        lat1 = origin_lat - r * cell_h
        lon1 = lon0 + cell_w
        lat0 = lat1 - cell_h
        did = cell["id"]
        features.append(
            {
                "type": "Feature",
                "properties": {"id": did, "name": cell["name"]},
                "geometry": {"type": "Polygon", "coordinates": [_cell_polygon(lon0, lat0, lon1, lat1)]},
            }
        )
        neigh = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            other = id_by_rc.get((r + dr, c + dc))
            if other:
                neigh.append(other)
        rows[did] = {
            "id": did,
            "name": cell["name"],
            "elevation_m": cell["elevation_m"],
            "drainage_mm_h": cell["drainage_mm_h"],
            "initial_water_m": cell.get("initial_water_m", 0.04),
            "population": cell["population"],
            "rainfall_factor": cell.get("rainfall_factor", 1.0),
            "is_coastal": "1" if cell.get("is_coastal") else "0",
            "neighbors": ";".join(neigh),
        }

    geojson = {"type": "FeatureCollection", "name": f"{region_id}_districts", "features": features}
    return _build_city_from_tables(
        region_id=region_id,
        city_name=city_name,
        state_name=state_name,
        geojson=geojson,
        rows=rows,
        canals=canals,
        blockable=blockable,
    )


def _mumbai() -> City:
    info = REGION_CATALOG["mumbai"]
    cells = [
        {"id": "borivali", "name": "Borivali", "row": 0, "col": 0, "elevation_m": 18, "drainage_mm_h": 18, "population": 320000, "rainfall_factor": 0.95},
        {"id": "kandivali", "name": "Kandivali", "row": 0, "col": 1, "elevation_m": 14, "drainage_mm_h": 16, "population": 280000, "rainfall_factor": 0.97},
        {"id": "malad", "name": "Malad", "row": 0, "col": 2, "elevation_m": 8, "drainage_mm_h": 12, "population": 350000, "rainfall_factor": 1.05, "is_coastal": True},
        {"id": "andheri", "name": "Andheri", "row": 1, "col": 0, "elevation_m": 16, "drainage_mm_h": 17, "population": 400000, "rainfall_factor": 1.0},
        {"id": "kurla", "name": "Kurla", "row": 1, "col": 1, "elevation_m": 6, "drainage_mm_h": 9, "population": 310000, "rainfall_factor": 1.12, "initial_water_m": 0.08},
        {"id": "bandra", "name": "Bandra", "row": 1, "col": 2, "elevation_m": 7, "drainage_mm_h": 11, "population": 270000, "rainfall_factor": 1.08, "is_coastal": True},
        {"id": "powai", "name": "Powai", "row": 2, "col": 0, "elevation_m": 22, "drainage_mm_h": 20, "population": 180000, "rainfall_factor": 0.96},
        {"id": "sion", "name": "Sion", "row": 2, "col": 1, "elevation_m": 9, "drainage_mm_h": 13, "population": 220000, "rainfall_factor": 1.04},
        {"id": "worli", "name": "Worli", "row": 2, "col": 2, "elevation_m": 5, "drainage_mm_h": 10, "population": 190000, "rainfall_factor": 1.1, "is_coastal": True},
        {"id": "chembur", "name": "Chembur", "row": 3, "col": 0, "elevation_m": 12, "drainage_mm_h": 14, "population": 240000, "rainfall_factor": 1.02},
        {"id": "dadar", "name": "Dadar", "row": 3, "col": 1, "elevation_m": 8, "drainage_mm_h": 12, "population": 260000, "rainfall_factor": 1.06},
        {"id": "colaba", "name": "Colaba", "row": 3, "col": 2, "elevation_m": 4, "drainage_mm_h": 10, "population": 150000, "rainfall_factor": 1.12, "is_coastal": True},
    ]
    canals = [
        {"id": "mithi", "name": "Mithi River", "districts": ["powai", "kurla", "sion", "dadar"], "sea": [72.82, 19.02]},
        {"id": "west_drain", "name": "Western Storm Drain", "districts": ["malad", "bandra", "worli", "colaba"], "sea": None},
    ]
    blockable = [
        {"id": "kurla_sion", "label": "Mithi River (Kurla – Sion)", "edge": ("kurla", "sion"), "canal_id": "mithi"},
        {"id": "bandra_worli", "label": "Western Drain (Bandra – Worli)", "edge": ("bandra", "worli"), "canal_id": "west_drain"},
    ]
    return _grid_city(
        region_id="mumbai",
        city_name=info.city,
        state_name=info.state,
        origin_lon=72.82,
        origin_lat=19.24,
        cell_w=0.055,
        cell_h=0.045,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _delhi() -> City:
    info = REGION_CATALOG["delhi"]
    cells = [
        {"id": "rohini", "name": "Rohini", "row": 0, "col": 0, "elevation_m": 220, "drainage_mm_h": 18, "population": 350000, "rainfall_factor": 0.94},
        {"id": "model_town", "name": "Model Town", "row": 0, "col": 1, "elevation_m": 214, "drainage_mm_h": 16, "population": 180000, "rainfall_factor": 0.97},
        {"id": "yamuna_vihar", "name": "Yamuna Vihar", "row": 0, "col": 2, "elevation_m": 205, "drainage_mm_h": 10, "population": 260000, "rainfall_factor": 1.1, "initial_water_m": 0.07},
        {"id": "punjabi_bagh", "name": "Punjabi Bagh", "row": 1, "col": 0, "elevation_m": 218, "drainage_mm_h": 17, "population": 220000, "rainfall_factor": 0.96},
        {"id": "karol_bagh", "name": "Karol Bagh", "row": 1, "col": 1, "elevation_m": 215, "drainage_mm_h": 15, "population": 200000, "rainfall_factor": 1.0},
        {"id": "shahdara", "name": "Shahdara", "row": 1, "col": 2, "elevation_m": 206, "drainage_mm_h": 11, "population": 300000, "rainfall_factor": 1.08},
        {"id": "dwarka", "name": "Dwarka", "row": 2, "col": 0, "elevation_m": 216, "drainage_mm_h": 19, "population": 280000, "rainfall_factor": 0.95},
        {"id": "cp", "name": "Connaught Place", "row": 2, "col": 1, "elevation_m": 214, "drainage_mm_h": 20, "population": 90000, "rainfall_factor": 0.98},
        {"id": "mayur_vihar", "name": "Mayur Vihar", "row": 2, "col": 2, "elevation_m": 204, "drainage_mm_h": 9, "population": 250000, "rainfall_factor": 1.12, "initial_water_m": 0.09},
        {"id": "saket", "name": "Saket", "row": 3, "col": 0, "elevation_m": 230, "drainage_mm_h": 18, "population": 170000, "rainfall_factor": 0.93},
        {"id": "okhla", "name": "Okhla", "row": 3, "col": 1, "elevation_m": 208, "drainage_mm_h": 12, "population": 210000, "rainfall_factor": 1.05},
        {"id": "kalindi_kunj", "name": "Kalindi Kunj", "row": 3, "col": 2, "elevation_m": 202, "drainage_mm_h": 8, "population": 140000, "rainfall_factor": 1.15, "initial_water_m": 0.1},
    ]
    canals = [
        {"id": "yamuna", "name": "Yamuna Corridor", "districts": ["yamuna_vihar", "shahdara", "mayur_vihar", "kalindi_kunj"], "sea": None},
        {"id": "najafgarh", "name": "Najafgarh Drain", "districts": ["rohini", "punjabi_bagh", "dwarka"], "sea": None},
    ]
    blockable = [
        {"id": "mayur_kalindi", "label": "Yamuna Corridor (Mayur Vihar – Kalindi Kunj)", "edge": ("mayur_vihar", "kalindi_kunj"), "canal_id": "yamuna"},
        {"id": "shahdara_mayur", "label": "Yamuna Corridor (Shahdara – Mayur Vihar)", "edge": ("shahdara", "mayur_vihar"), "canal_id": "yamuna"},
    ]
    return _grid_city(
        region_id="delhi",
        city_name=info.city,
        state_name=info.state,
        origin_lon=77.05,
        origin_lat=28.78,
        cell_w=0.07,
        cell_h=0.055,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _kolkata() -> City:
    info = REGION_CATALOG["kolkata"]
    cells = [
        {"id": "dumdum", "name": "Dum Dum", "row": 0, "col": 0, "elevation_m": 9, "drainage_mm_h": 14, "population": 220000, "rainfall_factor": 1.0},
        {"id": "salt_lake", "name": "Salt Lake", "row": 0, "col": 1, "elevation_m": 5, "drainage_mm_h": 11, "population": 190000, "rainfall_factor": 1.08, "initial_water_m": 0.07},
        {"id": "new_town", "name": "New Town", "row": 0, "col": 2, "elevation_m": 6, "drainage_mm_h": 15, "population": 160000, "rainfall_factor": 1.02},
        {"id": "howrah", "name": "Howrah", "row": 1, "col": 0, "elevation_m": 7, "drainage_mm_h": 12, "population": 280000, "rainfall_factor": 1.05, "is_coastal": True},
        {"id": "burrabazar", "name": "Burrabazar", "row": 1, "col": 1, "elevation_m": 8, "drainage_mm_h": 13, "population": 150000, "rainfall_factor": 1.04},
        {"id": "sealdah", "name": "Sealdah", "row": 1, "col": 2, "elevation_m": 7, "drainage_mm_h": 12, "population": 180000, "rainfall_factor": 1.06},
        {"id": "behala", "name": "Behala", "row": 2, "col": 0, "elevation_m": 6, "drainage_mm_h": 10, "population": 240000, "rainfall_factor": 1.1},
        {"id": "ballygunge", "name": "Ballygunge", "row": 2, "col": 1, "elevation_m": 8, "drainage_mm_h": 14, "population": 170000, "rainfall_factor": 1.01},
        {"id": "park_circus", "name": "Park Circus", "row": 2, "col": 2, "elevation_m": 7, "drainage_mm_h": 12, "population": 140000, "rainfall_factor": 1.03},
        {"id": "thakurpukur", "name": "Thakurpukur", "row": 3, "col": 0, "elevation_m": 5, "drainage_mm_h": 9, "population": 200000, "rainfall_factor": 1.12, "initial_water_m": 0.08},
        {"id": "tollygunge", "name": "Tollygunge", "row": 3, "col": 1, "elevation_m": 6, "drainage_mm_h": 10, "population": 210000, "rainfall_factor": 1.09},
        {"id": "jadavpur", "name": "Jadavpur", "row": 3, "col": 2, "elevation_m": 7, "drainage_mm_h": 11, "population": 190000, "rainfall_factor": 1.07},
    ]
    canals = [
        {"id": "hooghly", "name": "Hooghly Frontage", "districts": ["howrah", "behala", "thakurpukur"], "sea": [88.28, 22.48]},
        {"id": "east_canal", "name": "Eastern Canal", "districts": ["salt_lake", "sealdah", "park_circus", "jadavpur"], "sea": None},
    ]
    blockable = [
        {"id": "salt_sealdah", "label": "Eastern Canal (Salt Lake – Sealdah)", "edge": ("salt_lake", "sealdah"), "canal_id": "east_canal"},
        {"id": "behala_thakur", "label": "Hooghly Frontage (Behala – Thakurpukur)", "edge": ("behala", "thakurpukur"), "canal_id": "hooghly"},
    ]
    return _grid_city(
        region_id="kolkata",
        city_name=info.city,
        state_name=info.state,
        origin_lon=88.28,
        origin_lat=22.66,
        cell_w=0.05,
        cell_h=0.04,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _guwahati() -> City:
    info = REGION_CATALOG["guwahati"]
    cells = [
        {"id": "jalukbari", "name": "Jalukbari", "row": 0, "col": 0, "elevation_m": 55, "drainage_mm_h": 14, "population": 120000, "rainfall_factor": 1.05},
        {"id": "maligaon", "name": "Maligaon", "row": 0, "col": 1, "elevation_m": 52, "drainage_mm_h": 13, "population": 90000, "rainfall_factor": 1.06},
        {"id": "pandu", "name": "Pandu", "row": 0, "col": 2, "elevation_m": 48, "drainage_mm_h": 11, "population": 80000, "rainfall_factor": 1.1, "is_coastal": True},
        {"id": "fancy_bazar", "name": "Fancy Bazar", "row": 1, "col": 0, "elevation_m": 54, "drainage_mm_h": 12, "population": 100000, "rainfall_factor": 1.08},
        {"id": "panbazar", "name": "Panbazar", "row": 1, "col": 1, "elevation_m": 50, "drainage_mm_h": 11, "population": 85000, "rainfall_factor": 1.1},
        {"id": "ukhium", "name": "Uzan Bazar", "row": 1, "col": 2, "elevation_m": 47, "drainage_mm_h": 9, "population": 95000, "rainfall_factor": 1.14, "is_coastal": True, "initial_water_m": 0.08},
        {"id": "dispur", "name": "Dispur", "row": 2, "col": 0, "elevation_m": 60, "drainage_mm_h": 16, "population": 110000, "rainfall_factor": 1.02},
        {"id": "ganeshguri", "name": "Ganeshguri", "row": 2, "col": 1, "elevation_m": 56, "drainage_mm_h": 13, "population": 130000, "rainfall_factor": 1.07},
        {"id": "noonmati", "name": "Noonmati", "row": 2, "col": 2, "elevation_m": 58, "drainage_mm_h": 12, "population": 90000, "rainfall_factor": 1.05},
    ]
    canals = [
        {"id": "brahmaputra", "name": "Brahmaputra Front", "districts": ["pandu", "ukhium"], "sea": [91.78, 26.2]},
        {"id": "bharalu", "name": "Bharalu River", "districts": ["dispur", "ganeshguri", "panbazar", "ukhium"], "sea": None},
    ]
    blockable = [
        {"id": "ganesh_pan", "label": "Bharalu River (Ganeshguri – Panbazar)", "edge": ("ganeshguri", "panbazar"), "canal_id": "bharalu"},
        {"id": "pan_uzan", "label": "Bharalu River (Panbazar – Uzan Bazar)", "edge": ("panbazar", "ukhium"), "canal_id": "bharalu"},
    ]
    return _grid_city(
        region_id="guwahati",
        city_name=info.city,
        state_name=info.state,
        origin_lon=91.68,
        origin_lat=26.22,
        cell_w=0.05,
        cell_h=0.04,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _hyderabad() -> City:
    info = REGION_CATALOG["hyderabad"]
    cells = [
        {"id": "kukatpally", "name": "Kukatpally", "row": 0, "col": 0, "elevation_m": 540, "drainage_mm_h": 18, "population": 280000, "rainfall_factor": 0.96},
        {"id": "secunderabad", "name": "Secunderabad", "row": 0, "col": 1, "elevation_m": 530, "drainage_mm_h": 16, "population": 220000, "rainfall_factor": 0.98},
        {"id": "alwal", "name": "Alwal", "row": 0, "col": 2, "elevation_m": 535, "drainage_mm_h": 15, "population": 150000, "rainfall_factor": 0.97},
        {"id": "madhapur", "name": "Madhapur", "row": 1, "col": 0, "elevation_m": 545, "drainage_mm_h": 17, "population": 200000, "rainfall_factor": 0.95},
        {"id": "ameerpet", "name": "Ameerpet", "row": 1, "col": 1, "elevation_m": 525, "drainage_mm_h": 12, "population": 180000, "rainfall_factor": 1.05, "initial_water_m": 0.06},
        {"id": "habsiguda", "name": "Habsiguda", "row": 1, "col": 2, "elevation_m": 520, "drainage_mm_h": 11, "population": 160000, "rainfall_factor": 1.06},
        {"id": "gachibowli", "name": "Gachibowli", "row": 2, "col": 0, "elevation_m": 550, "drainage_mm_h": 19, "population": 170000, "rainfall_factor": 0.94},
        {"id": "mehdipatnam", "name": "Mehdipatnam", "row": 2, "col": 1, "elevation_m": 515, "drainage_mm_h": 10, "population": 210000, "rainfall_factor": 1.1, "initial_water_m": 0.08},
        {"id": "lb_nagar", "name": "LB Nagar", "row": 2, "col": 2, "elevation_m": 510, "drainage_mm_h": 9, "population": 240000, "rainfall_factor": 1.12, "initial_water_m": 0.09},
    ]
    canals = [
        {"id": "musa", "name": "Musi River", "districts": ["ameerpet", "mehdipatnam", "lb_nagar"], "sea": None},
        {"id": "hussain", "name": "Hussain Sagar Link", "districts": ["secunderabad", "ameerpet"], "sea": None},
    ]
    blockable = [
        {"id": "ameer_mehdi", "label": "Musi River (Ameerpet – Mehdipatnam)", "edge": ("ameerpet", "mehdipatnam"), "canal_id": "musa"},
        {"id": "mehdi_lb", "label": "Musi River (Mehdipatnam – LB Nagar)", "edge": ("mehdipatnam", "lb_nagar"), "canal_id": "musa"},
    ]
    return _grid_city(
        region_id="hyderabad",
        city_name=info.city,
        state_name=info.state,
        origin_lon=78.35,
        origin_lat=17.52,
        cell_w=0.06,
        cell_h=0.05,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _bengaluru() -> City:
    info = REGION_CATALOG["bengaluru"]
    cells = [
        {"id": "yelahanka", "name": "Yelahanka", "row": 0, "col": 0, "elevation_m": 920, "drainage_mm_h": 16, "population": 180000, "rainfall_factor": 0.95},
        {"id": "hebbal", "name": "Hebbal", "row": 0, "col": 1, "elevation_m": 910, "drainage_mm_h": 14, "population": 160000, "rainfall_factor": 0.98},
        {"id": "kr_puram", "name": "KR Puram", "row": 0, "col": 2, "elevation_m": 905, "drainage_mm_h": 13, "population": 200000, "rainfall_factor": 1.0},
        {"id": "rajajinagar", "name": "Rajajinagar", "row": 1, "col": 0, "elevation_m": 915, "drainage_mm_h": 15, "population": 170000, "rainfall_factor": 0.97},
        {"id": "mg_road", "name": "MG Road", "row": 1, "col": 1, "elevation_m": 900, "drainage_mm_h": 14, "population": 90000, "rainfall_factor": 1.02},
        {"id": "indiranagar", "name": "Indiranagar", "row": 1, "col": 2, "elevation_m": 895, "drainage_mm_h": 12, "population": 150000, "rainfall_factor": 1.04},
        {"id": "rr_nagar", "name": "RR Nagar", "row": 2, "col": 0, "elevation_m": 890, "drainage_mm_h": 11, "population": 190000, "rainfall_factor": 1.06},
        {"id": "jayanagar", "name": "Jayanagar", "row": 2, "col": 1, "elevation_m": 885, "drainage_mm_h": 10, "population": 180000, "rainfall_factor": 1.08, "initial_water_m": 0.07},
        {"id": "koramangala", "name": "Koramangala", "row": 2, "col": 2, "elevation_m": 880, "drainage_mm_h": 9, "population": 210000, "rainfall_factor": 1.12, "initial_water_m": 0.09},
    ]
    canals = [
        {"id": "vrishabhavathi", "name": "Vrishabhavathi Valley", "districts": ["rajajinagar", "rr_nagar", "jayanagar"], "sea": None},
        {"id": "bellandur", "name": "Bellandur Lake Chain", "districts": ["indiranagar", "koramangala"], "sea": None},
    ]
    blockable = [
        {"id": "rr_jaya", "label": "Vrishabhavathi (RR Nagar – Jayanagar)", "edge": ("rr_nagar", "jayanagar"), "canal_id": "vrishabhavathi"},
        {"id": "indi_kora", "label": "Bellandur Chain (Indiranagar – Koramangala)", "edge": ("indiranagar", "koramangala"), "canal_id": "bellandur"},
    ]
    return _grid_city(
        region_id="bengaluru",
        city_name=info.city,
        state_name=info.state,
        origin_lon=77.52,
        origin_lat=13.1,
        cell_w=0.06,
        cell_h=0.05,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _patna() -> City:
    info = REGION_CATALOG["patna"]
    cells = [
        {"id": "danapur", "name": "Danapur", "row": 0, "col": 0, "elevation_m": 53, "drainage_mm_h": 11, "population": 180000, "rainfall_factor": 1.08, "initial_water_m": 0.08},
        {"id": "bailey", "name": "Bailey Road", "row": 0, "col": 1, "elevation_m": 55, "drainage_mm_h": 13, "population": 160000, "rainfall_factor": 1.05},
        {"id": "digha", "name": "Digha Ghat", "row": 0, "col": 2, "elevation_m": 48, "drainage_mm_h": 8, "population": 140000, "rainfall_factor": 1.18, "is_coastal": True, "initial_water_m": 0.12},
        {"id": "phulwari", "name": "Phulwari", "row": 1, "col": 0, "elevation_m": 54, "drainage_mm_h": 12, "population": 200000, "rainfall_factor": 1.06},
        {"id": "kankarbagh", "name": "Kankarbagh", "row": 1, "col": 1, "elevation_m": 52, "drainage_mm_h": 10, "population": 250000, "rainfall_factor": 1.1, "initial_water_m": 0.09},
        {"id": "gandhi_maidan", "name": "Gandhi Maidan", "row": 1, "col": 2, "elevation_m": 50, "drainage_mm_h": 9, "population": 120000, "rainfall_factor": 1.12, "is_coastal": True},
        {"id": "aniskur", "name": "Anisabad", "row": 2, "col": 0, "elevation_m": 56, "drainage_mm_h": 14, "population": 170000, "rainfall_factor": 1.04},
        {"id": "rajendra_nagar", "name": "Rajendra Nagar", "row": 2, "col": 1, "elevation_m": 53, "drainage_mm_h": 11, "population": 190000, "rainfall_factor": 1.07},
        {"id": "patliputra", "name": "Patliputra", "row": 2, "col": 2, "elevation_m": 49, "drainage_mm_h": 8, "population": 150000, "rainfall_factor": 1.15, "is_coastal": True, "initial_water_m": 0.11},
    ]
    canals = [
        {"id": "ganga", "name": "Ganga Front", "districts": ["digha", "gandhi_maidan", "patliputra"], "sea": [85.2, 25.62]},
        {"id": "punpun", "name": "Punpun Drain", "districts": ["danapur", "phulwari", "kankarbagh", "rajendra_nagar"], "sea": None},
    ]
    blockable = [
        {"id": "kankar_raj", "label": "Punpun Drain (Kankarbagh – Rajendra Nagar)", "edge": ("kankarbagh", "rajendra_nagar"), "canal_id": "punpun"},
        {"id": "gandhi_patli", "label": "Ganga Front (Gandhi Maidan – Patliputra)", "edge": ("gandhi_maidan", "patliputra"), "canal_id": "ganga"},
    ]
    return _grid_city(
        region_id="patna",
        city_name=info.city,
        state_name=info.state,
        origin_lon=85.05,
        origin_lat=25.64,
        cell_w=0.05,
        cell_h=0.04,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _kochi() -> City:
    info = REGION_CATALOG["kochi"]
    cells = [
        {"id": "edappally", "name": "Edappally", "row": 0, "col": 0, "elevation_m": 8, "drainage_mm_h": 12, "population": 140000, "rainfall_factor": 1.08},
        {"id": "kakkanad", "name": "Kakkanad", "row": 0, "col": 1, "elevation_m": 10, "drainage_mm_h": 14, "population": 120000, "rainfall_factor": 1.05},
        {"id": "vyttila", "name": "Vyttila", "row": 0, "col": 2, "elevation_m": 4, "drainage_mm_h": 9, "population": 110000, "rainfall_factor": 1.14, "is_coastal": True, "initial_water_m": 0.1},
        {"id": "kadavanthra", "name": "Kadavanthra", "row": 1, "col": 0, "elevation_m": 6, "drainage_mm_h": 11, "population": 100000, "rainfall_factor": 1.1},
        {"id": "ernakulam", "name": "Ernakulam", "row": 1, "col": 1, "elevation_m": 5, "drainage_mm_h": 10, "population": 160000, "rainfall_factor": 1.12, "is_coastal": True},
        {"id": "fort_kochi", "name": "Fort Kochi", "row": 1, "col": 2, "elevation_m": 3, "drainage_mm_h": 8, "population": 90000, "rainfall_factor": 1.18, "is_coastal": True, "initial_water_m": 0.12},
        {"id": "tripunithura", "name": "Tripunithura", "row": 2, "col": 0, "elevation_m": 9, "drainage_mm_h": 13, "population": 130000, "rainfall_factor": 1.06},
        {"id": "thevara", "name": "Thevara", "row": 2, "col": 1, "elevation_m": 4, "drainage_mm_h": 9, "population": 85000, "rainfall_factor": 1.15, "is_coastal": True},
        {"id": "willingdon", "name": "Willingdon Island", "row": 2, "col": 2, "elevation_m": 2, "drainage_mm_h": 7, "population": 40000, "rainfall_factor": 1.2, "is_coastal": True, "initial_water_m": 0.14},
    ]
    canals = [
        {"id": "backwater", "name": "Vembanad Backwater", "districts": ["vyttila", "ernakulam", "fort_kochi", "willingdon"], "sea": [76.24, 9.96]},
        {"id": "periyar_link", "name": "Periyar Link Drain", "districts": ["edappally", "kadavanthra", "thevara"], "sea": None},
    ]
    blockable = [
        {"id": "erna_fort", "label": "Backwater (Ernakulam – Fort Kochi)", "edge": ("ernakulam", "fort_kochi"), "canal_id": "backwater"},
        {"id": "kada_thevara", "label": "Periyar Link (Kadavanthra – Thevara)", "edge": ("kadavanthra", "thevara"), "canal_id": "periyar_link"},
    ]
    return _grid_city(
        region_id="kochi",
        city_name=info.city,
        state_name=info.state,
        origin_lon=76.28,
        origin_lat=10.05,
        cell_w=0.045,
        cell_h=0.035,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _surat() -> City:
    info = REGION_CATALOG["surat"]
    cells = [
        {"id": "adajan", "name": "Adajan", "row": 0, "col": 0, "elevation_m": 12, "drainage_mm_h": 13, "population": 220000, "rainfall_factor": 1.05},
        {"id": "vesu", "name": "Vesu", "row": 0, "col": 1, "elevation_m": 10, "drainage_mm_h": 12, "population": 180000, "rainfall_factor": 1.08},
        {"id": "katargam", "name": "Katargam", "row": 0, "col": 2, "elevation_m": 11, "drainage_mm_h": 11, "population": 200000, "rainfall_factor": 1.07},
        {"id": "athwa", "name": "Athwa", "row": 1, "col": 0, "elevation_m": 8, "drainage_mm_h": 10, "population": 190000, "rainfall_factor": 1.12, "is_coastal": True},
        {"id": "ring_road", "name": "Ring Road", "row": 1, "col": 1, "elevation_m": 9, "drainage_mm_h": 11, "population": 160000, "rainfall_factor": 1.1},
        {"id": "varachha", "name": "Varachha", "row": 1, "col": 2, "elevation_m": 10, "drainage_mm_h": 12, "population": 240000, "rainfall_factor": 1.06},
        {"id": "udhna", "name": "Udhna", "row": 2, "col": 0, "elevation_m": 7, "drainage_mm_h": 9, "population": 210000, "rainfall_factor": 1.14, "initial_water_m": 0.09},
        {"id": "mahim", "name": "Nanpura", "row": 2, "col": 1, "elevation_m": 6, "drainage_mm_h": 8, "population": 150000, "rainfall_factor": 1.16, "is_coastal": True, "initial_water_m": 0.11},
        {"id": "sachin", "name": "Sachin", "row": 2, "col": 2, "elevation_m": 8, "drainage_mm_h": 10, "population": 170000, "rainfall_factor": 1.1},
    ]
    canals = [
        {"id": "tapi", "name": "Tapi River", "districts": ["katargam", "ring_road", "mahim"], "sea": [72.8, 21.14]},
        {"id": "creek", "name": "Mindhola Creek", "districts": ["athwa", "udhna", "sachin"], "sea": [72.78, 21.1]},
    ]
    blockable = [
        {"id": "ring_nan", "label": "Tapi River (Ring Road – Nanpura)", "edge": ("ring_road", "mahim"), "canal_id": "tapi"},
        {"id": "athwa_udhna", "label": "Mindhola Creek (Athwa – Udhna)", "edge": ("athwa", "udhna"), "canal_id": "creek"},
    ]
    return _grid_city(
        region_id="surat",
        city_name=info.city,
        state_name=info.state,
        origin_lon=72.75,
        origin_lat=21.24,
        cell_w=0.05,
        cell_h=0.04,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _visakhapatnam() -> City:
    info = REGION_CATALOG["visakhapatnam"]
    cells = [
        {"id": "madhurawada", "name": "Madhurawada", "row": 0, "col": 0, "elevation_m": 45, "drainage_mm_h": 15, "population": 160000, "rainfall_factor": 1.02},
        {"id": "mvp", "name": "MVP Colony", "row": 0, "col": 1, "elevation_m": 25, "drainage_mm_h": 13, "population": 180000, "rainfall_factor": 1.06},
        {"id": "rushikonda", "name": "Rushikonda", "row": 0, "col": 2, "elevation_m": 12, "drainage_mm_h": 10, "population": 90000, "rainfall_factor": 1.14, "is_coastal": True},
        {"id": "gajuwaka", "name": "Gajuwaka", "row": 1, "col": 0, "elevation_m": 30, "drainage_mm_h": 12, "population": 250000, "rainfall_factor": 1.08},
        {"id": "dwaraka", "name": "Dwaraka Nagar", "row": 1, "col": 1, "elevation_m": 18, "drainage_mm_h": 11, "population": 140000, "rainfall_factor": 1.1},
        {"id": "rk_beach", "name": "RK Beach", "row": 1, "col": 2, "elevation_m": 6, "drainage_mm_h": 8, "population": 110000, "rainfall_factor": 1.18, "is_coastal": True, "initial_water_m": 0.1},
        {"id": "anakapalle", "name": "Anakapalle", "row": 2, "col": 0, "elevation_m": 35, "drainage_mm_h": 14, "population": 150000, "rainfall_factor": 1.04},
        {"id": "kancharapalem", "name": "Kancharapalem", "row": 2, "col": 1, "elevation_m": 15, "drainage_mm_h": 9, "population": 170000, "rainfall_factor": 1.12, "initial_water_m": 0.08},
        {"id": "harbour", "name": "Harbour", "row": 2, "col": 2, "elevation_m": 4, "drainage_mm_h": 7, "population": 80000, "rainfall_factor": 1.2, "is_coastal": True, "initial_water_m": 0.12},
    ]
    canals = [
        {"id": "coast", "name": "Bay Front Drain", "districts": ["rushikonda", "rk_beach", "harbour"], "sea": [83.32, 17.68]},
        {"id": "meghadri", "name": "Meghadri Gedda", "districts": ["gajuwaka", "dwaraka", "kancharapalem"], "sea": None},
    ]
    blockable = [
        {"id": "rk_harbour", "label": "Bay Front (RK Beach – Harbour)", "edge": ("rk_beach", "harbour"), "canal_id": "coast"},
        {"id": "dwaraka_kanch", "label": "Meghadri Gedda (Dwaraka – Kancharapalem)", "edge": ("dwaraka", "kancharapalem"), "canal_id": "meghadri"},
    ]
    return _grid_city(
        region_id="visakhapatnam",
        city_name=info.city,
        state_name=info.state,
        origin_lon=83.18,
        origin_lat=17.82,
        cell_w=0.055,
        cell_h=0.045,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _bhubaneswar() -> City:
    info = REGION_CATALOG["bhubaneswar"]
    cells = [
        {"id": "chandrasekharpur", "name": "Chandrasekharpur", "row": 0, "col": 0, "elevation_m": 45, "drainage_mm_h": 14, "population": 160000, "rainfall_factor": 1.04},
        {"id": "patia", "name": "Patia", "row": 0, "col": 1, "elevation_m": 42, "drainage_mm_h": 13, "population": 140000, "rainfall_factor": 1.06},
        {"id": "rasulgarh", "name": "Rasulgarh", "row": 0, "col": 2, "elevation_m": 38, "drainage_mm_h": 11, "population": 120000, "rainfall_factor": 1.1},
        {"id": "saheed_nagar", "name": "Saheed Nagar", "row": 1, "col": 0, "elevation_m": 40, "drainage_mm_h": 12, "population": 130000, "rainfall_factor": 1.08},
        {"id": "unit_1", "name": "Unit-1", "row": 1, "col": 1, "elevation_m": 36, "drainage_mm_h": 10, "population": 110000, "rainfall_factor": 1.12, "initial_water_m": 0.08},
        {"id": "laxmisagar", "name": "Laxmisagar", "row": 1, "col": 2, "elevation_m": 32, "drainage_mm_h": 9, "population": 150000, "rainfall_factor": 1.14, "initial_water_m": 0.09},
        {"id": "khandagiri", "name": "Khandagiri", "row": 2, "col": 0, "elevation_m": 55, "drainage_mm_h": 16, "population": 100000, "rainfall_factor": 0.98},
        {"id": "old_town", "name": "Old Town", "row": 2, "col": 1, "elevation_m": 34, "drainage_mm_h": 10, "population": 125000, "rainfall_factor": 1.11},
        {"id": "cuttack_road", "name": "Cuttack Road", "row": 2, "col": 2, "elevation_m": 28, "drainage_mm_h": 8, "population": 180000, "rainfall_factor": 1.16, "initial_water_m": 0.11},
    ]
    canals = [
        {"id": "daya", "name": "Daya River", "districts": ["laxmisagar", "old_town", "cuttack_road"], "sea": None},
        {"id": "kuakhai", "name": "Kuakhai Link", "districts": ["patia", "unit_1", "laxmisagar"], "sea": None},
    ]
    blockable = [
        {"id": "unit_laxmi", "label": "Kuakhai Link (Unit-1 – Laxmisagar)", "edge": ("unit_1", "laxmisagar"), "canal_id": "kuakhai"},
        {"id": "old_cuttack", "label": "Daya River (Old Town – Cuttack Road)", "edge": ("old_town", "cuttack_road"), "canal_id": "daya"},
    ]
    return _grid_city(
        region_id="bhubaneswar",
        city_name=info.city,
        state_name=info.state,
        origin_lon=85.78,
        origin_lat=20.36,
        cell_w=0.05,
        cell_h=0.04,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _srinagar() -> City:
    info = REGION_CATALOG["srinagar"]
    cells = [
        {"id": "hazratbal", "name": "Hazratbal", "row": 0, "col": 0, "elevation_m": 1585, "drainage_mm_h": 10, "population": 90000, "rainfall_factor": 1.1, "is_coastal": True},
        {"id": "nishat", "name": "Nishat", "row": 0, "col": 1, "elevation_m": 1590, "drainage_mm_h": 11, "population": 70000, "rainfall_factor": 1.08},
        {"id": "shankaracharya", "name": "Shankaracharya", "row": 0, "col": 2, "elevation_m": 1650, "drainage_mm_h": 14, "population": 40000, "rainfall_factor": 0.95},
        {"id": "lal_chowk", "name": "Lal Chowk", "row": 1, "col": 0, "elevation_m": 1582, "drainage_mm_h": 9, "population": 120000, "rainfall_factor": 1.14, "initial_water_m": 0.1},
        {"id": "rajbagh", "name": "Rajbagh", "row": 1, "col": 1, "elevation_m": 1580, "drainage_mm_h": 8, "population": 110000, "rainfall_factor": 1.16, "initial_water_m": 0.12},
        {"id": "jawahar_nagar", "name": "Jawahar Nagar", "row": 1, "col": 2, "elevation_m": 1584, "drainage_mm_h": 10, "population": 95000, "rainfall_factor": 1.12},
        {"id": "bemina", "name": "Bemina", "row": 2, "col": 0, "elevation_m": 1583, "drainage_mm_h": 9, "population": 130000, "rainfall_factor": 1.13, "initial_water_m": 0.09},
        {"id": "batamaloo", "name": "Batamaloo", "row": 2, "col": 1, "elevation_m": 1581, "drainage_mm_h": 8, "population": 100000, "rainfall_factor": 1.15, "initial_water_m": 0.11},
        {"id": "pantha_chowk", "name": "Pantha Chowk", "row": 2, "col": 2, "elevation_m": 1586, "drainage_mm_h": 11, "population": 85000, "rainfall_factor": 1.08},
    ]
    canals = [
        {"id": "jhelum", "name": "Jhelum River", "districts": ["hazratbal", "lal_chowk", "bemina", "batamaloo"], "sea": None},
        {"id": "dal_outfall", "name": "Dal Lake Outfall", "districts": ["nishat", "rajbagh", "jawahar_nagar"], "sea": None},
    ]
    blockable = [
        {"id": "lal_bemina", "label": "Jhelum River (Lal Chowk – Bemina)", "edge": ("lal_chowk", "bemina"), "canal_id": "jhelum"},
        {"id": "raj_jawa", "label": "Dal Outfall (Rajbagh – Jawahar Nagar)", "edge": ("rajbagh", "jawahar_nagar"), "canal_id": "dal_outfall"},
    ]
    return _grid_city(
        region_id="srinagar",
        city_name=info.city,
        state_name=info.state,
        origin_lon=74.78,
        origin_lat=34.12,
        cell_w=0.04,
        cell_h=0.03,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _alappuzha() -> City:
    info = REGION_CATALOG["alappuzha"]
    cells = [
        {"id": "punnamada", "name": "Punnamada", "row": 0, "col": 0, "elevation_m": 1, "drainage_mm_h": 6, "population": 70000, "rainfall_factor": 1.2, "is_coastal": True, "initial_water_m": 0.15},
        {"id": "finishing", "name": "Finishing Point", "row": 0, "col": 1, "elevation_m": 2, "drainage_mm_h": 7, "population": 55000, "rainfall_factor": 1.18, "is_coastal": True, "initial_water_m": 0.13},
        {"id": "thanneermukkom", "name": "Thanneermukkom", "row": 0, "col": 2, "elevation_m": 1, "drainage_mm_h": 5, "population": 60000, "rainfall_factor": 1.22, "is_coastal": True, "initial_water_m": 0.16},
        {"id": "kuttanad_north", "name": "Kuttanad North", "row": 1, "col": 0, "elevation_m": -1, "drainage_mm_h": 4, "population": 80000, "rainfall_factor": 1.25, "initial_water_m": 0.18},
        {"id": "alappuzha_town", "name": "Alappuzha Town", "row": 1, "col": 1, "elevation_m": 3, "drainage_mm_h": 8, "population": 110000, "rainfall_factor": 1.15, "is_coastal": True},
        {"id": "kainakary", "name": "Kainakary", "row": 1, "col": 2, "elevation_m": -2, "drainage_mm_h": 3, "population": 45000, "rainfall_factor": 1.28, "initial_water_m": 0.2},
        {"id": "ambalamoghi", "name": "Ambalappuzha", "row": 2, "col": 0, "elevation_m": 2, "drainage_mm_h": 7, "population": 75000, "rainfall_factor": 1.16},
        {"id": "punnapra", "name": "Punnapra", "row": 2, "col": 1, "elevation_m": 1, "drainage_mm_h": 6, "population": 90000, "rainfall_factor": 1.2, "is_coastal": True, "initial_water_m": 0.14},
        {"id": "kuttanad_south", "name": "Kuttanad South", "row": 2, "col": 2, "elevation_m": -1, "drainage_mm_h": 4, "population": 65000, "rainfall_factor": 1.24, "initial_water_m": 0.17},
    ]
    canals = [
        {"id": "vembanad", "name": "Vembanad Lake", "districts": ["punnamada", "finishing", "thanneermukkom"], "sea": [76.35, 9.5]},
        {"id": "pamba", "name": "Pamba / AC Canal", "districts": ["kuttanad_north", "alappuzha_town", "kainakary", "kuttanad_south"], "sea": None},
    ]
    blockable = [
        {"id": "north_town", "label": "Pamba Canal (Kuttanad North – Town)", "edge": ("kuttanad_north", "alappuzha_town"), "canal_id": "pamba"},
        {"id": "town_kaina", "label": "Pamba Canal (Town – Kainakary)", "edge": ("alappuzha_town", "kainakary"), "canal_id": "pamba"},
    ]
    return _grid_city(
        region_id="alappuzha",
        city_name=info.city,
        state_name=info.state,
        origin_lon=76.32,
        origin_lat=9.55,
        cell_w=0.04,
        cell_h=0.03,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _vadodara() -> City:
    info = REGION_CATALOG["vadodara"]
    cells = [
        {"id": "gotri", "name": "Gotri", "row": 0, "col": 0, "elevation_m": 42, "drainage_mm_h": 13, "population": 150000, "rainfall_factor": 1.05},
        {"id": "fatehgunj", "name": "Fatehgunj", "row": 0, "col": 1, "elevation_m": 38, "drainage_mm_h": 11, "population": 120000, "rainfall_factor": 1.1},
        {"id": "nalanda", "name": "Nizampura", "row": 0, "col": 2, "elevation_m": 40, "drainage_mm_h": 12, "population": 140000, "rainfall_factor": 1.06},
        {"id": "alkapuri", "name": "Alkapuri", "row": 1, "col": 0, "elevation_m": 39, "drainage_mm_h": 12, "population": 130000, "rainfall_factor": 1.08},
        {"id": "sayajigunj", "name": "Sayajigunj", "row": 1, "col": 1, "elevation_m": 35, "drainage_mm_h": 9, "population": 160000, "rainfall_factor": 1.14, "initial_water_m": 0.09},
        {"id": "manjalpur", "name": "Manjalpur", "row": 1, "col": 2, "elevation_m": 33, "drainage_mm_h": 8, "population": 180000, "rainfall_factor": 1.16, "initial_water_m": 0.1},
        {"id": "akota", "name": "Akota", "row": 2, "col": 0, "elevation_m": 41, "drainage_mm_h": 14, "population": 145000, "rainfall_factor": 1.04},
        {"id": "kala_ghoda", "name": "Kala Ghoda", "row": 2, "col": 1, "elevation_m": 34, "drainage_mm_h": 9, "population": 110000, "rainfall_factor": 1.13},
        {"id": "tandalja", "name": "Tandalja", "row": 2, "col": 2, "elevation_m": 32, "drainage_mm_h": 7, "population": 155000, "rainfall_factor": 1.18, "initial_water_m": 0.12},
    ]
    canals = [
        {"id": "vishwamitri", "name": "Vishwamitri River", "districts": ["fatehgunj", "sayajigunj", "kala_ghoda", "tandalja"], "sea": None},
        {"id": "bhukhi", "name": "Bhukhi Nala", "districts": ["gotri", "alkapuri", "akota"], "sea": None},
    ]
    blockable = [
        {"id": "saya_kala", "label": "Vishwamitri (Sayajigunj – Kala Ghoda)", "edge": ("sayajigunj", "kala_ghoda"), "canal_id": "vishwamitri"},
        {"id": "kala_tand", "label": "Vishwamitri (Kala Ghoda – Tandalja)", "edge": ("kala_ghoda", "tandalja"), "canal_id": "vishwamitri"},
    ]
    return _grid_city(
        region_id="vadodara",
        city_name=info.city,
        state_name=info.state,
        origin_lon=73.14,
        origin_lat=22.34,
        cell_w=0.05,
        cell_h=0.04,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


def _mangaluru() -> City:
    info = REGION_CATALOG["mangaluru"]
    cells = [
        {"id": "surathkal", "name": "Surathkal", "row": 0, "col": 0, "elevation_m": 18, "drainage_mm_h": 13, "population": 120000, "rainfall_factor": 1.1, "is_coastal": True},
        {"id": "kavoor", "name": "Kavoor", "row": 0, "col": 1, "elevation_m": 22, "drainage_mm_h": 14, "population": 90000, "rainfall_factor": 1.06},
        {"id": "bajpe", "name": "Bajpe", "row": 0, "col": 2, "elevation_m": 80, "drainage_mm_h": 16, "population": 70000, "rainfall_factor": 1.0},
        {"id": "hampankatta", "name": "Hampankatta", "row": 1, "col": 0, "elevation_m": 12, "drainage_mm_h": 10, "population": 140000, "rainfall_factor": 1.14, "is_coastal": True},
        {"id": "kadri", "name": "Kadri", "row": 1, "col": 1, "elevation_m": 28, "drainage_mm_h": 12, "population": 110000, "rainfall_factor": 1.08},
        {"id": "kulshekar", "name": "Kulshekar", "row": 1, "col": 2, "elevation_m": 35, "drainage_mm_h": 13, "population": 95000, "rainfall_factor": 1.05},
        {"id": "ullal", "name": "Ullal", "row": 2, "col": 0, "elevation_m": 6, "drainage_mm_h": 7, "population": 130000, "rainfall_factor": 1.2, "is_coastal": True, "initial_water_m": 0.12},
        {"id": "pumpwell", "name": "Pumpwell", "row": 2, "col": 1, "elevation_m": 15, "drainage_mm_h": 9, "population": 100000, "rainfall_factor": 1.12, "initial_water_m": 0.08},
        {"id": "bc_road", "name": "BC Road", "row": 2, "col": 2, "elevation_m": 20, "drainage_mm_h": 11, "population": 85000, "rainfall_factor": 1.07},
    ]
    canals = [
        {"id": "netravati", "name": "Netravati River", "districts": ["ullal", "pumpwell", "bc_road"], "sea": [74.84, 12.84]},
        {"id": "gurupura", "name": "Gurupura River", "districts": ["surathkal", "hampankatta", "ullal"], "sea": [74.82, 12.88]},
    ]
    blockable = [
        {"id": "ullal_pump", "label": "Netravati (Ullal – Pumpwell)", "edge": ("ullal", "pumpwell"), "canal_id": "netravati"},
        {"id": "hampa_ullal", "label": "Gurupura (Hampankatta – Ullal)", "edge": ("hampankatta", "ullal"), "canal_id": "gurupura"},
    ]
    return _grid_city(
        region_id="mangaluru",
        city_name=info.city,
        state_name=info.state,
        origin_lon=74.8,
        origin_lat=12.98,
        cell_w=0.05,
        cell_h=0.04,
        cells=cells,
        canals=canals,
        blockable=blockable,
    )


_LOADERS = {
    "chennai": lambda: _load_chennai(DATA_DIR),
    "mumbai": _mumbai,
    "delhi": _delhi,
    "kolkata": _kolkata,
    "guwahati": _guwahati,
    "hyderabad": _hyderabad,
    "bengaluru": _bengaluru,
    "patna": _patna,
    "kochi": _kochi,
    "surat": _surat,
    "visakhapatnam": _visakhapatnam,
    "bhubaneswar": _bhubaneswar,
    "srinagar": _srinagar,
    "alappuzha": _alappuzha,
    "vadodara": _vadodara,
    "mangaluru": _mangaluru,
}


def load_city(region_id: str | None = None, data_dir: Path | None = None) -> City:
    rid = (region_id or "chennai").strip().lower()
    if rid not in _LOADERS:
        rid = "chennai"
    if rid == "chennai":
        return _load_chennai(data_dir or DATA_DIR)
    return _LOADERS[rid]()
