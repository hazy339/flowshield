import type { SimResult } from './api'

export type SourceSlice = { name: string; value: number; color: string }

export function waterSourceSlices(result: SimResult, idx: number, tIdx: number): SourceSlice[] {
  const d = result.districts[idx]
  const depth = result.water[tIdx][idx]
  const rainH = result.config.rain_duration_h || result.config.duration_h
  const elapsed = result.times_h[tIdx]
  const wet = Math.min(elapsed, rainH)
  const runoff = result.config.runoff ?? 0.92
  const rainIn =
    (result.config.rainfall_mm_h / 1000) * runoff * d.rainfall_factor * wet
  let drainOut = (d.drainage_mm_h / 1000) * result.config.drainage_scale * elapsed
  if (result.failed_districts.includes(d.id)) drainOut = 0
  const initial = d.initial_water_m * result.config.initial_scale
  const residual = Math.max(0, depth - Math.max(0, rainIn + initial - drainOut))

  const items: SourceSlice[] = [
    { name: 'Rainfall', value: Math.max(0, rainIn), color: '#4cc3ff' },
    { name: 'Upstream flow', value: Math.max(0, residual), color: '#f5a623' },
    { name: 'Initial stored', value: Math.max(0, initial), color: '#9b8cff' },
  ].filter((x) => x.value > 1e-6)

  if (!items.length) {
    return [{ name: 'No standing water', value: 1, color: '#3a465c' }]
  }
  return items
}

export type MoveChip = { neighbor: string; magnitude: number }

export function movementSummary(result: SimResult, idx: number, tIdx: number) {
  const did = result.districts[idx].id
  const flows = result.flow_m3s[tIdx]
  const incoming: MoveChip[] = []
  const outgoing: MoveChip[] = []
  let inM3s = 0
  let outM3s = 0

  result.flow_edges.forEach(([a, b], e) => {
    const f = flows[e]
    if (Math.abs(f) <= 1e-6) return
    if (a === did) {
      // F>0 means a→b (outgoing from this district)
      const neighbor = result.districts.find((d) => d.id === b)?.name ?? b
      const mag = Math.abs(f)
      if (f > 0) {
        outgoing.push({ neighbor, magnitude: mag })
        outM3s += mag
      } else {
        incoming.push({ neighbor, magnitude: mag })
        inM3s += mag
      }
    } else if (b === did) {
      // From b's view, outgoing is -F
      const neighbor = result.districts.find((d) => d.id === a)?.name ?? a
      const mag = Math.abs(f)
      const signed = -f
      if (signed > 0) {
        outgoing.push({ neighbor, magnitude: mag })
        outM3s += mag
      } else {
        incoming.push({ neighbor, magnitude: mag })
        inM3s += mag
      }
    }
  })

  incoming.sort((x, y) => y.magnitude - x.magnitude)
  outgoing.sort((x, y) => y.magnitude - x.magnitude)
  return {
    inM3s,
    outM3s,
    from: incoming.slice(0, 3),
    to: outgoing.slice(0, 3),
  }
}
