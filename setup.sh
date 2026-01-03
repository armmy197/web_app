#!/bin/bash

# Update system packages
apt-get update
apt-get upgrade -y

# Install system dependencies
apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libbz2-dev \
    liblzma-dev

# Create necessary directories
mkdir -p save_data/images
mkdir -p save_data/documents
mkdir -p save_data/certificates
mkdir -p save_data/exercise_images
mkdir -p save_data/lessons
mkdir -p save_data/quiz_results
mkdir -p save_data/certificates_files
mkdir -p images_logo

# Install Python packages
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt
