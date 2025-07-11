# ML Model Integration Plan: Drum Transcription AI

## Executive Summary

This document outlines the plan to transform our current placeholder drum transcription pipeline into a production-ready AI-powered system using state-of-the-art machine learning models. The goal is to achieve accurate drum pattern recognition that can convert songs to readable drum notation and export to MuseScore-compatible formats.

## Current State Analysis

### Architecture Strengths ✅

**Well-Designed Foundation:**
- Clean microservices architecture (Frontend, Backend, ML Worker)
- Docker containerization with proper service separation
- Async processing pipeline with Celery + Redis
- Real-time progress tracking via WebSocket
- Comprehensive database schema with proper relationships
- S3 integration for file storage and exports

**Working Components:**
- File upload and validation system
- Background task processing
- Export generation (PDF, MIDI, MusicXML)
- Frontend with real-time progress tracking
- Debug panel for development

### Critical Limitations ❌

**No Real ML Models:**
- Currently using basic signal processing instead of trained models
- Simple onset detection with librosa only
- Rudimentary spectral analysis for drum classification
- All drums incorrectly classified as snare (pitch 38)

**Poor Accuracy:**
- Frequency-based classification is too simplistic
- No proper source separation (only harmonic-percussive)
- Tempo detection unreliable for complex patterns
- Cannot distinguish between different drum types effectively

**Limited Export Quality:**
- Basic PDF generation without proper notation rendering
- Missing MuseScore native format support (.mscx/.mscz)
- No notation preview capabilities

## Target Architecture: Real AI-Powered Pipeline

### High-Level Flow
```
Audio Upload → Demucs v4 Source Separation → ADTLib Transcription → Enhanced Export Generation
```

### Model Integration Strategy

**1. Source Separation: Demucs v4**
- Replace basic harmonic-percussive separation
- Use Meta's state-of-the-art `htdemucs_ft` model
- Isolate clean drum track from mixed audio
- Supports GPU acceleration for faster processing

**2. Drum Transcription: ADTLib**
- Replace basic onset detection with trained models
- Automatic drum transcription with proper instrument classification
- Outputs kick, snare, hi-hat, and cymbal onsets
- Includes confidence scores for quality assessment

**3. Enhanced Export Generation**
- Improve PDF rendering with proper drum notation
- Add MuseScore native format support (.mscx/.mscz)
- Generate MusicXML compatible with MuseScore 4.x
- Include metadata (tempo, time signature, confidence)

## Implementation Plan

### Phase 1: Core ML Model Integration (Week 1-2)

**1.1 Demucs v4 Integration**
```python
# New dependencies in ml_worker/requirements.txt
demucs>=4.0.0
torch>=2.0.0
torchaudio>=2.0.0

# Pipeline enhancement
class EnhancedTranscriptionPipeline:
    def __init__(self):
        self.demucs_model = pretrained.get_model('htdemucs_ft')
        
    async def separate_drums(self, audio_data):
        # Use Demucs for high-quality separation
        separated = self.demucs_model(audio_data)
        return separated[0]  # drums channel
```

**1.2 ADTLib Integration**
```python
# Add ADTLib dependency
ADTLib>=1.0.0

# Replace basic transcription
from ADTLib import ADT

class EnhancedTranscriptionPipeline:
    def __init__(self):
        self.adt_model = ADT()
        
    async def transcribe_drums(self, drum_audio):
        # Use ADTLib for accurate transcription
        result = self.adt_model.transcribe(drum_audio)
        return self.parse_adt_output(result)
```

**1.3 Model Loading and Caching**
```python
# Pre-load models during container startup
class ModelManager:
    def __init__(self):
        self.models = {}
        
    async def load_models(self):
        # Cache models to avoid repeated loading
        self.models['demucs'] = pretrained.get_model('htdemucs_ft')
        self.models['adt'] = ADT()
```

### Phase 2: Export Format Enhancement (Week 2-3)

**2.1 MuseScore Format Support**
```python
# Add MuseScore CLI integration
async def generate_musescore_formats(self, score):
    # Export to MusicXML first
    musicxml_path = score.write('musicxml')
    
    # Use MuseScore CLI to convert to native formats
    subprocess.run(['mscore', '-o', 'output.mscx', musicxml_path])
    subprocess.run(['mscore', '-o', 'output.mscz', musicxml_path])
```

**2.2 Frontend Export Options Update**
```typescript
// Update ExportOptions.tsx
const exportOptions = [
  { format: 'pdf', name: 'PDF', description: 'Printable sheet music' },
  { format: 'midi', name: 'MIDI', description: 'For DAW import' },
  { format: 'musicxml', name: 'MusicXML', description: 'Universal format' },
  { format: 'mscx', name: 'MuseScore (XML)', description: 'MuseScore native format' },
  { format: 'mscz', name: 'MuseScore (Compressed)', description: 'MuseScore compressed format' }
]
```

**2.3 Enhanced PDF Generation**
```python
# Improve PDF rendering with proper notation
async def generate_enhanced_pdf(self, transcription):
    # Generate notation image using music21
    score = self.create_drum_score(transcription)
    
    # Use LilyPond for high-quality notation rendering
    score.write('lilypond.png')
    
    # Create professional PDF with notation
    return self.create_pdf_with_notation(score, transcription)
```

### Phase 3: Quality and Accuracy Improvements (Week 3-4)

**3.1 Post-Processing Pipeline**
```python
class PostProcessor:
    def quantize_notes(self, notes, time_signature='4/4'):
        # Snap notes to nearest grid positions
        pass
        
    def filter_low_confidence(self, notes, threshold=0.5):
        # Remove uncertain detections
        pass
        
    def merge_overlapping_hits(self, notes, window_ms=50):
        # Combine closely spaced hits
        pass
```

**3.2 Error Handling and Fallbacks**
```python
class RobustPipeline:
    async def process_with_fallback(self, audio):
        try:
            # Try Demucs v4 + ADTLib
            return await self.process_with_ml_models(audio)
        except Exception as e:
            logger.warning("ML models failed, using fallback", error=str(e))
            # Fallback to Spleeter + basic detection
            return await self.process_with_fallback_models(audio)
```

**3.3 Performance Optimization**
```python
# GPU detection and utilization
def setup_device():
    if torch.cuda.is_available():
        return torch.device('cuda')
    return torch.device('cpu')

# Memory management for large files
class MemoryEfficientProcessor:
    def process_in_chunks(self, audio, chunk_size=30):
        # Process long audio files in segments
        pass
```

### Phase 4: Production Optimization (Week 4+)

**4.1 Docker Configuration Updates**
```yaml
# docker-compose.yml updates
ml_worker:
  environment:
    - TORCH_HOME=/app/models
    - CUDA_VISIBLE_DEVICES=0
  volumes:
    - ./models:/app/models:cached
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

**4.2 Monitoring and Metrics**
```python
# Add processing metrics
from prometheus_client import Histogram, Counter

PROCESSING_TIME = Histogram('drum_transcription_seconds', 'Time spent processing')
ACCURACY_SCORE = Histogram('transcription_accuracy', 'Confidence scores')
MODEL_ERRORS = Counter('model_errors_total', 'ML model failures')
```

## Technical Specifications

### New Dependencies

**ML Worker Requirements:**
```txt
# Core ML models
demucs>=4.0.0
ADTLib>=1.0.0

# PyTorch ecosystem  
torch>=2.0.0
torchaudio>=2.0.0

# Audio processing
librosa>=0.10.1
soundfile>=0.12.1

# Notation and export
music21>=9.1.0
lilypond  # For high-quality notation rendering

# System tools
musescore  # For .mscx/.mscz export
```

**System Requirements:**
```dockerfile
# Add to ml_worker/Dockerfile
RUN apt-get update && apt-get install -y \
    musescore3 \
    lilypond \
    && rm -rf /var/lib/apt/lists/*
```

### API Endpoint Changes

**Enhanced Job Result Schema:**
```python
class TranscriptionResultSchema(BaseModel):
    tempo: int
    time_signature: str
    duration_seconds: float
    accuracy_score: float
    
    # Enhanced metadata
    drum_types_detected: List[str]
    confidence_by_instrument: Dict[str, float]
    processing_time_seconds: float
    
    # Expanded export formats
    download_urls: Dict[str, str]  # pdf, midi, musicxml, mscx, mscz
```

### Database Schema Updates

**Add Model Performance Tracking:**
```sql
-- New table for tracking ML model performance
CREATE TABLE model_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES transcription_jobs(id),
    model_version VARCHAR(50) NOT NULL,
    processing_time_seconds DECIMAL(6,2),
    accuracy_score DECIMAL(4,3),
    drum_types_detected JSONB,
    confidence_scores JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes for analytics
CREATE INDEX idx_model_performance_job ON model_performance(job_id);
CREATE INDEX idx_model_performance_model ON model_performance(model_version);
```

## Success Metrics

### Technical Performance
- **Processing Accuracy:** >75% F-score on standard drum patterns
- **Processing Time:** <60 seconds for 3-minute songs
- **Model Reliability:** <5% failure rate on valid audio files
- **Export Compatibility:** 100% success rate for all supported formats

### User Experience
- **End-to-End Workflow:** Upload to PDF download in <2 minutes
- **Notation Quality:** Clear, readable drum notation in all exports
- **Format Support:** Native MuseScore compatibility for .mscx/.mscz
- **Error Handling:** Meaningful error messages for all failure modes

### Accuracy Targets by Pattern Type
- **Simple Rock (4/4):** >80% F-score
- **Pop/Folk patterns:** >75% F-score  
- **Complex patterns:** >65% F-score
- **Tempo detection:** ±5 BPM accuracy

## Risk Assessment and Mitigation

### Technical Risks

**Model Dependencies:**
- *Risk:* ADTLib or Demucs models may fail on certain audio types
- *Mitigation:* Implement fallback pipeline with Spleeter + basic detection

**GPU Memory:**
- *Risk:* Large audio files may exceed GPU memory limits
- *Mitigation:* Implement audio chunking and CPU fallback

**Processing Time:**
- *Risk:* ML models may be too slow for user expectations
- *Mitigation:* Optimize model loading, implement processing queues

### Integration Risks

**Docker Complexity:**
- *Risk:* GPU support and model dependencies may complicate deployment
- *Mitigation:* Create separate CPU-only and GPU-enabled images

**File Format Compatibility:**
- *Risk:* MuseScore format exports may fail on some systems
- *Mitigation:* Ensure MusicXML export always works as fallback

## Testing Strategy

### Unit Tests
```python
class TestMLPipeline:
    def test_demucs_separation(self):
        # Test drum isolation quality
        pass
        
    def test_adt_transcription(self):
        # Test note detection accuracy
        pass
        
    def test_export_generation(self):
        # Test all format exports
        pass
```

### Integration Tests
- End-to-end processing with sample drum tracks
- Export format compatibility with MuseScore 4.x
- Performance benchmarks on various audio types

### User Acceptance Tests
- Upload real songs, verify notation quality
- Test with drummers for accuracy feedback
- Validate MuseScore import workflow

## Deployment Strategy

### Rollout Plan
1. **Development Environment:** Test ML model integration locally
2. **Staging Deployment:** Deploy with sample audio files for testing
3. **Beta Release:** Limited user testing with feedback collection
4. **Production Release:** Full deployment with monitoring

### Monitoring
```python
# Key metrics to track
- Processing success/failure rates
- Average processing time per job
- Model accuracy scores distribution
- User satisfaction ratings
- Export format usage patterns
```

## Timeline

### Week 1: ML Model Foundation
- [ ] Integrate Demucs v4 for source separation
- [ ] Set up ADTLib for drum transcription
- [ ] Implement model loading and caching
- [ ] Test basic ML pipeline functionality

### Week 2: Export Enhancement
- [ ] Add MuseScore format support (.mscx/.mscz)
- [ ] Improve PDF generation with notation rendering
- [ ] Update frontend export options
- [ ] Test format compatibility

### Week 3: Quality Improvements
- [ ] Implement post-processing pipeline
- [ ] Add error handling and fallbacks
- [ ] Optimize performance and memory usage
- [ ] Add comprehensive logging and metrics

### Week 4: Production Readiness
- [ ] Docker configuration for GPU support
- [ ] Performance testing and optimization
- [ ] Documentation and user guides
- [ ] Beta testing with real users

## Conclusion

This plan transforms our current placeholder system into a production-ready AI-powered drum transcription service. By integrating proven ML models (Demucs v4 + ADTLib) and enhancing export capabilities, we'll achieve the accuracy and user experience needed for a successful product.

The phased approach ensures we can validate each component before moving to the next, while the comprehensive testing strategy ensures reliability in production. With proper implementation, this system will deliver the goal of uploading a song and receiving accurate drum notation in PDF and MuseScore-compatible formats.