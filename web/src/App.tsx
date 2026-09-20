import { useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  clockLabel,
  fetchRegions,
  fetchScenarios,
  minutesEta,
  runSimulation,
  STATUS_COLOR,
  STATUS_LABEL,
  type RegionInfo,
  type ScenarioInfo,
  type SimResult,
} from './api'
import { FloodMap } from './FloodMap'
import { movementSummary, waterSourceSlices } from './hydrology'
import 'leaflet/dist/leaflet.css'
import './App.css'

function App() {
  const [regions, setRegions] = useState<RegionInfo[]>([])
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [regionId, setRegionId] = useState('chennai')
  const [preset, setPreset] = useState('Extreme flood')
  const [result, setResult] = useState<SimResult | null>(null)
  const [tIdx, setTIdx] = useState(0)
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    Promise.all([fetchRegions(), fetchScenarios()])
      .then(([r, s]) => {
        setRegions(r)
        setScenarios(s)
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  const simulate = async (rid = regionId, p = preset) => {
    setLoading(true)
    setError(null)
    setPlaying(false)
    try {
      const data = await runSimulation({ region_id: rid, preset: p })
      setResult(data)
      setTIdx(data.peak_hazard_index)
      setSelectedId(data.districts[0]?.id ?? '')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void simulate()
    // initial load only
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!playing || !result) return
    const id = window.setInterval(() => {
      setTIdx((t) => {
        if (t >= result.times_h.length - 1) {
          setPlaying(false)
          return t
        }
        return t + 1
      })
    }, 700)
    return () => window.clearInterval(id)
  }, [playing, result])

  const selectedIdx = useMemo(() => {
    if (!result) return 0
    const i = result.districts.findIndex((d) => d.id === selectedId)
    return i >= 0 ? i : 0
  }, [result, selectedId])

  const chartData = useMemo(() => {
    if (!result) return []
    return result.times_h.map((h, i) => ({
      t: Number(h.toFixed(2)),
      depth: result.water[i][selectedIdx],
    }))
  }, [result, selectedIdx])

  const sourceSlices = useMemo(() => {
    if (!result) return []
    return waterSourceSlices(result, selectedIdx, tIdx)
  }, [result, selectedIdx, tIdx])

  const move = useMemo(() => {
    if (!result) return null
    return movementSummary(result, selectedIdx, tIdx)
  }, [result, selectedIdx, tIdx])

  const sourceTotal = useMemo(
    () => sourceSlices.reduce((s, x) => s + x.value, 0) || 1,
    [sourceSlices],
  )

  if (!result && loading) {
    return <div className="boot">Running NumPy flood simulation…</div>
  }

  if (error && !result) {
    return (
      <div className="boot error">
        <p>{error}</p>
        <p className="hint">Start the API: py -3 -m uvicorn api.main:app --reload --port 8000</p>
      </div>
    )
  }

  if (!result) return null

  const hours = result.times_h[tIdx]
  const d = result.districts[selectedIdx]
  const depth = result.water[tIdx][selectedIdx]
  const status = result.status[tIdx][selectedIdx]
  const counts = result.counts[tIdx]

  return (
    <div className="app">
      <header className="top">
        <div>
          <div className="logo">
            <span>◆</span> FLOWSHIELD
          </div>
          <div className="sub">
            {result.city_name}, {result.state_name} · Python/NumPy engine · React viz
          </div>
        </div>
        <div className="top-controls">
          <label className="city-search-label" htmlFor="city-select">
            Search cities
          </label>
          <select
            id="city-select"
            value={regionId}
            onChange={(e) => {
              const id = e.target.value
              setRegionId(id)
              void simulate(id, preset)
            }}
          >
            {regions.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="layout">
        <aside className="panel left">
          <div className="panel-title">SCENARIO</div>
          <div className="scenario-list">
            {scenarios.map((s) => (
              <button
                key={s.preset}
                type="button"
                className={preset === s.preset ? 'active' : ''}
                onClick={() => {
                  setPreset(s.preset)
                  void simulate(regionId, s.preset)
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
          <p className="caption">{scenarios.find((s) => s.preset === preset)?.description}</p>
          <button type="button" className="primary" disabled={loading} onClick={() => void simulate()}>
            {loading ? 'Simulating…' : 'Run simulation'}
          </button>
        </aside>

        <main className="center">
          <FloodMap
            result={result}
            tIdx={tIdx}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <div className="timeline">
            <button type="button" onClick={() => setPlaying((p) => !p)}>
              {playing ? 'Pause' : 'Play'}
            </button>
            <button
              type="button"
              onClick={() => {
                setPlaying(false)
                setTIdx(0)
              }}
            >
              Reset
            </button>
            <div className="clock">{clockLabel(hours)}</div>
            <input
              type="range"
              min={0}
              max={result.times_h.length - 1}
              value={tIdx}
              onChange={(e) => {
                setPlaying(false)
                setTIdx(Number(e.target.value))
              }}
            />
            <div className="counts">
              Safe {counts.Safe} · Warning {counts.Warning} · Critical {counts.Critical} · Affected{' '}
              {result.affected_population[tIdx].toLocaleString()}
            </div>
          </div>
        </main>

        <aside className="panel right">
          <div className="panel-title">SELECTED REGION</div>
          <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
            {result.districts.map((x) => (
              <option key={x.id} value={x.id}>
                {x.name}
              </option>
            ))}
          </select>
          <div className="hazard" style={{ borderColor: `${STATUS_COLOR[status]}66` }}>
            <div className="district-name">{d.name}</div>
            <div className="place">
              {result.city_name}, {result.state_name}
            </div>
            <div className="k">FLOOD RISK</div>
            <div className="status" style={{ color: STATUS_COLOR[status] }}>
              {STATUS_LABEL[status]}
            </div>
            <div className="k">CURRENT WATER LEVEL</div>
            <div className="depth">
              {depth.toFixed(2)}
              <span> m</span>
            </div>
          </div>
          <div className="panel-title-sm">Early warning</div>
          <div className="row">
            <span>Time to warning</span>
            <strong>{minutesEta(d.time_to_warning_h, hours)}</strong>
          </div>
          <div className="row">
            <span>Time to critical</span>
            <strong>{minutesEta(d.time_to_critical_h, hours)}</strong>
          </div>
          <div className="panel-title-sm">Conditions</div>
          <div className="grid2">
            <div>
              <div className="k">Elevation</div>
              <div>{d.elevation_m.toFixed(1)} m</div>
            </div>
            <div>
              <div className="k">Drainage</div>
              <div>{(d.drainage_mm_h * result.drainage_scale).toFixed(0)} mm/h</div>
            </div>
            <div>
              <div className="k">Population</div>
              <div>{d.population.toLocaleString()}</div>
            </div>
            <div>
              <div className="k">Rainfall</div>
              <div>{result.rainfall_mm_h.toFixed(0)} mm/h</div>
            </div>
          </div>
        </aside>
      </div>

      <section className="hydro panel">
        <div className="panel-title">REGION HYDROLOGY · {d.name}</div>
        <div className="hydro-row">
          <div className="hydro-col">
            <div className="panel-title-sm">Water level over time</div>
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData}>
                  <CartesianGrid stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="t" stroke="#8ea0b8" tickFormatter={(v) => `${v}h`} />
                  <YAxis stroke="#8ea0b8" unit=" m" />
                  <RTooltip />
                  <Line type="monotone" dataKey="depth" stroke="#4cc3ff" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="hydro-col">
            <div className="panel-title-sm">Water sources</div>
            <p className="caption">Model-derived contribution estimate at this hour</p>
            <div className="chart-wrap pie-wrap">
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={sourceSlices}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={48}
                    outerRadius={78}
                    paddingAngle={2}
                  >
                    {sourceSlices.map((s) => (
                      <Cell key={s.name} fill={s.color} stroke="#0b1220" strokeWidth={2} />
                    ))}
                  </Pie>
                  <RTooltip
                    formatter={(value) => {
                      const n = typeof value === 'number' ? value : Number(value)
                      return [`${n.toFixed(2)} m`, 'Depth-equivalent']
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="src-legend">
              {sourceSlices.map((s) => (
                <div key={s.name} className="src-row">
                  <span>
                    <span className="src-dot" style={{ background: s.color }} />
                    {s.name}
                  </span>
                  <span>
                    {s.value.toFixed(2)} m · {Math.round((100 * s.value) / sourceTotal)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="panel-title-sm">Water movement</div>
        {move && (
          <>
            <div className="grid2 move-totals">
              <div>
                <div className="k">Incoming</div>
                <div>{move.inM3s.toFixed(1)} m³/s</div>
              </div>
              <div>
                <div className="k">Outgoing</div>
                <div>{move.outM3s.toFixed(1)} m³/s</div>
              </div>
            </div>
            <div className="move-cols">
              <div>
                {move.from.length === 0 ? (
                  <p className="caption">No incoming neighbour flow at this hour.</p>
                ) : (
                  move.from.map((r) => (
                    <div key={`in-${r.neighbor}`} className="move-chip">
                      From: {r.neighbor} · {r.magnitude.toFixed(1)} m³/s
                    </div>
                  ))
                )}
              </div>
              <div>
                {move.to.length === 0 ? (
                  <p className="caption">No outgoing neighbour flow at this hour.</p>
                ) : (
                  move.to.map((r) => (
                    <div key={`out-${r.neighbor}`} className="move-chip">
                      To: {r.neighbor} · {r.magnitude.toFixed(1)} m³/s
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  )
}

export default App
