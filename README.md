# Drum Transcription Service

A web-based service that automatically converts drum audio into readable sheet music notation, built with FastAPI, React, and machine learning.

## Features

- **Audio Upload**: Support for MP3, WAV, and M4A files up to 10MB
- **Real-time Processing**: Track progress with WebSocket updates
- **Multiple Export Formats**: PDF, MIDI, and MusicXML
- **Responsive UI**: Clean, modern interface built with React and Tailwind CSS
- **Scalable Architecture**: Microservices with Docker Compose

## Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM
- **PostgreSQL**: Robust relational database
- **Redis**: In-memory data store for caching and task queue
- **Celery**: Distributed task queue for background processing

### Frontend
- **React 18**: Modern UI library with hooks
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **TanStack Query**: Data fetching and state management

### ML Pipeline
- **Placeholder**: Ready for ML model integration
- **Celery Workers**: Background processing for audio transcription
- **Structured Logging**: Comprehensive logging with structlog

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd drum-script-ai
   ```

2. **Start the services**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Development Setup

1. **Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Development with hot reload**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

## Architecture

The system follows a microservices architecture with:

- **Frontend**: React SPA served by Nginx
- **Backend**: FastAPI application with async endpoints
- **Database**: PostgreSQL for persistent data
- **Cache**: Redis for session data and task queue
- **ML Worker**: Celery worker for audio processing
- **File Storage**: Local volumes (S3 for production)

## API Endpoints

### Transcription
- `POST /api/v1/transcription/upload` - Upload audio file
- `GET /api/v1/transcription/jobs/{job_id}` - Get job status
- `GET /api/v1/transcription/jobs/{job_id}/result` - Get transcription result
- `DELETE /api/v1/transcription/jobs/{job_id}` - Delete job

### Health
- `GET /api/v1/health` - System health check

### WebSocket
- `WS /ws/jobs/{job_id}` - Real-time job progress updates

## Database Schema

Key tables:
- `users` - User accounts and subscription info
- `transcription_jobs` - Processing jobs and status
- `transcription_results` - Processed results and metadata
- `usage_events` - Usage tracking for billing

## Development

### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Adding ML Models

The ML pipeline is designed to be extensible:

1. Add model dependencies to `ml_worker/requirements.txt`
2. Implement model loading in `ml_worker/pipeline/transcription.py`
3. Update processing stages as needed

## Production Deployment

For production deployment:

1. **Environment**: Set production environment variables
2. **Database**: Use managed PostgreSQL service
3. **Storage**: Configure AWS S3 for file storage
4. **Monitoring**: Add application monitoring
5. **SSL**: Configure HTTPS termination
6. **Scaling**: Use container orchestration (ECS, Kubernetes)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.