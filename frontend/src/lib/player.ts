import { buildAnchors, stretchConfig, stretchSegment, type StretchConfig } from './stretch'

export type SourceName = 'mix' | 'drums'

const BLOCK = 2048 // ScriptProcessor block (frames)
const MAX_SEGMENT_S = 0.25 // longest stretch of audio processed at once when no hit is near
const MIN_SEGMENT_S = 0.02

interface ClickBeat {
  time: number
  accent: boolean
}

interface Segment {
  v: number // virtual (monotonic) source frame where this segment starts
  song: number // song frame it maps to
}

/**
 * Plays the full mix or the isolated drums from one shared read position, so the
 * two are always in sync and toggling is just "read from the other buffer".
 *
 * - Speed: onset-anchored time-stretch (see stretch.ts), no pitch change; bypassed at 100%.
 *   Segment boundaries depend only on the hit list and the speed, never on the audio,
 *   so mix and drums stretch identically.
 * - Loop: the reader wraps at the loop end, sample-accurately, before stretching.
 * - Click: synthesised after the stretcher at the detected beat times, using the
 *   same source-position bookkeeping that drives the cursor, so it stays crisp at
 *   any speed and follows tempo drift.
 *
 * Bookkeeping: the reader counts "virtual" frames (monotonic, ignoring loop wraps).
 * Output frame n corresponds to virtual frame vOut = n * speed, and `segs` maps
 * virtual frames back to song positions across wraps and seeks.
 */
export class PlayerEngine {
  readonly ctx: AudioContext
  readonly sampleRate: number
  readonly length: number // frames
  onEnded?: () => void

  private node: ScriptProcessorNode
  private data: Record<SourceName, [Float32Array, Float32Array]>
  private _source: SourceName = 'mix'
  private _speed = 1
  private _playing = false
  private loop: { start: number; end: number } | null = null
  clickEnabled = false
  countInEnabled = false

  private readPos = 0
  private vRead = 0
  private vOut = 0
  private segs: Segment[] = [{ v: 0, song: 0 }]
  private tmp = new Float32Array(BLOCK * 2)
  // time-stretch state: anchors (song frames), one source segment, and a FIFO of stretched output
  private anchors: Float64Array
  private cfg: StretchConfig
  private seg: Float32Array
  private fifo: Float32Array
  private fifoStart = 0
  private fifoEnd = 0 // frames

  private beatFrames: Float64Array
  private beatAccent: Uint8Array
  private perBar: number
  private clickWave: [Float32Array, Float32Array]
  private activeClicks: { wave: Float32Array; start: number }[] = []
  private countIn: { pos: number; total: number; clicks: { at: number; accent: boolean }[] } | null = null

  // what the listener hears "now": song frame at perf time, advancing at `rate` frames/ms
  private clock = { song: 0, perf: 0, rate: 0 }
  /** Diagnostics for tests: counts clicks rendered. */
  stats = { clicks: 0, blocks: 0, wraps: 0 }

  constructor(
    ctx: AudioContext,
    mix: AudioBuffer,
    drums: AudioBuffer,
    beats: ClickBeat[],
    perBar: number,
    onsets: number[] = [],
  ) {
    this.ctx = ctx
    this.sampleRate = ctx.sampleRate
    this.length = Math.max(mix.length, drums.length)
    const chans = (b: AudioBuffer): [Float32Array, Float32Array] => [
      b.getChannelData(0),
      b.getChannelData(b.numberOfChannels > 1 ? 1 : 0),
    ]
    this.data = { mix: chans(mix), drums: chans(drums) }
    this.beatFrames = Float64Array.from(beats.map((b) => b.time * this.sampleRate))
    this.beatAccent = Uint8Array.from(beats.map((b) => (b.accent ? 1 : 0)))
    this.perBar = perBar
    this.anchors = buildAnchors(onsets, this.sampleRate)
    this.cfg = stretchConfig(this.sampleRate)
    const maxSeg = Math.ceil((MAX_SEGMENT_S + MIN_SEGMENT_S) * this.sampleRate) + 8
    this.seg = new Float32Array(maxSeg * 2)
    this.fifo = new Float32Array((maxSeg * 2 + BLOCK) * 2 * 2) // one segment at 50% plus a block, with headroom
    this.clickWave = [this.makeClick(1245, 0.45), this.makeClick(1865, 0.6)]
    this.node = ctx.createScriptProcessor(BLOCK, 0, 2)
    this.node.onaudioprocess = (e) => this.process(e)
    this.node.connect(ctx.destination)
  }

  destroy(): void {
    this._playing = false
    this.node.onaudioprocess = null
    this.node.disconnect()
  }

  // ---- public state -------------------------------------------------------

  get playing(): boolean {
    return this._playing
  }
  get countingIn(): boolean {
    return this.countIn !== null
  }
  get speed(): number {
    return this._speed
  }
  get source(): SourceName {
    return this._source
  }
  get duration(): number {
    return this.length / this.sampleRate
  }
  get loopRange(): { start: number; end: number } | null {
    return this.loop && { start: this.loop.start / this.sampleRate, end: this.loop.end / this.sampleRate }
  }

  /** Song position being heard right now, in seconds. */
  get currentTime(): number {
    let f = this.clock.song + (performance.now() - this.clock.perf) * this.clock.rate
    if (this.loop && this.clock.rate > 0) {
      const len = this.loop.end - this.loop.start
      if (f >= this.loop.end) f = this.loop.start + ((f - this.loop.start) % len)
      if (f < this.loop.start) f = this.loop.start
    }
    return Math.min(Math.max(f, 0), this.length) / this.sampleRate
  }

  // ---- transport ----------------------------------------------------------

  async play(): Promise<void> {
    if (this._playing) return
    if (this.ctx.state !== 'running') await this.ctx.resume()
    let at = this.currentTime * this.sampleRate
    if (at >= this.length - 1) at = 0
    if (this.loop && (at < this.loop.start || at >= this.loop.end)) at = this.loop.start
    this.seekFrames(at)
    if (this.loop && this.countInEnabled) {
      this.seekFrames(this.loop.start)
      this.countIn = this.buildCountIn(this.loop.start)
    }
    this._playing = true
  }

  pause(): void {
    if (!this._playing) return
    const at = this.countIn ? this.readPos : this.currentTime * this.sampleRate
    this._playing = false
    this.countIn = null
    this.seekFrames(at)
  }

  seek(seconds: number): void {
    this.countIn = null
    this.seekFrames(seconds * this.sampleRate)
  }

  setSpeed(speed: number): void {
    const s = Math.min(1, Math.max(0.5, Math.round(speed * 20) / 20))
    if (s === this._speed) return
    const at = this.countIn ? this.readPos : this.currentTime * this.sampleRate
    this._speed = s
    this.seekFrames(at)
    if (this.countIn && this.loop) this.countIn = this.buildCountIn(this.loop.start)
  }

  setSource(source: SourceName): void {
    if (source === this._source) return
    const at = this.countIn ? this.readPos : this.currentTime * this.sampleRate
    this._source = source
    this.seekFrames(at) // flush the stretcher so the switch is immediate
  }

  /** Loop between two song times (seconds), or null to clear. */
  setLoop(range: { start: number; end: number } | null): void {
    if (!range) {
      const at = this.countIn ? this.readPos : this.currentTime * this.sampleRate
      this.loop = null
      this.countIn = null
      this.seekFrames(at)
      return
    }
    const start = Math.max(0, Math.round(range.start * this.sampleRate))
    const end = Math.min(this.length, Math.round(range.end * this.sampleRate))
    if (end - start < 64) return
    const at = this.currentTime * this.sampleRate
    this.loop = { start, end }
    this.countIn = null
    this.seekFrames(at >= start && at < end ? at : start)
  }

  // ---- internals ----------------------------------------------------------

  private makeClick(freq: number, gain: number): Float32Array {
    const n = Math.round(0.03 * this.sampleRate)
    const w = new Float32Array(n)
    for (let i = 0; i < n; i++) {
      const t = i / this.sampleRate
      w[i] = gain * Math.sin(2 * Math.PI * freq * t) * Math.exp(-t * 160)
    }
    return w
  }

  private seekFrames(frame: number): void {
    const f = Math.min(Math.max(Math.round(frame), 0), this.length)
    this.readPos = f
    this.vRead = 0
    this.vOut = 0
    this.segs = [{ v: 0, song: f }]
    this.fifoStart = this.fifoEnd = 0
    this.activeClicks = []
    this.clock = { song: f, perf: performance.now(), rate: 0 }
  }

  private buildCountIn(loopStart: number) {
    // one bar of clicks, spaced like the beats of the bar being looped
    let i = 0
    while (i < this.beatFrames.length - 1 && this.beatFrames[i] < loopStart - 0.02 * this.sampleRate) i++
    const clicks: { at: number; accent: boolean }[] = []
    let at = 0
    for (let k = 0; k < this.perBar; k++) {
      clicks.push({ at: Math.round(at), accent: k === 0 })
      const a = this.beatFrames[Math.min(i + k, this.beatFrames.length - 1)]
      const b = this.beatFrames[Math.min(i + k + 1, this.beatFrames.length - 1)]
      const gap = b > a ? b - a : 0.5 * this.sampleRate
      at += gap / this._speed
    }
    return { pos: 0, total: Math.round(at), clicks }
  }

  /** Fill `target` (interleaved stereo) with `count` frames from the active source, wrapping at the loop end. */
  private read(target: Float32Array, count: number): void {
    const [l, r] = this.data[this._source]
    let i = 0
    while (i < count) {
      if (this.loop && this.readPos >= this.loop.end) {
        this.readPos = this.loop.start
        this.segs.push({ v: this.vRead + i, song: this.readPos })
        this.stats.wraps++
      }
      const limit = this.loop ? this.loop.end : Infinity
      const m = Math.min(count - i, limit - this.readPos)
      const avail = Math.max(0, Math.min(m, this.length - this.readPos))
      for (let k = 0; k < avail; k++) {
        target[2 * (i + k)] = l[this.readPos + k]
        target[2 * (i + k) + 1] = r[this.readPos + k]
      }
      for (let k = avail; k < m; k++) {
        target[2 * (i + k)] = 0
        target[2 * (i + k) + 1] = 0
      }
      i += m
      this.readPos += m
    }
    this.vRead += count
  }

  /** Read the audio up to the next anchor (drum hit) and append its stretched version to the FIFO. */
  private produceSegment(): void {
    const sr = this.sampleRate
    if (this.loop && this.readPos >= this.loop.end) {
      // wrap now so the segment below starts at the loop start
      this.readPos = this.loop.start
      this.segs.push({ v: this.vRead, song: this.readPos })
      this.stats.wraps++
    }
    const a = this.readPos
    const limit = this.loop ? this.loop.end : a >= this.length ? Infinity : this.length
    const minSeg = Math.round(MIN_SEGMENT_S * sr)
    let b = Math.min(limit, a + Math.round(MAX_SEGMENT_S * sr))
    // first anchor far enough ahead to make a useful segment
    let lo = 0
    let hi = this.anchors.length
    while (lo < hi) {
      const mid = (lo + hi) >> 1
      if (this.anchors[mid] < a + minSeg) lo = mid + 1
      else hi = mid
    }
    if (lo < this.anchors.length && this.anchors[lo] < b) b = this.anchors[lo]
    if (limit - b < minSeg) b = limit // do not leave a sliver before the loop end / song end
    const ls = Math.max(1, Math.round(b - a))

    const v0 = this.vRead
    this.read(this.seg, ls)
    const outFrames = Math.round((v0 + ls) / this._speed) - Math.round(v0 / this._speed)

    // make room in the FIFO
    if ((this.fifoEnd + outFrames) * 2 > this.fifo.length) {
      this.fifo.copyWithin(0, this.fifoStart * 2, this.fifoEnd * 2)
      this.fifoEnd -= this.fifoStart
      this.fifoStart = 0
    }
    if ((this.fifoEnd + outFrames) * 2 > this.fifo.length) {
      const bigger = new Float32Array((this.fifoEnd + outFrames) * 4)
      bigger.set(this.fifo.subarray(0, this.fifoEnd * 2))
      this.fifo = bigger
    }
    stretchSegment(this.seg, ls, this.fifo, this.fifoEnd, outFrames, this.cfg)
    this.fifoEnd += outFrames
  }

  private songAt(v: number): number {
    let s = this.segs[0]
    for (let i = 1; i < this.segs.length && this.segs[i].v <= v; i++) s = this.segs[i]
    return s.song + (v - s.v)
  }

  private renderMusic(outL: Float32Array, outR: Float32Array, off: number, count: number): void {
    const tmp = this.tmp
    if (this._speed === 1) {
      this.read(tmp, count)
    } else {
      let guard = 0
      while (this.fifoEnd - this.fifoStart < count && guard++ < 256) this.produceSegment()
      const got = Math.min(count, this.fifoEnd - this.fifoStart)
      tmp.fill(0, 0, count * 2)
      tmp.set(this.fifo.subarray(this.fifoStart * 2, (this.fifoStart + got) * 2))
      this.fifoStart += got
    }
    for (let i = 0; i < count; i++) {
      outL[off + i] = tmp[2 * i]
      outR[off + i] = tmp[2 * i + 1]
    }

    const v0 = this.vOut
    const v1 = v0 + count * this._speed
    if (this.clickEnabled) this.scheduleClicks(v0, v1, off)
    this.vOut = v1
    while (this.segs.length > 1 && this.segs[1].v <= v0) this.segs.shift()

    if (!this.loop && this.songAt(v1) >= this.length) {
      this._playing = false
      this.clock = { song: this.length, perf: performance.now(), rate: 0 }
      setTimeout(() => this.onEnded?.(), 0)
    }
  }

  /** Start a click for every beat whose song position falls inside virtual range [v0, v1). */
  private scheduleClicks(v0: number, v1: number, off: number): void {
    for (let i = 0; i < this.segs.length; i++) {
      const seg = this.segs[i]
      const segEnd = i + 1 < this.segs.length ? this.segs[i + 1].v : Infinity
      const a = Math.max(v0, seg.v)
      const b = Math.min(v1, segEnd)
      if (b <= a) continue
      const s0 = seg.song + (a - seg.v)
      const s1 = seg.song + (b - seg.v)
      // first beat >= s0
      let lo = 0
      let hi = this.beatFrames.length
      while (lo < hi) {
        const mid = (lo + hi) >> 1
        if (this.beatFrames[mid] < s0) lo = mid + 1
        else hi = mid
      }
      for (let k = lo; k < this.beatFrames.length && this.beatFrames[k] < s1; k++) {
        const outOffset = off + Math.round((a - v0 + (this.beatFrames[k] - s0)) / this._speed)
        this.activeClicks.push({ wave: this.clickWave[this.beatAccent[k]], start: outOffset })
        this.stats.clicks++
      }
    }
  }

  private mixClicks(outL: Float32Array, outR: Float32Array, n: number): void {
    if (this.activeClicks.length === 0) return
    const keep: typeof this.activeClicks = []
    for (const c of this.activeClicks) {
      const from = Math.max(0, c.start)
      const to = Math.min(n, c.start + c.wave.length)
      for (let i = from; i < to; i++) {
        const s = c.wave[i - c.start]
        outL[i] += s
        outR[i] += s
      }
      if (c.start + c.wave.length > n) keep.push({ wave: c.wave, start: c.start - n })
    }
    this.activeClicks = keep
  }

  private process(e: AudioProcessingEvent): void {
    const outL = e.outputBuffer.getChannelData(0)
    const outR = e.outputBuffer.getChannelData(1)
    const n = outL.length
    outL.fill(0)
    outR.fill(0)
    if (!this._playing) return
    this.stats.blocks++

    // when the audio produced by this callback reaches the speakers
    const latencyMs = ((n / this.sampleRate) + (this.ctx.outputLatency || this.ctx.baseLatency || 0)) * 1000
    let off = 0
    if (this.countIn) {
      const ci = this.countIn
      const m = Math.min(n, ci.total - ci.pos)
      for (const c of ci.clicks) {
        if (c.at >= ci.pos && c.at < ci.pos + m) {
          this.activeClicks.push({ wave: this.clickWave[c.accent ? 1 : 0], start: c.at - ci.pos })
          this.stats.clicks++
        }
      }
      ci.pos += m
      off = m
      if (ci.pos >= ci.total) this.countIn = null
    }
    if (off < n && !this.countIn) {
      const heard = this.songAt(this.vOut)
      this.renderMusic(outL, outR, off, n - off)
      if (this._playing) {
        this.clock = {
          song: heard,
          perf: performance.now() + latencyMs + (off / this.sampleRate) * 1000,
          rate: (this._speed * this.sampleRate) / 1000,
        }
      }
    }
    this.mixClicks(outL, outR, n)
  }
}

/** Fetch + decode an audio file into the context's sample rate. */
export async function loadAudio(ctx: BaseAudioContext, url: string): Promise<AudioBuffer> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Could not load audio (${res.status})`)
  return ctx.decodeAudioData(await res.arrayBuffer())
}
