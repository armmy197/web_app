#!/bin/bash

# อัปเดตระบบ
apt-get update

# ติดตั้ง dependencies พื้นฐาน
apt-get install -y \
    python3-dev \
    build-essential

# สร้างโฟลเดอร์ที่จำเป็น
mkdir -p save_data/{images,documents,certificates,exercise_images,lessons,quiz_results,certificates_files}
mkdir -p images_logo

# ติดตั้ง Python packages
pip install --upgrade pip
pip install -r requirements.txt
