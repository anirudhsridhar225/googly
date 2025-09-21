# Configuration Guide

## Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Fill in the required values in `.env`:

### Required Configuration

- `GEMINI_API_KEY`: Your Google Gemini API key
- `GOOGLE_CLOUD_PROJECT_ID`: Your Google Cloud project ID

### Optional Configuration

- `FIRESTORE_DATABASE_ID`: Firestore database ID (default: "(default)")
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key file (optional if using default credentials)
- `ENVIRONMENT`: Application environment (default: "development")
- `LOG_LEVEL`: Logging level (default: "INFO")

### Classification Configuration

- `DEFAULT_CONFIDENCE_THRESHOLD_AUTO_ACCEPT`: Confidence threshold for auto-acceptance (default: 0.85)
- `DEFAULT_CONFIDENCE_THRESHOLD_HUMAN_REVIEW`: Confidence threshold for human review (default: 0.60)
- `DEFAULT_TOP_K_BUCKETS`: Number of top buckets to select (default: 3)
- `DEFAULT_TOP_N_CONTEXT_CHUNKS`: Number of context chunks to retrieve (default: 5)

## Google Cloud Setup

### 1. Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file as `GEMINI_API_KEY`

### 2. Firestore Setup

1. Create a Google Cloud project
2. Enable the Firestore API
3. Set up authentication:
   - **Option A**: Use Application Default Credentials (recommended for local development)
     ```bash
     gcloud auth application-default login
     ```
   - **Option B**: Use a service account key file
     1. Create a service account in Google Cloud Console
     2. Download the JSON key file
     3. Set `GOOGLE_APPLICATION_CREDENTIALS` to the file path

## Testing Configuration

Run the startup checks to verify your configuration:

```bash
uv run python startup.py
```

This will test:
- Configuration validation
- Firestore connection
- Firestore collections initialization
- Gemini API configuration

## Dependencies

Install all required dependencies:

```bash
uv sync
```

The following packages are required:
- `google-cloud-firestore`: Firestore client
- `google-generativeai`: Gemini API client
- `scikit-learn`: Machine learning algorithms
- `numpy`: Numerical computing
- `python-dotenv`: Environment variable loading
- `pydantic-settings`: Configuration management