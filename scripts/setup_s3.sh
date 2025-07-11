#!/bin/bash

# S3 Bucket Setup Script for Drum Transcription Service
# This script creates and configures an S3 bucket with all necessary settings

set -e

# Configuration variables
BUCKET_NAME=${BUCKET_NAME:-"drum-transcription-bucket"}
AWS_REGION=${AWS_REGION:-"us-east-1"}
IAM_USER_NAME="drum-transcription-app"
POLICY_NAME="DrumTranscriptionS3Policy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting S3 bucket setup for Drum Transcription Service${NC}"

# Function to check if bucket exists
bucket_exists() {
    aws s3api head-bucket --bucket "$1" 2>/dev/null
    return $?
}

# 1. Create S3 bucket
echo -e "\n${YELLOW}Step 1: Creating S3 bucket...${NC}"
if bucket_exists "$BUCKET_NAME"; then
    echo -e "${YELLOW}Bucket $BUCKET_NAME already exists${NC}"
else
    aws s3 mb "s3://$BUCKET_NAME" --region "$AWS_REGION"
    echo -e "${GREEN}✓ Bucket created successfully${NC}"
fi

# 2. Block public access
echo -e "\n${YELLOW}Step 2: Configuring public access block...${NC}"
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo -e "${GREEN}✓ Public access blocked${NC}"

# 3. Enable server-side encryption
echo -e "\n${YELLOW}Step 3: Enabling server-side encryption (AES256)...${NC}"
aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }
        ]
    }'

echo -e "${GREEN}✓ Encryption enabled${NC}"

# 4. Create and apply lifecycle policy
echo -e "\n${YELLOW}Step 4: Setting up lifecycle policies...${NC}"
cat > /tmp/lifecycle-policy.json <<EOF
{
    "Rules": [
        {
            "ID": "CleanupTempFiles",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "temp/"
            },
            "Expiration": {
                "Days": 1
            }
        },
        {
            "ID": "CleanupProcessedFiles",
            "Status": "Enabled",
            "Filter": {
                "Prefix": "processed/"
            },
            "Expiration": {
                "Days": 30
            }
        }
    ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --lifecycle-configuration file:///tmp/lifecycle-policy.json

echo -e "${GREEN}✓ Lifecycle policies configured${NC}"

# 5. Configure CORS
echo -e "\n${YELLOW}Step 5: Configuring CORS...${NC}"
cat > /tmp/cors-config.json <<EOF
{
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
            "AllowedOrigins": [
                "http://localhost:3000",
                "http://localhost:8000"
            ],
            "ExposeHeaders": ["ETag"],
            "MaxAgeSeconds": 3600
        }
    ]
}
EOF

aws s3api put-bucket-cors \
    --bucket "$BUCKET_NAME" \
    --cors-configuration file:///tmp/cors-config.json

echo -e "${GREEN}✓ CORS configured${NC}"

# 6. Create IAM policy
echo -e "\n${YELLOW}Step 6: Creating IAM policy...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

cat > /tmp/iam-policy.json <<EOF
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
            "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": "arn:aws:s3:::$BUCKET_NAME"
        }
    ]
}
EOF

# Check if policy exists
POLICY_ARN="arn:aws:iam::$ACCOUNT_ID:policy/$POLICY_NAME"
if aws iam get-policy --policy-arn "$POLICY_ARN" 2>/dev/null; then
    echo -e "${YELLOW}Policy already exists${NC}"
else
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file:///tmp/iam-policy.json
    echo -e "${GREEN}✓ IAM policy created${NC}"
fi

# 7. Create IAM user
echo -e "\n${YELLOW}Step 7: Creating IAM user...${NC}"
if aws iam get-user --user-name "$IAM_USER_NAME" 2>/dev/null; then
    echo -e "${YELLOW}User already exists${NC}"
else
    aws iam create-user --user-name "$IAM_USER_NAME"
    echo -e "${GREEN}✓ IAM user created${NC}"
fi

# Attach policy to user
aws iam attach-user-policy \
    --user-name "$IAM_USER_NAME" \
    --policy-arn "$POLICY_ARN"

echo -e "${GREEN}✓ Policy attached to user${NC}"

# 8. Create access keys
echo -e "\n${YELLOW}Step 8: Creating access keys...${NC}"
echo -e "${YELLOW}Note: If keys already exist, you may need to delete old ones first${NC}"

# Create new access key
ACCESS_KEY_OUTPUT=$(aws iam create-access-key --user-name "$IAM_USER_NAME" 2>/dev/null || echo "")

if [ -n "$ACCESS_KEY_OUTPUT" ]; then
    ACCESS_KEY_ID=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.AccessKeyId')
    SECRET_ACCESS_KEY=$(echo "$ACCESS_KEY_OUTPUT" | jq -r '.AccessKey.SecretAccessKey')
    
    echo -e "${GREEN}✓ Access keys created${NC}"
    echo -e "\n${YELLOW}Add these to your .env file:${NC}"
    echo "AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID"
    echo "AWS_SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY"
    echo "AWS_S3_BUCKET=$BUCKET_NAME"
    echo "AWS_REGION=$AWS_REGION"
    
    # Save to env.example
    cat >> .env.example <<EOF

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_S3_BUCKET=$BUCKET_NAME
AWS_REGION=$AWS_REGION
EOF
    
else
    echo -e "${RED}Failed to create access keys. Keys might already exist.${NC}"
    echo -e "${YELLOW}To create new keys, first delete existing ones with:${NC}"
    echo "aws iam delete-access-key --user-name $IAM_USER_NAME --access-key-id <existing-key-id>"
fi

# Clean up temporary files
rm -f /tmp/lifecycle-policy.json /tmp/cors-config.json /tmp/iam-policy.json

echo -e "\n${GREEN}S3 bucket setup complete!${NC}"
echo -e "${YELLOW}Bucket name: $BUCKET_NAME${NC}"
echo -e "${YELLOW}Region: $AWS_REGION${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Add the AWS credentials to your .env file"
echo "2. Test the setup using the test_s3.py script"
echo "3. Update your application code to use S3 for file storage"