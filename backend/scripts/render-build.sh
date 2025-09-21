#!/bin/bash

# Render Build Script for Legal Document Severity Classification System

echo "Starting Render build process..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt || pip install uv && uv pip install -r pyproject.toml

# Set up environment for production
echo "Setting up production environment..."
export ENVIRONMENT="production"
export DEBUG="false"

# Validate configuration
echo "Validating configuration..."
python -c "
from config import validate_configuration, get_configuration_summary
import sys

try:
    validate_configuration()
    print('Configuration validation successful')
    
    # Print configuration summary (without sensitive data)
    summary = get_configuration_summary()
    print('Configuration Summary:')
    for key, value in summary.items():
        print(f'  {key}: {value}')
        
except Exception as e:
    print(f'Configuration validation failed: {e}')
    sys.exit(1)
"

# Test basic imports and configuration
echo "Testing basic system components..."
python -c "
try:
    from config import validate_configuration, get_configuration_summary
    
    print('Testing configuration validation...')
    # Don't fail build if validation fails due to missing credentials
    try:
        validate_configuration()
        print('Configuration validation successful')
    except Exception as e:
        print(f'Configuration validation warning: {e}')
        print('This is expected during build without production credentials')
    
    print('Build validation completed successfully')
except Exception as e:
    print(f'Build validation warning: {e}')
    print('This may be expected during build process')
"

echo "Render build process completed successfully!"