"""
S3 Service for handling file uploads and downloads
"""

import boto3
from botocore.exceptions import ClientError
import structlog
from typing import Optional, BinaryIO
import os
from datetime import datetime
import hashlib

from app.config import settings

logger = structlog.get_logger()


class S3Service:
    """Service for interacting with AWS S3"""
    
    def __init__(self):
        self.bucket_name = settings.AWS_S3_BUCKET
        self.region = settings.AWS_REGION
        
        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, self.bucket_name]):
            logger.warning("S3 credentials not configured, using local file storage")
            self.s3_client = None
        else:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )
            logger.info("S3 client initialized", bucket=self.bucket_name, region=self.region)
    
    def is_configured(self) -> bool:
        """Check if S3 is properly configured"""
        return self.s3_client is not None
    
    def generate_file_key(self, prefix: str, filename: str, user_id: str = None) -> str:
        """Generate a unique S3 key for a file"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_hash = hashlib.md5(f"{filename}{timestamp}".encode()).hexdigest()[:8]
        
        if user_id:
            return f"{prefix}/{user_id}/{timestamp}_{file_hash}_{filename}"
        return f"{prefix}/{timestamp}_{file_hash}_{filename}"
    
    async def upload_file(
        self, 
        file_data: BinaryIO, 
        key: str,
        content_type: str = None,
        metadata: dict = None
    ) -> Optional[str]:
        """Upload a file to S3"""
        if not self.is_configured():
            logger.warning("S3 not configured, cannot upload file")
            return None
        
        try:
            extra_args = {
                'ServerSideEncryption': 'AES256'
            }
            
            if content_type:
                extra_args['ContentType'] = content_type
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_fileobj(
                file_data,
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )
            
            logger.info("File uploaded to S3", key=key, bucket=self.bucket_name)
            
            # Generate the S3 URL
            s3_url = f"s3://{self.bucket_name}/{key}"
            return s3_url
            
        except ClientError as e:
            logger.error("Failed to upload file to S3", error=str(e), key=key)
            raise
        except Exception as e:
            logger.error("Unexpected error uploading to S3", error=str(e), key=key)
            raise
    
    async def download_file(self, key: str, download_path: str) -> bool:
        """Download a file from S3"""
        if not self.is_configured():
            logger.warning("S3 not configured, cannot download file")
            return False
        
        try:
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            
            self.s3_client.download_file(
                self.bucket_name,
                key,
                download_path
            )
            
            logger.info("File downloaded from S3", key=key, path=download_path)
            return True
            
        except ClientError as e:
            logger.error("Failed to download file from S3", error=str(e), key=key)
            return False
        except Exception as e:
            logger.error("Unexpected error downloading from S3", error=str(e), key=key)
            return False
    
    async def get_file_stream(self, key: str):
        """Get a file stream from S3"""
        if not self.is_configured():
            logger.warning("S3 not configured, cannot get file stream")
            return None
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body']
            
        except ClientError as e:
            logger.error("Failed to get file stream from S3", error=str(e), key=key)
            return None
    
    async def delete_file(self, key: str) -> bool:
        """Delete a file from S3"""
        if not self.is_configured():
            logger.warning("S3 not configured, cannot delete file")
            return False
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info("File deleted from S3", key=key)
            return True
            
        except ClientError as e:
            logger.error("Failed to delete file from S3", error=str(e), key=key)
            return False
    
    async def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3"""
        if not self.is_configured():
            return False
        
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error("Error checking file existence", error=str(e), key=key)
            return False
    
    async def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for temporary access to a file"""
        if not self.is_configured():
            logger.warning("S3 not configured, cannot generate presigned URL")
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error("Failed to generate presigned URL", error=str(e), key=key)
            return None
    
    async def list_files(self, prefix: str, max_keys: int = 100) -> list:
        """List files in S3 with a given prefix"""
        if not self.is_configured():
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            if 'Contents' not in response:
                return []
            
            files = []
            for obj in response['Contents']:
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })
            
            return files
            
        except ClientError as e:
            logger.error("Failed to list files from S3", error=str(e), prefix=prefix)
            return []


# Global S3 service instance
s3_service = S3Service()