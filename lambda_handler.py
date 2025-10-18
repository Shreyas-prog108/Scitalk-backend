"""
AWS Lambda handler for SciTalk Backend API
"""
from mangum import Mangum
from app import app

# Create the Lambda handler with API Gateway compatibility
# Mangum handles the translation between Lambda events and ASGI
# FastAPI's CORS middleware will handle all CORS headers
lambda_handler = Mangum(app, lifespan="off")
