# Render Deployment Guide

This guide explains how to deploy the Legal Document Severity Classification System to Render.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **Google Cloud Project**: Set up with Firestore and Gemini API enabled
3. **Service Account**: Create a Google Cloud service account with appropriate permissions

## Environment Variables

Set these environment variables in your Render service:

### Required Variables

```bash
# Gemini API Configuration
GEMINI_API_KEY=your_actual_gemini_api_key

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT_ID=your_actual_project_id
FIRESTORE_DATABASE_ID=(default)

# Google Cloud Service Account (as JSON string)
SERVICE_KEY_JSON={"type":"service_account","project_id":"..."}
```

### Optional Variables (with defaults)

```bash
# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
WORKERS=2

# Performance Configuration
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=300
GEMINI_RATE_LIMIT=60

# Security Configuration
CORS_ORIGINS=https://yourdomain.com
API_KEY_HEADER=X-API-Key

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30
```

## Render Service Configuration

### 1. Create Web Service

1. Connect your GitHub repository to Render
2. Create a new **Web Service**
3. Select your repository and branch

### 2. Service Settings

```yaml
Name: legal-document-classifier
Environment: Python 3
Region: Choose your preferred region
Branch: main (or your deployment branch)
Root Directory: backend
```

### 3. Build & Deploy Settings

```yaml
Build Command: ./render-build.sh
Start Command: ./render-start.sh
```

### 4. Environment Variables

Add all the required environment variables listed above in the Render dashboard.

## Google Cloud Service Account Setup

### 1. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create legal-doc-classifier \
    --description="Service account for legal document classifier" \
    --display-name="Legal Document Classifier"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:legal-doc-classifier@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:legal-doc-classifier@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### 2. Generate Service Account Key

```bash
# Generate key file
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=legal-doc-classifier@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Convert to single-line JSON for Render environment variable
cat service-account-key.json | jq -c . | pbcopy
```

### 3. Set SERVICE_KEY_JSON

Paste the single-line JSON as the value for the `SERVICE_KEY_JSON` environment variable in Render.

## Deployment Process

1. **Push Code**: Push your code to the connected GitHub repository
2. **Auto Deploy**: Render will automatically build and deploy
3. **Monitor Logs**: Check the deployment logs in Render dashboard
4. **Test Endpoints**: Verify the service is running by accessing health check endpoints

## Health Check Endpoints

Once deployed, you can verify the service is running:

```bash
# Health check
curl https://your-service-name.onrender.com/health

# API documentation
curl https://your-service-name.onrender.com/docs
```

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check that all dependencies are in `pyproject.toml`
   - Verify build script permissions: `chmod +x render-build.sh`

2. **Service Account Issues**
   - Ensure `SERVICE_KEY_JSON` is properly formatted (single-line JSON)
   - Verify service account has necessary permissions

3. **Environment Variables**
   - Check all required variables are set in Render dashboard
   - Ensure no placeholder values in production

4. **Firestore Connection**
   - Verify project ID is correct
   - Check service account permissions
   - Ensure Firestore is enabled in Google Cloud Console

### Debugging

Check logs in Render dashboard:
- Build logs for deployment issues
- Service logs for runtime issues

### Performance Optimization

1. **Scaling**: Adjust `WORKERS` environment variable based on traffic
2. **Caching**: Enable Redis if needed for high-traffic scenarios
3. **Monitoring**: Use Render metrics and set up alerts

## Security Considerations

1. **Environment Variables**: Never commit sensitive values to git
2. **CORS**: Set specific origins instead of "*" in production
3. **API Keys**: Rotate keys regularly
4. **Service Account**: Use principle of least privilege

## Cost Optimization

1. **Instance Type**: Start with basic tier and scale as needed
2. **Auto-scaling**: Configure based on actual usage patterns
3. **Monitoring**: Set up alerts for unusual resource usage

## Support

For deployment issues:
1. Check Render documentation
2. Review service logs
3. Verify Google Cloud configuration
4. Test locally with production environment variables