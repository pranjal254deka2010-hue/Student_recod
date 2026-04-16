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

# --- 2. DOCUMENT GENERATORS (ID & Receipt - Same as before) ---
def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    ox, oy, cw, ch = 10, 10, 85, 55
    pdf.set_draw_color(0, 51, 102); pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102); pdf.rect(ox, oy, cw, 12, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 9); pdf.set_xy(ox + 12, oy + 4)
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='L')
    
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try:
            header, encoded = photo_data.split(",", 1)
            pdf.image(BytesIO(base64.b64decode(encoded)), x=ox + 62, y=oy + 15, w=18, h=22)
        except: pdf.rect(ox + 62, oy + 15, 18, 22)
    
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 8)
    fields = [("NAME:", student.get('name')), ("ROLL NO:", student.get('roll_no')), ("COURSE:", student.get('course')), ("SESSION:", student.get('session'))]
    y = oy + 18
    for lbl, val in fields:
        pdf.set_xy(ox + 4, y); pdf.cell(18, 5, lbl)
        pdf.set_font("Arial", '', 8); pdf.cell(40, 5, str(val).upper(), ln=True); y += 6; pdf.set_font("Arial", 'B', 8)
    return pdf.output(dest='S').encode('latin-1')

def create_fee_receipt(student_name, roll_no, payment):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 32, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=15, y=12, h=28)
    pdf.set_text_color(255, 255, 255); pdf.set_xy(50, 18); pdf.set_font("Arial", 'B', 18)
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
    
    if os.path.exists("signature.png"): pdf.image("signature.png", x=145, y=105, h=25)
    pdf.set_xy(140, 135); pdf.set_font("Arial", 'B', 10); pdf.cell(50, 5, "Authorized Signatory", border='T', align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. APP LOGIC ---
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
            else: st.error("Login Failed")
else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = False; st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        t1, t2, t3 = st.tabs(["Enroll Student", "Fee Collection", "Master Records"])
        
        with t1:
            with st.form("enroll", clear_on_submit=True):
                c1, c2 = st.columns(2)
                r, n = c1.text_input("Roll No"), c1.text_input("Name")
                crs = c1.selectbox("Course", ["DMLT", "Radiology", "ECG", "Nursing"])
                j_date = c2.date_input("Admission Date", datetime.date.today())
                p_set = c2.text_input("Set Password")
                up = st.file_uploader("Photo", type=['jpg', 'png'])
                if st.form_submit_button("Save Student"):
                    img = f"data:image/png;base64,{base64.b64encode(up.getvalue()).decode()}" if up else ""
                    supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "joining_date": str(j_date), "password": p_set, "photo_url": img, "is_active": True}).execute()
                    st.success("Enrolled!")

        with t2:
            st.subheader("💰 Intelligent Fee Ledger")
            students = supabase.table("students").select("*").eq("is_active", True).execute().data
            if students:
                s_dict = {f"{s['name']} (Joined: {s['joining_date']})": s for s in students}
                sel_name = st.selectbox("Select Student", list(s_dict.keys()))
                sel_s = s_dict[sel_name]
                
                # --- CALCULATE PENDING MONTHS ---
                start = datetime.datetime.strptime(sel_s['joining_date'], '%Y-%m-%d').date()
                now = datetime.date.today()
                diff = relativedelta(now, start)
                months_passed = diff.years * 12 + diff.months + 1
                
                paid_count = len(supabase.table("fee_records").select("id").eq("roll_no", sel_s['roll_no']).eq("fee_type", "Monthly Tuition").execute().data)
                pending = months_passed - paid_count
                
                st.metric("Months Since Admission", months_passed)
                st.metric("Pending Monthly Fees", max(0, pending), delta_color="inverse")

                col_a, col_b = st.columns(2)
                amt = col_a.number_input("Amount", min_value=0)
                f_cat = col_a.selectbox("Category", ["Monthly Tuition", "Admission Fee", "Exam Fee"])
                f_desc = col_b.text_input("For Month (e.g. June 2026)")
                if st.button("Generate Receipt"):
                    r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    p_data = {"roll_no": sel_s['roll_no'], "student_name": sel_s['name'], "amount_paid": amt, "fee_type": f_cat if f_cat != "Monthly Tuition" else f"Monthly Tuition: {f_desc}", "receipt_no": r_id, "payment_date": str(now), "payment_mode": "Recorded"}
                    supabase.table("fee_records").insert(p_data).execute()
                    st.download_button("📩 Receipt", create_fee_receipt(sel_s['name'], sel_s['roll_no'], p_data), f"Rec_{r_id}.pdf")

        with t3:
            st.subheader("📋 Student Management")
            recs = supabase.table("students").select("*").execute().data
            for row in recs:
                c_1, c_2, c_3 = st.columns([2, 1, 1])
                c_1.write(f"**{row['name']}** ({row['roll_no']}) - {row['course']}")
                status = "✅ Active" if row['is_active'] else "🎓 Complete"
                c_2.write(status)
                if c_3.button("Toggle Status", key=row['roll_no']):
                    supabase.table("students").update({"is_active": not row['is_active']}).eq("roll_no", row['roll_no']).execute()
                    st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 {s['name']}")
        st.write(f"Joined on: {s['joining_date']}")
        st.download_button("🪪 ID Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
        history = supabase.table("fee_records").select("*").eq("roll_no", s['roll_no']).execute().data
        if history:
            for p in history:
                st.write(f"**{p['fee_type']}** | ₹{p['amount_paid']} | {p['payment_date']}")
                st.download_button("📄 PDF", create_fee_receipt(s['name'], s['roll_no'], p), f"Rec_{p['receipt_no']}.pdf", key=p['receipt_no'])
