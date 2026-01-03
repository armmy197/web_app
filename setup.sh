#!/bin/bash

# อัปเดต pip
pip install --upgrade pip

# ติดตั้ง dependencies
pip install -r requirements.txt

# สร้างโฟลเดอร์ที่จำเป็น
mkdir -p data save_data save_data/images save_data/documents save_data/certificates save_data/exercise_images save_data/lessons save_data/quiz_results save_data/certificates_files images_logo

# สร้างไฟล์ข้อมูลเริ่มต้น
python -c "
import pandas as pd
import os
from datetime import datetime

# สร้างไฟล์ students.xlsx
df_students = pd.DataFrame(columns=['student_id', 'fullname', 'email', 'phone', 'created_date', 'status'])
df_students.to_excel('data/students.xlsx', index=False)

# สร้างไฟล์ courses.xlsx
df_courses = pd.DataFrame(columns=[
    'course_id', 'course_name', 'teacher_id', 'teacher_name', 
    'description', 'image_path', 'jitsi_room', 'max_students', 
    'current_students', 'class_type', 'status', 'security_code', 'created_date'
])
df_courses.to_excel('data/courses.xlsx', index=False)

# สร้างไฟล์ admin.xlsx
df_admin = pd.DataFrame(columns=[
    'teacher_id', 'username', 'password_hash', 'fullname', 
    'email', 'created_at', 'role'
])
df_admin.to_excel('data/admin.xlsx', index=False)

# สร้างไฟล์ students_check.xlsx
df_check = pd.DataFrame(columns=[
    'check_id', 'student_id', 'fullname', 'check_date', 
    'check_time', 'attendance_count', 'status'
])
df_check.to_excel('save_data/students_check.xlsx', index=False)

# สร้างไฟล์ teachers.xlsx
df_teachers = pd.DataFrame(columns=[
    'teacher_id', 'username', 'password_hash', 'fullname', 
    'email', 'phone', 'created_at', 'role', 'status'
])
df_teachers.to_excel('save_data/teachers.xlsx', index=False)

# สร้างไฟล์ student_courses.xlsx
df_student_courses = pd.DataFrame(columns=[
    'enrollment_id', 'student_id', 'fullname', 'course_id', 
    'course_name', 'enrollment_date', 'completion_status', 
    'completion_date', 'certificate_issued'
])
df_student_courses.to_excel('save_data/student_courses.xlsx', index=False)

print('Initial setup completed!')
"

echo "Setup completed successfully!"
