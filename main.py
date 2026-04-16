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
# Ensure these are set in Streamlit Secrets
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
    
    # Border & Header
    pdf.set_draw_color(0, 51, 102); pdf.rect(10, 10, 190, 150) 
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 25, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=13, y=12, h=20)
    
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 15)
    pdf.set_xy(40, 13); pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE")
    pdf.set_font("Arial", 'B', 10); pdf.set_xy(40, 21); pdf.cell(0, 5, "OFFICIAL EXAMINATION ADMIT CARD")
    
    # Candidate Info
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 11)
    pdf.set_xy(15, 42); pdf.cell(0, 8, f"EXAM: {clean_pdf_text(exam['exam_name']).upper()}")
    
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try: pdf.image(BytesIO(base64.b64decode(photo_data.split(",")[1])), x=150, y=42, w=40, h=45)
        except: pdf.rect(150, 42, 40, 45)
    else: pdf.rect(150, 42, 40, 45)

    pdf.set_font("Arial", '', 11)
    pdf.set_xy(15, 52); pdf.cell(0, 8, f"Candidate: {clean_pdf_text(student['name'])}")
    pdf.set_xy(15, 60); pdf.cell(0, 8, f"Roll No: {student['roll_no']}")
    pdf.set_xy(15, 68); pdf.cell(0, 8, f"Course: {student['course']}")
    
    # Subject Table
    pdf.set_xy(15, 90); pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 10, "Subject Name", border=1, fill=True, align='C')
    pdf.cell(45, 10, "Exam Date", border=1, fill=True, align='C', ln=True)
    
    pdf.set_font("Arial", '', 10)
    raw_subs = exam.get('subject_details', "")
    for line in raw_subs.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            pdf.set_x(15)
            pdf.cell(90, 10, clean_pdf_text(parts[0].strip()), border=1)
            pdf.cell(45, 10, clean_pdf_text(parts[1].strip()), border=1, align='C', ln=True)
            
    pdf.ln(10); pdf.set_x(15); pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, f"Reporting Time: {clean_pdf_text(exam['reporting_time'])}")
    pdf.ln(6); pdf.set_x(15); pdf.cell(0, 8, f"Venue: {clean_pdf_text(exam['venue'])}")
    
    if os.path.exists("signature.png"): pdf.image("signature.png", x=150, y=135, h=15)
    pdf.set_xy(150, 152); pdf.set_font("Arial", 'B', 8); pdf.cell(40, 5, "Controller of Exams", border='T', align='C')
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    ox, oy, cw, ch = 10, 10, 85, 55
    pdf.set_draw_color(0, 51, 102); pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102); pdf.rect(ox, oy, cw, 12, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 9); pdf.set_xy(ox + 12, oy + 4)
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='L')
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try: pdf.image(BytesIO(base64.b64decode(photo_data.split(",")[1])), x=ox + 62, y=oy + 15, w=18, h=22)
        except: pdf.rect(ox + 62, oy + 15, 18, 22)
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 8)
    fields = [("NAME:", student.get('name')), ("ROLL NO:", student.get('roll_no')), ("COURSE:", student.get('course'))]
    y = oy + 18
    for lbl, val in fields:
        pdf.set_xy(ox + 4, y); pdf.cell(18, 5, lbl); pdf.set_font("Arial", '', 8)
        pdf.cell(40, 5, clean_pdf_text(val).upper(), ln=True); y += 6; pdf.set_font("Arial", 'B', 8)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def create_fee_receipt(student_name, roll_no, payment):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 32, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=15, y=12, h=28)
    pdf.set_text_color(255, 255, 255); pdf.set_xy(50, 15); pdf.set_font("Arial", 'B', 18); pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    pdf.set_font("Arial", '', 11); pdf.set_x(50); pdf.cell(0, 6, "Near Daily Bazar, Dhupdhara 783123", ln=True)
    pdf.set_text_color(0, 0, 0); pdf.set_xy(10, 50); pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "OFFICIAL MONEY RECEIPT", ln=True, align='C')
    pdf.set_font("Arial", '', 11); pdf.cell(95, 8, f"Receipt: {payment['receipt_no']}"); pdf.cell(95, 8, f"Date: {payment['payment_date']}", ln=True, align='R')
    pdf.ln(10); pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 10); pdf.cell(130, 10, "Description", border=1, fill=True); pdf.cell(60, 10, "Amount (INR)", border=1, fill=True, align='C', ln=True)
    pdf.set_font("Arial", '', 11); pdf.cell(130, 20, f"Fees for {clean_pdf_text(student_name)} - {clean_pdf_text(payment['fee_type'])}", border=1); pdf.cell(60, 20, f"Rs. {payment['amount_paid']}/-", border=1, align='C', ln=True)
    if os.path.exists("signature.png"): pdf.image("signature.png", x=145, y=105, h=30)
    pdf.set_xy(140, 140); pdf.set_font("Arial", 'B', 10); pdf.cell(50, 5, "Authorized Signatory", border='T', align='C')
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 4. LOGIN LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None, 'edit_id': None})

if not st.session_state.auth:
    st.title("🔐 OPI Master Portal")
    u, p = st.text_input("User ID / Roll No"), st.text_input("Password", type="password")
    if st.button("Access"):
        if u == "admin" and p == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'}); st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
            if res.data:
                st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]}); st.rerun()
            else: st.error("Login Failed")
else:
    if st.sidebar.button("Logout"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        tabs = st.tabs(["Enroll", "Fees", "Exams", "Records"])
        
        with tabs[0]: # Enroll
            with st.form("enroll_form"):
                c1, c2 = st.columns(2)
                r, n, crs = c1.text_input("Roll No"), c1.text_input("Name"), c1.selectbox("Course", ["DMLT", "Radiology", "ECG", "Nursing"])
                ph, m_fee, pw = c1.text_input("WhatsApp"), c2.number_input("Fee", value=2500), c2.text_input("Password")
                if st.form_submit_button("Save"):
                    supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "password": pw, "is_active": True, "monthly_fee_amount": m_fee, "phone": ph, "exam_cleared": False}).execute()
                    st.success("Enrolled!")

        with tabs[1]: # Fees
            st.subheader("Record Fees")
            st.write("Functionality is active in database.")

        with tabs[2]: # Exams
            st.subheader("Publish Exams")
            with st.form("publish_exam"):
                e_crs = st.selectbox("For Course", ["DMLT", "Radiology", "ECG", "Nursing"])
                e_nm = st.text_input("Exam Name")
                e_sub = st.text_area("Schedule (Subject: Date)")
                e_tm = st.text_input("Time", value="09:00 AM")
                e_vn = st.text_input("Venue", value="OPI Hall")
                if st.form_submit_button("Publish"):
                    supabase.table("exam_schedules").insert({"course": e_crs, "exam_name": e_nm, "subject_details": e_sub, "reporting_time": e_tm, "venue": e_vn}).execute()
                    st.success("Exam Published!")

        with tabs[3]: # Records
            st.subheader("Student List")
            recs = supabase.table("students").select("*").execute().data
            for row in recs:
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"**{row['name']}** ({row['roll_no']})")
                clr = "✅ Shared" if row['exam_cleared'] else "❌ Locked"
                if c2.button(clr, key=f"cl_{row['roll_no']}"):
                    supabase.table("students").update({"exam_cleared": not row['exam_cleared']}).eq("roll_no", row['roll_no']).execute()
                    st.rerun()
                if c3.button("Delete", key=f"dl_{row['roll_no']}"):
                    supabase.table("students").delete().eq("roll_no", row['roll_no']).execute(); st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 {s['name']}")
        st.write(f"Roll No: {s['roll_no']} | Course: {s['course']}")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.download_button("🪪 ID Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
            
            st.divider()
            exams = supabase.table("exam_schedules").select("*").eq("course", s['course']).order('id', desc=True).execute().data
            if exams:
                latest = exams[0]
                if s.get('exam_cleared', False):
                    st.success(f"Admit Card for {latest['exam_name']}")
                    st.download_button("📄 Download Admit Card", create_admit_card(s, latest), f"Admit_{s['roll_no']}.pdf")
                else:
                    st.error("🔒 Admit Card Locked.")
