import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os
import datetime
import urllib.parse
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
        pdf.set_xy(ox + 4, y); pdf.cell(18, 5, lbl); pdf.set_font("Arial", '', 8); pdf.cell(40, 5, str(val).upper(), ln=True); y += 6; pdf.set_font("Arial", 'B', 8)
    pdf.set_xy(ox + 4, oy + 47); pdf.set_font("Arial", 'B', 7); pdf.cell(18, 4, "ADDRESS:", 0)
    pdf.set_font("Arial", '', 6); pdf.set_xy(ox + 22, oy + 47); pdf.multi_cell(40, 3, str(student.get('address', 'N/A')))
    return pdf.output(dest='S').encode('latin-1')

def create_fee_receipt(student_name, roll_no, payment):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 32, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=15, y=12, h=28)
    pdf.set_text_color(255, 255, 255); pdf.set_xy(50, 15); pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    pdf.set_font("Arial", '', 11); pdf.set_x(50); pdf.cell(0, 6, "Near Daily Bazar, Dhupdhara 783123", ln=True)
    pdf.set_text_color(0, 0, 0); pdf.set_xy(10, 50); pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "OFFICIAL MONEY RECEIPT", ln=True, align='C')
    pdf.set_font("Arial", '', 11); pdf.cell(95, 8, f"Receipt No: {payment['receipt_no']}"); pdf.cell(95, 8, f"Date: {payment['payment_date']}", ln=True, align='R')
    pdf.ln(10); pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 10); pdf.cell(130, 10, "Description", border=1, fill=True); pdf.cell(60, 10, "Amount (INR)", border=1, fill=True, align='C', ln=True)
    pdf.set_font("Arial", '', 11); pdf.cell(130, 20, f"Fees for {student_name} - {payment['fee_type']}", border=1); pdf.cell(60, 20, f"Rs. {payment['amount_paid']}/-", border=1, align='C', ln=True)
    if os.path.exists("signature.png"): pdf.image("signature.png", x=145, y=110, h=30)
    pdf.set_xy(140, 145); pdf.set_font("Arial", 'B', 10); pdf.cell(50, 5, "Authorized Signatory", border='T', align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. APP LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None, 'edit_mode': False, 'edit_student_id': None})

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
        t1, t2, t3 = st.tabs(["Enroll Student", "Fee Collection", "Master Records & Management"])
        
        with t1:
            st.subheader("📝 New Enrollment")
            with st.form("enroll", clear_on_submit=True):
                c1, c2 = st.columns(2)
                r, n = c1.text_input("Roll No"), c1.text_input("Name")
                crs = c1.selectbox("Course", ["DMLT", "Radiology", "ECG Technician", "Nursing Assistant"])
                ph = c1.text_input("WhatsApp No (e.g., 91...)")
                
                # --- RESTORED JOINING DATE ---
                j_date = c2.date_input("Joining Date", datetime.date.today())
                m_fee = c2.number_input("Monthly Fee Amount", value=2500)
                p_set = c2.text_input("Set Password")
                addr = st.text_area("Address")
                up = st.file_uploader("Photo", type=['jpg', 'png'])
                if st.form_submit_button("Save Student"):
                    img = f"data:image/png;base64,{base64.b64encode(up.getvalue()).decode()}" if up else ""
                    supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "password": p_set, "photo_url": img, "is_active": True, "monthly_fee_amount": m_fee, "address": addr, "phone": ph, "joining_date": str(j_date)}).execute()
                    st.success("Registration Successful!")

        with t2:
            st.subheader("💰 Smart Fee Collection")
            students = supabase.table("students").select("*").eq("is_active", True).execute().data
            if students:
                s_dict = {f"{s['name']} (Roll: {s['roll_no']})": s for s in students}
                sel_name = st.selectbox("Select Student", list(s_dict.keys()))
                sel_s = s_dict[sel_name]
                
                # Show joining date for context
                st.info(f"📅 Student Joined on: {sel_s.get('joining_date')}")

                late_fine = 0; today = datetime.date.today()
                f_cat = st.selectbox("Category", ["Monthly Tuition", "Admission Fee", "Registration Fee", "Examination Fee"])
                
                if f_cat == "Monthly Tuition" and today.day > 10:
                    late_fine = (today.day - 10) * 50
                    st.warning(f"⚠️ Late fine calculated: ₹{late_fine}")

                col_a, col_b = st.columns(2)
                base_amt = col_a.number_input("Base Amount", value=int(sel_s.get('monthly_fee_amount', 2500)) if f_cat == "Monthly Tuition" else 0)
                fine_to_apply = col_a.number_input("Fine to Add", value=late_fine)
                f_desc = col_b.text_input("Month/Description (e.g. May 2026)")
                mode = col_b.selectbox("Mode", ["Cash", "UPI", "Bank"])
                
                if st.button("Generate Receipt"):
                    r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    desc = f"{f_cat} ({f_desc})"
                    if fine_to_apply > 0: desc += f" + Fine (₹{fine_to_apply})"
                    p_data = {"roll_no": sel_s['roll_no'], "student_name": sel_s['name'], "amount_paid": base_amt + fine_to_apply, "fee_type": desc, "receipt_no": r_id, "payment_date": str(today), "payment_mode": mode}
                    supabase.table("fee_records").insert(p_data).execute()
                    st.download_button("📩 Download PDF", create_fee_receipt(sel_s['name'], sel_s['roll_no'], p_data), f"Rec_{r_id}.pdf")

        with t3:
            st.subheader("📋 OPI Database & Reminders")
            recs = supabase.table("students").select("*").execute().data
            
            # --- EDIT MODAL (RE-ADDED JOINING DATE) ---
            if st.session_state.edit_mode:
                edit_s = next((item for item in recs if item["roll_no"] == st.session_state.edit_student_id), None)
                if edit_s:
                    st.info(f"🛠️ Editing: {edit_s['name']}")
                    with st.form("edit_form"):
                        c_e1, c_e2 = st.columns(2)
                        e_name = c_e1.text_input("Name", value=edit_s['name'])
                        e_ph = c_e1.text_input("Phone", value=edit_s.get('phone', ''))
                        e_pass = c_e1.text_input("Password", value=edit_s['password'])
                        
                        # --- EDIT JOINING DATE ---
                        current_j = datetime.datetime.strptime(edit_s['joining_date'], '%Y-%m-%d').date() if edit_s.get('joining_date') else datetime.date.today()
                        e_jdate = c_e2.date_input("Joining Date", value=current_j)
                        e_fee = c_e2.number_input("Monthly Fee", value=int(edit_s.get('monthly_fee_amount', 2500)))
                        e_addr = st.text_area("Address", value=edit_s.get('address', ''))
                        
                        if st.form_submit_button("Update Data"):
                            supabase.table("students").update({"name": e_name, "phone": e_ph, "password": e_pass, "monthly_fee_amount": e_fee, "address": e_addr, "joining_date": str(e_jdate)}).eq("roll_no", edit_s['roll_no']).execute()
                            st.session_state.edit_mode = False; st.success("Updated!"); st.rerun()
                        if st.button("Cancel"):
                            st.session_state.edit_mode = False; st.rerun()

            # --- MASTER TABLE DISPLAY ---
            for row in recs:
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"**{row['name']}** ({row['roll_no']}) Joined: {row.get('joining_date')}")
                c2.write(f"PW: `{row['password']}`")
                
                if c3.button("Edit ✏️", key=f"ed_{row['roll_no']}"):
                    st.session_state.edit_mode = True
                    st.session_state.edit_student_id = row['roll_no']
                    st.rerun()
                
                # WhatsApp Reminder
                today = datetime.date.today()
                fine = (today.day - 10) * 50 if today.day > 10 else 0
                msg = f"Dear {row['name']}, OPI reminder: Your fees for {today.strftime('%B')} are due. Current fine is Rs {fine}."
                wa_link = f"https://wa.me/{row.get('phone')}?text={urllib.parse.quote(msg)}"
                c4.markdown(f"[📲 Send Reminder]({wa_link})")
