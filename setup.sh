#!/bin/bash

# Create necessary directories
mkdir -p save_data/images
mkdir -p save_data/documents
mkdir -p save_data/certificates
mkdir -p save_data/exercise_images
mkdir -p save_data/lessons
mkdir -p save_data/quiz_results
mkdir -p save_data/certificates_files

# Install Google Sheets dependencies
pip install --upgrade gspread google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client oauth2client

# Create necessary files
touch save_data/lessons/.gitkeep
touch save_data/quiz_results/.gitkeep
