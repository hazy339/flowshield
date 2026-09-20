import { useEffect, useMemo } from 'react'
import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
} from 'react-leaflet'
import type { SimResult } from './api'
import { STATUS_COLOR, STATUS_LABEL } from './api'

type Props = {
  result: SimResult
  tIdx: number
  selectedId: string
  onSelect: (id: string) => void
}

type GJFeature = {
  type: string
  properties?: { id?: string }
  geometry?: {
    type: string
    coordinates: number[][][] | number[][][][]
  }
}

type GJCollection = {
  type: string
  features: GJFeature[]
}

function FitBounds({ geojson }: { geojson: GJCollection }) {
  const map = useMap()
  useEffect(() => {
    const coords: [number, number][] = []
    for (const f of geojson.features) {
      const g = f.geometry
      if (!g) continue
      if (g.type === 'Polygon') {
        for (const ring of g.coordinates as number[][][]) {
          for (const [lon, lat] of ring) coords.push([lat, lon])
        }
      } else if (g.type === 'MultiPolygon') {
        for (const poly of g.coordinates as number[][][][]) {
          for (const ring of poly) {
            for (const [lon, lat] of ring) coords.push([lat, lon])
          }
        }
      }
    }
    if (coords.length) {
      map.fitBounds(coords, { padding: [28, 28] })
    }
  }, [geojson, map])
  return null
}

function fillForStatus(status: number, depth: number): string {
  if (status >= 2) return '#1a8cff'
  if (status >= 1) return '#2aa9ff'
  if (depth < 0.05) return 'transparent'
  return '#3ec7ff'
}

export function FloodMap({ result, tIdx, selectedId, onSelect }: Props) {
  const statusRow = result.status[tIdx]
  const waterRow = result.water[tIdx]
  const idToIndex = useMemo(() => {
    const m = new Map<string, number>()
    result.districts.forEach((d, i) => m.set(d.id, i))
    return m
  }, [result.districts])

  const styleFeature = (feature?: GJFeature) => {
    const id = String(feature?.properties?.id ?? '')
    const i = idToIndex.get(id)
    if (i == null) {
      return { fillOpacity: 0.02, color: '#fff', weight: 0.8, fillColor: '#fff' }
    }
    const st = statusRow[i]
    const depth = waterRow[i]
    const selected = id === selectedId
    return {
      fillColor: fillForStatus(st, depth),
      fillOpacity: depth < 0.05 && st < 1 ? 0.02 : 0.18 + Math.min(0.35, depth * 0.25),
      color: selected ? '#ffffff' : '#9ae0ff',
      weight: selected ? 2.4 : 0.9,
      opacity: 0.55,
    }
  }

  const flowLines = useMemo(() => {
    const flows = result.flow_m3s[tIdx]
    const abs = flows.map(Math.abs)
    const positive = abs.filter((v) => v > 1e-6).sort((a, b) => a - b)
    const ref = positive.length ? positive[Math.floor(positive.length * 0.88)] || positive[positive.length - 1] : 0
    const minF = ref > 0 ? 0.012 * ref : 1
    const lines: { key: string; positions: [number, number][]; weight: number; opacity: number }[] = []

    result.flow_edges.forEach((edge, e) => {
      const f = flows[e]
      const mag = Math.abs(f)
      if (mag < minF) return
      const [a, b] = edge
      const canal = result.canal_paths.find((c) => {
        const ids = c.districts
        for (let i = 0; i < ids.length - 1; i++) {
          if ((ids[i] === a && ids[i + 1] === b) || (ids[i] === b && ids[i + 1] === a)) return true
        }
        return false
      })
      let positions: [number, number][]
      if (canal && canal.coords.length >= 2) {
        positions = canal.coords.map(([lat, lon]) => [lat, lon] as [number, number])
        const da = result.districts.find((d) => d.id === a)
        const db = result.districts.find((d) => d.id === b)
        if (da && db) {
          const p0 = positions[0]
          const d0a = (p0[0] - da.lat) ** 2 + (p0[1] - da.lon) ** 2
          const d0b = (p0[0] - db.lat) ** 2 + (p0[1] - db.lon) ** 2
          if (d0b < d0a) positions = [...positions].reverse()
          if (f < 0) positions = [...positions].reverse()
        }
      } else {
        const da = result.districts.find((d) => d.id === a)
        const db = result.districts.find((d) => d.id === b)
        if (!da || !db) return
        positions =
          f >= 0
            ? [
                [da.lat, da.lon],
                [db.lat, db.lon],
              ]
            : [
                [db.lat, db.lon],
                [da.lat, da.lon],
              ]
      }
      const intensity = ref > 0 ? Math.min(1, (mag / ref) ** 0.75) : 0.4
      lines.push({
        key: `${a}-${b}-${e}`,
        positions,
        weight: 2 + 3.2 * intensity,
        opacity: 0.35 + 0.4 * intensity,
      })
    })
    return lines
  }, [result, tIdx])

  return (
    <MapContainer className="flood-map" center={[13.05, 80.24]} zoom={11} scrollWheelZoom>
      <TileLayer
        attribution="Google"
        url="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
        maxZoom={20}
      />
      <FitBounds geojson={result.geojson as GJCollection} />
      <GeoJSON
        key={`${result.region_id}-${tIdx}-${selectedId}`}
        data={result.geojson as never}
        style={styleFeature as never}
        onEachFeature={(feature, layer) => {
          const id = String((feature as GJFeature).properties?.id ?? '')
          const i = idToIndex.get(id)
          if (i == null) return
          layer.on('click', () => onSelect(id))
          layer.bindTooltip(
            `${result.districts[i].name} · ${waterRow[i].toFixed(2)} m · ${STATUS_LABEL[statusRow[i]]}`,
          )
        }}
      />
      {flowLines.map((line) => (
        <Polyline
          key={line.key}
          positions={line.positions}
          pathOptions={{
            color: '#7ec8ff',
            weight: line.weight,
            opacity: line.opacity,
            dashArray: '2 10',
          }}
        />
      ))}
      {result.districts.map((d, i) => (
        <CircleMarker
          key={d.id}
          center={[d.lat, d.lon]}
          radius={d.id === selectedId ? 9 : 7}
          pathOptions={{
            color: '#0b1220',
            weight: 1,
            fillColor: STATUS_COLOR[statusRow[i]],
            fillOpacity: 0.95,
          }}
          eventHandlers={{ click: () => onSelect(d.id) }}
        >
          <Tooltip direction="top" offset={[0, -8]} permanent={d.id === selectedId}>
            {d.name} · {waterRow[i].toFixed(2)} m
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
