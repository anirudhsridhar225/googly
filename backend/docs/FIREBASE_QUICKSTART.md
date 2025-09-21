# Firebase Quick Start with UV

This guide will help you quickly set up Firebase for the Legal Document Classification System using `uv`.

## Prerequisites

1. **Install UV** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # or
   pip install uv
   ```

2. **Create Firebase Project** (if not done):
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project
   - Enable Firestore Database

## Quick Setup (3 steps)

### Step 1: Configure Environment

1. **Download Service Account Key**:
   - Go to Google Cloud Console → IAM & Admin → Service Accounts
   - Create service account with Firestore permissions
   - Download JSON key as `service-account-key.json` in the `backend/` folder

2. **Update .env file**:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your Firebase project details
   ```

### Step 2: Run Setup Script

```bash
cd backend
./setup_firebase.sh
```

This script will:
- ✅ Validate your configuration
- ✅ Initialize Firebase connection
- ✅ Create required collections
- ✅ Add sample data
- ✅ Run connection tests

### Step 3: Verify Setup

```bash
# Quick connection test
uv run test_firestore_client.py

# Or run full test suite
uv run python -m pytest test_firestore_client.py -v
```

## Manual Setup (if you prefer)

If you want to run each step manually:

```bash
cd backend

# 1. Install dependencies
uv sync

# 2. Initialize Firebase
uv run initialize_firebase.py

# 3. Test connection
uv run test_firestore_client.py

# 4. Run your app
uv run python main.py
```

## Troubleshooting

### Common Issues

1. **"Configuration validation failed"**
   - Check your `.env` file has all required values
   - Verify your Firebase project ID is correct

2. **"Permission denied"**
   - Ensure your service account has the right permissions:
     - Cloud Datastore User
     - Firebase Admin SDK Administrator Service Agent

3. **"Project not found"**
   - Double-check your `GOOGLE_CLOUD_PROJECT_ID` in `.env`
   - Make sure Firestore is enabled in your Firebase project

4. **"Service account key not found"**
   - Download the JSON key from Google Cloud Console
   - Save it as `service-account-key.json` in the backend folder
   - Update `GOOGLE_APPLICATION_CREDENTIALS` path in `.env`

### Getting Help

If you encounter issues:

1. **Check logs**: The setup script provides detailed error messages
2. **Verify credentials**: Run `uv run python -c "from config import validate_configuration; validate_configuration()"`
3. **Test connection**: Run `uv run test_firestore_client.py` for detailed diagnostics

## What's Created

After successful setup, you'll have:

- ✅ Firestore database with required collections:
  - `legal_documents`
  - `semantic_buckets`
  - `document_classifications`
  - `classification_rules`
  - `review_queue`

- ✅ Sample data for testing
- ✅ Validated configuration
- ✅ Working Firebase connection

## Next Steps

1. **Create Indexes**: Follow the index creation guide in Firebase Console
2. **Upload Documents**: Start adding your legal reference documents
3. **Run Tests**: Execute the full test suite to verify everything works
4. **Start Classifying**: Begin using the classification API

Your Firebase setup is now complete! 🎉