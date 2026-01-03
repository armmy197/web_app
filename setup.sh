#!/bin/bash

# Update package list
apt-get update -y

# Install system dependencies for Google Sheets and SSL
apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev

# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# Install Python packages from requirements.txt
pip install --no-cache-dir -r requirements.txt

# Create necessary directories
mkdir -p save_data/images
mkdir -p save_data/documents
mkdir -p save_data/certificates
mkdir -p save_data/exercise_images
mkdir -p save_data/lessons
mkdir -p save_data/quiz_results
mkdir -p save_data/certificates_files

# Make directories writable
chmod -R 755 save_data 2>/dev/null || true
