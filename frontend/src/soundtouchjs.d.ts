declare module 'soundtouchjs' {
  export class FifoSampleBuffer {
    readonly frameCount: number
    putSamples(samples: Float32Array, position?: number, numFrames?: number): void
    receiveSamples(output: Float32Array, numFrames?: number): void
    clear(): void
  }
  export class Stretch {
    constructor(createBuffers: boolean)
    tempo: number
    inputBuffer: FifoSampleBuffer
    outputBuffer: FifoSampleBuffer
    setParameters(sampleRate: number, sequenceMs: number, seekWindowMs: number, overlapMs: number): void
    process(): void
    clear(): void
  }
}
