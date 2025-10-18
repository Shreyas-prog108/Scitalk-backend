#!/bin/bash

# AWS Lambda Deployment Script using Container Images
# Deploys SciTalk Backend to AWS Lambda

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="${FUNCTION_NAME:-scitalk-backend}"
ECR_REPO_NAME="${ECR_REPO_NAME:-scitalk-backend}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")

echo -e "${BLUE}🚀 Deploying SciTalk Backend to AWS Lambda...${NC}"

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not installed. Please install it first.${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not installed. Please install it first.${NC}"
    exit 1
fi

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo -e "${RED}❌ AWS credentials not configured. Run: aws configure${NC}"
    exit 1
fi

if [ -z "$GROQ_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  GROQ_API_KEY not set. The Lambda function will need this configured.${NC}"
fi

# ECR Registry URL
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPO_NAME}:latest"

echo -e "${BLUE}📋 Configuration:${NC}"
echo -e "  Region: ${AWS_REGION}"
echo -e "  Function: ${FUNCTION_NAME}"
echo -e "  ECR Repo: ${ECR_REPO_NAME}"
echo -e "  Image URI: ${IMAGE_URI}"

# Step 1: Create ECR repository if it doesn't exist
echo -e "\n${BLUE}1️⃣  Checking ECR repository...${NC}"
if ! aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} &> /dev/null; then
    echo -e "${YELLOW}Creating ECR repository...${NC}"
    aws ecr create-repository \
        --repository-name ${ECR_REPO_NAME} \
        --region ${AWS_REGION} \
        --image-scanning-configuration scanOnPush=true \
        --output text
    echo -e "${GREEN}✅ ECR repository created${NC}"
else
    echo -e "${GREEN}✅ ECR repository exists${NC}"
fi

# Step 2: Login to ECR
echo -e "\n${BLUE}2️⃣  Logging into ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${ECR_REGISTRY}
echo -e "${GREEN}✅ Logged into ECR${NC}"

# Step 3: Build Docker image
echo -e "\n${BLUE}3️⃣  Building Docker image...${NC}"
docker build --platform linux/amd64 -t ${ECR_REPO_NAME}:latest .
echo -e "${GREEN}✅ Docker image built${NC}"

# Step 4: Tag image
echo -e "\n${BLUE}4️⃣  Tagging Docker image...${NC}"
docker tag ${ECR_REPO_NAME}:latest ${IMAGE_URI}
echo -e "${GREEN}✅ Image tagged${NC}"

# Step 5: Push to ECR
echo -e "\n${BLUE}5️⃣  Pushing image to ECR...${NC}"
docker push ${IMAGE_URI}
echo -e "${GREEN}✅ Image pushed to ECR${NC}"

# Step 6: Create or update Lambda function
echo -e "\n${BLUE}6️⃣  Deploying Lambda function...${NC}"

# Check if function exists
if aws lambda get-function --function-name ${FUNCTION_NAME} --region ${AWS_REGION} &> /dev/null; then
    echo -e "${YELLOW}Updating existing Lambda function...${NC}"
    aws lambda update-function-code \
        --function-name ${FUNCTION_NAME} \
        --image-uri ${IMAGE_URI} \
        --region ${AWS_REGION} \
        --output text
    
    # Wait for update to complete
    aws lambda wait function-updated \
        --function-name ${FUNCTION_NAME} \
        --region ${AWS_REGION}
    
    # Update environment variables if GROQ_API_KEY is set
    if [ ! -z "$GROQ_API_KEY" ]; then
        aws lambda update-function-configuration \
            --function-name ${FUNCTION_NAME} \
            --environment "Variables={GROQ_API_KEY=${GROQ_API_KEY}}" \
            --region ${AWS_REGION} \
            --output text
    fi
    
    echo -e "${GREEN}✅ Lambda function updated${NC}"
else
    echo -e "${YELLOW}Creating new Lambda function...${NC}"
    
    # Create execution role if it doesn't exist
    ROLE_NAME="${FUNCTION_NAME}-role"
    ROLE_ARN=$(aws iam get-role --role-name ${ROLE_NAME} --query 'Role.Arn' --output text 2>/dev/null || echo "")
    
    if [ -z "$ROLE_ARN" ]; then
        echo -e "${YELLOW}Creating IAM role...${NC}"
        
        # Create trust policy
        cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
        
        ROLE_ARN=$(aws iam create-role \
            --role-name ${ROLE_NAME} \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            --query 'Role.Arn' \
            --output text)
        
        # Attach basic Lambda execution policy
        aws iam attach-role-policy \
            --role-name ${ROLE_NAME} \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
        
        echo -e "${GREEN}✅ IAM role created${NC}"
        echo -e "${YELLOW}Waiting for role to propagate...${NC}"
        sleep 10
    fi
    
    # Create Lambda function
    ENV_VARS="Variables={}"
    if [ ! -z "$GROQ_API_KEY" ]; then
        ENV_VARS="Variables={GROQ_API_KEY=${GROQ_API_KEY}}"
    fi
    
    aws lambda create-function \
        --function-name ${FUNCTION_NAME} \
        --package-type Image \
        --code ImageUri=${IMAGE_URI} \
        --role ${ROLE_ARN} \
        --timeout 30 \
        --memory-size 1024 \
        --environment "${ENV_VARS}" \
        --region ${AWS_REGION} \
        --output text
    
    echo -e "${GREEN}✅ Lambda function created${NC}"
fi

# Step 7: Create Function URL (Lambda URL for direct HTTP access)
echo -e "\n${BLUE}7️⃣  Setting up Lambda Function URL...${NC}"
FUNCTION_URL=$(aws lambda get-function-url-config \
    --function-name ${FUNCTION_NAME} \
    --region ${AWS_REGION} \
    --query 'FunctionUrl' \
    --output text 2>/dev/null || echo "")

if [ -z "$FUNCTION_URL" ] || [ "$FUNCTION_URL" == "None" ]; then
    FUNCTION_URL=$(aws lambda create-function-url-config \
        --function-name ${FUNCTION_NAME} \
        --auth-type NONE \
        --cors "AllowOrigins=*,AllowMethods=*,AllowHeaders=*" \
        --region ${AWS_REGION} \
        --query 'FunctionUrl' \
        --output text)
    
    # Add permission for function URL
    aws lambda add-permission \
        --function-name ${FUNCTION_NAME} \
        --statement-id FunctionURLAllowPublicAccess \
        --action lambda:InvokeFunctionUrl \
        --principal "*" \
        --function-url-auth-type NONE \
        --region ${AWS_REGION} \
        --output text 2>/dev/null || true
    
    echo -e "${GREEN}✅ Function URL created${NC}"
else
    echo -e "${GREEN}✅ Function URL already exists${NC}"
fi

# Summary
echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "\n${BLUE}📋 Deployment Details:${NC}"
echo -e "  Function: ${FUNCTION_NAME}"
echo -e "  Region: ${AWS_REGION}"
echo -e "  Image: ${IMAGE_URI}"
echo -e "\n${BLUE}🔗 API Endpoint:${NC}"
echo -e "  ${GREEN}${FUNCTION_URL}${NC}"
echo -e "\n${BLUE}📚 API Documentation:${NC}"
echo -e "  ${FUNCTION_URL}docs"
echo -e "\n${BLUE}🧪 Test Deployment:${NC}"
echo -e "  curl ${FUNCTION_URL}"
echo -e "  curl -X POST ${FUNCTION_URL}api/demo/full-workflow"
echo -e "\n${YELLOW}⚠️  Don't forget to set GROQ_API_KEY environment variable if not already set:${NC}"
echo -e "  aws lambda update-function-configuration \\"
echo -e "    --function-name ${FUNCTION_NAME} \\"
echo -e "    --environment 'Variables={GROQ_API_KEY=your_key_here}' \\"
echo -e "    --region ${AWS_REGION}"
echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
