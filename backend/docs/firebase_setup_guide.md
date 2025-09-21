# Firebase Setup Guide (Using UV)

## Prerequisites

First, make sure you have `uv` installed:
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

## Step 1: Create Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project" or "Add project"
3. Enter your project name (e.g., "legal-document-classifier")
4. Enable Google Analytics if desired
5. Click "Create project"

## Step 2: Enable Firestore Database

1. In your Firebase project console, go to "Firestore Database"
2. Click "Create database"
3. Choose "Start in test mode" (you can secure it later)
4. Select a location for your database (choose one close to your users)

## Step 3: Create Service Account Key

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Select your Firebase project
3. Go to "IAM & Admin" > "Service Accounts"
4. Click "Create Service Account"
5. Enter details:
   - Name: `legal-document-classifier-service`
   - Description: `Service account for legal document classification system`
6. Click "Create and Continue"
7. Add roles:
   - `Cloud Datastore User`
   - `Firebase Admin SDK Administrator Service Agent`
8. Click "Continue" and "Done"
9. Find your service account in the list and click on it
10. Go to "Keys" tab
11. Click "Add Key" > "Create new key"
12. Choose "JSON" format
13. Download the key file and save it as `service-account-key.json` in your backend folder

## Step 4: Set up Environment Variables

Update your `.env` file in your backend directory:

```env
# Gemini API Configuration
GEMINI_API_KEY="your_gemini_api_key_here"

# Google Cloud Configuration  
GOOGLE_CLOUD_PROJECT_ID="your-firebase-project-id"
FIRESTORE_DATABASE_ID="(default)"
GOOGLE_APPLICATION_CREDENTIALS="./service-account-key.json"

# Google Cloud Vision API
VISION_API_ENABLED=true

# Application Configuration
ENVIRONMENT="development"
LOG_LEVEL="INFO"

# Classification Configuration
DEFAULT_CONFIDENCE_THRESHOLD_AUTO_ACCEPT=0.85
DEFAULT_CONFIDENCE_THRESHOLD_HUMAN_REVIEW=0.60
DEFAULT_TOP_K_BUCKETS=3
DEFAULT_TOP_N_CONTEXT_CHUNKS=5
```

Replace:
- `your_gemini_api_key_here` with your actual Gemini API key
- `your-firebase-project-id` with your Firebase project ID

## Step 5: Initialize Firebase using UV

Run the Firebase initialization script:

```bash
cd backend
uv run initialize_firebase.py
```

This will:
- Validate your configuration
- Test the Firestore connection
- Initialize required collections
- Create sample data
- Document required indexes

## Step 6: Install Dependencies (if needed)

If you need to install additional dependencies:

```bash
cd backend
uv add google-cloud-firestore firebase-admin
```

## Step 7: Run Tests

Test your Firebase setup:

```bash
cd backend
uv run python -m pytest test_firestore_client.py -v
```