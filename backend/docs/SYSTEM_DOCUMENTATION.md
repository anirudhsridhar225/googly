# Legal Document Severity Classification System

## Overview

The Legal Document Severity Classification System is an AI-powered solution that classifies legal documents by severity level using a sophisticated bucketed context mechanism. The system leverages Google's Gemini model for embeddings and classification, with Firestore for scalable document storage.

## System Architecture

### Core Components

1. **Document Processing Service** - Handles document ingestion and text extraction
2. **Bucket Management Service** - Creates and maintains semantic buckets using clustering
3. **Classification Service** - Performs document classification using bucket-based context
4. **Rule Engine** - Applies deterministic rules and overrides
5. **Audit Service** - Manages comprehensive logging and audit trails
6. **Monitoring Service** - Tracks performance metrics and system health

### Technology Stack

- **Backend Framework**: FastAPI
- **AI/ML**: Google Gemini API
- **Database**: Google Firestore
- **Language**: Python 3.11+
- **Deployment**: Render (or any container platform)

## API Endpoints

### Health Check Endpoints

- `GET /health` - Comprehensive health check with component status
- `GET /health/ready` - Readiness check for deployment orchestration
- `GET /health/live` - Basic liveness check
- `GET /system/info` - System information for monitoring

### Classification Endpoints

- `POST /api/classification/classify` - Classify a single document
- `POST /api/classification/batch` - Batch document classification
- `GET /api/classification/result/{id}` - Get classification result

### Reference Document Management

- `POST /api/reference/upload` - Upload reference documents
- `GET /api/reference/documents` - List reference documents
- `DELETE /api/reference/{id}` - Delete reference document

### Bucket Management

- `GET /api/reference/buckets` - List semantic buckets
- `POST /api/reference/buckets/rebuild` - Rebuild bucket structure

## Configuration

### Environment Variables

#### Required Variables

```bash
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CLOUD_PROJECT_ID=your_project_id
```

#### Optional Variables (with defaults)

```bash
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=1

# Classification settings
DEFAULT_CONFIDENCE_THRESHOLD_AUTO_ACCEPT=0.85
DEFAULT_CONFIDENCE_THRESHOLD_HUMAN_REVIEW=0.60
DEFAULT_TOP_K_BUCKETS=3
DEFAULT_TOP_N_CONTEXT_CHUNKS=5

# Performance settings
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=300
GEMINI_RATE_LIMIT=60

# Security settings
CORS_ORIGINS=*
API_KEY_HEADER=X-API-Key

# Monitoring settings
ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30
```

### Google Cloud Setup

1. **Create Google Cloud Project**
2. **Enable APIs**:
   - Firestore API
   - Gemini API (AI Platform)
3. **Create Service Account** with roles:
   - Firestore User
   - AI Platform User
4. **Generate Service Account Key**

For local development, save the key file and set:
```bash
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
```

For Render deployment, set the key as JSON string:
```bash
SERVICE_KEY_JSON={"type":"service_account",...}
```

## Deployment

### Local Development

1. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   # or
   uv pip install -r pyproject.toml
   ```

2. **Set Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Run Application**:
   ```bash
   uvicorn main:app --reload
   ```

### Render Deployment

1. **Connect Repository** to Render
2. **Create Web Service** with settings:
   - **Build Command**: `./render-build.sh`
   - **Start Command**: `./render-start.sh`
   - **Environment**: Python 3
3. **Set Environment Variables** in Render dashboard
4. **Deploy**

See `RENDER_DEPLOYMENT.md` for detailed deployment instructions.

## System Initialization

The system performs comprehensive startup checks:

1. **Configuration Validation** - Validates all environment variables
2. **Environment Check** - Ensures required variables are present
3. **Firestore Connection** - Tests database connectivity
4. **Schema Initialization** - Sets up Firestore collections
5. **Gemini API Validation** - Validates AI service configuration
6. **Performance Setup** - Initializes monitoring systems
7. **Audit Setup** - Configures audit logging

## Monitoring and Health Checks

### Health Check Endpoints

- **Liveness**: `/health/live` - Basic service availability
- **Readiness**: `/health/ready` - Service ready to accept traffic
- **Health**: `/health` - Comprehensive component health status

### Monitoring Metrics

- Classification latency and throughput
- Error rates by component
- Confidence score distributions
- Bucket selection patterns
- Resource utilization

## Security Considerations

1. **API Keys**: Store securely in environment variables
2. **CORS**: Configure specific origins for production
3. **Rate Limiting**: Built-in rate limiting per endpoint
4. **Input Validation**: Comprehensive request validation
5. **Audit Logging**: All operations are logged for compliance

## Troubleshooting

### Common Issues

1. **Configuration Errors**:
   - Check environment variables are set correctly
   - Verify Google Cloud credentials

2. **Firestore Connection Issues**:
   - Ensure Firestore API is enabled
   - Check service account permissions
   - Verify project ID is correct

3. **Gemini API Issues**:
   - Verify API key is valid
   - Check rate limits
   - Ensure AI Platform API is enabled

4. **Performance Issues**:
   - Monitor resource usage via `/system/info`
   - Check health status via `/health`
   - Review application logs

### Debugging

1. **Enable Debug Logging**:
   ```bash
   LOG_LEVEL=DEBUG
   DEBUG=true
   ```

2. **Check System Status**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/system/info
   ```

3. **Review Startup Logs** for initialization issues

## Development Guidelines

### Code Structure

- **Routes**: API endpoint definitions in `routes/`
- **Services**: Business logic in individual service files
- **Models**: Data models and schemas in `models.py`
- **Config**: Configuration management in `config.py`
- **Tests**: Comprehensive test suite with >90% coverage

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest -m "unit"
pytest -m "integration"
```

### Contributing

1. Follow existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure all health checks pass
5. Test deployment on staging environment

## Support

For technical support:
1. Check system health endpoints
2. Review application logs
3. Consult troubleshooting guide
4. Contact development team