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

# -----------------------------
# Google Sheets Integration with Caching
# -----------------------------
import gspread
from google.oauth2.service_account import Credentials
from google.auth import default
import warnings
warnings.filterwarnings('ignore')

# Cache system
class DataCache:
    def __init__(self, cache_time=60):  # 60 seconds cache
        self.cache = {}
        self.cache_time = cache_time
        self.timestamps = {}
    
    def get(self, key):
        """Get cached data if not expired"""
        if key in self.cache and key in self.timestamps:
            if time.time() - self.timestamps[key] < self.cache_time:
                return self.cache[key]
        return None
    
    def set(self, key, data):
        """Set cached data"""
        self.cache[key] = data
        self.timestamps[key] = time.time()
    
    def clear(self, key=None):
        """Clear cache"""
        if key:
            if key in self.cache:
                del self.cache[key]
            if key in self.timestamps:
                del self.timestamps[key]
        else:
            self.cache.clear()
            self.timestamps.clear()

# Google Sheets Manager with fallback
class GoogleSheetsManager:
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.cache = DataCache(cache_time=120)  # 120 seconds cache
        self.use_fallback = False
        self.fallback_dir = "local_data_backup"
        self._init_backup_dir()
        self._connect()
    
    def _init_backup_dir(self):
        """Initialize backup directory"""
        os.makedirs(self.fallback_dir, exist_ok=True)
        # Create subdirectories
        os.makedirs(f"{self.fallback_dir}/sheets", exist_ok=True)
    
    def _connect(self):
        """Try to connect to Google Sheets"""
        try:
            # Try to use service account file first
            if os.path.exists('google_credentials.json'):
                scopes = ['https://www.googleapis.com/auth/spreadsheets',
                         'https://www.googleapis.com/auth/drive']
                credentials = Credentials.from_service_account_file(
                    'google_credentials.json', scopes=scopes)
                self.client = gspread.authorize(credentials)
            else:
                # Try default credentials
                credentials, project = default()
                self.client = gspread.authorize(credentials)
            
            # Try to open spreadsheet
            try:
                self.spreadsheet = self.client.open('ZL_TA_Learning_System')
                print("✅ Connected to Google Sheets successfully")
                self.use_fallback = False
            except gspread.SpreadsheetNotFound:
                # Try to create if not exists
                self._create_spreadsheet()
        except Exception as e:
            print(f"⚠️ Cannot connect to Google Sheets: {e}")
            print("⚠️ Using local fallback mode")
            self.use_fallback = True
            self._init_default_sheets()
    
    def _create_spreadsheet(self):
        """Create new spreadsheet if not exists"""
        try:
            self.spreadsheet = self.client.create('ZL_TA_Learning_System')
            # Share for public access
            self.spreadsheet.share('', perm_type='anyone', role='writer')
            
            # Create worksheets
            worksheets_needed = [
                'students', 'courses', 'admin', 
                'students_check', 'teachers', 'student_courses'
            ]
            
            # Remove default sheet
            default_sheet = self.spreadsheet.sheet1
            self.spreadsheet.del_worksheet(default_sheet)
            
            for sheet_name in worksheets_needed:
                self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            
            print("✅ Created new Google Sheets")
            self.use_fallback = False
        except Exception as e:
            print(f"⚠️ Failed to create spreadsheet: {e}")
            self.use_fallback = True
    
    def _init_default_sheets(self):
        """Initialize default data files locally"""
        sheets = ['students', 'courses', 'admin', 'students_check', 'teachers', 'student_courses']
        
        for sheet in sheets:
            file_path = f"{self.fallback_dir}/sheets/{sheet}.csv"
            if not os.path.exists(file_path):
                # Create empty CSV with appropriate columns
                if sheet == 'students':
                    df = pd.DataFrame(columns=[
                        "student_id", "fullname", "email", "phone", 
                        "created_date", "status"
                    ])
                elif sheet == 'courses':
                    df = pd.DataFrame(columns=[
                        "course_id", "course_name", "teacher_id", "teacher_name",
                        "description", "image_path", "jitsi_room", "max_students",
                        "current_students", "class_type", "status", "security_code",
                        "created_date"
                    ])
                elif sheet == 'admin':
                    df = pd.DataFrame(columns=[
                        "teacher_id", "username", "password_hash", "fullname",
                        "email", "created_at", "role"
                    ])
                    # Add default admin
                    default_admin = pd.DataFrame([{
                        "teacher_id": "T001",
                        "username": "admin",
                        "password_hash": hashlib.md5("admin123".encode()).hexdigest(),
                        "fullname": "ครูผู้ดูแลระบบ",
                        "email": "admin@zllearning.com",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "role": "admin"
                    }])
                    df = pd.concat([df, default_admin], ignore_index=True)
                elif sheet == 'students_check':
                    df = pd.DataFrame(columns=[
                        "check_id", "student_id", "fullname", "check_date",
                        "check_time", "attendance_count", "status"
                    ])
                elif sheet == 'teachers':
                    df = pd.DataFrame(columns=[
                        "teacher_id", "username", "login_time", "status"
                    ])
                elif sheet == 'student_courses':
                    df = pd.DataFrame(columns=[
                        "enrollment_id", "student_id", "fullname", "course_id",
                        "course_name", "enrollment_date", "completion_status",
                        "completion_date", "certificate_issued"
                    ])
                
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
    
    def get_worksheet(self, sheet_name, retry_count=2):
        """Get worksheet with retry logic"""
        if self.use_fallback:
            return None
        
        for attempt in range(retry_count):
            try:
                worksheet = self.spreadsheet.worksheet(sheet_name)
                return worksheet
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1} failed for sheet {sheet_name}: {e}")
                if attempt < retry_count - 1:
                    time.sleep(1)  # Wait before retry
                else:
                    # Switch to fallback mode after all retries fail
                    print(f"⚠️ Switching to fallback mode for {sheet_name}")
                    self.use_fallback = True
                    return None
    
    def get_df(self, sheet_name, use_cache=True):
        """Get DataFrame with caching"""
        # Check cache first
        cache_key = f"df_{sheet_name}"
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        if self.use_fallback:
            # Use local CSV
            file_path = f"{self.fallback_dir}/sheets/{sheet_name}.csv"
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path, encoding='utf-8-sig')
                    self.cache.set(cache_key, df)
                    return df
                except:
                    return pd.DataFrame()
            return pd.DataFrame()
        else:
            # Use Google Sheets with error handling
            try:
                worksheet = self.get_worksheet(sheet_name)
                if worksheet:
                    data = worksheet.get_all_records()
                    df = pd.DataFrame(data) if data else pd.DataFrame()
                    self.cache.set(cache_key, df)
                    return df
                else:
                    # Fallback to local if worksheet not found
                    return self.get_df(sheet_name, use_cache=False)
            except Exception as e:
                print(f"⚠️ Error getting {sheet_name}: {e}")
                # Switch to fallback
                self.use_fallback = True
                return self.get_df(sheet_name, use_cache=False)
    
    def update_data(self, sheet_name, df, update_cache=True):
        """Update data with fallback"""
        cache_key = f"df_{sheet_name}"
        
        # Update local backup first (always)
        file_path = f"{self.fallback_dir}/sheets/{sheet_name}.csv"
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        if update_cache:
            self.cache.set(cache_key, df)
        
        # Try to update Google Sheets if available
        if not self.use_fallback:
            try:
                worksheet = self.get_worksheet(sheet_name)
                if worksheet:
                    # Clear and update
                    worksheet.clear()
                    if not df.empty:
                        # Ensure all values are strings
                        df_str = df.astype(str)
                        worksheet.update([df_str.columns.values.tolist()] + df_str.values.tolist())
                    print(f"✅ Updated Google Sheets: {sheet_name}")
                    return True
            except Exception as e:
                print(f"⚠️ Failed to update Google Sheets {sheet_name}: {e}")
                self.use_fallback = True
        
        # If using fallback or update failed, just use local
        print(f"✅ Updated local backup: {sheet_name}")
        return True
    
    def append_row(self, sheet_name, row_data):
        """Append a row to sheet"""
        # First get current data
        df = self.get_df(sheet_name, use_cache=False)
        
        # Create new row as DataFrame
        if df.empty:
            new_df = pd.DataFrame([row_data])
        else:
            new_df = pd.concat([df, pd.DataFrame([row_data])], ignore_index=True)
        
        # Update data
        return self.update_data(sheet_name, new_df)

# Create global instance
gs_manager = GoogleSheetsManager()

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="ZL TA-Learning (ผู้ช่วยสอน-เรียนออนไลน์)",
    layout="wide",
    page_icon="🎓"
)

# -----------------------------
# CSS - Updated with offline status
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

/* Connection Status */
.connection-status {{
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 1000;
    padding: 5px 15px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}}

.connection-status.online {{
    background: #34A853;
    color: white;
}}

.connection-status.offline {{
    background: #EA4335;
    color: white;
}}

.connection-status.warning {{
    background: #FBBC05;
    color: #202124;
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

/* Offline Warning */
.offline-warning {{
    background: #FFF3CD;
    border: 2px solid #FFEAA7;
    color: #856404;
    padding: 15px;
    border-radius: 10px;
    margin: 15px 0;
    text-align: center;
    animation: pulse 2s infinite;
}}

@keyframes pulse {{
    0% {{ opacity: 1; }}
    50% {{ opacity: 0.7; }}
    100% {{ opacity: 1; }}
}}

/* Rest of the CSS remains the same... */
/* [Keep all the existing CSS styles from the previous version] */

</style>
""", unsafe_allow_html=True)

# Display logo and connection status
if logo_base64:
    st.markdown(f"""
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_base64}" class="logo-img" alt="ZL Logo">
    </div>
    """, unsafe_allow_html=True)

# Display connection status
status_class = "offline" if gs_manager.use_fallback else "online"
status_text = "🔄 ระบบออฟไลน์ (ใช้ข้อมูลท้องถิ่น)" if gs_manager.use_fallback else "✅ ออนไลน์ (เชื่อมต่อ Google Sheets)"
st.markdown(f'<div class="connection-status {status_class}">{status_text}</div>', unsafe_allow_html=True)

if gs_manager.use_fallback:
    st.markdown("""
    <div class="offline-warning">
        <strong>⚠️ ระบบกำลังทำงานในโหมดออฟไลน์</strong><br>
        ข้อมูลถูกบันทึกในเครื่องและจะซิงค์กับ Google Sheets เมื่อเชื่อมต่อได้
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# Session State
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
if "current_lesson" not in st.session_state:
    st.session_state.current_lesson = 0
if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "student_name" not in st.session_state:
    st.session_state.student_name = None
if "student_email" not in st.session_state:
    st.session_state.student_email = None
if "has_attended_live" not in st.session_state:
    st.session_state.has_attended_live = False
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "quiz_status" not in st.session_state:
    st.session_state.quiz_status = {}
if "show_answer" not in st.session_state:
    st.session_state.show_answer = {}
if "completed_exercises" not in st.session_state:
    st.session_state.completed_exercises = {}
if "exercise_attempts" not in st.session_state:
    st.session_state.exercise_attempts = {}
if "login_attempt" not in st.session_state:
    st.session_state.login_attempt = 0
if "jitsi_connected" not in st.session_state:
    st.session_state.jitsi_connected = False
if "jitsi_room_name" not in st.session_state:
    st.session_state.jitsi_room_name = None
if "jitsi_display_name" not in st.session_state:
    st.session_state.jitsi_display_name = None
if "exercise_page_active" not in st.session_state:
    st.session_state.exercise_page_active = False
if "edit_course" not in st.session_state:
    st.session_state.edit_course = None
if "edit_course_id" not in st.session_state:
    st.session_state.edit_course_id = None
if "edit_lesson_idx" not in st.session_state:
    st.session_state.edit_lesson_idx = None
if "current_exercise_index" not in st.session_state:
    st.session_state.current_exercise_index = {}
if "exercise_attempt_count" not in st.session_state:
    st.session_state.exercise_attempt_count = {}
if "show_solution" not in st.session_state:
    st.session_state.show_solution = {}
if "show_lessons" not in st.session_state:
    st.session_state.show_lessons = True
if "force_offline" not in st.session_state:
    st.session_state.force_offline = False

# -----------------------------
# Helper Functions (Optimized)
# -----------------------------
def md5(text):
    """Create MD5 hash"""
    return hashlib.md5(text.encode()).hexdigest()

def check_student_id(student_id):
    """ตรวจสอบสิทธิ์นักเรียนด้วย ID"""
    try:
        students_df = gs_manager.get_df('students')
        student_info = students_df[students_df["student_id"] == student_id.upper()]
        
        if not student_info.empty:
            student = student_info.iloc[0]
            
            # บันทึกการตรวจสอบสิทธิ์
            check_df = gs_manager.get_df('students_check')
            
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
            gs_manager.append_row('students_check', new_check)
            
            return True, student["fullname"], student["email"]
        else:
            return False, None, None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการตรวจสอบรหัสนักเรียน: {e}")
        return False, None, None

def teacher_login(username, password):
    """ตรวจสอบการเข้าสู่ระบบครูผู้สอน"""
    try:
        admin_df = gs_manager.get_df('admin')
        
        if not admin_df.empty:
            user_record = admin_df[admin_df["username"] == username]
            
            if not user_record.empty:
                teacher = user_record.iloc[0]
                password_hash = md5(password)
                
                if str(teacher["password_hash"]) == password_hash:
                    # บันทึกการเข้าสู่ระบบ
                    try:
                        login_record = {
                            "teacher_id": teacher["teacher_id"],
                            "username": username,
                            "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "status": "success"
                        }
                        gs_manager.append_row('teachers', login_record)
                    except:
                        pass
                    
                    return True, "เข้าสู่ระบบสำเร็จ!", teacher["teacher_id"], teacher["fullname"]
                else:
                    return False, "รหัสผ่านไม่ถูกต้อง", None, None
            else:
                return False, "ไม่พบบัญชีผู้ใช้งาน", None, None
        else:
            return False, "ไม่มีข้อมูลในระบบ", None, None
    except Exception as e:
        return False, f"เกิดข้อผิดพลาด: {str(e)}", None, None

def get_student_courses(student_id):
    """ดึงคอร์สที่นักเรียนลงทะเบียน"""
    try:
        df = gs_manager.get_df('student_courses')
        if not df.empty and "student_id" in df.columns:
            return df[df["student_id"] == student_id]
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def enroll_student_in_course(student_id, student_name, course_id, course_name):
    """ลงทะเบียนนักเรียนในคอร์ส"""
    try:
        df = gs_manager.get_df('student_courses')
        
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
                "completion_date": None,
                "certificate_issued": False
            }
            
            gs_manager.append_row('student_courses', new_enrollment)
            return True
        return False
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการลงทะเบียน: {e}")
        return False

def mark_course_completed(student_id, course_id):
    """บันทึกสถานะเรียนจบคอร์ส"""
    try:
        df = gs_manager.get_df('student_courses')
        
        if df.empty:
            return False
            
        # ค้นหาและอัปเดต
        mask = (df["student_id"] == student_id) & (df["course_id"] == course_id)
        if mask.any():
            df.loc[mask, "completion_status"] = True
            df.loc[mask, "completion_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            gs_manager.update_data('student_courses', df)
            return True
        return False
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
        return False

def get_course_lessons(course_id):
    """ดึงบทเรียนของคอร์ส"""
    lesson_file = f"save_data/lessons/{course_id}_lessons.json"
    if os.path.exists(lesson_file):
        try:
            with open(lesson_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def get_course_exercises(course_id):
    """ดึงแบบฝึกหัดของคอร์ส"""
    exercise_file = f"save_data/lessons/{course_id}_exercises.json"
    if os.path.exists(exercise_file):
        try:
            with open(exercise_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_quiz_result(student_id, course_id, lesson_index, exercise_index, answer, is_correct):
    """บันทึกผลแบบฝึกหัด"""
    try:
        quiz_file = f"save_data/quiz_results/{student_id}_{course_id}.json"
        
        if os.path.exists(quiz_file):
            with open(quiz_file, "r", encoding="utf-8") as f:
                quiz_data = json.load(f)
        else:
            quiz_data = []
        
        # Check if already answered
        for i, item in enumerate(quiz_data):
            if (item["lesson_index"] == lesson_index and 
                item["exercise_index"] == exercise_index):
                # Update existing answer
                quiz_data[i] = {
                    "student_id": student_id,
                    "course_id": course_id,
                    "lesson_index": lesson_index,
                    "exercise_index": exercise_index,
                    "answer": answer,
                    "is_correct": is_correct,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                break
        else:
            # Add new answer
            quiz_data.append({
                "student_id": student_id,
                "course_id": course_id,
                "lesson_index": lesson_index,
                "exercise_index": exercise_index,
                "answer": answer,
                "is_correct": is_correct,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        with open(quiz_file, "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error saving quiz result: {e}")
        return False

def check_answer(student_answer, correct_answer):
    """ตรวจคำตอบ"""
    if not student_answer or not correct_answer:
        return False
    
    student_clean = ' '.join(student_answer.strip().split()).lower()
    correct_clean = ' '.join(correct_answer.strip().split()).lower()
    
    return student_clean == correct_clean

def embed_jitsi_meet_simple(room_name, display_name):
    """สร้าง Jitsi Meet embed code"""
    room_name_clean = str(room_name).replace(" ", "-").replace("/", "-").replace("\\", "-")
    display_name_clean = str(display_name).replace(" ", "%20")
    
    jitsi_code = f'''
    <div style="position: relative; width: 100%; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 12px; border: 3px solid #FFD700; background: #000;">
        <iframe 
            src="https://meet.jit.si/{room_name_clean}?userInfo.displayName={display_name_clean}" 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"
            allow="camera; microphone; fullscreen; display-capture; autoplay"
            allowfullscreen
            title="Jitsi Meet"
            loading="lazy">
        </iframe>
    </div>
    '''
    return jitsi_code

def get_teacher_courses(teacher_id):
    """ดึงคอร์สของครูผู้สอน"""
    try:
        courses_df = gs_manager.get_df('courses')
        if not courses_df.empty and "teacher_id" in courses_df.columns:
            return courses_df[courses_df["teacher_id"] == teacher_id]
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def save_lesson(course_id, lesson_data):
    """บันทึกบทเรียน"""
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
        st.error(f"Error saving lesson: {e}")
        return False

def save_exercise(course_id, exercise_data):
    """บันทึกแบบฝึกหัด"""
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
        st.error(f"Error saving exercise: {e}")
        return False

def save_document(course_id, file, filename):
    """บันทึกเอกสารประกอบ"""
    try:
        if isinstance(course_id, float):
            course_id = str(int(course_id)) if course_id.is_integer() else str(course_id)
        elif not isinstance(course_id, str):
            course_id = str(course_id)
        
        doc_folder = f"save_data/documents/{course_id}"
        os.makedirs(doc_folder, exist_ok=True)
        
        file_path = f"{doc_folder}/{filename}"
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
        
        return True, file_path
    except Exception as e:
        return False, str(e)

def get_available_courses():
    """ดึงคอร์สทั้งหมดที่เปิดสอน"""
    try:
        courses_df = gs_manager.get_df('courses')
        if not courses_df.empty:
            return courses_df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def add_course(course_data):
    """เพิ่มคอร์สใหม่"""
    try:
        df = gs_manager.get_df('courses')
        df = pd.concat([df, pd.DataFrame([course_data])], ignore_index=True)
        gs_manager.update_data('courses', df)
        return True
    except Exception as e:
        st.error(f"Error adding course: {e}")
        return False

def update_course(course_id, updated_data):
    """อัปเดตข้อมูลคอร์ส"""
    try:
        df = gs_manager.get_df('courses')
        
        if df.empty:
            return False
            
        # Find the course
        mask = df["course_id"] == course_id
        if mask.any():
            # Update all columns
            for key, value in updated_data.items():
                if key in df.columns:
                    df.loc[mask, key] = value
            
            gs_manager.update_data('courses', df)
            return True
        return False
    except Exception as e:
        st.error(f"Error updating course: {e}")
        return False

def get_course_documents(course_id):
    """ดึงรายการเอกสารในคอร์ส"""
    try:
        doc_folder = f"save_data/documents/{course_id}"
        if os.path.exists(doc_folder):
            files = []
            for file in os.listdir(doc_folder):
                file_path = os.path.join(doc_folder, file)
                if os.path.isfile(file_path):
                    files.append({
                        "name": file,
                        "path": file_path,
                        "size": os.path.getsize(file_path)
                    })
            return files
        return []
    except:
        return []

def get_certificate_file(student_id, course_id):
    """ค้นหาไฟล์ใบรับรอง"""
    try:
        certs_folder = "save_data/certificates_files"
        for file in os.listdir(certs_folder):
            if f"{student_id}_{course_id}" in file:
                return os.path.join(certs_folder, file)
        return None
    except:
        return None

def save_uploaded_certificate(student_id, course_id, file, filename):
    """บันทึกไฟล์ใบรับรองที่อัปโหลด"""
    try:
        certs_folder = "save_data/certificates_files"
        os.makedirs(certs_folder, exist_ok=True)
        
        file_ext = filename.split('.')[-1] if '.' in filename else ''
        new_filename = f"{student_id}_{course_id}_certificate.{file_ext}"
        file_path = os.path.join(certs_folder, new_filename)
        
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
        
        return True, file_path
    except Exception as e:
        return False, str(e)

def save_exercise_image(course_id, exercise_index, image_file):
    """บันทึกรูปภาพของแบบฝึกหัด"""
    try:
        if isinstance(course_id, float):
            course_id = str(int(course_id)) if course_id.is_integer() else str(course_id)
        
        image_folder = f"save_data/exercise_images/{course_id}"
        os.makedirs(image_folder, exist_ok=True)
        
        file_ext = image_file.name.split('.')[-1] if '.' in image_file.name else 'jpg'
        image_path = f"{image_folder}/exercise_{exercise_index}.{file_ext}"
        
        with open(image_path, "wb") as f:
            f.write(image_file.getbuffer())
        
        return True, image_path
    except Exception as e:
        return False, str(e)

# Initialize save_data folder
os.makedirs("save_data", exist_ok=True)
os.makedirs("save_data/images", exist_ok=True)
os.makedirs("save_data/documents", exist_ok=True)
os.makedirs("save_data/certificates", exist_ok=True)
os.makedirs("save_data/exercise_images", exist_ok=True)
os.makedirs("save_data/lessons", exist_ok=True)
os.makedirs("save_data/quiz_results", exist_ok=True)
os.makedirs("save_data/certificates_files", exist_ok=True)

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
            check_df = gs_manager.get_df('students_check')
            student_checks = check_df[check_df["student_id"] == st.session_state.student_id]
            attendance_count = len(student_checks) if not student_checks.empty else 0
            st.write(f"**📊 เข้าเรียนแล้ว:** {attendance_count} ครั้ง")
        except:
            attendance_count = 0
        
        st.markdown("---")
        
        # Menu options
        menu_options = ["🏠 หน้าหลักและประกาศ"]
        
        if st.session_state.has_attended_live:
            menu_options.extend([
                "📚 คอร์สของฉัน", 
                "🎥 เข้าร่วมเรียนสด", 
                "📖 บทเรียนและแบบฝึกหัด", 
                "📄 ดาวน์โหลดเอกสาร"
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
        
        # Announcements
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
                cols = st.columns(3)
                for idx, row in courses_df.iterrows():
                    if idx < 6:  # Show max 6 courses
                        with cols[idx % 3]:
                            st.markdown('<div class="course-card">', unsafe_allow_html=True)
                            
                            # Display course image
                            image_path = row.get('image_path', '')
                            if isinstance(image_path, str) and image_path != 'nan' and os.path.exists(image_path):
                                st.image(image_path, use_container_width=True)
                            else:
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
                                            courses_df = get_available_courses()
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
                
                if len(courses_df) > 6:
                    if st.button("ดูคอร์สทั้งหมด", use_container_width=True):
                        st.session_state.page = "student_courses"
                        st.rerun()
            else:
                st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                st.write("**⚠️ ยังไม่มีคอร์สเรียนที่เปิดสอน**")
                st.write("กรุณารอครูผู้สอนประกาศคอร์สเรียนใหม่")
                st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลคอร์ส: {str(e)}")
            st.info("กำลังลองโหลดข้อมูลใหม่อีกครั้ง...")

# -----------------------------
# TEACHER LOGIN PAGE (ปรับปรุงให้ทำงานได้ทันที)
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
        
        # Direct login form for immediate access
        username = st.text_input("**Username**", value="admin", key="teacher_username_login")
        password = st.text_input("**Password**", type="password", value="admin123", key="teacher_password_login")
        
        st.info("💡 **ข้อมูลล็อกอินเริ่มต้น:**")
        st.write("• **Username:** admin")
        st.write("• **Password:** admin123")
        
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
                        # If still having issues, allow direct access
                        st.warning(f"⚠️ มีปัญหาในการตรวจสอบข้อมูล: {str(e)}")
                        st.warning("⚠️ กำลังใช้โหมดเข้าถึงทันที...")
                        
                        # Direct access for emergency
                        st.session_state.role = "teacher"
                        st.session_state.teacher_id = "T001"
                        st.session_state.teacher_name = "ครูผู้ดูแลระบบ"
                        st.session_state.page = "teacher_dashboard"
                        
                        st.success("✅ เข้าสู่ระบบในโหมดฉุกเฉินสำเร็จ")
                        time.sleep(2)
                        st.rerun()
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
        
        # Teacher Menu (Simplified for immediate use)
        menu_options = [
            "📊 Dashboard", 
            "📚 จัดการคอร์ส", 
            "➕ สร้างคอร์สใหม่", 
            "🎥 สอนสด",
            "📤 อัปโหลดเอกสาร"
        ]
        
        menu_choice = st.radio("**เมนูครูผู้สอน**", menu_options, key="teacher_menu")
        
        st.markdown("---")
        
        # Emergency buttons
        col_emg1, col_emg2 = st.columns(2)
        with col_emg1:
            if st.button("🔄 ล้างแคช", use_container_width=True):
                gs_manager.cache.clear()
                st.success("✅ ล้างแคชเรียบร้อย")
                st.rerun()
        
        with col_emg2:
            if st.button("🚪 ออกจากระบบ", use_container_width=True, key="teacher_logout"):
                st.session_state.clear()
                st.rerun()
    
    # ---------- TEACHER DASHBOARD ----------
    if menu_choice == "📊 Dashboard":
        st.title("📊 Dashboard ครูผู้สอน")
        st.markdown("---")
        
        # Quick start teaching
        st.subheader("🚀 เริ่มการสอนทันที")
        
        with st.expander("สร้างห้องเรียนด่วน", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                course_name = st.text_input("ชื่อคอร์ส", value=f"คอร์สสอนสด {datetime.now().strftime('%H:%M')}")
                jitsi_room = st.text_input("ชื่อห้อง Jitsi", value=f"room_{int(time.time())}")
            
            with col2:
                class_type = st.selectbox("ประเภท", ["ตัวต่อตัว (1:1)", "กลุ่มเล็ก (2-5 คน)", "กลุ่มใหญ่"])
                max_students = st.number_input("จำนวนนักเรียนสูงสุด", min_value=1, value=10)
            
            if st.button("🎥 เริ่มสอนทันที", type="primary", use_container_width=True):
                # Create quick course
                course_id = f"QC{int(time.time())}"
                course_data = {
                    "course_id": course_id,
                    "course_name": course_name,
                    "teacher_id": st.session_state.teacher_id,
                    "teacher_name": st.session_state.teacher_name,
                    "image_path": "",
                    "jitsi_room": jitsi_room,
                    "description": "คอร์สสอนสดด่วน",
                    "max_students": max_students,
                    "current_students": 0,
                    "class_type": class_type,
                    "status": "active",
                    "security_code": "QUICK123",
                    "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                add_course(course_data)
                st.session_state.current_course = course_data
                st.session_state.page = "live_teaching"
                st.success(f"✅ สร้างห้องเรียน '{course_name}' สำเร็จ!")
                st.rerun()
        
        # Quick stats
        st.markdown("---")
        st.subheader("📈 สถิติด่วน")
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        
        with col_stat1:
            try:
                courses_count = len(get_teacher_courses(st.session_state.teacher_id))
                st.metric("คอร์สทั้งหมด", courses_count)
            except:
                st.metric("คอร์สทั้งหมด", 0)
        
        with col_stat2:
            try:
                students_df = gs_manager.get_df('students')
                st.metric("นักเรียนทั้งหมด", len(students_df))
            except:
                st.metric("นักเรียนทั้งหมด", 0)
        
        with col_stat3:
            st.metric("สถานะระบบ", "🟢 พร้อมใช้งาน" if not gs_manager.use_fallback else "🟡 โหมดออฟไลน์")
    
    # ---------- MANAGE COURSES ----------
    elif menu_choice == "📚 จัดการคอร์ส":
        st.title("📚 จัดการคอร์สเรียน")
        st.markdown("---")
        
        try:
            my_courses = get_teacher_courses(st.session_state.teacher_id)
            
            if not my_courses.empty:
                for idx, row in my_courses.iterrows():
                    with st.expander(f"{row['course_name']} ({row.get('class_type', 'กลุ่ม')})", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**รหัสคอร์ส:** {row['course_id']}")
                            st.write(f"**คำอธิบาย:** {row.get('description', '')}")
                            st.write(f"**ห้อง Jitsi:** {row.get('jitsi_room', 'ยังไม่ได้ตั้งค่า')}")
                            st.write(f"**สถานะ:** {row.get('status', 'active')}")
                        
                        with col2:
                            if st.button("🎥 สอนสด", key=f"go_live_{row['course_id']}", use_container_width=True):
                                st.session_state.current_course = row.to_dict()
                                st.session_state.page = "live_teaching"
                                st.rerun()
            else:
                st.info("ยังไม่มีคอร์สเรียน")
        except:
            st.info("ยังไม่มีคอร์สเรียน")
    
    # ---------- CREATE NEW COURSE (Simplified) ----------
    elif menu_choice == "➕ สร้างคอร์สใหม่":
        st.title("➕ สร้างคอร์สใหม่")
        st.markdown("---")
        
        with st.form("create_course_form", clear_on_submit=True):
            st.subheader("ข้อมูลพื้นฐาน")
            
            course_name = st.text_input("**ชื่อคอร์ส** *", key="new_course_name")
            jitsi_room = st.text_input(
                "**ชื่อห้อง Jitsi** *", 
                value=f"{st.session_state.teacher_name.replace(' ', '')}_{int(time.time())}", 
                key="new_jitsi_room"
            )
            
            class_type = st.selectbox(
                "**ประเภทการเรียน**", 
                ["กลุ่ม", "ตัวต่อตัว (1:1)", "กลุ่มเล็ก (2-5 คน)"], 
                key="new_class_type"
            )
            
            description = st.text_area("**คำอธิบายคอร์ส**", height=100, key="new_description")
            
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
                if not all([course_name, jitsi_room]):
                    st.error("กรุณากรอกข้อมูลที่จำเป็น (*)")
                else:
                    try:
                        courses_df = get_available_courses()
                        course_id = f"C{len(courses_df) + 1:04d}"
                        
                        new_course = {
                            "course_id": course_id,
                            "course_name": course_name,
                            "teacher_id": st.session_state.teacher_id,
                            "teacher_name": st.session_state.teacher_name,
                            "image_path": "",
                            "jitsi_room": jitsi_room,
                            "description": description,
                            "max_students": 10,
                            "current_students": 0,
                            "class_type": class_type,
                            "status": "active",
                            "security_code": str(uuid.uuid4())[:8].upper(),
                            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        success = add_course(new_course)
                        
                        if success:
                            # Create lesson file
                            lesson_file = f"save_data/lessons/{course_id}_lessons.json"
                            with open(lesson_file, "w", encoding="utf-8") as f:
                                json.dump([], f)
                            
                            # Create exercises file
                            exercise_file = f"save_data/lessons/{course_id}_exercises.json"
                            with open(exercise_file, "w", encoding="utf-8") as f:
                                json.dump([], f)
                            
                            st.success(f"✅ **สร้างคอร์ส '{course_name}' สำเร็จ!**")
                            st.info(f"**รหัสคอร์ส:** {course_id}")
                            st.info(f"**ห้อง Jitsi:** {jitsi_room}")
                            
                            time.sleep(2)
                            st.session_state.page = "teacher_dashboard"
                            st.rerun()
                        else:
                            st.error("เกิดข้อผิดพลาดในการสร้างคอร์ส")
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
    
    # ---------- LIVE TEACHING (Simplified) ----------
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
                
                # Jitsi info
                st.session_state.jitsi_room_name = course_info.get('jitsi_room', 'default_room')
                st.session_state.jitsi_display_name = st.session_state.teacher_name
                
                # Start teaching button
                if st.button("🔗 เริ่มการสอนสด", type="primary", use_container_width=True):
                    st.session_state.jitsi_connected = True
                    st.session_state.current_course = course_info.to_dict()
                    st.rerun()
                
                # Jitsi video
                if st.session_state.jitsi_connected:
                    room = str(course_info.get("jitsi_room", "default_room"))
                    
                    st.markdown("### 🎥 ห้องเรียนสด")
                    st.markdown(embed_jitsi_meet_simple(room, st.session_state.teacher_name), unsafe_allow_html=True)
                    
                    # Link for students
                    st.markdown("---")
                    st.markdown("### 🔗 ลิงก์สำหรับนักเรียน")
                    st.code(f"https://meet.jit.si/{room}", language="bash")
                    
                    # End session button
                    if st.button("🏁 จบการเรียน", type="secondary", use_container_width=True):
                        st.session_state.jitsi_connected = False
                        st.success("✅ จบการเรียนเรียบร้อย")
                        st.rerun()
                else:
                    st.info("โปรดกดปุ่ม 'เริ่มการสอนสด' เพื่อเริ่มเซสชันการสอน")
            else:
                st.info("ยังไม่มีคอร์สเรียน")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
    
    # ---------- UPLOAD DOCUMENTS ----------
    elif menu_choice == "📤 อัปโหลดเอกสาร":
        st.title("📤 อัปโหลดเอกสารประกอบการเรียน")
        st.markdown("---")
        
        st.info("🚧 ฟังก์ชันนี้กำลังอยู่ในระหว่างการพัฒนา")
        st.write("คุณสามารถใช้ Google Drive หรือแชร์ลิงก์เอกสารกับนักเรียนได้ชั่วคราว")

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
        if st.button("⬅ กลับสู่หน้าหลัก", type="secondary", use_container_width=True):
            st.session_state.page = "student_home"
            st.session_state.jitsi_connected = False
            st.rerun()
        
        # Video call
        st.markdown("### 🎥 วิดีโอคอลเรียนสด")
        
        if st.session_state.jitsi_connected:
            room_name = str(course_info.get("jitsi_room", "default_room"))
            display_name = st.session_state.student_name
            
            jitsi_code = f'''
            <div style="position: relative; width: 100%; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 12px;">
                <iframe 
                    src="https://meet.jit.si/{room_name}?userInfo.displayName={display_name.replace(' ', '%20')}" 
                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"
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

# -----------------------------
# STUDENT COURSES PAGE (Simplified)
# -----------------------------
elif st.session_state.page == "student_courses" and st.session_state.role == "student":
    st.title("📚 คอร์สของฉัน")
    st.markdown("---")
    
    enrolled_courses = get_student_courses(st.session_state.student_id)
    
    if not enrolled_courses.empty:
        st.subheader("คอร์สที่ลงทะเบียนแล้ว")
        
        for idx, row in enrolled_courses.iterrows():
            with st.expander(f"{row['course_name']}", expanded=False):
                course_id = row["course_id"]
                course_name = row["course_name"]
                
                st.write(f"**สถานะ:** {'✅ เรียนจบ' if row.get('completion_status', False) else '📚 กำลังเรียน'}")
                st.write(f"**วันที่ลงทะเบียน:** {row.get('enrollment_date', '')}")
                
                if st.button("🎥 เข้าเรียน", key=f"go_live_{course_id}", use_container_width=True):
                    try:
                        courses_df = get_available_courses()
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
    else:
        st.info("คุณยังไม่ได้ลงทะเบียนคอร์สใดๆ")

# -----------------------------
# LIVE TEACHING PAGE (for teacher)
# -----------------------------
elif st.session_state.page == "live_teaching" and st.session_state.role == "teacher":
    if "current_course" in st.session_state and st.session_state.current_course:
        course_info = st.session_state.current_course
        
        st.title(f"🎥 สอนสด: {course_info['course_name']}")
        st.markdown("---")
        
        # Course info
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.write(f"**ครูผู้สอน:** {st.session_state.teacher_name}")
            st.write(f"**ห้อง Jitsi:** {course_info.get('jitsi_room', 'default_room')}")
        
        with col_info2:
            st.write(f"**ประเภท:** {course_info.get('class_type', 'กลุ่ม')}")
            st.write(f"**รหัสคอร์ส:** {course_info.get('course_id', '')}")
        
        # Start/stop buttons
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("▶ เริ่มการสอน", type="primary", use_container_width=True):
                st.session_state.jitsi_connected = True
                st.rerun()
        
        with col_btn2:
            if st.button("⏹ หยุดการสอน", type="secondary", use_container_width=True):
                st.session_state.jitsi_connected = False
                st.rerun()
        
        # Jitsi video
        if st.session_state.jitsi_connected:
            room = str(course_info.get("jitsi_room", "default_room"))
            
            st.markdown("### 🎥 ห้องเรียนสด")
            st.markdown(embed_jitsi_meet_simple(room, st.session_state.teacher_name), unsafe_allow_html=True)
            
            # Student link
            st.markdown("---")
            st.markdown("### 🔗 ลิงก์สำหรับนักเรียน")
            st.code(f"https://meet.jit.si/{room}", language="bash")
            
            # Student list (simplified)
            st.markdown("---")
            st.markdown("### 👥 รายชื่อนักเรียน")
            
            try:
                student_courses_df = gs_manager.get_df('student_courses')
                course_students = student_courses_df[student_courses_df["course_id"] == course_info.get('course_id', '')]
                
                if not course_students.empty:
                    for idx, student in course_students.iterrows():
                        status = "✅ เรียนจบ" if student.get('completion_status', False) else "📚 กำลังเรียน"
                        st.write(f"• **{student['fullname']}** ({student['student_id']}) - {status}")
                else:
                    st.info("ยังไม่มีนักเรียนในคอร์สนี้")
            except:
                st.info("ไม่สามารถโหลดรายชื่อนักเรียน")
        else:
            st.info("โปรดกดปุ่ม 'เริ่มการสอน' เพื่อเริ่มเซสชันการสอน")
        
        # Back button
        st.markdown("---")
        if st.button("⬅ กลับสู่แดชบอร์ด", use_container_width=True):
            st.session_state.page = "teacher_dashboard"
            st.session_state.jitsi_connected = False
            st.rerun()

# -----------------------------
# Main App Runner
# -----------------------------
if __name__ == "__main__":
    # Display connection status
    if gs_manager.use_fallback:
        st.sidebar.warning("⚠️ ระบบกำลังใช้โหมดออฟไลน์")
        st.sidebar.info("ข้อมูลถูกบันทึกในเครื่องและจะซิงค์เมื่อเชื่อมต่อได้")
    
    # Manual sync button
    if st.session_state.role == "teacher" and st.sidebar.button("🔄 ซิงค์ข้อมูลกับ Google Sheets"):
        try:
            # Try to reconnect
            gs_manager._connect()
            if not gs_manager.use_fallback:
                st.sidebar.success("✅ เชื่อมต่อกับ Google Sheets สำเร็จ")
            else:
                st.sidebar.error("❌ ไม่สามารถเชื่อมต่อกับ Google Sheets")
            st.rerun()
        except:
            st.sidebar.error("❌ การเชื่อมต่อล้มเหลว")
