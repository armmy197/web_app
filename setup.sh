#!/bin/bash

# Update system packages
apt-get update

# Install system dependencies for Google Sheets
apt-get install -y build-essential libssl-dev libffi-dev python3-dev

# Upgrade pip
pip install --upgrade pip

# Install Python packages
pip install --no-cache-dir streamlit==1.28.1
pip install --no-cache-dir pandas==2.1.3
pip install --no-cache-dir gspread==5.11.3
pip install --no-cache-dir google-auth==2.23.0
pip install --no-cache-dir google-auth-oauthlib==1.1.0
pip install --no-cache-dir google-auth-httplib2==0.1.0
pip install --no-cache-dir google-api-python-client==2.108.0
pip install --no-cache-dir oauth2client==4.1.3
pip install --no-cache-dir Pillow==10.1.0
pip install --no-cache-dir pyOpenSSL==23.2.0

# Create necessary directories
mkdir -p save_data/images
mkdir -p save_data/documents
mkdir -p save_data/certificates
mkdir -p save_data/exercise_images
mkdir -p save_data/lessons
mkdir -p save_data/quiz_results
mkdir -p save_data/certificates_files
