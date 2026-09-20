export type RegionInfo = {
  id: string
  city: string
  state: string
  label: string
  description: string
}

export type ScenarioInfo = {
  label: string
  preset: string
  description: string
}

export type DistrictInfo = {
  id: string
  name: string
  lat: number
  lon: number
  elevation_m: number
  drainage_mm_h: number
  population: number
  coastal: boolean
  rainfall_factor: number
  initial_water_m: number
  time_to_warning_h: number | null
  time_to_critical_h: number | null
}

export type SimResult = {
  region_id: string
  city_name: string
  state_name: string
  label: string
  times_h: number[]
  warning_m: number
  critical_m: number
  rainfall_mm_h: number
  drainage_scale: number
  districts: DistrictInfo[]
  water: number[][]
  status: number[][]
  flow_edges: [string, string][]
  flow_m3s: number[][]
  counts: { Safe: number; Warning: number; Critical: number }[]
  affected_population: number[]
  peak_hazard_index: number
  first_critical_hour: number | null
  geojson: {
    type: string
    features: {
      type: string
      properties?: { id?: string }
      geometry?: { type: string; coordinates: unknown }
    }[]
  }
  canal_paths: { id: string; name: string; districts: string[]; coords: [number, number][] }[]
  blockable_channels: { label: string; edge: [string, string] }[]
  failed_districts: string[]
  blocked_edges: [string, string][]
  config: {
    rainfall_mm_h: number
    duration_h: number
    rain_duration_h: number
    drainage_scale: number
    initial_scale: number
    runoff: number
  }
}

export const STATUS_LABEL = ['Safe', 'Warning', 'Critical'] as const
export const STATUS_COLOR = ['#1ee0ac', '#f5a623', '#e74c3c'] as const

const BASE = ''

export async function fetchRegions(): Promise<RegionInfo[]> {
  const r = await fetch(`${BASE}/api/regions`)
  if (!r.ok) throw new Error('Failed to load regions')
  return r.json()
}

export async function fetchScenarios(): Promise<ScenarioInfo[]> {
  const r = await fetch(`${BASE}/api/scenarios`)
  if (!r.ok) throw new Error('Failed to load scenarios')
  return r.json()
}

export async function runSimulation(body: {
  region_id: string
  preset: string
}): Promise<SimResult> {
  const r = await fetch(`${BASE}/api/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) {
    const detail = await r.text()
    throw new Error(detail || 'Simulation failed')
  }
  return r.json()
}

export function clockLabel(hours: number): string {
  const h = Math.floor(hours)
  const m = Math.round((hours - h) * 60)
  return `T+${h}h ${String(m).padStart(2, '0')}m`
}

export function minutesEta(target: number | null, now: number): string {
  if (target == null || Number.isNaN(target)) return 'Not reached'
  if (now + 1e-9 >= target) return 'Already reached'
  const mins = Math.max(0, (target - now) * 60)
  if (mins < 1) return '< 1 min'
  if (mins < 60) return `${Math.round(mins)} min`
  return `${(mins / 60).toFixed(1)} h`
}
