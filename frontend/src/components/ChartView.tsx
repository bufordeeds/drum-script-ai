import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fileUrl, type HitsDoc, type JobResult } from '../api'
import { PlayerEngine, loadAudio, type SourceName } from '../lib/player'
import { Grid, formatTime } from '../lib/timing'
import Score, { type ScoreHandle } from './Score'

interface Props {
  jobId: string
  result: JobResult
}

const DRUM_LABEL: Record<string, string> = { kick: 'kick', snare: 'snare', hihat: 'hi-hat', tom: 'toms', cymbal: 'cymbals' }

export default function ChartView({ jobId, result }: Props) {
  const [doc, setDoc] = useState<HitsDoc | null>(null)
  const [xml, setXml] = useState<string | null>(null)
  const [engine, setEngine] = useState<PlayerEngine | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [audioState, setAudioState] = useState('Loading audio…')

  const [playing, setPlaying] = useState(false)
  const [source, setSource] = useState<SourceName>('mix')
  const [speed, setSpeed] = useState(100)
  const [click, setClick] = useState(false)
  const [countIn, setCountIn] = useState(true)
  const [loop, setLoop] = useState<{ from: number; to: number } | null>(null)

  const scoreRef = useRef<ScoreHandle>(null)
  const timeRef = useRef<HTMLSpanElement>(null)
  const barRef = useRef<HTMLSpanElement>(null)
  const grid = useMemo(() => (doc ? new Grid(doc) : null), [doc])

  // chart data
  useEffect(() => {
    let cancelled = false
    Promise.all([
      fetch(fileUrl(jobId, 'hits')).then((r) => (r.ok ? r.json() : Promise.reject(new Error('hits.json missing')))),
      fetch(fileUrl(jobId, 'musicxml')).then((r) => (r.ok ? r.text() : Promise.reject(new Error('MusicXML missing')))),
    ])
      .then(([d, x]) => {
        if (cancelled) return
        setDoc(d)
        setXml(x)
      })
      .catch((e) => !cancelled && setLoadError(String(e.message ?? e)))
    return () => {
      cancelled = true
    }
  }, [jobId])

  // audio
  useEffect(() => {
    if (!grid) return
    let cancelled = false
    let created: PlayerEngine | null = null
    const ctx = new AudioContext()
    ;(async () => {
      try {
        const [mix, drums] = await Promise.all([
          loadAudio(ctx, fileUrl(jobId, 'mix')),
          loadAudio(ctx, fileUrl(jobId, 'drums')),
        ])
        if (cancelled) return
        created = new PlayerEngine(ctx, mix, drums, grid.clickBeats(), grid.perBar)
        created.onEnded = () => setPlaying(false)
        ;(window as any).__engine = created // handy for debugging / automated tests
        setEngine(created)
        setAudioState('')
      } catch (e) {
        if (!cancelled) setAudioState(`Audio failed to load: ${e instanceof Error ? e.message : e}`)
      }
    })()
    return () => {
      cancelled = true
      created?.destroy()
      ctx.close().catch(() => undefined)
    }
  }, [jobId, grid])

  // cursor + clock, driven by the audio position
  useEffect(() => {
    if (!engine || !grid) return
    let raf = 0
    const tick = () => {
      const t = engine.currentTime
      scoreRef.current?.setCursor(grid.timeToQ(t), engine.playing)
      if (timeRef.current) timeRef.current.textContent = `${formatTime(t)} / ${formatTime(engine.duration)}`
      if (barRef.current) barRef.current.textContent = engine.countingIn ? 'count-in' : `bar ${grid.barAt(t)}`
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [engine, grid])

  // push UI state into the engine
  useEffect(() => engine?.setSource(source), [engine, source])
  useEffect(() => engine?.setSpeed(speed / 100), [engine, speed])
  useEffect(() => {
    if (engine) engine.clickEnabled = click
  }, [engine, click])
  useEffect(() => {
    if (engine) engine.countInEnabled = countIn
  }, [engine, countIn])
  useEffect(() => {
    if (!engine || !grid) return
    engine.setLoop(loop ? { start: Math.max(0, grid.barStart(loop.from)), end: grid.barEnd(loop.to) } : null)
  }, [engine, grid, loop])

  const toggle = useCallback(async () => {
    if (!engine) return
    if (engine.playing) {
      engine.pause()
      setPlaying(false)
    } else {
      await engine.play()
      setPlaying(true)
    }
  }, [engine])

  const seekBar = useCallback(
    (bar: number) => {
      if (!engine || !grid) return
      engine.seek(Math.max(0, grid.barStart(Math.min(Math.max(bar, 1), grid.barCount))))
    },
    [engine, grid],
  )

  const onBarClick = useCallback(
    (bar: number, extend: boolean) => {
      if (!grid || !engine) return
      if (extend) {
        const anchor = loop ? loop.from : grid.barAt(engine.currentTime)
        setLoop({ from: Math.min(anchor, bar), to: Math.max(loop ? loop.to : anchor, bar) })
      } else if (loop && (bar < loop.from || bar > loop.to)) {
        setLoop(null)
        seekBar(bar)
      } else {
        seekBar(bar)
      }
    },
    [engine, grid, loop, seekBar],
  )

  // keyboard: space = play/pause, arrows = previous/next bar
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return
      if (e.code === 'Space') {
        e.preventDefault()
        void toggle()
      } else if ((e.code === 'ArrowLeft' || e.code === 'ArrowRight') && engine && grid) {
        e.preventDefault()
        seekBar(grid.barAt(engine.currentTime) + (e.code === 'ArrowRight' ? 1 : -1))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [toggle, engine, grid, seekBar])

  if (loadError) return <div className="p-4 bg-red-50 text-red-800 rounded-lg">Could not load the transcription: {loadError}</div>
  if (!doc || !xml || !grid) return <div className="text-gray-500">Loading chart…</div>

  const s = result.summary
  const setLoopField = (field: 'from' | 'to', value: number) => {
    const v = Math.min(Math.max(Math.round(value) || 1, 1), grid.barCount)
    const cur = loop ?? { from: v, to: v }
    const next = field === 'from' ? { from: v, to: Math.max(cur.to, v) } : { from: Math.min(cur.from, v), to: v }
    setLoop(next)
  }
  const btn = 'px-3 py-1.5 rounded-md text-sm font-medium border transition-colors'
  const on = 'bg-primary-600 text-white border-primary-600'
  const off = 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 break-all">{result.filename}</h2>
          <p className="text-sm text-gray-600" data-testid="summary">
            {doc.time_signature[0]}/{doc.time_signature[1]} · ~{Math.round(doc.tempo_bpm)} BPM · {doc.bars.length} bars ·{' '}
            {doc.hits.length} hits
            {s?.hits_per_drum &&
              ` (${Object.entries(s.hits_per_drum)
                .map(([k, v]) => `${v} ${DRUM_LABEL[k] ?? k}`)
                .join(', ')})`}
          </p>
        </div>
        <div className="flex gap-2">
          <a className={`${btn} ${on}`} href={fileUrl(jobId, 'musicxml', true)} data-testid="dl-musicxml">
            Download MusicXML
          </a>
          <a className={`${btn} ${on}`} href={fileUrl(jobId, 'midi', true)} data-testid="dl-midi">
            Download MIDI
          </a>
          <a className={`${btn} ${off}`} href={fileUrl(jobId, 'hits', true)} data-testid="dl-hits">
            hits.json
          </a>
        </div>
      </div>

      <div className="sticky top-0 z-20 bg-gray-50/95 backdrop-blur py-2" data-testid="transport">
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm px-3 py-2 flex flex-wrap items-center gap-x-5 gap-y-2">
          <div className="flex items-center gap-2">
            <button
              className={`${btn} ${on} w-24 disabled:opacity-50`}
              onClick={() => void toggle()}
              disabled={!engine}
              data-testid="play"
              title="Space"
            >
              {playing ? '❚❚ Pause' : '▶ Play'}
            </button>
            <button
              className={`${btn} ${off} disabled:opacity-50`}
              disabled={!engine}
              data-testid="rewind"
              onClick={() => engine && engine.seek(loop ? Math.max(0, grid.barStart(loop.from)) : 0)}
              title="Back to start"
            >
              ⏮
            </button>
            <div className="text-sm tabular-nums text-gray-700 w-40">
              <span ref={timeRef} data-testid="time">0:00.0</span>
              <span className="text-gray-400"> · </span>
              <span ref={barRef} data-testid="bar">bar 1</span>
            </div>
          </div>

          <div className="flex items-center" role="group" aria-label="Audio source">
            {(['mix', 'drums'] as SourceName[]).map((name) => (
              <button
                key={name}
                className={`${btn} ${source === name ? on : off} ${name === 'mix' ? 'rounded-r-none' : 'rounded-l-none -ml-px'}`}
                onClick={() => setSource(name)}
                data-testid={`source-${name}`}
                aria-pressed={source === name}
              >
                {name === 'mix' ? 'Full mix' : 'Drums only'}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-700">
            Speed
            <input
              type="range"
              min={50}
              max={100}
              step={5}
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              data-testid="speed"
              className="w-28"
            />
            <span className="tabular-nums w-10" data-testid="speed-label">{speed}%</span>
          </label>

          <label className="flex items-center gap-1.5 text-sm text-gray-700">
            <input type="checkbox" checked={click} onChange={(e) => setClick(e.target.checked)} data-testid="click" />
            Click
          </label>

          <div className="flex items-center gap-2 text-sm text-gray-700">
            <span>Loop bars</span>
            <input
              type="number"
              min={1}
              max={grid.barCount}
              value={loop?.from ?? ''}
              placeholder="from"
              onChange={(e) => setLoopField('from', Number(e.target.value))}
              data-testid="loop-from"
              className="w-16 border border-gray-300 rounded px-1.5 py-1"
            />
            <span>–</span>
            <input
              type="number"
              min={1}
              max={grid.barCount}
              value={loop?.to ?? ''}
              placeholder="to"
              onChange={(e) => setLoopField('to', Number(e.target.value))}
              data-testid="loop-to"
              className="w-16 border border-gray-300 rounded px-1.5 py-1"
            />
            <button className={`${btn} ${off} disabled:opacity-40`} disabled={!loop} onClick={() => setLoop(null)} data-testid="loop-clear">
              Clear
            </button>
            <label className="flex items-center gap-1.5">
              <input type="checkbox" checked={countIn} onChange={(e) => setCountIn(e.target.checked)} data-testid="count-in" />
              1-bar count-in
            </label>
          </div>
          {audioState && <span className="text-sm text-gray-500" data-testid="audio-state">{audioState}</span>}
        </div>
      </div>

      <p className="text-xs text-gray-500">
        Click a bar to jump there. Drag across bars (or shift-click) to loop them. Space plays/pauses, ← → step by bar.
      </p>

      <Score
        ref={scoreRef}
        musicxml={xml}
        perBar={grid.perBar}
        loop={loop}
        onBarClick={onBarClick}
        onBarRange={(from, to) => setLoop({ from, to })}
      />
    </div>
  )
}
