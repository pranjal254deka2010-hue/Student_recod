import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os
import datetime
import urllib.parse

# --- 1. DATABASE CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. HELPERS ---
def clean_pdf_text(text):
    if not text: return ""
    return str(text).replace("₹", "Rs. ").encode('ascii', 'ignore').decode('ascii')

# --- 3. DOCUMENT GENERATORS ---

def create_admit_card(student, exam):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # 🏛️ Branded Header Box
    pdf.set_draw_color(0, 51, 102); pdf.rect(10, 10, 190, 150) 
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 25, 'F')
    
    if os.path.exists("logo.png"): pdf.image("logo.png", x=13, y=12, h=20)
    
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 15)
    pdf.set_xy(40, 13); pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE")
    pdf.set_font("Arial", 'B', 10); pdf.set_xy(40, 21); pdf.cell(0, 5, "OFFICIAL EXAMINATION ADMIT CARD")
    
    # 👤 Candidate Details Block
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 11)
    pdf.set_xy(15, 42); pdf.cell(0, 8, f"EXAM: {clean_pdf_text(exam['exam_name']).upper()}")
    
    # Student Photo
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try: pdf.image(BytesIO(base64.b64decode(photo_data.split(",")[1])), x=150, y=42, w=40, h=45)
        except: pdf.rect(150, 42, 40, 45)
    else: pdf.rect(150, 42, 40, 45)

    pdf.set_font("Arial", '', 11)
    pdf.set_xy(15, 52); pdf.cell(0, 8, f"Candidate Name: {clean_pdf_text(student['name'])}")
    pdf.set_xy(15, 60); pdf.cell(0, 8, f"Roll Number: {student['roll_no']}")
    pdf.set_xy(15, 68); pdf.cell(0, 8, f"Course: {student['course']}")
    
    # 📚 SUBJECT SCHEDULE TABLE (FIXED LOGIC)
    pdf.set_xy(15, 90); pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 10, "Subject Name", border=1, fill=True, align='C')
    pdf.cell(45, 10, "Exam Date", border=1, fill=True, align='C', ln=True)
    
    pdf.set_font("Arial", '', 10)
    # The fix: Improved parsing of the subject text area
    raw_subjects = exam.get('subject_details', "")
    for line in raw_subjects.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            pdf.set_x(15)
            pdf.cell(90, 10, clean_pdf_text(parts[0].strip()), border=1)
            pdf.cell(45, 10, clean_pdf_text(parts[1].strip()), border=1, align='C', ln=True)
            
    # 🕒 Reporting & Venue Info
    pdf.ln(10); pdf.set_x(15); pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, f"Reporting Time: {clean_pdf_text(exam['reporting_time'])}")
    pdf.ln(6); pdf.set_x(15)
    pdf.cell(0, 8, f"Venue: {clean_pdf_text(exam['venue'])}")
    
    # ✍️ Signature
    if os.path.exists("signature.png"): pdf.image("signature.png", x=150, y=135, h=15)
    pdf.set_xy(150, 152); pdf.set_font("Arial", 'B', 8); pdf.cell(40, 5, "Controller of Exams", border='T', align='C')
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# (create_id_card and create_fee_receipt functions remain standard)

# --- 4. APP AUTH & MAIN LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None, 'edit_id': None})

if not st.session_state.auth:
    st.title("🔐 OPI Master Portal")
    u, p = st.text_input("User ID"), st.text_input("Password", type="password")
    if st.button("Access"):
        if u == "admin" and p == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'}); st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
            if res.data:
                st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]}); st.rerun()
            else: st.error("Access Denied")
else:
    if st.sidebar.button("Logout"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        t1, t2, t3, t4 = st.tabs(["Enroll", "Fees", "Exam Portal", "Student Management"])
        
        with t3: # EXAM PORTAL
            st.subheader("📅 Publish Exam Schedule")
            with st.form("exam_form_v2"):
                e_crs = st.selectbox("Select Course Target", ["DMLT", "Radiology", "ECG", "Nursing"])
                e_nm = st.text_input("Exam Heading (e.g. Annual Exam June 2026)")
                st.write("📋 **Instructions for Subject List:** Use the format `Subject Name : Date` (Example: `Anatomy : 15-06-2026`) and press Enter for the next line.")
                e_subs = st.text_area("Subject Schedule", height=150)
                c_x, c_y = st.columns(2)
                e_tm = c_x.text_input("Reporting Time", value="09:00 AM")
                e_vn = c_y.text_input("Venue", value="OPI Examination Hall")
                if st.form_submit_button("Publish & Grant Access"):
                    supabase.table("exam_schedules").insert({
                        "course": e_crs, "exam_name": e_nm, 
                        "subject_details": e_subs, "reporting_time": e_tm, 
                        "venue": e_vn
                    }).execute()
                    st.success("Exam Published! Now go to 'Student Management' to clear specific students.")

        with t4: # CLEARANCE
            st.subheader("📋 Student Clearance & Records")
            recs = supabase.table("students").select("*").execute().data
            
            # Master Management List
            for row in recs:
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"**{row['name']}** ({row['course']})")
                
                # Manual Clearance Button
                clr_status = "✅ CLEARED" if row['exam_cleared'] else "🔒 LOCKED"
                if c2.button(clr_status, key=f"clr_btn_{row['roll_no']}"):
                    supabase.table("students").update({"exam_cleared": not row['exam_cleared']}).eq("roll_no", row['roll_no']).execute()
                    st.rerun()
                
                if c3.button("Edit ✏️", key=f"edit_btn_{row['roll_no']}"):
                    st.session_state.edit_id = row['roll_no']; st.rerun()
                
                if c4.button("Delete 🗑️", key=f"del_btn_{row['roll_no']}"):
                    supabase.table("fee_records").delete().eq("roll_no", row['roll_no']).execute()
                    supabase.table("students").delete().eq("roll_no", row['roll_no']).execute(); st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 {s['name']}")
        col1, col2 = st.columns([1, 2])
        with col1:
            if s.get('photo_url'): st.image(s['photo_url'], width=150)
            st.download_button("🪪 ID Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
            
            # --- ADMIT CARD LOGIC ---
            st.divider()
            exams = supabase.table("exam_schedules").select("*").eq("course", s['course']).order('id', desc=True).execute().data
            if exams:
                latest = exams[0]
                if s.get('exam_cleared', False):
                    st.success(f"Admit Card: {latest['exam_name']}")
                    st.download_button("📄 Download Admit Card", create_admit_card(s, latest), f"Admit_{s['roll_no']}.pdf")
                else:
                    st.error("🔒 Admit Card access not granted. Please clear your dues at the OPI Office.")
            else:
                st.write("No upcoming exams scheduled for your course.")

        with col2:
            st.subheader("💳 Your Payment Records")
            h = supabase.table("fee_records").select("*").eq("roll_no", str(s['roll_no'])).execute().data
            if h:
                for p in h:
                    st.write(f"**{p['fee_type']}** | Rs. {p['amount_paid']}")
                    # (Standard fee receipt download button code)
