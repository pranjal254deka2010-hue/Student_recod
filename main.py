import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os
import datetime

# --- 1. DATABASE CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. DOCUMENT GENERATORS (ID CARD & RECEIPT) ---

def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    ox, oy, cw, ch = 10, 10, 85, 55
    pdf.set_draw_color(0, 51, 102)
    pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(ox, oy, cw, 12, 'F')
    
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 9)
    pdf.set_xy(ox + 12, oy + 2.5)
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='L')
    
    # Photo
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try:
            header, encoded = photo_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            pdf.image(BytesIO(img_bytes), x=ox + 62, y=oy + 15, w=18, h=22)
        except: pdf.rect(ox + 62, oy + 15, 18, 22)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 8)
    fields = [("NAME:", student.get('name')), ("ROLL NO:", student.get('roll_no')), ("COURSE:", student.get('course')), ("SESSION:", student.get('session'))]
    y = oy + 18
    for lbl, val in fields:
        pdf.set_xy(ox + 4, y)
        pdf.cell(18, 5, lbl); pdf.set_font("Arial", '', 8)
        pdf.cell(40, 5, str(val).upper(), ln=True); y += 6; pdf.set_font("Arial", 'B', 8)
    
    return pdf.output(dest='S').encode('latin-1')

def create_fee_receipt(student_name, roll_no, payment):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 30, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=15, y=12, h=25)
    pdf.set_text_color(255, 255, 255); pdf.set_xy(45, 15); pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    pdf.set_font("Arial", '', 10); pdf.set_x(45); pdf.cell(0, 5, "Guwahati | Dhupdhara, Assam", ln=True)
    
    pdf.set_text_color(0, 0, 0); pdf.set_xy(10, 45); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"MONEY RECEIPT - {payment['fee_type'].upper()}", ln=True, align='C')
    pdf.set_font("Arial", '', 11); pdf.cell(95, 8, f"Receipt: {payment['receipt_no']}")
    pdf.cell(95, 8, f"Date: {payment['payment_date']}", ln=True, align='R')
    
    pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 10)
    pdf.cell(130, 10, "Description", border=1, fill=True)
    pdf.cell(60, 10, "Amount (INR)", border=1, fill=True, align='C', ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(130, 15, f"Fee payment for {student_name} (Roll: {roll_no})", border=1)
    pdf.cell(60, 15, f"{payment['amount_paid']}/-", border=1, align='C', ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- 3. AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

if not st.session_state.auth:
    st.title("🔐 OPI Master Portal")
    u, p = st.text_input("User ID"), st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'}); st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
            if res.data:
                st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]}); st.rerun()
            else: st.error("Invalid Credentials")
else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = False; st.rerun()

    # --- ADMIN SIDE ---
    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        t1, t2, t3 = st.tabs(["Enroll Student", "Fee Management", "Master Records"])
        
        with t1:
            with st.form("enroll", clear_on_submit=True):
                c1, c2 = st.columns(2)
                r, n = c1.text_input("Roll No"), c1.text_input("Name")
                crs = c1.selectbox("Course", ["DMLT", "Radiology", "ECG", "Nursing"])
                bg = c2.selectbox("B. Group", ["A+", "B+", "O+", "AB+"])
                sess, p_set = c2.text_input("Session"), c2.text_input("Set Password")
                addr = st.text_area("Address")
                up = st.file_uploader("Photo", type=['jpg', 'png'])
                if st.form_submit_button("Save Student"):
                    img = f"data:image/png;base64,{base64.b64encode(up.getvalue()).decode()}" if up else ""
                    supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "blood_group": bg, "session": sess, "address": addr, "password": p_set, "photo_url": img}).execute()
                    st.success("Enrolled!")

        with t2:
            st.subheader("💰 Collect Fees")
            students = supabase.table("students").select("roll_no", "name").execute().data
            if students:
                s_list = {f"{s['name']} ({s['roll_no']})": s['roll_no'] for s in students}
                sel_s = st.selectbox("Select Student", list(s_list.keys()))
                amt = st.number_input("Amount Paid", min_value=0)
                f_type = st.selectbox("Fee Type", ["Admission", "Monthly Tuition", "Exam Fee", "Other"])
                mode = st.selectbox("Payment Mode", ["Cash", "UPI/GPay", "Bank Transfer"])
                if st.button("Generate Receipt"):
                    r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    p_data = {"roll_no": s_list[sel_s], "student_name": sel_s.split(" (")[0], "amount_paid": amt, "fee_type": f_type, "payment_mode": mode, "receipt_no": r_id, "payment_date": str(datetime.date.today())}
                    supabase.table("fee_records").insert(p_data).execute()
                    st.download_button("📩 Download Receipt", create_fee_receipt(p_data['student_name'], p_data['roll_no'], p_data), f"Receipt_{r_id}.pdf")

        with t3:
            st.dataframe(supabase.table("students").select("*").execute().data)

    # --- STUDENT SIDE ---
    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 {s['name']}")
        st.download_button("🪪 Download ID Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
        st.subheader("💳 Your Payment History")
        history = supabase.table("fee_records").select("*").eq("roll_no", s['roll_no']).execute().data
        if history:
            for p in history:
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"**{p['fee_type']}** - ₹{p['amount_paid']} ({p['payment_date']})")
                col_b.download_button("📄 PDF", create_fee_receipt(s['name'], s['roll_no'], p), f"Receipt_{p['receipt_no']}.pdf", key=p['receipt_no'])
