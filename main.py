import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os
import datetime
import urllib.parse

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="OPI Master Portal", layout="wide", page_icon="🏥")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. CONSTANTS ---
COURSES = ["DMLT First Year", "DMLT Second Year", "ICU Technician", "First AID and Patient Care", "X Ray Technology"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "N/A"]

# --- 3. HELPER: IMAGE COMPRESSOR (CRITICAL FIX) ---
def compress_image(uploaded_file):
    """Resizes and compresses image to ensure it fits in DB and PDF."""
    if uploaded_file is None: return ""
    img = Image.open(uploaded_file)
    # Convert to RGB if it's RGBA (removes transparency which crashes PDFs)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    # Resize to a standard passport size (300x400 approx)
    img.thumbnail((300, 400))
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=70) # Compress to 70% quality
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}"

# --- 4. HELPER: TEXT CLEANER ---
def safe_str(text):
    if text is None or text == "": return "N/A"
    s = str(text).replace("₹", "Rs. ")
    return "".join(c for c in s if ord(c) < 128)

# --- 5. PDF ENGINE ---

def create_id_card(s):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    ox, oy, cw, ch = 10, 10, 85, 55
    pdf.set_draw_color(0, 51, 102); pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102); pdf.rect(ox, oy, cw, 12, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 8.5); pdf.set_xy(ox + 12, oy + 4)
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    
    # PHOTO RENDERING
    photo_data = s.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try:
            header, encoded = photo_data.split(",", 1)
            img_bytes = BytesIO(base64.b64decode(encoded))
            pdf.image(img_bytes, x=ox + 64, y=oy + 14, w=17, h=21, type='JPEG')
        except: pdf.rect(ox + 64, oy + 14, 17, 21)
    else: pdf.rect(ox + 64, oy + 14, 17, 21)
        
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 7.5)
    details = [
        ("NAME", s.get('name')), ("ROLL", s.get('roll_no')), 
        ("COURSE", s.get('course')), ("SESS", s.get('academic_session', 'N/A')),
        ("BLOOD", s.get('blood_group', 'N/A')), ("EMG", s.get('emergency_contact', 'N/A'))
    ]
    y_p = oy + 14
    for l, v in details:
        pdf.set_xy(ox + 3, y_p); pdf.cell(15, 4.5, f"{l}:"); pdf.set_font("Arial", '', 7.5)
        pdf.cell(40, 4.5, safe_str(v).upper(), ln=True); y_p += 4.5; pdf.set_font("Arial", 'B', 7.5)
    
    pdf.set_xy(ox + 3, oy + 43); pdf.set_font("Arial", 'B', 6.5); pdf.cell(10, 3, "ADDR:")
    pdf.set_font("Arial", '', 6); pdf.set_xy(ox + 13, oy + 43)
    pdf.multi_cell(68, 2.8, safe_str(s.get('address', 'N/A')))
    return pdf.output(dest='S').encode('latin-1', 'replace')

def create_admit_card(s, exam):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    pdf.set_draw_color(0, 51, 102); pdf.rect(10, 10, 190, 160)
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 25, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=13, y=12, h=18)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 15); pdf.set_xy(40, 14); pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE")
    
    photo_data = s.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try:
            header, encoded = photo_data.split(",", 1)
            pdf.image(BytesIO(base64.b64decode(encoded)), x=150, y=42, w=40, h=45, type='JPEG')
        except: pdf.rect(150, 42, 40, 45)

    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 11); pdf.set_xy(15, 45)
    pdf.cell(0, 8, f"EXAM: {safe_str(exam['exam_name']).upper()}", ln=True)
    pdf.set_font("Arial", '', 11); pdf.set_x(15); pdf.cell(0, 7, f"Candidate: {safe_str(s['name'])}", ln=True)
    pdf.set_x(15); pdf.cell(0, 7, f"Roll No: {s['roll_no']}", ln=True)
    pdf.set_x(15); pdf.cell(0, 7, f"Course: {s['course']}", ln=True)

    pdf.set_xy(15, 95); pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 10, "Subject Name", border=1, fill=True, align='C'); pdf.cell(45, 10, "Date", border=1, fill=True, align='C', ln=True)
    pdf.set_font("Arial", '', 10)
    for line in str(exam.get('subject_details', "")).split("\n"):
        if ":" in line:
            p = line.split(":", 1); pdf.set_x(15); pdf.cell(100, 9, safe_str(p[0]), border=1); pdf.cell(45, 9, safe_str(p[1]), border=1, align='C', ln=True)
    
    if os.path.exists("signature.png"): pdf.image("signature.png", x=155, y=140, h=15)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 6. APP LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None, 'edit_id': None})

if not st.session_state.auth:
    st.title("🏥 OPI Master Portal")
    u, p = st.text_input("User ID"), st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'}); st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
            if res.data: st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]}); st.rerun()
            else: st.error("Access Denied")
else:
    if st.sidebar.button("Logout"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

    if st.session_state.role == "Admin":
        t = st.tabs(["New Enrollment", "Fee Collection", "Exam Center", "Records"])
        
        with t[0]: # ENROLLMENT
            with st.form("enroll_f", clear_on_submit=True):
                c1, c2 = st.columns(2)
                r_i, n_i = c1.text_input("Roll No"), c1.text_input("Name")
                c_i, b_i = c1.selectbox("Course", COURSES), c1.selectbox("Blood Group", BLOOD_GROUPS)
                ses_i, ph_i = c1.text_input("Session"), c2.text_input("WhatsApp")
                emg_i, f_i = c2.text_input("Emergency No"), c2.number_input("Fee", value=2500)
                pw_i, a_i = c2.text_input("Password"), st.text_area("Address")
                up_i = st.file_uploader("Photo", type=['jpg', 'png'])
                if st.form_submit_button("Save"):
                    img_data = compress_image(up_i) # COMPRESSION APPLIED
                    try:
                        supabase.table("students").insert({"roll_no": r_i, "name": n_i, "course": c_i, "blood_group": b_i, "academic_session": ses_i, "emergency_contact": emg_i, "password": pw_i, "photo_url": img_data, "phone": ph_i, "monthly_fee_amount": f_i, "address": a_i, "is_active": True, "joining_date": str(datetime.date.today())}).execute()
                        st.success("Enrolled Successfully!")
                    except Exception as ex: st.error(f"Save Error: Likely Roll No already exists.")

        with t[3]: # MANAGEMENT
            st.subheader("📋 Student Records")
            stu_list = supabase.table("students").select("*").execute().data
            for s in stu_list:
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{s['name']}** ({s['course']})")
                if c2.button("Edit ⚙️", key=f"e_{s['roll_no']}"): st.session_state.edit_id = s['roll_no']; st.rerun()
                if c3.button("Del 🗑️", key=f"d_{s['roll_no']}"): supabase.table("students").delete().eq("roll_no", s['roll_no']).execute(); st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user; st.title(f"👋 {s['name']}")
        st.download_button("🪪 Download Official Identity Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
