# MVP Feature Specification: Drum Transcription Service

## Product Vision

A web-based service that automatically converts drum audio into readable sheet music notation, targeting drummers, music students, and content creators who need accurate drum transcriptions quickly and affordably.

## Target User Stories

### Primary User: Intermediate Drummer

_"I want to learn the drum part from my favorite song, but I can't find sheet music anywhere and transcribing by ear takes me hours."_

### Secondary User: Music Teacher

_"I need drum notation for my students but don't have time to transcribe everything manually."_

### Tertiary User: Content Creator

_"I want to create drum covers and need the notation to learn complex parts quickly."_

## Core Feature Set

### 1. Audio Upload & Processing

**What it does:** Users upload audio files and receive drum notation
**Acceptance Criteria:**

-   Supports MP3, WAV, M4A files up to 10MB
-   Max song length: 6 minutes
-   Processing time: <60 seconds for typical 3-minute song
-   Clear progress indicators during processing
-   Error handling for unsupported formats

**Technical Implementation:**

-   Frontend: React file upload with drag-and-drop
-   Backend: FastAPI endpoint with file validation
-   Audio processing: librosa for format conversion
-   Storage: Temporary S3 bucket for uploaded files

### 2. Drum Transcription Engine

**What it does:** Converts audio to drum notation using pre-trained models
**Acceptance Criteria:**

-   Detects kick, snare, hi-hat (closed/open), crash, ride cymbals
-   Accuracy target: >75% F-score on simple rock/pop patterns
-   Handles 4/4 time signatures
-   Outputs quantized to 16th note resolution
-   Tempo detection within ±5 BPM

**Technical Implementation:**

-   Source separation: Demucs v4 (fallback to Spleeter for speed)
-   Transcription: ADTLib or Google's OaF Drums model
-   Post-processing: Music21 for quantization and formatting

### 3. Notation Preview & Validation

**What it does:** Shows transcribed notation for validation before download
**Acceptance Criteria:**

-   Clean, readable drum notation preview
-   Basic audio playback with original track
-   Scroll through multiple pages/measures
-   Mobile-responsive design
-   Clear "looks good" vs "needs adjustment" feedback

**Technical Implementation:**

-   Notation rendering: VexFlow (simplified, read-only)
-   Audio playback: Basic HTML5 audio player
-   Static notation display (no complex interactions)

### 4. Export Options

**What it does:** Users can download their transcriptions in multiple formats
**Acceptance Criteria:**

-   PDF export with clean formatting
-   MIDI file export for DAW import
-   MusicXML export for MuseScore/Sibelius
-   PNG export for quick sharing

**Technical Implementation:**

-   PDF: Music21 → LilyPond → PDF generation
-   MIDI: Music21 native export
-   MusicXML: Music21 native export
-   PNG: Server-side VexFlow rendering

### 5. Freemium Business Model

**What it does:** Free tier with limitations, paid plans for full access
**Acceptance Criteria:**

-   Free: 3 transcriptions per month, 2-minute max length
-   Basic Plan ($9.99/month): Unlimited transcriptions, 6-minute max
-   Pro Plan ($19.99/month): Unlimited + priority processing + advanced features
-   Clear upgrade prompts without being pushy

**Technical Implementation:**

-   Authentication: Auth0 or similar
-   Payment processing: Stripe
-   Usage tracking: PostgreSQL with Redis caching
-   Rate limiting: Redis-based counters

## Non-Functional Requirements

### Performance

-   Page load time: <3 seconds
-   Processing start time: <5 seconds after upload
-   99% uptime SLA
-   Handles 50 concurrent users

### Accuracy Targets

-   Simple rock patterns (4/4, basic kit): >80% F-score
-   Pop/folk patterns: >75% F-score
-   Complex jazz/fusion: >60% F-score (aspirational)

### User Experience

-   No-registration trial: Users can try one transcription without signing up
-   Clear error messages with helpful suggestions
-   Mobile-friendly interface (responsive design)
-   Accessibility compliance (WCAG 2.1 AA)

## Out of Scope for MVP

### Explicitly NOT Including:

-   Real-time transcription (live audio input)
-   Advanced editing (adding/removing notes)
-   Multiple drum kit configurations
-   Time signature changes within songs
-   Velocity/dynamics detection
-   Social features (sharing, collaboration)
-   Mobile app (web-only for MVP)
-   Batch processing multiple files
-   API for third-party developers

## Success Metrics

### Technical Metrics

-   Processing success rate: >95%
-   Average processing time: <45 seconds
-   Transcription accuracy: >75% F-score on test dataset
-   Zero critical bugs in production

### Business Metrics

-   100+ trial users in first month
-   15+ paying subscribers by month 3
-   User satisfaction: >4.0/5.0 rating
-   Conversion rate: >5% trial-to-paid

### User Validation Metrics

-   Task completion rate: >90% (upload to export)
-   Time to first success: <5 minutes
-   Support ticket volume: <5% of total users

## Technical Architecture Overview

```
Frontend (React + TypeScript)
├── File Upload Component
├── Processing Status Component
├── Notation Display Component (VexFlow)
├── Audio Player Component
└── Export Options Component

Backend (Python + FastAPI)
├── File Upload Endpoint
├── Transcription Processing Queue
├── User Management & Auth
├── Payment Processing
└── Export Generation

ML Pipeline
├── Audio Preprocessing (librosa)
├── Source Separation (Demucs/Spleeter)
├── Drum Transcription (ADTLib/OaF)
└── Notation Generation (music21)

Infrastructure
├── AWS EC2 for web servers
├── AWS S3 for file storage
├── Redis for caching & queues
├── PostgreSQL for user data
└── AWS Lambda for background processing
```

## Development Milestones

### Week 1-2: Project Setup

-   Development environment setup
-   Basic React app with file upload
-   FastAPI backend with health checks
-   CI/CD pipeline configuration

### Week 3-6: Core Transcription Pipeline

-   Audio processing integration
-   ML model integration (ADTLib)
-   Basic notation display
-   End-to-end transcription working

### Week 7-10: User Experience

-   Authentication system
-   Payment integration
-   Export functionality
-   Error handling and polish

### Week 11-14: Production Deployment

-   AWS infrastructure setup
-   Performance optimization
-   Security hardening
-   Beta user testing

### Week 15-16: Launch Preparation

-   Documentation completion
-   Marketing site
-   Monitoring and analytics
-   Public launch

## Risk Mitigation

### Technical Risks

-   **ML model accuracy too low:** Have backup models ready (Omnizart, commercial APIs)
-   **Processing too slow:** Implement queue system with status updates
-   **Audio format compatibility:** Extensive testing with common formats

### Business Risks

-   **No market demand:** Quick user interviews before development
-   **Competition from free tools:** Focus on superior accuracy and UX
-   **Scaling costs:** Monitor usage patterns and optimize aggressively

## Validation Plan

### Pre-Development (Week 0)

-   10 user interviews with target personas
-   Competitive analysis of existing tools
-   Technical feasibility testing with sample audio

### During Development (Weeks 4, 8, 12)

-   Weekly demos with potential users
-   A/B testing of key user flows
-   Performance benchmarking on real songs

### Pre-Launch (Week 14)

-   Closed beta with 20 selected users
-   Load testing with simulated traffic
-   Accuracy testing on curated song dataset

This MVP specification balances ambition with achievability, focusing on core value delivery while setting up foundations for future growth.
