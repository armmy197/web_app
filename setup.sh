#!/bin/bash

# อัปเดตแพ็คเกจระบบ
apt-get update

# ติดตั้ง dependencies ของระบบสำหรับ Google Sheets
apt-get install -y build-essential libssl-dev libffi-dev python3-dev

# อัปเกรด pip
pip install --upgrade pip

# ติดตั้งแพ็คเกจ Python
pip install --no-cache-dir -r requirements.txt

# สร้างไดเรกทอรีที่จำเป็น
mkdir -p save_data/images
mkdir -p save_data/documents
mkdir -p save_data/certificates
mkdir -p save_data/exercise_images
mkdir -p save_data/lessons
mkdir -p save_data/quiz_results
mkdir -p save_data/certificates_files
