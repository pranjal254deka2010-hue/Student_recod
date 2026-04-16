import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os
import datetime
from dateutil.relativedelta import relativedelta

# --- 1. DATABASE CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. DOCUMENT GENERATORS ---

def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    ox, oy, cw, ch = 10, 10, 85, 55
    pdf.set_draw_color(0, 51, 102); pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102); pdf.rect(ox, oy, cw, 12, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 9); pdf.set_xy(ox + 12, oy + 2.5) 
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='L')
    pdf.set_font("Arial", '', 6); pdf.set_xy(ox + 12, oy + 7)
    pdf.cell(cw - 12, 3, "Near Daily Bazar, Dhupdhara 783123", ln=True, align='L')
    
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try:
            pdf.image(BytesIO(base64.b64decode(photo_data.split(",")[1])), x=ox + 62, y=oy + 15, w=18, h=22)
        except: pdf.rect(ox + 62, oy + 15, 18, 22)
    
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 8)
    fields = [("NAME:", student.get('name')), ("ROLL NO:", student.get('roll_no')), ("COURSE:", student.get('course')), ("SESSION:", student.get('session'))]
    y = oy + 18
    for lbl, val in fields:
        pdf.set_xy(ox + 4, y); pdf.cell(18, 5, lbl); pdf.set_font("Arial", '', 8)
        pdf.cell(40, 5, str(val if val else "N/A").upper(), ln=True); y += 6; pdf.set_font("Arial", 'B', 8)
    
    pdf.set_xy(ox + 4, oy + 47); pdf.set_font("Arial", 'B', 7); pdf.cell(18, 4, "ADDRESS:", 0)
    pdf.set_font("Arial", '', 6); pdf.set_xy(ox + 22, oy + 47)
    pdf.multi_cell(40, 3, str(student.get('address', 'N/A')))
    return pdf.output(dest='S').encode('latin-1')

def create_fee_receipt(student_name, roll_no, payment):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 32, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=15, y=12, h=28)
    pdf.set_text_color(255, 255, 255); pdf.set_xy(50, 15); pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    pdf.set_font("Arial", '', 11); pdf.set_x(50); pdf.cell(0, 6, "Near Daily Bazar, Dhupdhara 783123", ln=True)
    
    pdf.set_text_color(0, 0, 0); pdf.set_xy(10, 50); pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "OFFICIAL MONEY RECEIPT", ln=True, align='C')
    pdf.set_font("Arial", '', 11); pdf.cell(95, 8, f"Receipt No: {payment['receipt_no']}")
    pdf.cell(95, 8, f"Date: {payment['payment_date']}", ln=True, align='R')
    
    pdf.ln(10); pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 10)
    pdf.cell(130, 10, "Description / Particulars", border=1, fill=True)
    pdf.cell(60, 10, "Amount (INR)", border=1, fill=True, align='C', ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(130, 20, f"Fees for {student_name} - {payment['fee_type']}", border=1)
    pdf.cell(60, 20, f"Rs. {payment['amount_paid']}/-", border=1, align='C', ln=True)
    
    if os.path.exists("signature.png"): pdf.image("signature.png", x=145, y=110, h=30)
    pdf.set_xy(140, 145); pdf.set_font("Arial", 'B', 10); pdf.cell(50, 5, "Authorized Signatory", border='T', align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. AUTHENTICATION & PORTAL LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

if not st.session_state.auth:
    st.title("🔐 OPI Master Portal")
    u, p = st.text_input("User ID"), st.text_input("Password", type="password")
    if st.button("Access System"):
        if u == "admin" and p == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'}); st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
            if res.data:
                st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]}); st.rerun()
            else: st.error("Login Failed")
else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = False; st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        t1, t2, t3 = st.tabs(["Enroll Student", "Monthly Fee Collection", "Master Records"])
        
        with t1:
            with st.form("enroll", clear_on_submit=True):
                c1, c2 = st.columns(2)
                r, n = c1.text_input("Roll No"), c1.text_input("Name")
                crs = c1.selectbox("Course", ["DMLT", "Radiology", "ECG", "Nursing Assistant"])
                # Set specific monthly fee for this student
                m_fee = c1.number_input("Monthly Fee for this Student", value=2500)
                j_date = c2.date_input("Joining Date", datetime.date.today())
                p_set = c2.text_input("Set Password")
                addr = st.text_area("Address")
                up = st.file_uploader("Photo", type=['jpg', 'png'])
                if st.form_submit_button("Save Student"):
                    img = f"data:image/png;base64,{base64.b64encode(up.getvalue()).decode()}" if up else ""
                    supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "joining_date": str(j_date), "password": p_set, "photo_url": img, "is_active": True, "monthly_fee_amount": m_fee, "address": addr}).execute()
                    st.success("Registration Successful!")

        with t2:
            st.subheader("💰 Smart Fee & Fine Ledger")
            students = supabase.table("students").select("*").eq("is_active", True).execute().data
            if students:
                s_dict = {f"{s['name']} (Roll: {s['roll_no']})": s for s in students}
                sel_name = st.selectbox("Select Student", list(s_dict.keys()))
                sel_s = s_dict[sel_name]
                
                # --- AUTOMATED FINE CALCULATION (After 10th) ---
                due_day = 10 
                today = datetime.date.today()
                late_fine = 0
                if today.day > due_day:
                    days_late = today.day - due_day
                    late_fine = days_late * 50
                    st.warning(f"⚠️ {days_late} Days Late. Automated Fine: ₹{late_fine}")
                else:
                    st.success("✅ Payment within due date (10th). No fine added.")

                col_a, col_b = st.columns(2)
                base_amt = col_a.number_input("Base Monthly Fee", value=int(sel_s.get('monthly_fee_amount', 2500)))
                fine_to_apply = col_a.number_input("Fine to Add", value=late_fine)
                f_desc = col_b.text_input("For Month/Reason (e.g. May 2026)")
                mode = col_b.selectbox("Mode", ["Cash", "UPI", "Bank Transfer"])
                
                total_collected = base_amt + fine_to_apply
                st.write(f"### Total to Collect: ₹{total_collected}")
                
                if st.button("Generate & Save Receipt"):
                    r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    desc = f"Monthly Tuition ({f_desc})"
                    if fine_to_apply > 0: desc += f" + Late Fine (₹{fine_to_apply})"
                    
                    p_data = {"roll_no": sel_s['roll_no'], "student_name": sel_s['name'], "amount_paid": total_collected, "fee_type": desc, "receipt_no": r_id, "payment_date": str(today), "payment_mode": mode}
                    supabase.table("fee_records").insert(p_data).execute()
                    st.download_button("📩 Download Receipt", create_fee_receipt(sel_s['name'], sel_s['roll_no'], p_data), f"Rec_{r_id}.pdf")

        with t3:
            st.subheader("📋 Student Directory")
            recs = supabase.table("students").select("*").execute().data
            st.dataframe(recs)

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 {s['name']}")
        col1, col2 = st.columns([1, 2])
        with col1:
            if s.get('photo_url'): st.image(s['photo_url'], width=150)
            st.download_button("🪪 ID Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
        with col2:
            st.subheader("💳 Your Payment Records")
            history = supabase.table("fee_records").select("*").eq("roll_no", s['roll_no']).execute().data
            if history:
                for p in history:
                    c_a, c_b = st.columns([3, 1])
                    c_a.write(f"**{p['fee_type']}** | ₹{p['amount_paid']} | {p['payment_date']}")
                    c_b.download_button("📄 Receipt", create_fee_receipt(s['name'], s['roll_no'], p), f"Rec_{p['receipt_no']}.pdf", key=p['receipt_no'])
