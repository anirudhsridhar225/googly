# Deployment Checklist

## Before Deployment

### 1. Environment Variables (Required)
Update these in your `.env` file or deployment environment:

```bash
# Get from https://makersuite.google.com/app/apikey
GEMINI_API_KEY="your_actual_gemini_api_key"

# Your Google Cloud Project ID
GOOGLE_CLOUD_PROJECT_ID="your_actual_project_id"

# For Render deployment, set this as environment variable
SERVICE_KEY_JSON='{"type":"service_account","project_id":"...your_service_account_json..."}'
```

### 2. Google Cloud Setup
1. Create a Google Cloud project
2. Enable Firestore API
3. Create a service account with Firestore permissions
4. Download service account key (for local) or copy JSON (for Render)

### 3. Dependencies
All dependencies are in `pyproject.toml` - they'll install automatically.

## Deployment Commands

### Local Development
```bash
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

### Render Deployment
1. Connect your GitHub repo to Render
2. Set environment variables in Render dashboard
3. Deploy automatically on push

## Health Check
Once deployed, test these endpoints:
- `GET /` - Basic health check
- `GET /health` - Detailed system health
- `GET /docs` - API documentation

## Common Issues
- **Firestore errors**: Check service account permissions
- **Gemini API errors**: Verify API key is correct
- **Import errors**: All fixed in this version

The system will start even if some services fail - check logs for details.