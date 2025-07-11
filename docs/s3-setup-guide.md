# S3 Setup Guide for Drum Transcription Service

This guide walks you through setting up AWS S3 for storing audio files and transcription results.

## Quick Setup

1. **Run the automated setup script:**
   ```bash
   chmod +x scripts/setup_s3.sh
   ./scripts/setup_s3.sh
   ```

2. **Add the generated credentials to your `.env` file:**
   ```env
   AWS_ACCESS_KEY_ID=your-access-key-here
   AWS_SECRET_ACCESS_KEY=your-secret-key-here
   AWS_S3_BUCKET=drum-transcription-bucket
   AWS_REGION=us-east-1
   ```

3. **Test the setup:**
   ```bash
   python scripts/test_s3.py
   ```

## Manual Setup Steps

### 1. Create S3 Bucket

```bash
aws s3 mb s3://drum-transcription-bucket --region us-east-1
```

### 2. Configure Bucket Security

Block public access:
```bash
aws s3api put-public-access-block \
    --bucket drum-transcription-bucket \
    --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

### 3. Enable Encryption

```bash
aws s3api put-bucket-encryption \
    --bucket drum-transcription-bucket \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'
```

### 4. Set Up Lifecycle Policies

Create a lifecycle policy file (`lifecycle-policy.json`):
```json
{
    "Rules": [
        {
            "ID": "CleanupTempFiles",
            "Status": "Enabled",
            "Filter": {"Prefix": "temp/"},
            "Expiration": {"Days": 1}
        },
        {
            "ID": "CleanupProcessedFiles",
            "Status": "Enabled",
            "Filter": {"Prefix": "processed/"},
            "Expiration": {"Days": 30}
        }
    ]
}
```

Apply the policy:
```bash
aws s3api put-bucket-lifecycle-configuration \
    --bucket drum-transcription-bucket \
    --lifecycle-configuration file://lifecycle-policy.json
```

### 5. Configure CORS

Create a CORS configuration file (`cors-config.json`):
```json
{
    "CORSRules": [{
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["http://localhost:3000", "http://localhost:8000"],
        "ExposeHeaders": ["ETag"],
        "MaxAgeSeconds": 3600
    }]
}
```

Apply CORS:
```bash
aws s3api put-bucket-cors \
    --bucket drum-transcription-bucket \
    --cors-configuration file://cors-config.json
```

### 6. Create IAM User and Policy

Create IAM policy (`iam-policy.json`):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::drum-transcription-bucket/*"
        },
        {
            "Effect": "Allow",
            "Action": ["s3:ListBucket"],
            "Resource": "arn:aws:s3:::drum-transcription-bucket"
        }
    ]
}
```

Create the policy and user:
```bash
# Create policy
aws iam create-policy \
    --policy-name DrumTranscriptionS3Policy \
    --policy-document file://iam-policy.json

# Create user
aws iam create-user --user-name drum-transcription-app

# Attach policy
aws iam attach-user-policy \
    --user-name drum-transcription-app \
    --policy-arn arn:aws:iam::YOUR-ACCOUNT-ID:policy/DrumTranscriptionS3Policy

# Create access keys
aws iam create-access-key --user-name drum-transcription-app
```

## S3 Bucket Structure

The application uses the following folder structure in S3:

```
drum-transcription-bucket/
├── uploads/          # Original uploaded audio files
│   └── {user_id}/
│       └── {timestamp}_{hash}_{filename}
├── processed/        # Processed transcriptions and MIDI files
│   └── {user_id}/
│       └── {job_id}/
│           ├── transcription.json
│           └── output.mid
└── temp/            # Temporary files (auto-deleted after 1 day)
    └── {job_id}/
        └── {temp_files}
```

## Integration with Application

The application automatically uses S3 when configured. The `S3Service` class in `backend/app/services/s3.py` provides:

- File upload with encryption
- File download and streaming
- Presigned URL generation for temporary access
- File listing and deletion
- Automatic fallback to local storage if S3 is not configured

### Usage Example

```python
from app.services.s3 import s3_service

# Upload a file
s3_url = await s3_service.upload_file(
    file_data=audio_file,
    key="uploads/user123/audio.mp3",
    content_type="audio/mpeg"
)

# Generate presigned URL for download
download_url = await s3_service.generate_presigned_url(
    key="processed/user123/job456/output.mid",
    expiration=3600  # 1 hour
)
```

## Monitoring and Costs

### CloudWatch Metrics
- Monitor bucket size and request metrics in AWS CloudWatch
- Set up alarms for unusual activity

### Cost Optimization
- Lifecycle policies automatically delete old files
- Consider using S3 Intelligent-Tiering for long-term storage
- Monitor costs through AWS Cost Explorer

### Storage Classes
- Standard: For frequently accessed files (uploads, recent processed files)
- Standard-IA: For older processed files (configure after 30 days)
- Glacier: For long-term archival (optional)

## Security Best Practices

1. **Never commit AWS credentials** - Always use environment variables
2. **Use IAM roles** in production instead of access keys when possible
3. **Enable MFA** for the AWS root account
4. **Regularly rotate** access keys
5. **Monitor access** through CloudTrail logs
6. **Use bucket policies** to restrict access by IP if needed

## Troubleshooting

### Common Issues

1. **Access Denied Errors**
   - Check IAM policy is attached to user
   - Verify bucket name matches configuration
   - Ensure credentials are correctly set in `.env`

2. **Bucket Already Exists**
   - S3 bucket names are globally unique
   - Add a unique suffix to your bucket name

3. **CORS Errors**
   - Verify CORS configuration includes your frontend URL
   - Check browser console for specific CORS error messages

4. **File Upload Failures**
   - Check file size limits (50MB default)
   - Verify S3 service is configured (`s3_service.is_configured()`)
   - Check CloudWatch logs for detailed errors

### Testing S3 Connection

Run the test script to verify everything is working:
```bash
python scripts/test_s3.py
```

This will test:
- Bucket access
- File upload/download
- Encryption
- Lifecycle policies
- CORS configuration