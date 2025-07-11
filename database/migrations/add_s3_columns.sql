-- Add S3 storage columns to transcription_jobs table
ALTER TABLE transcription_jobs 
ADD COLUMN IF NOT EXISTS s3_audio_key VARCHAR(500),
ADD COLUMN IF NOT EXISTS s3_export_keys JSONB;

-- Add index on s3_audio_key for faster lookups
CREATE INDEX IF NOT EXISTS idx_transcription_jobs_s3_audio_key 
ON transcription_jobs(s3_audio_key) 
WHERE s3_audio_key IS NOT NULL;