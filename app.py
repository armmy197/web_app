import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import os
import json
import time
from pathlib import Path
import uuid
import base64
from PIL import Image
import io
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="ZL TA-Learning (ผู้ช่วยสอน-เรียนออนไลน์)",
    layout="wide",
    page_icon="🎓"
)

# -----------------------------
# Google Sheets Configuration
# -----------------------------
@st.cache_resource
def init_google_sheets():
    """Initialize Google Sheets connection"""
    try:
        # For deployment, use Streamlit secrets
        if 'GOOGLE_CREDENTIALS' in st.secrets:
            credentials_dict = dict(st.secrets['GOOGLE_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
        else:
            # For local development, use service account file
            creds_file = 'credentials.json'
            if os.path.exists(creds_file):
                credentials = Credentials.from_service_account_file(
                    creds_file,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
            else:
                st.error("กรุณาตั้งค่า Google Cloud Credentials")
                st.info("""
                **วิธีตั้งค่า:**
                1. สร้าง Service Account ใน Google Cloud Console
                2. เปิดใช้งาน Google Sheets API และ Google Drive API
                3. ดาวน์โหลดไฟล์ credentials.json
                4. วางไฟล์ credentials.json ในโฟลเดอร์โปรเจค
                """)
                return None, None
        
        # Create clients
        gc = gspread.authorize(credentials)
        drive_service = build('drive', 'v3', credentials=credentials)
        
        return gc, drive_service
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {str(e)}")
        return None, None

# Initialize Google Sheets connection
gc, drive_service = init_google_sheets()

# -----------------------------
# Google Sheets Helper Functions
# -----------------------------
def get_or_create_spreadsheet(spreadsheet_name="ZL_TA_Learning_DB"):
    """Get or create a Google Spreadsheet"""
    try:
        if gc is None:
            return None
        
        # Try to open existing spreadsheet
        try:
            spreadsheet = gc.open(spreadsheet_name)
            return spreadsheet
        except gspread.SpreadsheetNotFound:
            # Create new spreadsheet
            spreadsheet = gc.create(spreadsheet_name)
            
            # Share with the service account
            spreadsheet.share(spreadsheet.client.auth.service_account_email, 
                             perm_type='user', 
                             role='writer')
            
            return spreadsheet
    except Exception as e:
        st.error(f"ไม่สามารถสร้างหรือเปิด Google Sheet: {str(e)}")
        return None

def get_sheet_data(sheet_name, spreadsheet_name="ZL_TA_Learning_DB"):
    """Read data from Google Sheet"""
    try:
        if gc is None:
            return pd.DataFrame()
            
        spreadsheet = get_or_create_spreadsheet(spreadsheet_name)
        if spreadsheet is None:
            return pd.DataFrame()
            
        worksheet = spreadsheet.worksheet(sheet_name)
        records = worksheet.get_all_records()
        return pd.DataFrame(records)
    except gspread.WorksheetNotFound:
        # Create worksheet if it doesn't exist
        try:
            spreadsheet = get_or_create_spreadsheet(spreadsheet_name)
            if spreadsheet:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                # Add default headers
                headers = get_default_headers(sheet_name)
                if headers:
                    worksheet.append_row(headers)
                return pd.DataFrame(columns=headers)
        except:
            pass
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"ไม่พบข้อมูลใน {sheet_name}: {str(e)}")
        return pd.DataFrame()

def update_sheet_data(sheet_name, df, spreadsheet_name="ZL_TA_Learning_DB"):
    """Update Google Sheet with DataFrame"""
    try:
        if gc is None or df.empty:
            return False
            
        spreadsheet = get_or_create_spreadsheet(spreadsheet_name)
        if spreadsheet is None:
            return False
        
        # Try to get existing worksheet or create new one
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        
        # Clear existing data
        worksheet.clear()
        
        # Convert DataFrame to list of lists
        data = [df.columns.tolist()] + df.values.tolist()
        
        # Update sheet
        worksheet.update('A1', data)
        
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {str(e)}")
        return False

def append_to_sheet(sheet_name, new_row, spreadsheet_name="ZL_TA_Learning_DB"):
    """Append new row to Google Sheet"""
    try:
        if gc is None:
            return False
            
        spreadsheet = get_or_create_spreadsheet(spreadsheet_name)
        if spreadsheet is None:
            return False
        
        # Try to get existing worksheet or create new one
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            # Add default headers
            headers = get_default_headers(sheet_name)
            if headers:
                worksheet.append_row(headers)
        
        # Append new row
        worksheet.append_row(new_row)
        
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเพิ่มข้อมูล: {str(e)}")
        return False

def update_sheet_row(sheet_name, column_name, search_value, updates, spreadsheet_name="ZL_TA_Learning_DB"):
    """Update specific row in Google Sheet"""
    try:
        if gc is None:
            return False
            
        spreadsheet = get_or_create_spreadsheet(spreadsheet_name)
        if spreadsheet is None:
            return False
            
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Get all records
        records = worksheet.get_all_records()
        
        if not records:
            return False
            
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        if column_name in df.columns:
            # Find row index
            matching_rows = df[df[column_name] == search_value]
            
            if not matching_rows.empty:
                row_index = matching_rows.index[0] + 2  # +2 for header row and 1-based index
                
                # Update each field
                for key, value in updates.items():
                    if key in df.columns:
                        col_index = df.columns.get_loc(key)
                        # Update cell
                        cell = worksheet.cell(row_index, col_index + 1)
                        cell.value = value
                        worksheet.update_cell(row_index, col_index + 1, value)
                
                return True
        
        return False
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอัปเดตข้อมูล: {str(e)}")
        return False

def get_default_headers(sheet_name):
    """Get default headers for each sheet"""
    headers_map = {
        "students": ["student_id", "fullname", "email", "phone", "created_date", "status"],
        "courses": ["course_id", "course_name", "teacher_id", "teacher_name", "description", 
                   "image_path", "jitsi_room", "max_students", "current_students", 
                   "class_type", "status", "security_code", "created_date"],
        "admin": ["teacher_id", "username", "password_hash", "fullname", "email", 
                 "created_at", "role"],
        "students_check": ["check_id", "student_id", "fullname", "check_date", "check_time", 
                          "attendance_count", "status"],
        "student_courses": ["enrollment_id", "student_id", "fullname", "course_id", "course_name",
                          "enrollment_date", "completion_status", "completion_date", "certificate_issued"],
        "teachers": ["teacher_id", "username", "password_hash", "fullname", "email", 
                    "phone", "created_at", "role", "status"]
    }
    
    return headers_map.get(sheet_name, [])

def initialize_google_sheets():
    """Initialize Google Sheets with required structure"""
    if gc is None:
        st.warning("⚠️ ไม่สามารถเชื่อมต่อกับ Google Sheets")
        return
    
    try:
        spreadsheet = get_or_create_spreadsheet("ZL_TA_Learning_DB")
        if spreadsheet is None:
            return
        
        # Create required worksheets if they don't exist
        required_sheets = ["students", "courses", "admin", "students_check", "student_courses"]
        
        for sheet_name in required_sheets:
            try:
                spreadsheet.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                headers = get_default_headers(sheet_name)
                if headers:
                    worksheet.append_row(headers)
        
        # Add sample data if sheets are empty
        add_sample_data()
        
    except Exception as e:
        st.warning(f"เกิดข้อผิดพลาดในการเตรียม Google Sheets: {str(e)}")

def add_sample_data():
    """Add sample data to Google Sheets if empty"""
    # Add sample students
    students_df = get_sheet_data("students")
    if students_df.empty:
        sample_students = [
            ["ZLS101", "สมชาย ใจดี", "somchai@example.com", "0812345678", 
             datetime.now().strftime("%Y-%m-%d"), "active"],
            ["ZLS102", "สมหญิง เก่งเรียน", "somying@example.com", "0823456789", 
             datetime.now().strftime("%Y-%m-%d"), "active"],
            ["ZLS103", "นักศึกษา ตัวอย่าง", "student@example.com", "0834567890", 
             datetime.now().strftime("%Y-%m-%d"), "active"]
        ]
        for student in sample_students:
            append_to_sheet("students", student)
    
    # Add sample teacher
    admin_df = get_sheet_data("admin")
    if admin_df.empty:
        # Password: teacher123
        sample_teacher = ["T001", "teacher", md5("teacher123"), "ครูตัวอย่าง", 
                         "teacher@example.com", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "teacher"]
        append_to_sheet("admin", sample_teacher)

# -----------------------------
# Application Functions
# -----------------------------
def md5(text):
    """Create MD5 hash"""
    return hashlib.md5(text.encode()).hexdigest()

def check_student_id(student_id):
    """ตรวจสอบสิทธิ์นักเรียนด้วย ID (Google Sheets)"""
    try:
        students_df = get_sheet_data("students")
        
        if students_df.empty:
            return False, None, None
            
        student_info = students_df[students_df["student_id"] == student_id.upper()]
        
        if not student_info.empty:
            student = student_info.iloc[0]
            
            # บันทึกการตรวจสอบสิทธิ์
            check_df = get_sheet_data("students_check")
            
            # นับจำนวนครั้งที่เคยเข้าเรียน
            attendance_count = 0
            if not check_df.empty and "student_id" in check_df.columns:
                student_checks = check_df[check_df["student_id"] == student_id.upper()]
                attendance_count = len(student_checks) if not student_checks.empty else 0
            
            # บันทึกข้อมูลใหม่
            new_check = {
                "check_id": f"CHK{int(time.time())}",
                "student_id": student_id.upper(),
                "fullname": student["fullname"],
                "check_date": datetime.now().strftime("%Y-%m-%d"),
                "check_time": datetime.now().strftime("%H:%M:%S"),
                "attendance_count": attendance_count + 1,
                "status": "verified"
            }
            
            # เพิ่มข้อมูลใหม่
            append_to_sheet("students_check", list(new_check.values()))
            
            return True, student["fullname"], student.get("email", "")
        else:
            return False, None, None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการตรวจสอบรหัสนักเรียน: {str(e)}")
        return False, None, None

def get_student_courses(student_id):
    """ดึงคอร์สที่นักเรียนลงทะเบียน (Google Sheets)"""
    try:
        df = get_sheet_data("student_courses")
        if not df.empty and "student_id" in df.columns:
            return df[df["student_id"] == student_id]
        return pd.DataFrame()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลคอร์ส: {str(e)}")
        return pd.DataFrame()

def enroll_student_in_course(student_id, student_name, course_id, course_name):
    """ลงทะเบียนนักเรียนในคอร์ส (Google Sheets)"""
    try:
        df = get_sheet_data("student_courses")
        
        # ตรวจสอบว่าลงทะเบียนแล้วหรือยัง
        already_enrolled = False
        if not df.empty:
            already_enrolled = df[
                (df["student_id"] == student_id) & 
                (df["course_id"] == course_id)
            ].shape[0] > 0
        
        if not already_enrolled:
            new_enrollment = {
                "enrollment_id": f"ENR{int(time.time())}",
                "student_id": student_id,
                "fullname": student_name,
                "course_id": course_id,
                "course_name": course_name,
                "enrollment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "completion_status": False,
                "completion_date": "",
                "certificate_issued": False
            }
            
            success = append_to_sheet("student_courses", list(new_enrollment.values()))
            return success
        return False
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการลงทะเบียน: {str(e)}")
        return False

def mark_course_completed(student_id, course_id):
    """บันทึกสถานะเรียนจบคอร์ส (Google Sheets)"""
    try:
        # Find the enrollment_id
        df = get_sheet_data("student_courses")
        if df.empty:
            return False
            
        enrollment = df[(df["student_id"] == student_id) & (df["course_id"] == course_id)]
        
        if not enrollment.empty:
            enrollment_id = enrollment.iloc[0]["enrollment_id"]
            updates = {
                "completion_status": True,
                "completion_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            success = update_sheet_row("student_courses", "enrollment_id", enrollment_id, updates)
            return success
        
        return False
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {str(e)}")
        return False

def teacher_login(username, password):
    """ตรวจสอบการเข้าสู่ระบบครูผู้สอน (Google Sheets)"""
    try:
        admin_df = get_sheet_data("admin")
        
        if admin_df.empty:
            return False, "ไม่พบข้อมูลในระบบ", None, None
            
        user_record = admin_df[admin_df["username"] == username]
        
        if not user_record.empty:
            teacher = user_record.iloc[0]
            password_hash = md5(password)
            
            if teacher["password_hash"] == password_hash:
                return True, "เข้าสู่ระบบสำเร็จ!", teacher["teacher_id"], teacher["fullname"]
            else:
                return False, "รหัสผ่านไม่ถูกต้อง", None, None
        else:
            return False, "ไม่พบบัญชีผู้ใช้งาน", None, None
    except Exception as e:
        return False, f"เกิดข้อผิดพลาด: {str(e)}", None, None

def get_teacher_courses(teacher_id):
    """ดึงคอร์สของครูผู้สอน (Google Sheets)"""
    try:
        courses_df = get_sheet_data("courses")
        if not courses_df.empty and "teacher_id" in courses_df.columns:
            return courses_df[courses_df["teacher_id"] == teacher_id]
        return pd.DataFrame()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลคอร์สครู: {str(e)}")
        return pd.DataFrame()

def get_available_courses():
    """ดึงคอร์สทั้งหมดที่เปิดสอน (Google Sheets)"""
    try:
        courses_df = get_sheet_data("courses")
        if not courses_df.empty:
            return courses_df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลคอร์สทั้งหมด: {str(e)}")
        return pd.DataFrame()

def create_new_course(course_data):
    """สร้างคอร์สใหม่ (Google Sheets)"""
    try:
        # Append new course
        success = append_to_sheet("courses", list(course_data.values()))
        
        if success:
            # Create empty lesson files locally
            course_id = course_data["course_id"]
            lesson_file = f"save_data/lessons/{course_id}_lessons.json"
            exercise_file = f"save_data/lessons/{course_id}_exercises.json"
            
            os.makedirs(os.path.dirname(lesson_file), exist_ok=True)
            
            with open(lesson_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            
            with open(exercise_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            
            return True
        return False
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการสร้างคอร์ส: {str(e)}")
        return False

def update_course(course_id, updates):
    """อัปเดตข้อมูลคอร์ส (Google Sheets)"""
    try:
        success = update_sheet_row("courses", "course_id", course_id, updates)
        return success
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอัปเดตคอร์ส: {str(e)}")
        return False

def get_course_lessons(course_id):
    """ดึงบทเรียนของคอร์ส (JSON file)"""
    lesson_file = f"save_data/lessons/{course_id}_lessons.json"
    if os.path.exists(lesson_file):
        try:
            with open(lesson_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def get_course_exercises(course_id):
    """ดึงแบบฝึกหัดของคอร์ส (JSON file)"""
    exercise_file = f"save_data/lessons/{course_id}_exercises.json"
    if os.path.exists(exercise_file):
        try:
            with open(exercise_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_lesson(course_id, lesson_data):
    """บันทึกบทเรียน (JSON file)"""
    try:
        lesson_file = f"save_data/lessons/{course_id}_lessons.json"
        
        if os.path.exists(lesson_file):
            with open(lesson_file, "r", encoding="utf-8") as f:
                lessons = json.load(f)
        else:
            lessons = []
        
        lessons.append(lesson_data)
        
        with open(lesson_file, "w", encoding="utf-8") as f:
            json.dump(lessons, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึกบทเรียน: {str(e)}")
        return False

def save_exercise(course_id, exercise_data):
    """บันทึกแบบฝึกหัด (JSON file)"""
    try:
        exercise_file = f"save_data/lessons/{course_id}_exercises.json"
        
        if os.path.exists(exercise_file):
            with open(exercise_file, "r", encoding="utf-8") as f:
                exercises = json.load(f)
        else:
            exercises = []
        
        exercises.append(exercise_data)
        
        with open(exercise_file, "w", encoding="utf-8") as f:
            json.dump(exercises, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึกแบบฝึกหัด: {str(e)}")
        return False

def check_answer(student_answer, correct_answer):
    """ตรวจคำตอบ (case insensitive และลบช่องว่าง)"""
    if not student_answer or not correct_answer:
        return False
    
    # ลบช่องว่างที่เกินและแปลงเป็นตัวพิมพ์เล็ก
    student_clean = ' '.join(student_answer.strip().split()).lower()
    correct_clean = ' '.join(correct_answer.strip().split()).lower()
    
    return student_clean == correct_clean

def init_data_folder():
    """Initialize data folder for files"""
    # Create save_data folder
    save_data = "save_data"
    os.makedirs(save_data, exist_ok=True)
    
    # Create subfolders
    subfolders = ["images", "documents", "certificates", "exercise_images", 
                  "lessons", "quiz_results", "certificates_files"]
    
    for folder in subfolders:
        os.makedirs(f"{save_data}/{folder}", exist_ok=True)

# -----------------------------
# CSS Styling
# -----------------------------
# Function to encode logo image
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Load logo if exists
logo_path = "images_logo/logo_ZL.png"
logo_base64 = ""
if os.path.exists(logo_path):
    logo_base64 = get_base64_of_bin_file(logo_path)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Mitr:wght@300;400;500;600;700&display=swap');

* {{
    font-family: 'Mitr', sans-serif;
}}

/* Main Colors */
:root {{
    --primary-color: #E6F7FF;
    --secondary-color: #FFF9C4;
    --main-title: #1A237E;
    --sub-title: #FFD700;
    --success-color: #2E7D32;
    --warning-color: #F57C00;
    --border-radius: 12px;
    --box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    --transition: all 0.3s ease;
}}

/* Logo in top left */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
#root > div:nth-child(1) > div > div > div > div > section > div > div:nth-child(1) > div > div:nth-child(1) > div {{
    padding-top: 20px;
}}

.logo-container {{
    position: fixed;
    top: 10px;
    left: 10px;
    z-index: 1000;
    background: white;
    border-radius: 10px;
    padding: 5px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}}

.logo-img {{
    height: 50px;
    width: auto;
}}

@media (max-width: 768px) {{
    .logo-container {{
        top: 5px;
        left: 5px;
    }}
    .logo-img {{
        height: 40px;
    }}
}}

/* Main Container */
.main-header {{
    background: linear-gradient(135deg, var(--primary-color), #B3E5FC);
    padding: 25px;
    border-radius: var(--border-radius);
    border: 3px solid #90CAF9;
    margin-bottom: 30px;
    animation: fadeIn 0.8s ease;
}}

.main-header h1 {{
    color: var(--main-title);
    text-align: center;
    font-weight: 700;
    margin-bottom: 10px;
    font-size: 2.5rem;
}}

.main-header h3 {{
    color: var(--main-title);
    text-align: center;
    font-weight: 600;
    opacity: 0.9;
}}

/* Cards */
.card {{
    background: white;
    padding: 25px;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    margin: 20px 0;
    border: 3px solid #E3F2FD;
    transition: var(--transition);
}}

.card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    border-color: var(--sub-title);
}}

/* Info Boxes */
.info-box {{
    background-color: var(--primary-color);
    border: 3px solid #81D4FA;
    border-radius: var(--border-radius);
    padding: 20px;
    margin: 20px 0;
    color: var(--main-title);
    animation: slideInRight 0.5s ease;
}}

.warning-box {{
    background-color: var(--secondary-color);
    border: 3px solid #FFE082;
    border-radius: var(--border-radius);
    padding: 20px;
    margin: 20px 0;
    animation: slideInLeft 0.5s ease;
}}

/* Jitsi Container */
.jitsi-container {{
    position: relative;
    width: 100%;
    padding-bottom: 56.25%; /* 16:9 Aspect Ratio */
    height: 0;
    overflow: hidden;
    border-radius: var(--border-radius);
    border: 3px solid var(--sub-title);
    margin-bottom: 20px;
    background: #000;
}}

.jitsi-iframe {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: none;
}}

/* Buttons */
.stButton > button {{
    background: linear-gradient(135deg, var(--main-title), #3949AB);
    color: white;
    border: none;
    padding: 12px 28px;
    border-radius: 8px;
    font-weight: 600;
    transition: var(--transition);
    font-size: 1rem;
}}

.stButton > button:hover {{
    background: linear-gradient(135deg, #3949AB, #283593);
    transform: translateY(-3px);
    box-shadow: 0 6px 20px rgba(26, 35, 126, 0.3);
}}

/* Form Elements */
.stTextInput > div > div > input {{
    border: 2px solid #BBDEFB;
    border-radius: 8px;
    padding: 12px;
    font-size: 1rem;
    transition: var(--transition);
}}

.stTextInput > div > div > input:focus {{
    border-color: var(--main-title);
    box-shadow: 0 0 0 3px rgba(26, 35, 126, 0.1);
}}

/* Success/Error Messages */
.stSuccess {{
    background: #E8F5E9;
    border: 2px solid #A5D6A7;
    border-radius: var(--border-radius);
    color: var(--success-color);
    padding: 15px;
}}

.stError {{
    background: #FFEBEE;
    border: 2px solid #EF9A9A;
    border-radius: var(--border-radius);
    color: #C62828;
    padding: 15px;
}}

/* Animations */
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(-20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes slideInRight {{
    from {{ opacity: 0; transform: translateX(30px); }}
    to {{ opacity: 1; transform: translateX(0); }}
}}

@keyframes slideInLeft {{
    from {{ opacity: 0; transform: translateX(-30px); }}
    to {{ opacity: 1; transform: translateX(0); }}
}}

/* Course Card */
.course-card {{
    background: white;
    padding: 20px;
    border-radius: var(--border-radius);
    box-shadow: var(--box-shadow);
    margin: 15px 0;
    border: 2px solid #E3F2FD;
    transition: var(--transition);
}}

.course-card:hover {{
    border-color: var(--sub-title);
    transform: scale(1.02);
}}

.course-card h4 {{
    color: var(--main-title);
    margin-bottom: 10px;
    font-size: 1.3rem;
    border-bottom: 2px solid var(--secondary-color);
    padding-bottom: 8px;
}}

/* Stats Cards */
.stats-card {{
    background: linear-gradient(135deg, var(--main-title), #3949AB);
    color: white;
    padding: 25px;
    border-radius: var(--border-radius);
    text-align: center;
    border: 3px solid var(--sub-title);
}}

/* Loading Spinner */
.spinner {{
    border: 4px solid var(--primary-color);
    border-top: 4px solid var(--main-title);
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin: 20px auto;
}}

@keyframes spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}
</style>
""", unsafe_allow_html=True)

# Display logo on every page
if logo_base64:
    st.markdown(f"""
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_base64}" class="logo-img" alt="ZL Logo">
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# Session State Initialization
# -----------------------------
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "student_check"
if "teacher_id" not in st.session_state:
    st.session_state.teacher_id = None
if "teacher_name" not in st.session_state:
    st.session_state.teacher_name = None
if "current_course" not in st.session_state:
    st.session_state.current_course = None
if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "student_name" not in st.session_state:
    st.session_state.student_name = None
if "student_email" not in st.session_state:
    st.session_state.student_email = None
if "has_attended_live" not in st.session_state:
    st.session_state.has_attended_live = False
if "jitsi_connected" not in st.session_state:
    st.session_state.jitsi_connected = False
if "jitsi_room_name" not in st.session_state:
    st.session_state.jitsi_room_name = None
if "jitsi_display_name" not in st.session_state:
    st.session_state.jitsi_display_name = None
if "edit_course" not in st.session_state:
    st.session_state.edit_course = None
if "edit_course_id" not in st.session_state:
    st.session_state.edit_course_id = None
if "edit_lesson_idx" not in st.session_state:
    st.session_state.edit_lesson_idx = None
if "show_lessons" not in st.session_state:
    st.session_state.show_lessons = True

# Initialize data folder and Google Sheets
init_data_folder()
initialize_google_sheets()

# -----------------------------
# STUDENT ID CHECK PAGE
# -----------------------------
if st.session_state.page == "student_check":
    st.markdown("""
    <div class="main-header">
        <h1>🎓 ZL TA-Learning ระบบผู้ช่วยสอน</h1>
        <h3>เรียนสดออนไลน์ ได้ทุกที่ (100% Live Class)</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.write("### 📋 ขั้นตอนการเข้าเรียน")
        st.write("1. **กรอกรหัสนักเรียน** (เช่น ZLS101, ZLS102)")
        st.write("2. **ยอมรับเงื่อนไขการเข้าเรียน**")
        st.write("3. **กดปุ่ม 'ตรวจสอบสิทธิ์'**")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Student ID Input
        student_id = st.text_input(
            "**รหัสนักเรียน (Student ID)** *", 
            placeholder="เช่น ZLS101, ZLS102, ZLS103 ...",
            key="student_id_input"
        )
        
        # Terms Agreement
        agree_terms = st.checkbox(
            "**✔️ ยอมรับเงื่อนไขและข้อตกลงการเข้าเรียน**",
            key="agree_terms"
        )
        
        # Action Buttons
        col_a, col_b = st.columns(2)
        
        with col_a:
            check_btn = st.button(
                "🔍 ตรวจสอบสิทธิ์", 
                type="primary", 
                use_container_width=True,
                disabled=not (student_id and agree_terms),
                key="check_student_btn"
            )
        
        with col_b:
            teacher_login_btn = st.button(
                "👨‍🏫 เข้าสู่ระบบครู", 
                use_container_width=True,
                key="teacher_login_btn"
            )
        
        # Button Actions
        if teacher_login_btn:
            st.session_state.page = "teacher_login"
            st.rerun()
        
        if check_btn:
            if not student_id:
                st.error("⚠️ กรุณากรอกรหัสนักเรียน")
            elif not agree_terms:
                st.error("⚠️ กรุณายอมรับเงื่อนไขการเข้าเรียน")
            else:
                with st.spinner("กำลังตรวจสอบสิทธิ์..."):
                    time.sleep(1)
                    verified, student_name, student_email = check_student_id(student_id)
                    
                    if verified:
                        st.session_state.student_id = student_id.upper()
                        st.session_state.student_name = student_name
                        st.session_state.student_email = student_email
                        st.session_state.role = "student"
                        st.session_state.page = "student_home"
                        
                        st.success(f"✅ **ตรวจสอบสิทธิ์สำเร็จ!**")
                        st.info(f"**ชื่อ:** {student_name}")
                        st.info(f"**อีเมล:** {student_email}")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"❌ **ไม่พบข้อมูลนักเรียนรหัส:** {student_id}")
                        st.info("กรุณาตรวจสอบรหัสนักเรียนให้ถูกต้อง หรือติดต่อครูผู้สอน")

# -----------------------------
# STUDENT HOME PAGE
# -----------------------------
elif st.session_state.page == "student_home" and st.session_state.role == "student":
    # Sidebar
    with st.sidebar:
        st.title(f"👨‍🎓 {st.session_state.student_name}")
        st.write(f"**ID:** {st.session_state.student_id}")
        
        # Get attendance count
        try:
            check_df = get_sheet_data("students_check")
            student_checks = check_df[check_df["student_id"] == st.session_state.student_id]
            attendance_count = len(student_checks) if not student_checks.empty else 0
            st.write(f"**📊 เข้าเรียนแล้ว:** {attendance_count} ครั้ง")
        except:
            attendance_count = 0
        
        st.markdown("---")
        
        # เมนูสำหรับนักเรียน
        menu_options = ["🏠 หน้าหลักและประกาศ"]
        
        # เพิ่มเมนูเฉพาะเมื่อได้เข้าเรียนสดแล้ว
        if st.session_state.has_attended_live:
            menu_options.extend([
                "📚 คอร์สของฉัน", 
                "🎥 เข้าร่วมเรียนสด"
            ])
        else:
            menu_options.extend(["📚 คอร์สของฉัน"])
        
        menu_choice = st.radio("**เมนูหลัก**", menu_options, key="student_menu")
        
        st.markdown("---")
        
        if st.button("🚪 ออกจากระบบ", use_container_width=True, key="student_logout"):
            st.session_state.clear()
            st.rerun()
    
    # ---------- STUDENT HOME & ANNOUNCEMENTS ----------
    if menu_choice == "🏠 หน้าหลักและประกาศ":
        st.title(f"สวัสดี, {st.session_state.student_name}! 👋")
        st.markdown("---")
        
        # Announcements Section
        st.subheader("📢 ประกาศและข่าวสารล่าสุด")
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.write("**📅 ระบบเรียนออนไลน์แบบสด (Live Class Only)**")
        st.write("• เรียนสดผ่าน Jitsi Meet เท่านั้น")
        st.write("• เข้าเรียนสดก่อนถึงจะสามารถเข้าถึงบทเรียนและแบบฝึกหัดได้")
        st.write("• รองรับทั้งรูปแบบตัวต่อตัวและกลุ่ม")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Available courses preview
        st.subheader("📚 คอร์สเรียนที่เปิดสอน")
        
        try:
            courses_df = get_available_courses()
            
            if not courses_df.empty:
                # Create course grid
                cols = st.columns(3)
                for idx, row in courses_df.iterrows():
                    if idx < 6:  # Show max 6 courses
                        with cols[idx % 3]:
                            st.markdown('<div class="course-card">', unsafe_allow_html=True)
                            
                            # Display course image if exists
                            image_path = row.get('image_path', '')
                            if isinstance(image_path, str) and image_path != 'nan' and os.path.exists(image_path):
                                st.image(image_path, use_container_width=True)
                            else:
                                # Placeholder image
                                st.markdown(
                                    '<div style="background: linear-gradient(135deg, #E6F7FF, #B3E5FC); height: 150px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #1A237E; font-weight: bold;">ภาพคอร์สเรียน</div>',
                                    unsafe_allow_html=True
                                )
                            
                            course_name = str(row.get("course_name", "ไม่มีชื่อ"))
                            teacher_name = str(row.get("teacher_name", "ครูผู้สอน"))
                            description = str(row.get("description", "ไม่มีคำอธิบาย"))
                            class_type = str(row.get("class_type", "กลุ่ม"))
                            course_id = str(row.get("course_id", ""))
                            
                            st.markdown(f'<h4>{course_name}</h4>', unsafe_allow_html=True)
                            st.write(f"👨‍🏫 **ครูผู้สอน:** {teacher_name}")
                            st.write(f"📖 **คำอธิบาย:** {description[:80]}...")
                            st.write(f"👥 **ประเภท:** {class_type}")
                            
                            # Check if already enrolled
                            enrolled_courses = get_student_courses(st.session_state.student_id)
                            is_enrolled = False
                            
                            if not enrolled_courses.empty and course_id and course_id != 'nan':
                                is_enrolled = not enrolled_courses[enrolled_courses["course_id"] == course_id].empty
                            
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if not is_enrolled and course_id and course_id != 'nan':
                                    if st.button("📝 ลงทะเบียน", key=f"enroll_{course_id}_{idx}", use_container_width=True):
                                        success = enroll_student_in_course(
                                            st.session_state.student_id,
                                            st.session_state.student_name,
                                            course_id,
                                            course_name
                                        )
                                        if success:
                                            st.success(f"✅ ลงทะเบียนคอร์ส **{course_name}** สำเร็จ!")
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.info("คุณได้ลงทะเบียนคอร์สนี้เรียบร้อยแล้ว")
                                elif course_id and course_id != 'nan':
                                    st.success("✅ **ลงทะเบียนแล้ว**")
                            
                            with col_btn2:
                                if is_enrolled:
                                    if st.button("🎥 เข้าเรียนสด", key=f"live_home_{course_id}_{idx}", use_container_width=True):
                                        try:
                                            courses_df = get_sheet_data("courses")
                                            if course_id:
                                                course_info = courses_df[courses_df["course_id"] == course_id]
                                                if not course_info.empty:
                                                    course_row = course_info.iloc[0]
                                                    course_data = {
                                                        "course_id": course_row.get('course_id', ''),
                                                        "course_name": course_row.get('course_name', ''),
                                                        "teacher_id": course_row.get('teacher_id', ''),
                                                        "teacher_name": course_row.get('teacher_name', 'ครูผู้สอน'),
                                                        "jitsi_room": course_row.get('jitsi_room', 'default_room'),
                                                        "description": course_row.get('description', ''),
                                                        "class_type": course_row.get('class_type', 'กลุ่ม')
                                                    }
                                                    st.session_state.current_course = course_data
                                                    st.session_state.page = "live_student_session"
                                                    st.rerun()
                                        except Exception as e:
                                            st.error(f"เกิดข้อผิดพลาด: {e}")
                            
                            st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                st.write("**⚠️ ยังไม่มีคอร์สเรียนที่เปิดสอน**")
                st.write("กรุณารอครูผู้สอนประกาศคอร์สเรียนใหม่")
                st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลคอร์ส: {str(e)}")
    
    # ---------- STUDENT COURSES PAGE ----------
    elif menu_choice == "📚 คอร์สของฉัน":
        st.title("📚 คอร์สของฉัน")
        st.markdown("---")
        
        enrolled_courses = get_student_courses(st.session_state.student_id)
        
        if not enrolled_courses.empty:
            st.subheader("คอร์สที่ลงทะเบียนแล้ว")
            
            cols = st.columns(3)
            for idx, row in enrolled_courses.iterrows():
                with cols[idx % 3]:
                    st.markdown('<div class="course-card">', unsafe_allow_html=True)
                    
                    course_id = row["course_id"]
                    course_name = row["course_name"]
                    
                    # Try to get course details
                    try:
                        courses_df = get_sheet_data("courses")
                        course_details = courses_df[courses_df["course_id"] == course_id]
                        
                        if not course_details.empty:
                            course_detail = course_details.iloc[0]
                            image_path = course_detail.get('image_path', '')
                            
                            if image_path and os.path.exists(image_path):
                                st.image(image_path, use_container_width=True)
                    except:
                        pass
                    
                    st.markdown(f'<h4>{course_name}</h4>', unsafe_allow_html=True)
                    st.write(f"**สถานะ:** {'✅ เรียนจบ' if row.get('completion_status', False) else '📚 กำลังเรียน'}")
                    st.write(f"**วันที่ลงทะเบียน:** {row.get('enrollment_date', '')}")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("🎥 เข้าเรียน", key=f"go_live_{course_id}", use_container_width=True):
                            try:
                                courses_df = get_sheet_data("courses")
                                if course_id:
                                    course_info = courses_df[courses_df["course_id"] == course_id]
                                    if not course_info.empty:
                                        course_row = course_info.iloc[0]
                                        course_data = {
                                            "course_id": course_row.get('course_id', ''),
                                            "course_name": course_row.get('course_name', ''),
                                            "teacher_id": course_row.get('teacher_id', ''),
                                            "teacher_name": course_row.get('teacher_name', 'ครูผู้สอน'),
                                            "jitsi_room": course_row.get('jitsi_room', 'default_room'),
                                            "description": course_row.get('description', ''),
                                            "class_type": course_row.get('class_type', 'กลุ่ม')
                                        }
                                        st.session_state.current_course = course_data
                                        st.session_state.page = "live_student_session"
                                        st.rerun()
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาด: {e}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("คุณยังไม่ได้ลงทะเบียนคอร์สใดๆ")

# -----------------------------
# LIVE STUDENT SESSION PAGE
# -----------------------------
elif st.session_state.page == "live_student_session" and st.session_state.role == "student":
    if "current_course" in st.session_state and st.session_state.current_course:
        course_info = st.session_state.current_course
        
        # Mark as attended live
        st.session_state.has_attended_live = True
        
        # Save Jitsi info
        st.session_state.jitsi_room_name = course_info.get('jitsi_room', 'default_room')
        st.session_state.jitsi_display_name = st.session_state.student_name
        
        # Auto connect to Jitsi
        st.session_state.jitsi_connected = True
        
        st.title(f"🎥 เรียนสด: {course_info['course_name']}")
        st.markdown("---")
        
        # Course Information
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.write(f"**👨‍🏫 ครูผู้สอน:** {course_info.get('teacher_name', 'ครูผู้สอน')}")
        with col_info2:
            st.write(f"**👥 ประเภท:** {course_info.get('class_type', 'กลุ่ม')}")
        with col_info3:
            st.write(f"**👨‍🎓 นักเรียน:** {st.session_state.student_name}")
        
        # Action Buttons
        st.markdown("---")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⬅ กลับสู่หน้าหลัก", type="secondary", use_container_width=True):
                st.session_state.page = "student_home"
                st.session_state.jitsi_connected = False
                st.rerun()
        
        # Jitsi Meet Embed
        st.markdown("### 🎥 วิดีโอคอลเรียนสด")
        
        if st.session_state.jitsi_connected:
            room_name = str(course_info.get("jitsi_room", "default_room"))
            display_name = st.session_state.student_name
            
            # สร้าง Jitsi iframe
            jitsi_code = f'''
            <div class="jitsi-container">
                <iframe 
                    src="https://meet.jit.si/{room_name}?userInfo.displayName={display_name.replace(' ', '%20')}" 
                    class="jitsi-iframe"
                    allow="camera; microphone; fullscreen; display-capture; autoplay"
                    allowfullscreen
                    title="Jitsi Meet"
                    loading="lazy">
                </iframe>
            </div>
            '''
            st.markdown(jitsi_code, unsafe_allow_html=True)
        else:
            st.info("กำลังเชื่อมต่อกับห้องเรียน...")
    else:
        st.session_state.page = "student_home"
        st.rerun()

# -----------------------------
# TEACHER LOGIN PAGE
# -----------------------------
elif st.session_state.page == "teacher_login":
    st.markdown("""
    <div class="main-header">
        <h1>👨‍🏫 เข้าสู่ระบบครูผู้สอน</h1>
        <h3>ระบบจัดการการสอนออนไลน์</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div style="color: #1A237E; border-bottom: 3px solid #FFD700; padding-bottom: 10px; margin-bottom: 25px; font-weight: 700;">กรุณาเข้าสู่ระบบ</div>', unsafe_allow_html=True)
        
        username = st.text_input("**Username**", key="teacher_username_login")
        password = st.text_input("**Password**", type="password", key="teacher_password_login")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("เข้าสู่ระบบ", 
                        type="primary", 
                        use_container_width=True, 
                        key="teacher_login_btn"):
                if username and password:
                    try:
                        success, message, teacher_id, teacher_name = teacher_login(username, password)
                        
                        if success:
                            st.session_state.role = "teacher"
                            st.session_state.teacher_id = teacher_id
                            st.session_state.teacher_name = teacher_name
                            st.session_state.page = "teacher_dashboard"
                            
                            st.success(f"✅ {message}")
                            st.info(f"ยินดีต้อนรับคุณครู {teacher_name}")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
                else:
                    st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
        
        with col_b:
            if st.button("← กลับไปหน้าตรวจสอบสิทธิ์นักเรียน", 
                        use_container_width=True,
                        key="back_to_student_check"):
                st.session_state.page = "student_check"
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# TEACHER DASHBOARD
# -----------------------------
elif st.session_state.page == "teacher_dashboard" and st.session_state.role == "teacher":
    # Sidebar
    with st.sidebar:
        st.title(f"👨‍🏫 {st.session_state.teacher_name}")
        st.write(f"**ID:** {st.session_state.teacher_id}")
        
        st.markdown("---")
        
        # Teacher Menu
        menu_options = [
            "📊 Dashboard", 
            "📚 จัดการคอร์ส", 
            "➕ สร้างคอร์สใหม่", 
            "📖 จัดการบทเรียน", 
            "📝 จัดการแบบฝึกหัด", 
            "🎥 สอนสด"
        ]
        
        menu_choice = st.radio("**เมนูครูผู้สอน**", menu_options, key="teacher_menu")
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 ออกจากระบบ", use_container_width=True, key="teacher_logout"):
            st.session_state.clear()
            st.rerun()
    
    # ---------- TEACHER DASHBOARD ----------
    if menu_choice == "📊 Dashboard":
        st.title("📊 Dashboard ครูผู้สอน")
        st.markdown("---")
        
        # Stats cards
        col1, col2, col3 = st.columns(3)
        
        try:
            my_courses = get_teacher_courses(st.session_state.teacher_id)
            num_courses = len(my_courses)
        except:
            num_courses = 0
            my_courses = pd.DataFrame()
        
        with col1:
            st.markdown(f"""
            <div class="stats-card">
                <h4>คอร์สของฉัน</h4>
                <h2>{num_courses}</h2>
                <p>คอร์ส</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            try:
                student_courses_df = get_sheet_data("student_courses")
                teacher_course_ids = my_courses["course_id"].tolist() if not my_courses.empty else []
                teacher_students = student_courses_df[student_courses_df["course_id"].isin(teacher_course_ids)] if not student_courses_df.empty else pd.DataFrame()
                enrolled_students = teacher_students["student_id"].nunique() if not teacher_students.empty else 0
            except:
                enrolled_students = 0
            
            st.markdown(f"""
            <div class="stats-card">
                <h4>นักเรียนลงทะเบียน</h4>
                <h2>{enrolled_students}</h2>
                <p>คน</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            total_lessons = 0
            try:
                for course_id in my_courses["course_id"]:
                    lessons = get_course_lessons(course_id)
                    total_lessons += len(lessons)
            except:
                pass
            
            st.markdown(f"""
            <div class="stats-card">
                <h4>บทเรียนทั้งหมด</h4>
                <h2>{total_lessons}</h2>
                <p>บท</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Recent courses
        st.subheader("คอร์สล่าสุดของฉัน")
        if not my_courses.empty:
            cols = st.columns(3)
            for idx, row in my_courses.tail(3).iterrows():
                with cols[idx % 3]:
                    st.markdown('<div class="course-card">', unsafe_allow_html=True)
                    
                    image_path = row.get("image_path", "")
                    if image_path and os.path.exists(image_path):
                        st.image(image_path, use_container_width=True)
                    else:
                        st.markdown(
                            '<div style="background: linear-gradient(135deg, #E6F7FF, #B3E5FC); height: 120px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #1A237E; font-weight: bold;">ภาพคอร์สเรียน</div>',
                            unsafe_allow_html=True
                        )
                    
                    st.write(f"**{row['course_name']}**")
                    st.caption(row.get("description", "")[:80] + "...")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("จัดการ", key=f"manage_{row['course_id']}", use_container_width=True):
                            st.session_state.edit_course = row.to_dict()
                            st.session_state.page = "edit_course"
                            st.rerun()
                    with col_b:
                        if st.button("สอนสด", key=f"live_{row['course_id']}", use_container_width=True):
                            st.session_state.current_course = row.to_dict()
                            st.session_state.page = "live_teaching"
                            st.rerun()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("ยังไม่มีคอร์สเรียน กรุณาสร้างคอร์สใหม่")
    
    # ---------- MANAGE COURSES ----------
    elif menu_choice == "📚 จัดการคอร์ส":
        st.title("📚 จัดการคอร์สเรียน")
        st.markdown("---")
        
        try:
            my_courses = get_teacher_courses(st.session_state.teacher_id)
            
            if not my_courses.empty:
                for idx, row in my_courses.iterrows():
                    with st.expander(f"{row['course_name']} ({row.get('class_type', 'กลุ่ม')})"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            image_path = row.get("image_path", "")
                            if image_path and os.path.exists(image_path):
                                st.image(image_path, width=150)
                            
                            st.write(f"**รหัสคอร์ส:** {row['course_id']}")
                            st.write(f"**คำอธิบาย:** {row.get('description', '')}")
                            st.write(f"**ห้อง Jitsi:** {row.get('jitsi_room', 'ยังไม่ได้ตั้งค่า')}")
                            st.write(f"**สถานะ:** {row.get('status', 'active')}")
                        
                        with col2:
                            if st.button("✏️ แก้ไข", key=f"edit_{row['course_id']}", use_container_width=True):
                                st.session_state.edit_course = row.to_dict()
                                st.session_state.page = "edit_course"
                                st.rerun()
                            
                            if st.button("🎥 สอนสด", key=f"go_live_{row['course_id']}", use_container_width=True):
                                st.session_state.current_course = row.to_dict()
                                st.session_state.page = "live_teaching"
                                st.rerun()
            else:
                st.info("ยังไม่มีคอร์สเรียน")
        except:
            st.info("ยังไม่มีคอร์สเรียน")
    
    # ---------- CREATE NEW COURSE ----------
    elif menu_choice == "➕ สร้างคอร์สใหม่":
        st.title("➕ สร้างคอร์สใหม่")
        st.markdown("---")
        
        with st.form("create_course_form", clear_on_submit=True):
            st.subheader("ข้อมูลพื้นฐาน")
            
            col1, col2 = st.columns(2)
            with col1:
                course_name = st.text_input("**ชื่อคอร์ส** *", key="new_course_name")
                class_type = st.selectbox(
                    "**ประเภทการเรียน** *", 
                    ["ตัวต่อตัว (1:1)", "กลุ่มเล็ก (2-5 คน)", "กลุ่มใหญ่"], 
                    key="new_class_type"
                )
            
            with col2:
                max_students = st.number_input(
                    "**จำนวนนักเรียนสูงสุด**", 
                    min_value=1, 
                    max_value=50, 
                    value=10, 
                    key="new_max_students"
                )
                
                jitsi_room = st.text_input(
                    "**ชื่อห้อง Jitsi** *", 
                    value=f"{st.session_state.teacher_name.replace(' ', '')}_{int(time.time())}", 
                    key="new_jitsi_room"
                )
            
            st.subheader("รายละเอียดคอร์ส")
            description = st.text_area("**คำอธิบายคอร์ส** *", height=150, key="new_description")
            
            st.subheader("รูปภาพคอร์ส")
            image = st.file_uploader(
                "**อัปโหลดรูปปกคอร์ส** (ไม่บังคับ)", 
                type=["jpg", "png", "jpeg"], 
                key="new_course_image"
            )
            
            # Generate security code
            security_code = str(uuid.uuid4())[:8].upper()
            
            st.markdown("---")
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                submitted = st.form_submit_button("✅ สร้างคอร์ส", type="primary", use_container_width=True)
            with col_cancel:
                cancel_btn = st.form_submit_button("❌ ยกเลิก", use_container_width=True)
            
            if cancel_btn:
                st.session_state.page = "teacher_dashboard"
                st.rerun()
            
            if submitted:
                if not all([course_name, jitsi_room, description]):
                    st.error("กรุณากรอกข้อมูลที่จำเป็น (*)")
                else:
                    try:
                        courses_df = get_sheet_data("courses")
                        
                        # Generate course ID
                        course_id = f"C{len(courses_df) + 1:04d}"
                        
                        # Save image
                        img_path = ""
                        if image:
                            img_path = f"save_data/images/{course_id}_{image.name}"
                            try:
                                os.makedirs(os.path.dirname(img_path), exist_ok=True)
                                with open(img_path, "wb") as f:
                                    f.write(image.getbuffer())
                            except Exception as e:
                                st.warning(f"ไม่สามารถบันทึกรูปภาพ: {e}")
                                img_path = ""
                        
                        # Create course data
                        new_course = {
                            "course_id": course_id,
                            "course_name": course_name,
                            "teacher_id": st.session_state.teacher_id,
                            "teacher_name": st.session_state.teacher_name,
                            "image_path": img_path,
                            "jitsi_room": jitsi_room,
                            "description": description,
                            "max_students": max_students,
                            "current_students": 0,
                            "class_type": class_type,
                            "status": "active",
                            "security_code": security_code,
                            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Save to Google Sheets
                        success = create_new_course(new_course)
                        
                        if success:
                            st.success(f"✅ **สร้างคอร์ส '{course_name}' สำเร็จ!**")
                            st.info(f"**รหัสคอร์ส:** {course_id}")
                            st.info(f"**รหัสความปลอดภัย:** {security_code}")
                            st.info(f"**ห้อง Jitsi:** {jitsi_room}")
                            
                            # Auto redirect after 3 seconds
                            time.sleep(3)
                            st.session_state.page = "teacher_dashboard"
                            st.rerun()
                        else:
                            st.error("เกิดข้อผิดพลาดในการสร้างคอร์ส")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
    
    # ---------- MANAGE LESSONS ----------
    elif menu_choice == "📖 จัดการบทเรียน":
        st.title("📖 จัดการบทเรียน")
        st.markdown("---")
        
        try:
            my_courses = get_teacher_courses(st.session_state.teacher_id)
            
            if not my_courses.empty:
                selected_course = st.selectbox(
                    "**เลือกคอร์ส**", 
                    my_courses["course_name"].tolist(), 
                    key="select_course_lessons"
                )
                course_id = my_courses[my_courses["course_name"] == selected_course]["course_id"].iloc[0]
                
                st.write(f"**คอร์ส:** {selected_course}")
                st.markdown("---")
                
                # Load existing lessons
                lessons = get_course_lessons(course_id)
                
                # Display existing lessons
                st.subheader("บทเรียนที่มีอยู่")
                if lessons:
                    for i, lesson in enumerate(lessons):
                        with st.expander(f"บทที่ {i+1}: {lesson.get('title', 'ไม่มีชื่อ')}"):
                            st.write(f"**หัวข้อ:** {lesson.get('title', 'ไม่มีชื่อ')}")
                            
                            # แสดงไฟล์แนบถ้ามี
                            if lesson.get('file'):
                                file_path = lesson.get('file')
                                if file_path and os.path.exists(file_path):
                                    st.write(f"**ไฟล์แนบ:** {os.path.basename(file_path)}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✏️ แก้ไข", key=f"edit_lesson_{course_id}_{i}", use_container_width=True):
                                    st.session_state.edit_lesson_idx = i
                                    st.session_state.edit_course_id = course_id
                                    st.session_state.page = "edit_lesson"
                                    st.rerun()
                            with col2:
                                if st.button("🗑️ ลบ", key=f"delete_lesson_{course_id}_{i}", use_container_width=True):
                                    lessons.pop(i)
                                    lesson_file = f"save_data/lessons/{course_id}_lessons.json"
                                    with open(lesson_file, "w", encoding="utf-8") as f:
                                        json.dump(lessons, f, ensure_ascii=False, indent=2)
                                    st.success("✅ ลบบทเรียนเรียบร้อย")
                                    time.sleep(1)
                                    st.rerun()
                else:
                    st.info("ยังไม่มีบทเรียนในคอร์สนี้")
                
                # Add new lesson
                st.subheader("เพิ่มบทเรียนใหม่")
                with st.form("add_lesson_form", clear_on_submit=True):
                    lesson_title = st.text_input("**หัวข้อบทเรียน** *", key=f"new_lesson_title_{course_id}")
                    lesson_content = st.text_area("**เนื้อหาบทเรียน** *", height=200, key=f"new_lesson_content_{course_id}")
                    
                    col_add, _ = st.columns(2)
                    with col_add:
                        submitted = st.form_submit_button("✅ เพิ่มบทเรียน", use_container_width=True)
                    
                    if submitted:
                        if lesson_title and lesson_content:
                            # Add new lesson
                            new_lesson = {
                                "title": lesson_title,
                                "content": lesson_content,
                                "file": "",
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            
                            success = save_lesson(course_id, new_lesson)
                            if success:
                                st.success("✅ **เพิ่มบทเรียนสำเร็จ!**")
                                st.rerun()
                            else:
                                st.error("เกิดข้อผิดพลาดในการบันทึกบทเรียน")
                        else:
                            st.error("กรุณากรอกข้อมูลที่จำเป็น (*)")
            else:
                st.info("ยังไม่มีคอร์สเรียน")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
    
    # ---------- MANAGE EXERCISES ----------
    elif menu_choice == "📝 จัดการแบบฝึกหัด":
        st.title("📝 จัดการแบบฝึกหัด")
        st.markdown("---")
        
        try:
            my_courses = get_teacher_courses(st.session_state.teacher_id)
            
            if not my_courses.empty:
                selected_course = st.selectbox(
                    "**เลือกคอร์ส**", 
                    my_courses["course_name"].tolist(), 
                    key="select_course_exercises"
                )
                course_id = my_courses[my_courses["course_name"] == selected_course]["course_id"].iloc[0]
                
                st.write(f"**คอร์ส:** {selected_course}")
                st.markdown("---")
                
                # Load existing exercises
                exercises_data = get_course_exercises(course_id)
                
                # Display existing exercises
                st.subheader("แบบฝึกหัดที่มีอยู่")
                if exercises_data:
                    for lesson_index, lesson_exercises in enumerate(exercises_data):
                        exercises = lesson_exercises.get("exercises", [])
                        if exercises:
                            st.write(f"**บทที่ {lesson_index + 1}**")
                            for i, exercise in enumerate(exercises):
                                with st.expander(f"แบบฝึกหัดที่ {i+1}"):
                                    st.write(f"**คำถาม:** {exercise.get('question', '')}")
                                    st.write(f"**เฉลย:** {exercise.get('answer', '')}")
                
                # Add new exercise
                st.subheader("เพิ่มแบบฝึกหัดใหม่")
                
                # Get lessons for selection
                lessons = get_course_lessons(course_id)
                
                if lessons:
                    with st.form("add_exercise_form"):
                        lesson_options = [f"บทที่ {i+1}: {l.get('title', 'ไม่มีชื่อ')}" for i, l in enumerate(lessons)]
                        selected_lesson = st.selectbox("เลือกบทเรียน", lesson_options, key="exercise_lesson_select")
                        lesson_index = int(selected_lesson.split(":")[0].replace("บทที่ ", "")) - 1
                        
                        exercise_question = st.text_area("**คำถาม** *", height=100, key="exercise_question_input")
                        exercise_answer = st.text_area("**เฉลย** *", height=100, key="exercise_answer_input")
                        
                        col_save, _ = st.columns(2)
                        with col_save:
                            submitted = st.form_submit_button("✅ บันทึกแบบฝึกหัด", use_container_width=True)
                        
                        if submitted:
                            if exercise_question and exercise_answer:
                                # Create exercise data
                                new_exercise = {
                                    "lesson_index": lesson_index,
                                    "exercises": [{
                                        "question": exercise_question,
                                        "answer": exercise_answer,
                                        "image_path": "",
                                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }]
                                }
                                
                                success = save_exercise(course_id, new_exercise)
                                if success:
                                    st.success("✅ **บันทึกแบบฝึกหัดสำเร็จ!**")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("เกิดข้อผิดพลาดในการบันทึกแบบฝึกหัด")
                            else:
                                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
                else:
                    st.info("กรุณาสร้างบทเรียนก่อนเพิ่มแบบฝึกหัด")
            else:
                st.info("ยังไม่มีคอร์สเรียน")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
    
    # ---------- LIVE TEACHING ----------
    elif menu_choice == "🎥 สอนสด":
        st.title("🎥 การสอนสด")
        st.markdown("---")
        
        try:
            my_courses = get_teacher_courses(st.session_state.teacher_id)
            
            if not my_courses.empty:
                selected_course = st.selectbox(
                    "**เลือกคอร์ส**", 
                    my_courses["course_name"].tolist(), 
                    key="live_course_select"
                )
                course_info = my_courses[my_courses["course_name"] == selected_course].iloc[0]
                
                st.subheader(f"คอร์ส: {course_info['course_name']}")
                st.write(f"**ครูผู้สอน:** {st.session_state.teacher_name}")
                st.markdown("---")
                
                # Save Jitsi info
                st.session_state.jitsi_room_name = course_info.get('jitsi_room', 'default_room')
                st.session_state.jitsi_display_name = st.session_state.teacher_name
                
                # Jitsi Connection Control
                col_connect, col_disconnect = st.columns(2)
                with col_connect:
                    if st.button("🔗 เริ่มการสอนสด", type="primary", use_container_width=True):
                        st.session_state.jitsi_connected = True
                        st.rerun()
                with col_disconnect:
                    if st.button("❌ หยุดการสอน", use_container_width=True):
                        st.session_state.jitsi_connected = False
                        st.rerun()
                
                if st.session_state.jitsi_connected:
                    room = str(course_info.get("jitsi_room", "default_room"))
                    
                    # Jitsi for teacher
                    jitsi_code = f'''
                    <div class="jitsi-container">
                        <iframe 
                            src="https://meet.jit.si/{room}?userInfo.displayName={st.session_state.teacher_name.replace(' ', '%20')}" 
                            class="jitsi-iframe"
                            allow="camera; microphone; fullscreen; display-capture; autoplay"
                            allowfullscreen
                            title="Jitsi Meet"
                            loading="lazy">
                        </iframe>
                    </div>
                    '''
                    st.markdown(jitsi_code, unsafe_allow_html=True)
                else:
                    st.info("โปรดกดปุ่ม 'เริ่มการสอนสด' เพื่อเริ่มเซสชันการสอน")
                
                # Link for students
                st.markdown("---")
                st.markdown("### 🔗 ลิงก์สำหรับนักเรียน")
                room = course_info.get("jitsi_room", "default_room")
                st.code(f"https://meet.jit.si/{room}", language="bash")
                
                # End session
                st.markdown("---")
                if st.button("🏁 จบการเรียน", type="secondary", key="end_session", use_container_width=True):
                    st.session_state.jitsi_connected = False
                    st.session_state.page = "teacher_dashboard"
                    st.rerun()
            else:
                st.info("ยังไม่มีคอร์สเรียน")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

# -----------------------------
# EDIT LESSON PAGE
# -----------------------------
elif st.session_state.page == "edit_lesson" and st.session_state.role == "teacher":
    if "edit_course_id" in st.session_state and "edit_lesson_idx" in st.session_state:
        course_id = st.session_state.edit_course_id
        lesson_idx = st.session_state.edit_lesson_idx
        
        st.title("✏️ แก้ไขบทเรียน")
        st.markdown("---")
        
        # Load lessons
        lessons = get_course_lessons(course_id)
        
        if 0 <= lesson_idx < len(lessons):
            lesson = lessons[lesson_idx]
            
            with st.form("edit_lesson_form"):
                lesson_title = st.text_input("**หัวข้อบทเรียน** *", value=lesson.get('title', ''), key="edit_lesson_title")
                lesson_content = st.text_area("**เนื้อหาบทเรียน** *", value=lesson.get('content', ''), height=200, key="edit_lesson_content")
                
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    save_btn = st.form_submit_button("💾 บันทึกการแก้ไข", type="primary", use_container_width=True)
                
                with col2:
                    cancel_btn = st.form_submit_button("❌ ยกเลิก", use_container_width=True)
                
                if cancel_btn:
                    st.session_state.page = "manage_lessons"
                    st.rerun()
                
                if save_btn:
                    if lesson_title and lesson_content:
                        # Update lesson
                        lessons[lesson_idx]["title"] = lesson_title
                        lessons[lesson_idx]["content"] = lesson_content
                        lessons[lesson_idx]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Save to file
                        lesson_file = f"save_data/lessons/{course_id}_lessons.json"
                        with open(lesson_file, "w", encoding="utf-8") as f:
                            json.dump(lessons, f, ensure_ascii=False, indent=2)
                        
                        st.success("✅ **บันทึกการแก้ไขสำเร็จ!**")
                        time.sleep(1)
                        st.session_state.page = "manage_lessons"
                        st.rerun()
                    else:
                        st.error("กรุณากรอกข้อมูลที่จำเป็น (*)")
        else:
            st.error("ไม่พบบทเรียน")
            st.session_state.page = "manage_lessons"
            st.rerun()
    else:
        st.session_state.page = "teacher_dashboard"
        st.rerun()

# -----------------------------
# EDIT COURSE PAGE
# -----------------------------
elif st.session_state.page == "edit_course" and st.session_state.role == "teacher":
    if "edit_course" in st.session_state:
        course_info = st.session_state.edit_course
        
        st.title("✏️ แก้ไขข้อมูลคอร์ส")
        st.markdown("---")
        
        with st.form("edit_course_form"):
            st.subheader("ข้อมูลพื้นฐาน")
            
            col1, col2 = st.columns(2)
            with col1:
                course_name = st.text_input("**ชื่อคอร์ส** *", value=course_info.get('course_name', ''), key="edit_course_name")
                class_type = st.selectbox(
                    "**ประเภทการเรียน** *", 
                    ["ตัวต่อตัว (1:1)", "กลุ่มเล็ก (2-5 คน)", "กลุ่มใหญ่"], 
                    index=["ตัวต่อตัว (1:1)", "กลุ่มเล็ก (2-5 คน)", "กลุ่มใหญ่"].index(course_info.get('class_type', 'กลุ่ม')) 
                    if course_info.get('class_type') in ["ตัวต่อตัว (1:1)", "กลุ่มเล็ก (2-5 คน)", "กลุ่มใหญ่"] else 0,
                    key="edit_class_type"
                )
            
            with col2:
                max_students = st.number_input(
                    "**จำนวนนักเรียนสูงสุด**", 
                    min_value=1, max_value=50, 
                    value=int(course_info.get('max_students', 10)),
                    key="edit_max_students"
                )
                
                jitsi_room = st.text_input(
                    "**ชื่อห้อง Jitsi** *", 
                    value=course_info.get('jitsi_room', ''),
                    key="edit_jitsi_room"
                )
            
            st.subheader("รายละเอียดคอร์ส")
            description = st.text_area(
                "**คำอธิบายคอร์ส** *", 
                value=course_info.get('description', ''),
                height=100, 
                key="edit_description"
            )
            
            status = st.selectbox(
                "**สถานะ**", 
                ["active", "inactive", "completed"],
                index=["active", "inactive", "completed"].index(course_info.get('status', 'active'))
                if course_info.get('status') in ["active", "inactive", "completed"] else 0,
                key="edit_status"
            )
            
            st.markdown("---")
            col1_btn, col2_btn = st.columns(2)
            
            with col1_btn:
                save_btn = st.form_submit_button("💾 บันทึกการแก้ไข", type="primary", use_container_width=True)
            
            with col2_btn:
                cancel_btn = st.form_submit_button("❌ ยกเลิก", use_container_width=True)
            
            if cancel_btn:
                st.session_state.page = "teacher_dashboard"
                st.rerun()
            
            if save_btn:
                if not all([course_name, jitsi_room, description]):
                    st.error("กรุณากรอกข้อมูลที่จำเป็น (*)")
                else:
                    try:
                        # Prepare updates
                        updates = {
                            "course_name": course_name,
                            "class_type": class_type,
                            "max_students": max_students,
                            "jitsi_room": jitsi_room,
                            "description": description,
                            "status": status
                        }
                        
                        # Update in Google Sheets
                        success = update_course(course_info["course_id"], updates)
                        
                        if success:
                            st.success("✅ **บันทึกการแก้ไขสำเร็จ!**")
                            time.sleep(1)
                            st.session_state.page = "teacher_dashboard"
                            st.rerun()
                        else:
                            st.error("เกิดข้อผิดพลาดในการบันทึก")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
    else:
        st.session_state.page = "teacher_dashboard"
        st.rerun()


# -----------------------------
# MANAGE LESSONS PAGE
# -----------------------------
elif st.session_state.page == "manage_lessons" and st.session_state.role == "teacher":
    st.title("📖 จัดการบทเรียน")
    st.markdown("---")
    
    try:
        course_id = st.session_state.current_course
        
        # Get course details
        courses_df = get_sheet_data("courses")
        course_info = courses_df[courses_df["course_id"] == course_id].iloc[0]
        
        st.write(f"**คอร์ส:** {course_info['course_name']}")
        st.markdown("---")
        
        # Load existing lessons
        lessons = get_course_lessons(course_id)
        
        # Display existing lessons (แก้ไขตามข้อ 4 - เอาส่วนเนื้อหาออก)
        st.subheader("บทเรียนที่มีอยู่")
        if lessons:
            for i, lesson in enumerate(lessons):
                with st.expander(f"บทที่ {i+1}: {lesson.get('title', 'ไม่มีชื่อ')}"):
                    # เอาส่วนเนื้อหาออกตามข้อ 4
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✏️ แก้ไข", key=f"edit_lesson_{course_id}_{i}", use_container_width=True):
                            st.session_state.edit_lesson_idx = i
                            st.session_state.edit_course_id = course_id
                            st.session_state.page = "edit_lesson"
                            st.rerun()
                    with col2:
                        if st.button("🗑️ ลบ", key=f"delete_lesson_{course_id}_{i}", use_container_width=True):
                            lessons.pop(i)
                            lesson_file = f"save_data/lessons/{course_id}_lessons.json"
                            with open(lesson_file, "w", encoding="utf-8") as f:
                                json.dump(lessons, f, ensure_ascii=False, indent=2)
                            st.success("ลบบทเรียนเรียบร้อย")
                            st.rerun()
        else:
            st.info("ยังไม่มีบทเรียนในคอร์สนี้")
        
        # Add new lesson
        st.subheader("เพิ่มบทเรียนใหม่")
        with st.form("add_lesson_form", clear_on_submit=True):
            lesson_title = st.text_input("**หัวข้อบทเรียน** *", key=f"new_lesson_title_{course_id}")
            lesson_content = st.text_area("**เนื้อหาบทเรียน** *", height=200, key=f"new_lesson_content_{course_id}")
            lesson_file_upload = st.file_uploader(
                "**อัปโหลดไฟล์ประกอบ** (ไม่บังคับ)", 
                type=["pdf", "ppt", "pptx", "doc", "docx", "txt"], 
                key=f"lesson_file_upload_{course_id}"
            )
            
            col_add, col_cancel = st.columns(2)
            with col_add:
                submitted = st.form_submit_button("✅ เพิ่มบทเรียน", use_container_width=True)
            
            if submitted:
                if lesson_title and lesson_content:
                    # Save uploaded file
                    file_path = ""
                    if lesson_file_upload:
                        success, result = save_document(course_id, lesson_file_upload, lesson_file_upload.name)
                        if success:
                            file_path = result
                        else:
                            st.warning(f"ไม่สามารถบันทึกไฟล์: {result}")
                    
                    # Add new lesson
                    new_lesson = {
                        "title": lesson_title,
                        "content": lesson_content,
                        "file": file_path,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    success = save_lesson(course_id, new_lesson)
                    if success:
                        st.success("✅ **เพิ่มบทเรียนสำเร็จ!**")
                        st.rerun()
                    else:
                        st.error("เกิดข้อผิดพลาดในการบันทึกบทเรียน")
                else:
                    st.error("กรุณากรอกข้อมูลที่จำเป็น (*)")
        
        # Back button
        st.markdown("---")
        if st.button("⬅ กลับสู่แดชบอร์ด", use_container_width=True):
            st.session_state.page = "teacher_dashboard"
            st.rerun()
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
        st.session_state.page = "teacher_dashboard"
        st.rerun()

# -----------------------------
# Main App Runner
# -----------------------------
if __name__ == "__main__":
    # Display current page for debugging
    if st.session_state.get("debug", False):
        st.sidebar.write(f"Page: {st.session_state.page}")
        st.sidebar.write(f"Role: {st.session_state.role}")
        st.sidebar.write(f"Jitsi Connected: {st.session_state.jitsi_connected}")

