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
    pdf.set_draw_color(0, 51, 102); pdf.rect(10, 10, 190, 130) 
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 25, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=13, y=12, h=20)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 16)
    pdf.set_xy(40, 14); pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE")
    pdf.set_font("Arial", 'B', 10); pdf.set_xy(40, 22); pdf.cell(0, 5, "EXAMINATION ADMIT CARD")
    
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 11)
    pdf.set_xy(15, 40); pdf.cell(0, 8, f"EXAM: {exam['exam_name'].upper()}")
    
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try: pdf.image(BytesIO(base64.b64decode(photo_data.split(",")[1])), x=155, y=40, w=35, h=40)
        except: pdf.rect(155, 40, 35, 40)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_xy(15, 50); pdf.cell(0, 8, f"Name: {student['name']}")
    pdf.set_xy(15, 57); pdf.cell(0, 8, f"Roll No: {student['roll_no']}")
    pdf.set_xy(15, 64); pdf.cell(0, 8, f"Course: {student['course']}")
    
    pdf.set_xy(15, 80); pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 8, "Subject Name", border=1, fill=True); pdf.cell(40, 8, "Exam Date", border=1, fill=True, ln=True)
    pdf.set_font("Arial", '', 10)
    for line in exam['subject_details'].split("\n"):
        if ":" in line:
            subj, dt = line.split(":", 1)
            pdf.set_x(15); pdf.cell(90, 8, subj.strip(), border=1); pdf.cell(40, 8, dt.strip(), border=1, ln=True)
            
    pdf.set_xy(15, 115); pdf.set_font("Arial", 'I', 9); pdf.cell(0, 5, f"Reporting Time: {exam['reporting_time']} | Venue: {exam['venue']}")
    if os.path.exists("signature.png"): pdf.image("signature.png", x=155, y=115, h=15)
    pdf.set_xy(155, 130); pdf.set_font("Arial", 'B', 8); pdf.cell(35, 5, "Controller of Exams", border='T', align='C')
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

# --- 4. APP LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

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
        t1, t2, t3, t4 = st.tabs(["Enroll Student", "Fee Collection", "Exam Schedules", "Student Clearance"])
        
        with t1:
            with st.form("enroll", clear_on_submit=True):
                c1, c2 = st.columns(2)
                r, n, crs = c1.text_input("Roll No"), c1.text_input("Name"), c1.selectbox("Course", ["DMLT", "Radiology", "ECG Technician", "Nursing Assistant"])
                ph, m_fee, p_set = c1.text_input("WhatsApp"), c2.number_input("Monthly Fee", value=2500), c2.text_input("Password")
                j_date, addr = c2.date_input("Joining Date"), st.text_area("Address")
                up = st.file_uploader("Photo", type=['jpg', 'png'])
                if st.form_submit_button("Save"):
                    img = f"data:image/png;base64,{base64.b64encode(up.getvalue()).decode()}" if up else ""
                    supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "password": p_set, "photo_url": img, "is_active": True, "monthly_fee_amount": m_fee, "address": addr, "phone": ph, "joining_date": str(j_date), "exam_cleared": False}).execute()
                    st.success("Enrolled!")

        with t2:
            students = supabase.table("students").select("*").eq("is_active", True).execute().data
            if students:
                s_dict = {f"{s['name']} (ID: {s['roll_no']})": s for s in students}
                sel_s = s_dict[st.selectbox("Select Student", list(s_dict.keys()), key="fee_sel")]
                f_cat = st.selectbox("Type", ["Monthly Tuition", "Admission Fee", "Registration Fee", "Examination Fee"])
                c_a, c_b = st.columns(2)
                base_amt = c_a.number_input("Base Amount", value=int(sel_s.get('monthly_fee_amount', 2500)) if f_cat == "Monthly Tuition" else 0)
                f_desc, mode = c_b.text_input("Details"), c_b.selectbox("Mode", ["Cash", "UPI"])
                if st.button("Process Payment"):
                    r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    p_data = {"roll_no": sel_s['roll_no'], "student_name": sel_s['name'], "amount_paid": base_amt, "fee_type": f"{f_cat} ({f_desc})", "receipt_no": r_id, "payment_date": str(datetime.date.today()), "payment_mode": mode}
                    supabase.table("fee_records").insert(p_data).execute()
                    st.download_button("📩 Receipt PDF", create_fee_receipt(sel_s['name'], sel_s['roll_no'], p_data), f"Rec_{r_id}.pdf")

        with t3:
            st.subheader("📅 Manage Exam Schedules")
            with st.form("exam_form"):
                e_crs = st.selectbox("Course", ["DMLT", "Radiology", "ECG Technician", "Nursing Assistant"])
                e_nm = st.text_input("Exam Name")
                e_subs = st.text_area("Subjects (Format: Anatomy: 20-05-2026)")
                e_tm = st.text_input("Reporting Time", value="09:30 AM")
                e_vn = st.text_input("Venue", value="OPI Campus")
                if st.form_submit_button("Publish"):
                    supabase.table("exam_schedules").insert({"course": e_crs, "exam_name": e_nm, "subject_details": e_subs, "reporting_time": e_tm, "venue": e_vn}).execute()
                    st.success("Exam Published!")
            st.dataframe(supabase.table("exam_schedules").select("*").execute().data)

        with t4:
            st.subheader("🔑 Manual Exam Clearance")
            recs = supabase.table("students").select("*").execute().data
            for row in recs:
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{row['name']}** ({row['roll_no']}) - {row['course']}")
                status = "✅ CLEARED" if row['exam_cleared'] else "❌ LOCKED"
                c2.write(f"Status: {status}")
                label = "Lock Admit Card" if row['exam_cleared'] else "Give Admit Card Access"
                if c3.button(label, key=f"clr_{row['roll_no']}"):
                    supabase.table("students").update({"exam_cleared": not row['exam_cleared']}).eq("roll_no", row['roll_no']).execute()
                    st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 {s['name']}")
        col1, col2 = st.columns([1, 2])
        with col1:
            if s.get('photo_url'): st.image(s['photo_url'], width=150)
            st.download_button("🪪 ID Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
            
            # --- ADMIT CARD SECTION ---
            st.divider()
            exams = supabase.table("exam_schedules").select("*").eq("course", s['course']).execute().data
            if exams:
                latest = exams[-1]
                if s.get('exam_cleared', False):
                    st.success("✅ Your Admit Card is ready!")
                    st.download_button("📄 Download Admit Card", create_admit_card(s, latest), f"Admit_{s['roll_no']}.pdf")
                else:
                    st.error("🔒 Admit Card not shared yet. Please contact OPI Office.")
            else:
                st.write("No exams scheduled.")

        with col2:
            st.subheader("💳 Payments")
            h = supabase.table("fee_records").select("*").eq("roll_no", str(s['roll_no'])).execute().data
            if h:
                for p in h:
                    st.write(f"**{p['fee_type']}** | Rs. {p['amount_paid']}")
                    st.download_button(f"📄 Rec {p['receipt_no']}", create_fee_receipt(s['name'], s['roll_no'], p), f"OPI_{p['receipt_no']}.pdf", key=f"dl_{p['receipt_no']}")
