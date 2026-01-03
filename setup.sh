#!/bin/bash
# setup.sh

# อัปเดต package lists
apt-get update

# ติดตั้ง dependencies
apt-get install -y python3 python3-pip

# ติดตั้ง Python packages
pip3 install -r requirements.txt

# สร้างโฟลเดอร์ที่จำเป็น
mkdir -p save_data/{images,documents,certificates,exercise_images,lessons,quiz_results,certificates_files}
