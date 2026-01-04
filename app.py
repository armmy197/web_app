import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import os
import json
import time
import uuid
import base64
from PIL import Image
import io

# Firebase Imports
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter

# -----------------------------
# Firebase Initialization
# -----------------------------
def init_firebase():
    """Initialize Firebase with credentials from Streamlit secrets"""
    try:
        if not firebase_admin._apps:
            # Load configuration from secrets
            firebase_config = {
                "type": st.secrets.get("FIREBASE_TYPE", "service_account"),
                "project_id": st.secrets["FIREBASE_PROJECT_ID"],
                "private_key_id": st.secrets.get("FIREBASE_PRIVATE_KEY_ID", ""),
                "private_key": st.secrets["FIREBASE_PRIVATE_KEY"].replace('\\n', '\n'),
                "client_email": st.secrets["FIREBASE_CLIENT_EMAIL"],
                "client_id": st.secrets.get("FIREBASE_CLIENT_ID", ""),
                "auth_uri": st.secrets.get("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": st.secrets.get("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": st.secrets.get("FIREBASE_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": st.secrets.get("FIREBASE_CLIENT_X509_CERT_URL", ""),
                "universe_domain": st.secrets.get("FIREBASE_UNIVERSE_DOMAIN", "googleapis.com")
            }
            
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {
                'storageBucket': f"{st.secrets['FIREBASE_PROJECT_ID']}.appspot.com"
            })
        
        return firestore.client()
    except Exception as e:
        st.error(f"❌ Firebase initialization failed: {str(e)}")
        st.error("โปรดตรวจสอบ Secrets configuration")
        return None

# Initialize Firestore
try:
    db = init_firebase()
    if db:
        bucket = storage.bucket()
        st.sidebar.success("✅ Firebase Connected")
    else:
        st.error("❌ Could not initialize Firebase. Please check your secrets.")
        st.stop()
except Exception as e:
    st.error(f"❌ Firebase Error: {e}")
    st.stop()

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="ZL TA-Learning (ผู้ช่วยสอน-เรียนออนไลน์)",
    layout="wide",
    page_icon="🎓"
)

# -----------------------------
# CSS - ออกแบบใหม่ตามโทนสีที่กำหนด
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

/* Course Grid */
.course-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 25px;
    margin: 25px 0;
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

/* Jitsi Container - Mobile Responsive */
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

/* Fixed Jitsi Container - สำหรับหน้าทำแบบฝึกหัด */
.jitsi-container-fixed {{
    position: fixed;
    top: 80px;
    right: 20px;
    width: 400px;
    height: 300px;
    z-index: 999;
    border-radius: var(--border-radius);
    border: 3px solid var(--sub-title);
    background: #000;
    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
}}

.jitsi-iframe-fixed {{
    width: 100%;
    height: 100%;
    border: none;
    border-radius: var(--border-radius);
}}

/* สไตล์สำหรับหน้าเรียนสดนักเรียน - ปรับให้มีเฉพาะวิดีโอ */
.simple-video-container {{
    width: 100%;
    padding-bottom: 56.25%; /* 16:9 Aspect Ratio */
    position: relative;
    background: #000;
    border-radius: 12px;
    margin-bottom: 20px;
    border: 3px solid var(--sub-title);
}}

.simple-video-iframe {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    border: none;
    border-radius: 10px;
}}

/* Exercise Items */
.exercise-item {{
    background: white;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 15px;
    border-left: 5px solid var(--success-color);
    transition: var(--transition);
}}

.exercise-item:hover {{
    background: #F1F8E9;
}}

.exercise-question {{
    font-weight: 600;
    margin-bottom: 15px;
    color: var(--main-title);
    font-size: 1.1rem;
}}

.exercise-image {{
    width: 100%;
    max-width: 500px;
    border-radius: 8px;
    margin: 15px 0;
    border: 3px solid #B3E5FC;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}}

.exercise-answer {{
    background: #E8F5E9;
    padding: 15px;
    border-radius: 8px;
    margin-top: 15px;
    border: 2px solid #C8E6C9;
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

/* Teacher Video */
.teacher-video {{
    background: var(--main-title);
    border-radius: var(--border-radius);
    padding: 20px;
    color: white;
    text-align: center;
    border: 3px solid var(--sub-title);
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

/* Progress Bar */
.stProgress > div > div > div > div {{
    background: linear-gradient(90deg, var(--sub-title), #FFECB3);
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    background-color: var(--primary-color);
    padding: 5px;
    border-radius: 10px;
    border: 2px solid #B3E5FC;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 8px;
    padding: 10px 20px;
    transition: var(--transition);
}}

.stTabs [aria-selected="true"] {{
    background-color: var(--main-title);
    color: white;
}}

/* File Uploader */
.stFileUploader > div {{
    border: 2px dashed #BBDEFB;
    border-radius: var(--border-radius);
    padding: 20px;
}}

.stFileUploader > div:hover {{
    border-color: var(--main-title);
}}

/* Tables */
.stDataFrame {{
    border-radius: var(--border-radius);
    border: 2px solid #E3F2FD;
}}

/* Sidebar */
.sidebar .sidebar-content {{
    background: var(--primary-color);
    border-right: 3px solid #B3E5FC;
}}

/* Badges */
.success-badge {{
    background-color: #C8E6C9;
    color: var(--success-color);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 600;
    border: 1px solid #A5D6A7;
}}

.warning-badge {{
    background-color: var(--secondary-color);
    color: var(--warning-color);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 600;
    border: 1px solid #FFD54F;
}}

/* Exercise Page Layout */
.exercise-page-container {{
    margin-right: 430px;
    padding: 20px;
}}

@media (max-width: 768px) {{
    .exercise-page-container {{
        margin-right: 0;
        padding: 10px;
    }}
}}

/* Custom Scrollbar */
::-webkit-scrollbar {{
    width: 8px;
}}

::-webkit-scrollbar-track {{
    background: var(--primary-color);
    border-radius: 4px;
}}

::-webkit-scrollbar-thumb {{
    background: var(--main-title);
    border-radius: 4px;
}}

::-webkit-scrollbar-thumb:hover {{
    background: #3949AB;
}}

/* Form Group */
.form-group {{
    margin-bottom: 20px;
}}

.form-group label {{
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: var(--main-title);
}}

/* Alert Messages */
.alert-success {{
    background-color: #d4edda;
    border-color: #c3e6cb;
    color: #155724;
    padding: 12px;
    border-radius: 8px;
    margin: 10px 0;
}}

.alert-warning {{
    background-color: #fff3cd;
    border-color: #ffeaa7;
    color: #856404;
    padding: 12px;
    border-radius: 8px;
    margin: 10px 0;
}}

.alert-danger {{
    background-color: #f8d7da;
    border-color: #f5c6cb;
    color: #721c24;
    padding: 12px;
    border-radius: 8px;
    margin: 10px 0;
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

/* Empty State */
.empty-state {{
    text-align: center;
    padding: 40px 20px;
    color: #666;
}}

.empty-state img {{
    width: 100px;
    margin-bottom: 20px;
    opacity: 0.5;
}}

/* Mobile-specific Jitsi fixes */
.mobile-jitsi-notice {{
    background: var(--secondary-color);
    padding: 15px;
    border-radius: 10px;
    margin: 15px 0;
    text-align: center;
}}

.mobile-jitsi-notice ul {{
    text-align: left;
    display: inline-block;
}}

/* Jitsi Connection Status */
.jitsi-status {{
    background: var(--primary-color);
    padding: 10px;
    border-radius: 8px;
    margin: 10px 0;
    text-align: center;
    border: 2px solid #81D4FA;
}}

.jitsi-status.connected {{
    background: #E8F5E9;
    border-color: #A5D6A7;
}}

.jitsi-status.disconnected {{
    background: #FFEBEE;
    border-color: #EF9A9A;
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

# -----------------------------
# Firebase Helper Functions
# -----------------------------
def md5(text):
    """Create MD5 hash"""
    return hashlib.md5(text.encode()).hexdigest()

def upload_file_to_storage(file_bytes, destination_path, content_type=None):
    """Upload file to Firebase Storage"""
    try:
        blob = bucket.blob(destination_path)
        blob.upload_from_string(file_bytes, content_type=content_type)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        return None

def download_file_from_storage(storage_path, local_path):
    """Download file from Firebase Storage"""
    try:
        blob = bucket.blob(storage_path)
        blob.download_to_filename(local_path)
        return local_path
    except Exception as e:
        st.error(f"Error downloading file: {e}")
        return None

# -----------------------------
# Firestore CRUD Operations
# -----------------------------

def get_student(student_id):
    """Get student by ID"""
    try:
        doc_ref = db.collection('students').document(student_id.upper())
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        st.error(f"Error getting student: {e}")
        return None

def add_student(student_data):
    """Add new student"""
    try:
        doc_ref = db.collection('students').document(student_data['student_id'])
        doc_ref.set(student_data)
        return student_data['student_id']
    except Exception as e:
        st.error(f"Error adding student: {e}")
        return None

def get_all_students():
    """Get all students"""
    try:
        docs = db.collection('students').stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Error getting all students: {e}")
        return []

def get_course(course_id):
    """Get course by ID"""
    try:
        doc_ref = db.collection('courses').document(str(course_id))
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        st.error(f"Error getting course: {e}")
        return None

def get_courses_by_teacher(teacher_id):
    """Get courses by teacher"""
    try:
        query = db.collection('courses').where(filter=FieldFilter('teacher_id', '==', teacher_id))
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Error getting teacher courses: {e}")
        return []

def get_all_courses():
    """Get all courses"""
    try:
        docs = db.collection('courses').stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Error getting all courses: {e}")
        return []

def add_course(course_data):
    """Add new course"""
    try:
        doc_ref = db.collection('courses').document(course_data['course_id'])
        doc_ref.set(course_data)
        return course_data['course_id']
    except Exception as e:
        st.error(f"Error adding course: {e}")
        return None

def update_course(course_id, updates):
    """Update course data"""
    try:
        doc_ref = db.collection('courses').document(str(course_id))
        doc_ref.update(updates)
        return True
    except Exception as e:
        st.error(f"Error updating course: {e}")
        return False

def get_teacher_by_username(username):
    """Get teacher by username"""
    try:
        query = db.collection('teachers').where(filter=FieldFilter('username', '==', username))
        docs = query.stream()
        for doc in docs:
            return doc.to_dict()
        return None
    except Exception as e:
        st.error(f"Error getting teacher: {e}")
        return None

def add_teacher(teacher_data):
    """Add new teacher"""
    try:
        doc_ref = db.collection('teachers').document(teacher_data['teacher_id'])
        doc_ref.set(teacher_data)
        return teacher_data['teacher_id']
    except Exception as e:
        st.error(f"Error adding teacher: {e}")
        return None

def add_student_check(check_data):
    """Add student attendance check"""
    try:
        doc_ref = db.collection('student_checks').document(check_data['check_id'])
        doc_ref.set(check_data)
        return check_data['check_id']
    except Exception as e:
        st.error(f"Error adding student check: {e}")
        return None

def get_student_checks(student_id):
    """Get student attendance history"""
    try:
        query = db.collection('student_checks').where(filter=FieldFilter('student_id', '==', student_id))
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Error getting student checks: {e}")
        return []

def enroll_student(enrollment_data):
    """Enroll student in course"""
    try:
        enrollment_id = f"ENR{int(time.time())}"
        enrollment_data['enrollment_id'] = enrollment_id
        doc_ref = db.collection('enrollments').document(enrollment_id)
        doc_ref.set(enrollment_data)
        return enrollment_id
    except Exception as e:
        st.error(f"Error enrolling student: {e}")
        return None

def get_student_enrollments(student_id):
    """Get student's enrollments"""
    try:
        query = db.collection('enrollments').where(filter=FieldFilter('student_id', '==', student_id))
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Error getting enrollments: {e}")
        return []

def update_enrollment(enrollment_id, updates):
    """Update enrollment status"""
    try:
        doc_ref = db.collection('enrollments').document(enrollment_id)
        doc_ref.update(updates)
        return True
    except Exception as e:
        st.error(f"Error updating enrollment: {e}")
        return False

def get_lessons(course_id):
    """Get lessons for a course"""
    try:
        query = db.collection('lessons').where(filter=FieldFilter('course_id', '==', str(course_id)))
        docs = query.stream()
        lessons = []
        for doc in docs:
            lesson = doc.to_dict()
            lesson['id'] = doc.id
            lessons.append(lesson)
        
        # Sort by order if exists
        if lessons and 'order' in lessons[0]:
            lessons.sort(key=lambda x: x.get('order', 999))
        else:
            lessons.sort(key=lambda x: x.get('created_at', ''))
        
        return lessons
    except Exception as e:
        st.error(f"Error getting lessons: {e}")
        return []

def add_lesson(lesson_data):
    """Add new lesson"""
    try:
        doc_ref = db.collection('lessons').document()
        lesson_id = doc_ref.id
        lesson_data['id'] = lesson_id
        doc_ref.set(lesson_data)
        return lesson_id
    except Exception as e:
        st.error(f"Error adding lesson: {e}")
        return None

def update_lesson(lesson_id, updates):
    """Update lesson"""
    try:
        doc_ref = db.collection('lessons').document(lesson_id)
        doc_ref.update(updates)
        return True
    except Exception as e:
        st.error(f"Error updating lesson: {e}")
        return False

def get_exercises(course_id):
    """Get exercises for a course"""
    try:
        query = db.collection('exercises').where(filter=FieldFilter('course_id', '==', str(course_id)))
        docs = query.stream()
        exercises_by_lesson = {}
        
        for doc in docs:
            exercise = doc.to_dict()
            exercise['id'] = doc.id
            lesson_index = exercise.get('lesson_index', 0)
            
            if lesson_index not in exercises_by_lesson:
                exercises_by_lesson[lesson_index] = {
                    "lesson_index": lesson_index,
                    "exercises": []
                }
            
            exercises_by_lesson[lesson_index]["exercises"].append(exercise)
        
        # Convert to list and sort by lesson_index
        result = []
        for lesson_index in sorted(exercises_by_lesson.keys()):
            # Sort exercises within each lesson
            exercises_by_lesson[lesson_index]["exercises"].sort(
                key=lambda x: x.get('exercise_index', 999)
            )
            result.append(exercises_by_lesson[lesson_index])
        
        return result
    except Exception as e:
        st.error(f"Error getting exercises: {e}")
        return []

def add_exercise(exercise_data):
    """Add new exercise"""
    try:
        doc_ref = db.collection('exercises').document()
        exercise_id = doc_ref.id
        exercise_data['id'] = exercise_id
        doc_ref.set(exercise_data)
        return exercise_id
    except Exception as e:
        st.error(f"Error adding exercise: {e}")
        return None

def save_quiz_result_fb(quiz_data):
    """Save quiz result to Firebase"""
    try:
        quiz_id = f"{quiz_data['student_id']}_{quiz_data['course_id']}_{quiz_data['lesson_index']}_{quiz_data['exercise_index']}"
        quiz_data['quiz_id'] = quiz_id
        doc_ref = db.collection('quiz_results').document(quiz_id)
        doc_ref.set(quiz_data)
        return quiz_id
    except Exception as e:
        st.error(f"Error saving quiz result: {e}")
        return None

def get_student_quiz_results(student_id, course_id):
    """Get quiz results for a student in a course"""
    try:
        query = db.collection('quiz_results').where(filter=FieldFilter('student_id', '==', student_id)).where(filter=FieldFilter('course_id', '==', str(course_id)))
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Error getting quiz results: {e}")
        return []

def add_document(document_data):
    """Add document"""
    try:
        doc_ref = db.collection('documents').document()
        document_id = doc_ref.id
        document_data['id'] = document_id
        doc_ref.set(document_data)
        return document_id
    except Exception as e:
        st.error(f"Error adding document: {e}")
        return None

def get_course_documents_fb(course_id):
    """Get documents for a course"""
    try:
        query = db.collection('documents').where(filter=FieldFilter('course_id', '==', str(course_id)))
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Error getting documents: {e}")
        return []

def add_certificate(certificate_data):
    """Add certificate"""
    try:
        doc_ref = db.collection('certificates').document()
        cert_id = doc_ref.id
        certificate_data['id'] = cert_id
        doc_ref.set(certificate_data)
        return cert_id
    except Exception as e:
        st.error(f"Error adding certificate: {e}")
        return None

def get_student_certificates(student_id, course_id=None):
    """Get certificates for a student"""
    try:
        if course_id:
            query = db.collection('certificates').where(filter=FieldFilter('student_id', '==', student_id)).where(filter=FieldFilter('course_id', '==', str(course_id)))
        else:
            query = db.collection('certificates').where(filter=FieldFilter('student_id', '==', student_id))
        
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Error getting certificates: {e}")
        return []

# -----------------------------
# Application Helper Functions (Adapted for Firebase)
# -----------------------------
def check_student_id(student_id):
    """ตรวจสอบสิทธิ์นักเรียนด้วย ID"""
    try:
        student = get_student(student_id.upper())
        
        if student:
            # บันทึกการตรวจสอบสิทธิ์
            attendance_records = get_student_checks(student_id.upper())
            attendance_count = len(attendance_records)
            
            check_data = {
                "check_id": f"CHK{int(time.time())}",
                "student_id": student_id.upper(),
                "fullname": student["fullname"],
                "check_date": datetime.now().strftime("%Y-%m-%d"),
                "check_time": datetime.now().strftime("%H:%M:%S"),
                "attendance_count": attendance_count + 1,
                "status": "verified"
            }
            
            add_student_check(check_data)
            
            return True, student["fullname"], student.get("email", "")
        else:
            return False, None, None
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการตรวจสอบรหัสนักเรียน: {e}")
        return False, None, None

def teacher_login(username, password):
    """ตรวจสอบการเข้าสู่ระบบครูผู้สอน"""
    try:
        password_hash = md5(password)
        teacher = get_teacher_by_username(username)
        
        if teacher and teacher.get('password_hash') == password_hash:
            return True, "เข้าสู่ระบบสำเร็จ!", teacher["teacher_id"], teacher["fullname"]
        else:
            return False, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", None, None
    except Exception as e:
        return False, f"เกิดข้อผิดพลาด: {e}", None, None

def get_student_courses_fb(student_id):
    """ดึงคอร์สที่นักเรียนลงทะเบียน"""
    try:
        enrollments = get_student_enrollments(student_id)
        
        # Get course details for each enrollment
        courses = []
        for enrollment in enrollments:
            course = get_course(enrollment['course_id'])
            if course:
                course.update(enrollment)
                courses.append(course)
        
        return courses
    except Exception as e:
        st.error(f"Error getting student courses: {e}")
        return []

def enroll_student_in_course_fb(student_id, student_name, course_id, course_name):
    """ลงทะเบียนนักเรียนในคอร์ส"""
    try:
        # Check if already enrolled
        enrollments = get_student_enrollments(student_id)
        already_enrolled = any(
            e['course_id'] == course_id for e in enrollments
        )
        
        if not already_enrolled:
            enrollment_data = {
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
            
            enroll_student(enrollment_data)
            return True
        return False
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการลงทะเบียน: {e}")
        return False

def mark_course_completed_fb(student_id, course_id):
    """บันทึกสถานะเรียนจบคอร์ส"""
    try:
        enrollments = get_student_enrollments(student_id)
        for enrollment in enrollments:
            if enrollment['course_id'] == course_id:
                enrollment_id = enrollment.get('enrollment_id', enrollment.get('id'))
                if enrollment_id:
                    update_enrollment(enrollment_id, {
                        "completion_status": True,
                        "completion_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    return True
        return False
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
        return False

def get_course_lessons_fb(course_id):
    """ดึงบทเรียนของคอร์ส"""
    return get_lessons(course_id)

def get_course_exercises_fb(course_id):
    """ดึงแบบฝึกหัดของคอร์ส"""
    return get_exercises(course_id)

def save_quiz_result_fb_wrapper(student_id, course_id, lesson_index, exercise_index, answer, is_correct):
    """บันทึกผลแบบฝึกหัด"""
    try:
        quiz_data = {
            "student_id": student_id,
            "course_id": str(course_id),
            "lesson_index": lesson_index,
            "exercise_index": exercise_index,
            "answer": answer,
            "is_correct": is_correct,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        save_quiz_result_fb(quiz_data)
        return True
    except Exception as e:
        st.error(f"Error saving quiz result: {e}")
        return False

def save_lesson_fb(course_id, lesson_data):
    """บันทึกบทเรียน"""
    try:
        lesson_data['course_id'] = str(course_id)
        lesson_data['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lesson_data['order'] = len(get_lessons(course_id)) + 1
        
        add_lesson(lesson_data)
        return True
    except Exception as e:
        st.error(f"Error saving lesson: {e}")
        return False

def save_exercise_fb(course_id, exercise_data):
    """บันทึกแบบฝึกหัด"""
    try:
        # Handle the new exercise format
        lesson_index = exercise_data.get("lesson_index", 0)
        exercises_list = exercise_data.get("exercises", [])
        
        if exercises_list:
            for i, exercise in enumerate(exercises_list):
                exercise_data_full = {
                    "course_id": str(course_id),
                    "lesson_index": lesson_index,
                    "exercise_index": i,
                    "question": exercise.get("question", ""),
                    "answer": exercise.get("answer", ""),
                    "image_path": exercise.get("image_path", ""),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                add_exercise(exercise_data_full)
        
        return True
    except Exception as e:
        st.error(f"Error saving exercise: {e}")
        return False

def save_document_fb(course_id, file, filename):
    """บันทึกเอกสารประกอบ"""
    try:
        # Upload to Firebase Storage
        file_bytes = file.getvalue()
        storage_path = f"documents/{course_id}/{filename}"
        file_url = upload_file_to_storage(file_bytes, storage_path)
        
        if not file_url:
            return False, "Upload failed"
        
        # Save metadata to Firestore
        document_data = {
            "course_id": str(course_id),
            "filename": filename,
            "storage_path": storage_path,
            "url": file_url,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "size": len(file_bytes)
        }
        
        add_document(document_data)
        return True, file_url
    except Exception as e:
        return False, str(e)

def get_course_documents_fb_wrapper(course_id):
    """ดึงรายการเอกสารในคอร์ส"""
    documents = get_course_documents_fb(course_id)
    result = []
    for doc in documents:
        result.append({
            "name": doc.get("filename", ""),
            "path": doc.get("url", ""),
            "size": doc.get("size", 0)
        })
    return result

def create_certificate_fb(student_id, student_name, course_id, course_name, teacher_name):
    """สร้างใบรับรองการเรียนจบ"""
    try:
        cert_content = f"""
        ====================================================
                      ใบรับรองการเรียนจบ
        ====================================================

        ชื่อนักเรียน: {student_name}
        รหัสนักเรียน: {student_id}
        หลักสูตร: {course_name}
        ครูผู้สอน: {teacher_name}
        วันที่เรียนจบ: {datetime.now().strftime('%Y-%m-%d')}

        ====================================================
                    สถาบัน ZL TA-Learning
        ====================================================
        """
        
        # Upload certificate to Firebase Storage
        cert_filename = f"certificates/{student_id}_{course_id}_certificate.txt"
        cert_url = upload_file_to_storage(cert_content.encode('utf-8'), cert_filename, 'text/plain')
        
        if not cert_url:
            return False, "Upload failed"
        
        # Save certificate record
        certificate_data = {
            "student_id": student_id,
            "student_name": student_name,
            "course_id": str(course_id),
            "course_name": course_name,
            "teacher_name": teacher_name,
            "certificate_url": cert_url,
            "issued_date": datetime.now().strftime("%Y-%m-%d"),
            "certificate_id": f"CERT{int(time.time())}"
        }
        
        add_certificate(certificate_data)
        return True, cert_url
    except Exception as e:
        return False, str(e)

def get_certificate_file_fb(student_id, course_id):
    """ค้นหาไฟล์ใบรับรอง"""
    try:
        certificates = get_student_certificates(student_id, course_id)
        if certificates:
            return certificates[0].get('certificate_url')
        return None
    except:
        return None

def save_uploaded_certificate_fb(student_id, course_id, file, filename):
    """บันทึกไฟล์ใบรับรองที่อัปโหลด"""
    try:
        # Upload to Firebase Storage
        file_bytes = file.getvalue()
        storage_path = f"uploaded_certificates/{student_id}_{course_id}_{filename}"
        file_url = upload_file_to_storage(file_bytes, storage_path)
        
        if not file_url:
            return False, "Upload failed"
        
        # Save certificate record
        certificate_data = {
            "student_id": student_id,
            "course_id": str(course_id),
            "certificate_url": file_url,
            "filename": filename,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "certificate_id": f"UPLOAD{int(time.time())}"
        }
        
        add_certificate(certificate_data)
        return True, file_url
    except Exception as e:
        return False, str(e)

def get_available_courses_fb():
    """ดึงคอร์สทั้งหมดที่เปิดสอน"""
    return get_all_courses()

def check_answer(student_answer, correct_answer):
    """ตรวจคำตอบ (case insensitive และลบช่องว่าง)"""
    if not student_answer or not correct_answer:
        return False
    
    # ลบช่องว่างที่เกินและแปลงเป็นตัวพิมพ์เล็ก
    student_clean = ' '.join(student_answer.strip().split()).lower()
    correct_clean = ' '.join(correct_answer.strip().split()).lower()
    
    return student_clean == correct_clean

def save_exercise_image_fb(course_id, exercise_index, image_file):
    """บันทึกรูปภาพของแบบฝึกหัด"""
    try:
        # Upload to Firebase Storage
        file_bytes = image_file.getvalue()
        storage_path = f"exercise_images/{course_id}/exercise_{exercise_index}.{image_file.name.split('.')[-1]}"
        file_url = upload_file_to_storage(file_bytes, storage_path, 'image/jpeg')
        
        return True, file_url
    except Exception as e:
        return False, str(e)

def get_teacher_courses_fb(teacher_id):
    """ดึงคอร์สของครูผู้สอน"""
    return get_courses_by_teacher(teacher_id)

def embed_jitsi_meet_simple(room_name, display_name):
    """สร้าง Jitsi Meet embed code แบบง่ายๆ สำหรับนักเรียน"""
    room_name_clean = str(room_name).replace(" ", "-").replace("/", "-").replace("\\", "-")
    display_name_clean = str(display_name).replace(" ", "%20")
    
    jitsi_code = f'''
    <div class="simple-video-container">
        <iframe 
            src="https://meet.jit.si/{room_name_clean}?userInfo.displayName={display_name_clean}" 
            class="simple-video-iframe"
            allow="camera; microphone; fullscreen; display-capture; autoplay"
            allowfullscreen
            title="Jitsi Meet"
            loading="lazy">
        </iframe>
    </div>
    '''
    return jitsi_code

def embed_jitsi_meet(room_name, display_name, fixed=False):
    """สร้าง Jitsi Meet embed code ที่รองรับมือถือ"""
    room_name_clean = str(room_name).replace(" ", "-").replace("/", "-").replace("\\", "-")
    display_name_clean = str(display_name).replace(" ", "%20")
    
    if fixed:
        jitsi_code = f'''
        <div class="jitsi-container-fixed">
            <iframe 
                src="https://meet.jit.si/{room_name_clean}?userInfo.displayName={display_name_clean}" 
                class="jitsi-iframe-fixed"
                allow="camera; microphone; fullscreen; display-capture; autoplay"
                allowfullscreen
                title="Jitsi Meet">
            </iframe>
        </div>
        '''
    else:
        jitsi_code = f'''
        <div class="jitsi-container">
            <iframe 
                src="https://meet.jit.si/{room_name_clean}?userInfo.displayName={display_name_clean}" 
                class="jitsi-iframe"
                allow="camera; microphone; fullscreen; display-capture; autoplay"
                allowfullscreen
                title="Jitsi Meet"
                loading="lazy">
            </iframe>
        </div>
        
        <div class="jitsi-status {'connected' if st.session_state.jitsi_connected else 'disconnected'}">
            {'✅ Connected to Jitsi Meet' if st.session_state.jitsi_connected else '⚠️ Loading Jitsi Meet...'}
        </div>
        '''
    return jitsi_code

# -----------------------------
# Initialize Sample Data
# -----------------------------
def init_sample_data():
    """Initialize sample data if needed"""
    try:
        # Check if sample teacher exists
        sample_teacher = get_teacher_by_username("admin")
        if not sample_teacher:
            teacher_data = {
                "teacher_id": "TEA001",
                "username": "admin",
                "password_hash": md5("admin123"),
                "fullname": "ครูผู้ดูแลระบบ",
                "email": "admin@example.com",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "role": "admin"
            }
            add_teacher(teacher_data)
            st.sidebar.success("✅ สร้างข้อมูลครูผู้สอนตัวอย่างแล้ว")
        
        # Check if sample students exist
        sample_students = [
            {
                "student_id": "ZLS101",
                "fullname": "สมชาย ใจดี",
                "email": "somchai@example.com",
                "phone": "0812345678",
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "active"
            },
            {
                "student_id": "ZLS102",
                "fullname": "สมหญิง เก่งเรียน",
                "email": "somying@example.com",
                "phone": "0823456789",
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "active"
            },
            {
                "student_id": "ZLS103",
                "fullname": "นักศึกษา ตัวอย่าง",
                "email": "student@example.com",
                "phone": "0834567890",
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "active"
            }
        ]
        
        for student in sample_students:
            existing = get_student(student['student_id'])
            if not existing:
                add_student(student)
        
        return True
    except Exception as e:
        st.error(f"Error initializing sample data: {e}")
        return False

# Initialize sample data on first run
if "sample_data_initialized" not in st.session_state:
    init_sample_data()
    st.session_state.sample_data_initialized = True

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
            student_checks = get_student_checks(st.session_state.student_id)
            attendance_count = len(student_checks) if student_checks else 0
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
            courses = get_available_courses_fb()
            
            if courses:
                # Create course grid
                cols = st.columns(3)
                for idx, course in enumerate(courses):
                    if idx < 6:  # Show max 6 courses
                        with cols[idx % 3]:
                            st.markdown('<div class="course-card">', unsafe_allow_html=True)
                            
                            # Display course image if exists
                            image_path = course.get('image_path', '')
                            if isinstance(image_path, str) and image_path != 'nan' and image_path.startswith('http'):
                                st.image(image_path, use_container_width=True)
                            else:
                                # Placeholder image
                                st.markdown(
                                    '<div style="background: linear-gradient(135deg, #E6F7FF, #B3E5FC); height: 150px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #1A237E; font-weight: bold;">ภาพคอร์สเรียน</div>',
                                    unsafe_allow_html=True
                                )
                            
                            course_name = str(course.get("course_name", "ไม่มีชื่อ"))
                            teacher_name = str(course.get("teacher_name", "ครูผู้สอน"))
                            description = str(course.get("description", "ไม่มีคำอธิบาย"))
                            class_type = str(course.get("class_type", "กลุ่ม"))
                            course_id = str(course.get("course_id", ""))
                            
                            st.markdown(f'<h4>{course_name}</h4>', unsafe_allow_html=True)
                            st.write(f"👨‍🏫 **ครูผู้สอน:** {teacher_name}")
                            st.write(f"📖 **คำอธิบาย:** {description[:80]}...")
                            st.write(f"👥 **ประเภท:** {class_type}")
                            
                            # Check if already enrolled
                            enrolled_courses = get_student_courses_fb(st.session_state.student_id)
                            is_enrolled = False
                            
                            if enrolled_courses and course_id and course_id != 'nan':
                                is_enrolled = any(c['course_id'] == course_id for c in enrolled_courses)
                            
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if not is_enrolled and course_id and course_id != 'nan':
                                    if st.button("📝 ลงทะเบียน", key=f"enroll_{course_id}_{idx}", use_container_width=True):
                                        success = enroll_student_in_course_fb(
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
                                            course_data = {
                                                "course_id": course_id,
                                                "course_name": course_name,
                                                "teacher_id": course.get('teacher_id', ''),
                                                "teacher_name": teacher_name,
                                                "jitsi_room": course.get('jitsi_room', 'default_room'),
                                                "description": description,
                                                "class_type": class_type
                                            }
                                            st.session_state.current_course = course_data
                                            st.session_state.page = "live_student_session"
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"เกิดข้อผิดพลาด: {e}")
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                # Show more courses button if there are more
                if len(courses) > 6:
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
    
    # ---------- STUDENT COURSES PAGE ----------
    elif menu_choice == "📚 คอร์สของฉัน":
        st.title("📚 คอร์สของฉัน")
        st.markdown("---")
        
        enrolled_courses = get_student_courses_fb(st.session_state.student_id)
        
        if enrolled_courses:
            st.subheader("คอร์สที่ลงทะเบียนแล้ว")
            
            cols = st.columns(3)
            for idx, course in enumerate(enrolled_courses):
                with cols[idx % 3]:
                    st.markdown('<div class="course-card">', unsafe_allow_html=True)
                    
                    course_id = course["course_id"]
                    course_name = course["course_name"]
                    
                    # Try to get course details
                    try:
                        course_details = get_course(course_id)
                        
                        if course_details:
                            image_path = course_details.get('image_path', '')
                            
                            if image_path and image_path.startswith('http'):
                                st.image(image_path, use_container_width=True)
                    except:
                        pass
                    
                    st.markdown(f'<h4>{course_name}</h4>', unsafe_allow_html=True)
                    st.write(f"**สถานะ:** {'✅ เรียนจบ' if course.get('completion_status', False) else '📚 กำลังเรียน'}")
                    st.write(f"**วันที่ลงทะเบียน:** {course.get('enrollment_date', '')}")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("🎥 เข้าเรียน", key=f"go_live_{course_id}", use_container_width=True):
                            try:
                                course_info = get_course(course_id)
                                if course_info:
                                    course_data = {
                                        "course_id": course_id,
                                        "course_name": course_info.get('course_name', ''),
                                        "teacher_id": course_info.get('teacher_id', ''),
                                        "teacher_name": course_info.get('teacher_name', 'ครูผู้สอน'),
                                        "jitsi_room": course_info.get('jitsi_room', 'default_room'),
                                        "description": course_info.get('description', ''),
                                        "class_type": course_info.get('class_type', 'กลุ่ม')
                                    }
                                    st.session_state.current_course = course_data
                                    st.session_state.page = "live_student_session"
                                    st.rerun()
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาด: {e}")
                    
                    with col_btn2:
                        if course.get('completion_status', False):
                            if st.button("📜 ใบรับรอง", key=f"cert_{course_id}", use_container_width=True):
                                cert_url = get_certificate_file_fb(st.session_state.student_id, course_id)
                                if cert_url:
                                    # For now, just show the URL
                                    st.info(f"ใบรับรอง URL: {cert_url}")
                                    # In a real app, you would create a download button
                                else:
                                    st.info("ยังไม่มีใบรับรองสำหรับคอร์สนี้")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("คุณยังไม่ได้ลงทะเบียนคอร์สใดๆ")
            
            # Show available courses
            st.subheader("คอร์สเรียนที่เปิดสอน")
            try:
                courses = get_available_courses_fb()
                if courses:
                    for course in courses:
                        with st.expander(f"{course['course_name']} - {course.get('teacher_name', 'ครูผู้สอน')}"):
                            st.write(f"**คำอธิบาย:** {course.get('description', '')}")
                            st.write(f"**ประเภท:** {course.get('class_type', 'กลุ่ม')}")
                            
                            if st.button("📝 ลงทะเบียน", key=f"enroll_avail_{course['course_id']}"):
                                success = enroll_student_in_course_fb(
                                    st.session_state.student_id,
                                    st.session_state.student_name,
                                    course['course_id'],
                                    course['course_name']
                                )
                                if success:
                                    st.success(f"✅ ลงทะเบียนคอร์ส {course['course_name']} สำเร็จ!")
                                    st.rerun()
                else:
                    st.info("ยังไม่มีคอร์สเรียนที่เปิดสอน")
            except:
                st.info("ยังไม่มีคอร์สเรียนที่เปิดสอน")
    
    # ---------- STUDENT DOCUMENTS PAGE ----------
    elif menu_choice == "📄 ดาวน์โหลดเอกสาร":
        st.title("📄 ดาวน์โหลดเอกสารประกอบการเรียน")
        st.markdown("---")
        
        enrolled_courses = get_student_courses_fb(st.session_state.student_id)
        
        if enrolled_courses:
            # Filter only completed courses
            completed_courses = [c for c in enrolled_courses if c.get("completion_status") == True]
            
            if completed_courses:
                selected_course = st.selectbox(
                    "**เลือกคอร์ส**",
                    [c['course_name'] for c in completed_courses],
                    key="student_doc_course"
                )
                
                course_id = next((c['course_id'] for c in completed_courses if c['course_name'] == selected_course), None)
                
                if course_id:
                    # Get documents for this course
                    documents = get_course_documents_fb_wrapper(course_id)
                    
                    if documents:
                        st.subheader(f"เอกสารสำหรับคอร์ส: {selected_course}")
                        for doc in documents:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"📄 {doc['name']}")
                                st.caption(f"ขนาด: {doc['size']:,} bytes")
                            with col2:
                                # Since we have URLs, we can use markdown to create download links
                                st.markdown(f'<a href="{doc["path"]}" download="{doc["name"]}" style="text-decoration: none;"><button style="background: linear-gradient(135deg, #1A237E, #3949AB); color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer;">📥 ดาวน์โหลด</button></a>', unsafe_allow_html=True)
                    else:
                        st.info("ยังไม่มีเอกสารสำหรับคอร์สนี้")
            else:
                st.info("คุณยังไม่จบคอร์สใดๆ จึงไม่สามารถดาวน์โหลดเอกสารได้")
        else:
            st.info("คุณยังไม่ได้ลงทะเบียนคอร์สใดๆ")

# -----------------------------
# LIVE STUDENT SESSION PAGE (70/30 Layout)
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
            if st.button("📝 ไปทำแบบฝึกหัด", type="primary", use_container_width=True):
                st.session_state.exercise_page_active = True
                st.session_state.page = "student_exercise_page"
                st.rerun()
        with col_btn2:
            if st.button("⬅ กลับสู่หน้าหลัก", type="secondary", use_container_width=True):
                st.session_state.page = "student_home"
                st.session_state.jitsi_connected = False
                st.rerun()
        
        # --------------------------
        # SPLIT SCREEN LAYOUT (75/25)
        # --------------------------
        col_video, col_lesson = st.columns([75, 25])
        
        # LEFT SIDE: VIDEO CALL (75%)
        with col_video:
            st.markdown("### 🎥 วิดีโอคอลเรียนสด")
            
            if st.session_state.jitsi_connected:
                # Jitsi Meet Embed
                room_name = str(course_info.get("jitsi_room", "default_room"))
                display_name = st.session_state.student_name
                
                # สร้าง Jitsi iframe โดยตรง (ไม่มีกรอบดำ)
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
        
        # RIGHT SIDE: LESSONS (25%) - แบบ collapsible
        with col_lesson:
            st.markdown("### 📖 บทเรียน")
            
            # ปุ่มสำหรับแสดง/ซ่อนบทเรียน
            if st.button("📚 แสดง/ซ่อน บทเรียน", use_container_width=True):
                st.session_state.show_lessons = not st.session_state.get('show_lessons', True)
                st.rerun()
            
            # กำหนดค่าเริ่มต้น
            if 'show_lessons' not in st.session_state:
                st.session_state.show_lessons = True
            
            course_id = course_info.get("course_id", "")
            
            if course_id and st.session_state.show_lessons:
                # Load lessons
                lessons = get_course_lessons_fb(course_id)
                
                if lessons:
                    # Lesson selection
                    lesson_options = [f"บทที่ {i+1}: {l.get('title', 'ไม่มีชื่อ')}" for i, l in enumerate(lessons)]
                    selected_lesson = st.selectbox("เลือกบทเรียน", lesson_options, key="select_lesson_live")
                    
                    if selected_lesson:
                        lesson_index = int(selected_lesson.split(":")[0].replace("บทที่ ", "")) - 1
                        
                        if 0 <= lesson_index < len(lessons):
                            lesson = lessons[lesson_index]
                            
                            # Display lesson content
                            st.markdown("#### เนื้อหาบทเรียน")
                            content_preview = lesson.get('content', 'ยังไม่มีเนื้อหา')[:200]
                            st.write(f"{content_preview}..." if len(content_preview) >= 200 else content_preview)
                            
                            # File download
                            if lesson.get('file_url'):
                                file_url = lesson.get('file_url')
                                if file_url and isinstance(file_url, str) and file_url.strip():
                                    st.markdown(f'<a href="{file_url}" download style="text-decoration: none;"><button style="background: linear-gradient(135deg, #1A237E, #3949AB); color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; width: 100%;">📥 ดาวน์โหลด</button></a>', unsafe_allow_html=True)
                else:
                    st.info("ยังไม่มีบทเรียนในคอร์สนี้")
    else:
        st.session_state.page = "student_home"
        st.rerun()

# -----------------------------
# STUDENT EXERCISE PAGE (with fixed Jitsi)
# -----------------------------
elif st.session_state.page == "student_exercise_page" and st.session_state.role == "student":
    if "current_course" in st.session_state and st.session_state.current_course:
        course_info = st.session_state.current_course
        course_id = course_info.get("course_id", "")
        
        # Display fixed Jitsi if connected
        if st.session_state.jitsi_connected and st.session_state.jitsi_room_name:
            room_name = str(st.session_state.jitsi_room_name)
            display_name = st.session_state.jitsi_display_name
            
            jitsi_code = f'''
            <div style="position: fixed; top: 80px; right: 20px; width: 400px; height: 300px; z-index: 999; border-radius: 12px; border: 3px solid #FFD700; background: #000; box-shadow: 0 8px 25px rgba(0,0,0,0.3);">
                <iframe 
                    src="https://meet.jit.si/{room_name}?userInfo.displayName={display_name.replace(' ', '%20')}" 
                    style="width: 100%; height: 100%; border: none; border-radius: 12px;"
                    allow="camera; microphone; fullscreen; display-capture; autoplay"
                    allowfullscreen
                    title="Jitsi Meet">
                </iframe>
            </div>
            '''
            st.markdown(jitsi_code, unsafe_allow_html=True)
        
        # Main content with margin for fixed video
        st.markdown('<div class="exercise-page-container">', unsafe_allow_html=True)
        
        st.title(f"📝 แบบฝึกหัด: {course_info['course_name']}")
        st.markdown("---")
        
        # Back button - เพิ่มปุ่มกลับไปหน้าวิดีโอ
        col_back, col_live = st.columns([1, 1])
        with col_back:
            if st.button("⬅ กลับไปเรียนสด", use_container_width=True):
                st.session_state.page = "live_student_session"
                st.rerun()
        with col_live:
            if st.button("🎥 กลับไปหน้าวิดีโอ", use_container_width=True):
                st.session_state.exercise_page_active = False
                st.session_state.page = "live_student_session"
                st.rerun()
        
        # Load exercises
        exercises_data = get_course_exercises_fb(course_id)
        
        if exercises_data:
            # Initialize session state for exercises
            if course_id not in st.session_state.completed_exercises:
                st.session_state.completed_exercises[course_id] = {}
            
            if course_id not in st.session_state.exercise_attempts:
                st.session_state.exercise_attempts[course_id] = {}
            
            if 'current_exercise' not in st.session_state:
                st.session_state.current_exercise = {'lesson': 0, 'exercise': 0}
            
            # Navigation
            total_lessons = len(exercises_data)
            current_lesson = st.session_state.current_exercise['lesson']
            current_exercise = st.session_state.current_exercise['exercise']
            
            # Get current exercise
            if current_lesson < len(exercises_data):
                lesson_exercises = exercises_data[current_lesson]
                exercises = lesson_exercises.get("exercises", [])
                
                if current_exercise < len(exercises):
                    exercise = exercises[current_exercise]
                    exercise_key = f"{course_id}_{current_lesson}_{current_exercise}"
                    
                    # Exercise Progress
                    total_exercises = sum(len(le.get("exercises", [])) for le in exercises_data)
                    completed_count = sum(1 for key in st.session_state.completed_exercises.get(course_id, {}).values() if key)
                    
                    if total_exercises > 0:
                        st.write(f"**ความคืบหน้า:** {completed_count}/{total_exercises} ข้อ")
                        st.progress(completed_count / total_exercises)
                    
                    # Display exercise
                    st.markdown(f"### 📘 บทที่ {current_lesson + 1} - แบบฝึกหัดที่ {current_exercise + 1}")
                    
                    st.markdown(f'<div class="exercise-question">❓ {exercise.get("question", "ไม่มีคำถาม")}</div>', unsafe_allow_html=True)
                    
                    # Display image if exists
                    if exercise.get("image_path") and exercise["image_path"].startswith('http'):
                        st.image(exercise["image_path"], use_container_width=True, caption="รูปภาพคำถาม")
                    
                    is_completed = st.session_state.completed_exercises[course_id].get(exercise_key, False)
                    
                    if not is_completed:
                        # Get attempt count
                        attempt_count = st.session_state.exercise_attempts[course_id].get(exercise_key, 0)
                        
                        # แสดงจำนวนครั้งที่ตอบผิด
                        if attempt_count > 0:
                            if attempt_count == 1:
                                st.warning(f"⚠️ คุณตอบผิด {attempt_count} ครั้งแล้ว กรุณาตอบใหม่อีก 1 ครั้ง")
                            elif attempt_count == 2:
                                st.error(f"❌ คุณตอบผิด {attempt_count} ครั้งแล้ว")
                        
                        # Answer input
                        answer_key = f"ans_exercise_{current_lesson}_{current_exercise}"
                        user_answer = st.text_area("**คำตอบของคุณ:**", key=answer_key, height=100)
                        
                        col_submit = st.columns(1)[0]  # มีแค่ปุ่มส่งคำตอบปุ่มเดียว
                        
                        with col_submit:
                            if st.button("📤 ส่งคำตอบ", key=f"sub_exercise_{current_lesson}_{current_exercise}", use_container_width=True):
                                if user_answer.strip():
                                    # Check answer
                                    is_correct = check_answer(user_answer, exercise.get("answer", ""))
                                    
                                    if is_correct:
                                        # Save result
                                        save_quiz_result_fb_wrapper(
                                            st.session_state.student_id,
                                            course_id,
                                            current_lesson,
                                            current_exercise,
                                            user_answer,
                                            True
                                        )
                                        
                                        st.session_state.completed_exercises[course_id][exercise_key] = True
                                        st.session_state.exercise_attempts[course_id][exercise_key] = 0  # รีเซ็ตการนับครั้งผิด
                                        st.success("✅ **คำตอบถูกต้อง!**")
                                        time.sleep(1)
                                        
                                        # อัปเดตไปข้อถัดไป
                                        if current_exercise < len(exercises) - 1:
                                            st.session_state.current_exercise['exercise'] += 1
                                        elif current_lesson < total_lessons - 1:
                                            st.session_state.current_exercise['lesson'] += 1
                                            st.session_state.current_exercise['exercise'] = 0
                                        st.rerun()
                                    else:
                                        attempt_count += 1
                                        st.session_state.exercise_attempts[course_id][exercise_key] = attempt_count
                                        
                                        if attempt_count == 1:
                                            st.error("❌ **คำตอบไม่ถูกต้อง** กรุณาตอบใหม่อีก 1 ครั้ง")
                                            st.rerun()
                                        elif attempt_count == 2:
                                            st.error("❌ **คำตอบไม่ถูกต้อง** คุณตอบผิด 2 ครั้งแล้ว")
                                            # ไม่ต้องรีเซ็ต จะแสดงเฉลยด้านล่าง
                                            st.rerun()
                                else:
                                    st.warning("กรุณากรอกคำตอบก่อนส่ง")
                        
                        # แสดงเฉลยถ้าตอบผิด 2 ครั้ง
                        if attempt_count >= 2:
                            st.markdown("---")
                            st.markdown('<div style="background-color: #FFF9C4; border: 2px solid #FFD700; border-radius: 8px; padding: 15px; margin: 15px 0; color: #000;">', unsafe_allow_html=True)
                            st.markdown("### 📖 เฉลย")
                            st.write(f"**{exercise.get('answer', 'ไม่มีเฉลย')}**")
                            st.markdown('</div>', unsafe_allow_html=True)
                    
                    else:
                        st.success("✅ **คุณทำแบบฝึกหัดนี้เสร็จแล้ว!**")
                        
                        # แสดงเฉลยสำหรับข้อที่ทำเสร็จแล้ว
                        st.markdown('<div style="background-color: #FFF9C4; border: 2px solid #FFD700; border-radius: 8px; padding: 15px; margin: 15px 0; color: #000;">', unsafe_allow_html=True)
                        st.markdown("### 📖 เฉลย")
                        st.write(f"**{exercise.get('answer', 'ไม่มีเฉลย')}**")
                        st.markdown('</div>', unsafe_allow_html=True)
            
            # Navigation buttons - เอปุ่มข้ามออก
            st.markdown("---")
            col_nav1, col_nav2, col_nav3 = st.columns(3)
            
            with col_nav1:
                # Previous exercise button
                if current_exercise > 0:
                    if st.button("⬅ แบบฝึกหัดก่อนหน้า", use_container_width=True):
                        st.session_state.current_exercise['exercise'] -= 1
                        st.rerun()
                else:
                    st.button("⬅ แบบฝึกหัดก่อนหน้า", disabled=True, use_container_width=True)
            
            with col_nav2:
                # Next exercise button (แสดงเฉพาะเมื่อทำข้อปัจจุบันเสร็จแล้ว)
                exercise_key = f"{course_id}_{current_lesson}_{current_exercise}"
                is_current_completed = st.session_state.completed_exercises[course_id].get(exercise_key, False)
                attempt_count = st.session_state.exercise_attempts[course_id].get(exercise_key, 0)
                
                # สามารถกดถัดไปได้เมื่อ: ตอบถูก หรือ ตอบผิด 2 ครั้งแล้ว
                can_proceed = is_current_completed or attempt_count >= 2
                
                if can_proceed:
                    if current_exercise < len(exercises) - 1:
                        if st.button("แบบฝึกหัดถัดไป ➡", use_container_width=True):
                            st.session_state.current_exercise['exercise'] += 1
                            st.rerun()
                    elif current_lesson < total_lessons - 1:
                        if st.button("บทเรียนถัดไป ➡", use_container_width=True):
                            st.session_state.current_exercise['lesson'] += 1
                            st.session_state.current_exercise['exercise'] = 0
                            st.rerun()
                    else:
                        if st.button("🏆 ประกาศเรียนจบ", type="primary", use_container_width=True):
                            success = mark_course_completed_fb(st.session_state.student_id, course_id)
                            if success:
                                st.success("✅ **บันทึกการเรียนจบเรียบร้อย!**")
                                time.sleep(2)
                                st.session_state.page = "student_home"
                                st.rerun()
                else:
                    st.button("แบบฝึกหัดถัดไป ➡", disabled=True, use_container_width=True)
            
            with col_nav3:
                # Lesson navigation
                lesson_options = list(range(1, total_lessons + 1))
                selected_lesson = st.selectbox(
                    "ไปที่บทเรียน",
                    lesson_options,
                    index=current_lesson,
                    key="lesson_nav"
                )
                if selected_lesson - 1 != current_lesson:
                    st.session_state.current_exercise['lesson'] = selected_lesson - 1
                    st.session_state.current_exercise['exercise'] = 0
                    st.rerun()
        
        else:
            st.info("ยังไม่มีแบบฝึกหัดในคอร์สนี้")
        
        st.markdown('</div>', unsafe_allow_html=True)
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
            "🎥 สอนสด",
            "📤 อัปโหลดเอกสาร", 
            "🎓 ออกใบรับรอง", 
            "🔗 สร้างลิงก์เรียน"
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
            my_courses = get_teacher_courses_fb(st.session_state.teacher_id)
            num_courses = len(my_courses)
        except:
            num_courses = 0
            my_courses = []
        
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
                enrolled_students = 0
                for course in my_courses:
                    enrollments = get_student_enrollments(course['course_id'])
                    enrolled_students += len(enrollments)
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
                for course in my_courses:
                    lessons = get_course_lessons_fb(course['course_id'])
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
        if my_courses:
            cols = st.columns(3)
            for idx, course in enumerate(my_courses[-3:]):
                with cols[idx % 3]:
                    st.markdown('<div class="course-card">', unsafe_allow_html=True)
                    
                    image_path = course.get("image_path", "")
                    if image_path and image_path.startswith('http'):
                        st.image(image_path, use_container_width=True)
                    else:
                        st.markdown(
                            '<div style="background: linear-gradient(135deg, #E6F7FF, #B3E5FC); height: 120px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #1A237E; font-weight: bold;">ภาพคอร์สเรียน</div>',
                            unsafe_allow_html=True
                        )
                    
                    st.write(f"**{course['course_name']}**")
                    st.caption(course.get("description", "")[:80] + "...")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("จัดการ", key=f"manage_{course['course_id']}", use_container_width=True):
                            st.session_state.edit_course = course
                            st.session_state.page = "edit_course"
                            st.rerun()
                    with col_b:
                        if st.button("สอนสด", key=f"live_{course['course_id']}", use_container_width=True):
                            st.session_state.current_course = course
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
            my_courses = get_teacher_courses_fb(st.session_state.teacher_id)
            
            if my_courses:
                for course in my_courses:
                    with st.expander(f"{course['course_name']} ({course.get('class_type', 'กลุ่ม')})", expanded=True):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            image_path = course.get("image_path", "")
                            if image_path and image_path.startswith('http'):
                                st.image(image_path, width=150)
                            
                            st.write(f"**รหัสคอร์ส:** {course['course_id']}")
                            st.write(f"**คำอธิบาย:** {course.get('description', '')}")
                            st.write(f"**จำนวนนักเรียนสูงสุด:** {course.get('max_students', 10)} คน")
                            st.write(f"**ห้อง Jitsi:** {course.get('jitsi_room', 'ยังไม่ได้ตั้งค่า')}")
                            st.write(f"**สถานะ:** {course.get('status', 'active')}")
                        
                        with col2:
                            if st.button("✏️ แก้ไข", key=f"edit_{course['course_id']}", use_container_width=True):
                                st.session_state.edit_course = course
                                st.session_state.page = "edit_course"
                                st.rerun()
                            
                            if st.button("📖 บทเรียน", key=f"lessons_{course['course_id']}", use_container_width=True):
                                st.session_state.current_course = course['course_id']
                                st.session_state.page = "manage_lessons"
                                st.rerun()
                            
                            if st.button("🎥 สอนสด", key=f"go_live_{course['course_id']}", use_container_width=True):
                                st.session_state.current_course = course
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
                        # Generate course ID
                        all_courses = get_all_courses()
                        course_id = f"C{len(all_courses) + 1:04d}"
                        
                        # Save image to Firebase Storage if exists
                        img_url = ""
                        if image:
                            file_bytes = image.getvalue()
                            storage_path = f"course_images/{course_id}_{image.name}"
                            img_url = upload_file_to_storage(file_bytes, storage_path, 'image/jpeg')
                        
                        # Add course to Firestore
                        new_course = {
                            "course_id": course_id,
                            "course_name": course_name,
                            "teacher_id": st.session_state.teacher_id,
                            "teacher_name": st.session_state.teacher_name,
                            "image_path": img_url,
                            "jitsi_room": jitsi_room,
                            "description": description,
                            "max_students": max_students,
                            "current_students": 0,
                            "class_type": class_type,
                            "status": "active",
                            "security_code": security_code,
                            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        add_course(new_course)
                        
                        st.success(f"✅ **สร้างคอร์ส '{course_name}' สำเร็จ!**")
                        st.info(f"**รหัสคอร์ส:** {course_id}")
                        st.info(f"**รหัสความปลอดภัย:** {security_code}")
                        st.info(f"**ห้อง Jitsi:** {jitsi_room}")
                        
                        # Auto redirect after 3 seconds
                        time.sleep(3)
                        st.session_state.page = "teacher_dashboard"
                        st.rerun()
                    except Exception as e:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
    
    # ---------- MANAGE LESSONS ----------
    elif menu_choice == "📖 จัดการบทเรียน":
        st.title("📖 จัดการบทเรียน")
        st.markdown("---")
        
        try:
            my_courses = get_teacher_courses_fb(st.session_state.teacher_id)
            
            if my_courses:
                selected_course = st.selectbox(
                    "**เลือกคอร์ส**", 
                    [c['course_name'] for c in my_courses], 
                    key="select_course_lessons"
                )
                course_id = next((c['course_id'] for c in my_courses if c['course_name'] == selected_course), None)
                
                if course_id:
                    st.write(f"**คอร์ส:** {selected_course}")
                    st.markdown("---")
                    
                    # Load existing lessons
                    lessons = get_course_lessons_fb(course_id)
                    
                    # Display existing lessons
                    st.subheader("บทเรียนที่มีอยู่")
                    if lessons:
                        for i, lesson in enumerate(lessons):
                            with st.expander(f"บทที่ {i+1}: {lesson.get('title', 'ไม่มีชื่อ')}", expanded=False):
                                st.write(f"**หัวข้อ:** {lesson.get('title', 'ไม่มีชื่อ')}")
                                
                                # แสดงไฟล์แนบถ้ามี
                                if lesson.get('file_url'):
                                    file_url = lesson.get('file_url')
                                    st.write(f"**ไฟล์แนบ:** {os.path.basename(file_url) if 'http' in file_url else file_url}")
                                    st.markdown(f'<a href="{file_url}" download style="text-decoration: none;"><button style="background: linear-gradient(135deg, #1A237E, #3949AB); color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer;">📥 ดาวน์โหลดไฟล์</button></a>', unsafe_allow_html=True)
                                
                                # ปุ่มจัดการ
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    if st.button("✏️ แก้ไข", key=f"edit_lesson_{course_id}_{i}", use_container_width=True):
                                        st.session_state.edit_lesson_idx = i
                                        st.session_state.edit_course_id = course_id
                                        st.session_state.page = "edit_lesson"
                                        st.rerun()
                                
                                with col2:
                                    if st.button("🗑️ ลบเนื้อหา", key=f"delete_content_{course_id}_{i}", use_container_width=True):
                                        # ลบเฉพาะเนื้อหา แต่ไม่ลบบทเรียนทั้งหมด
                                        update_lesson(lesson['id'], {"content": ""})
                                        st.success("✅ ลบเนื้อหาบทเรียนเรียบร้อย")
                                        time.sleep(1)
                                        st.rerun()
                                
                                with col3:
                                    if st.button("🗑️ ลบบทเรียน", key=f"delete_lesson_{course_id}_{i}", use_container_width=True, type="secondary"):
                                        # ลบบทเรียนทั้งหมด
                                        # Note: In Firebase, we need to delete the document
                                        st.warning("Feature under development")
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
                                file_url = ""
                                if lesson_file_upload:
                                    file_bytes = lesson_file_upload.getvalue()
                                    storage_path = f"lesson_files/{course_id}/{lesson_file_upload.name}"
                                    file_url = upload_file_to_storage(file_bytes, storage_path)
                                
                                # Add new lesson
                                new_lesson = {
                                    "title": lesson_title,
                                    "content": lesson_content,
                                    "file_url": file_url,
                                    "course_id": course_id,
                                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                
                                success = save_lesson_fb(course_id, new_lesson)
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

# -----------------------------
# Main App Runner
# -----------------------------
if __name__ == "__main__":
    # Display current page for debugging
    if st.session_state.get("debug", False):
        st.sidebar.write(f"Page: {st.session_state.page}")
        st.sidebar.write(f"Role: {st.session_state.role}")
        st.sidebar.write(f"Jitsi Connected: {st.session_state.jitsi_connected}")
