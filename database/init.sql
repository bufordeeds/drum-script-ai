-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE subscription_tier AS ENUM ('free', 'basic', 'pro');
CREATE TYPE job_status AS ENUM ('pending', 'uploading', 'validating', 'processing', 'completed', 'error');
CREATE TYPE event_type AS ENUM ('transcription', 'export');

-- Users and authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth0_id VARCHAR(255) UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    subscription_tier subscription_tier NOT NULL DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transcription jobs
CREATE TABLE transcription_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    status job_status NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    result_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usage tracking for billing
CREATE TABLE usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_type event_type NOT NULL,
    job_id UUID REFERENCES transcription_jobs(id) ON DELETE SET NULL,
    credits_used INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processed results storage metadata
CREATE TABLE transcription_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES transcription_jobs(id) ON DELETE CASCADE UNIQUE,
    musicxml_s3_key VARCHAR(500),
    midi_s3_key VARCHAR(500),
    pdf_s3_key VARCHAR(500),
    audio_duration_seconds DECIMAL(6,2),
    detected_tempo INTEGER,
    detected_time_signature VARCHAR(10),
    accuracy_score DECIMAL(4,3) CHECK (accuracy_score >= 0 AND accuracy_score <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_jobs_user_status ON transcription_jobs(user_id, status);
CREATE INDEX idx_jobs_created_at ON transcription_jobs(created_at DESC);
CREATE INDEX idx_usage_events_user_date ON usage_events(user_id, created_at);
CREATE INDEX idx_usage_events_created_at ON usage_events(created_at DESC);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Initial demo user for development
INSERT INTO users (email, subscription_tier) 
VALUES ('demo@example.com', 'free')
ON CONFLICT (email) DO NOTHING;