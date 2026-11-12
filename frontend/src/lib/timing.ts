import type { HitsDoc } from '../api'

/**
 * Maps between audio time (seconds) and score position (quarter notes from the
 * start of bar 1) using the detected beats. Every beat is one quarter note, so
 * tempo drift is absorbed here: the chart is laid out in beats, the audio is not.
 */
export class Grid {
  /** Every beat of every bar, plus the end of the last bar. */
  readonly beats: number[]
  readonly perBar: number
  readonly barCount: number

  constructor(doc: HitsDoc) {
    this.perBar = doc.time_signature[0]
    this.barCount = doc.bars.length
    this.beats = doc.bars.flatMap((b) => b.beats)
    this.beats.push(doc.bars[doc.bars.length - 1].end_s)
  }

  get totalQ(): number {
    return this.beats.length - 1
  }

  timeToQ(t: number): number {
    const b = this.beats
    if (t <= b[0]) return 0
    if (t >= b[b.length - 1]) return this.totalQ
    let lo = 0
    let hi = b.length - 1
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1
      if (b[mid] <= t) lo = mid
      else hi = mid
    }
    return lo + (t - b[lo]) / (b[lo + 1] - b[lo])
  }

  qToTime(q: number): number {
    const b = this.beats
    const c = Math.min(Math.max(q, 0), this.totalQ)
    const i = Math.min(Math.floor(c), b.length - 2)
    return b[i] + (c - i) * (b[i + 1] - b[i])
  }

  /** 1-based bar number containing time t. */
  barAt(t: number): number {
    return Math.min(this.barCount, Math.floor(this.timeToQ(t) / this.perBar + 1e-9) + 1)
  }

  barStart(bar: number): number {
    return this.beats[(bar - 1) * this.perBar]
  }

  barEnd(bar: number): number {
    return this.beats[bar * this.perBar]
  }

  /** Beats for the click track: time + whether it is a downbeat. */
  clickBeats(): { time: number; accent: boolean }[] {
    return this.beats.slice(0, -1).map((time, i) => ({ time, accent: i % this.perBar === 0 }))
  }
}

export function formatTime(t: number): string {
  const s = Math.max(0, t)
  const m = Math.floor(s / 60)
  return `${m}:${(s - m * 60).toFixed(1).padStart(4, '0')}`
}
