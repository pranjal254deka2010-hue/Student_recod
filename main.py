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

# --- 2. HELPERS ---
def clean_pdf_text(text):
    if not text: return ""
    return str(text).replace("₹", "Rs. ").encode('ascii', 'ignore').decode('ascii')

# --- 3. DOCUMENT GENERATORS ---
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
        pdf.set_xy(ox + 4, y); pdf.cell(18, 5, lbl); pdf.set_font("Arial", '', 8)
        pdf.cell(40, 5, clean_pdf_text(val).upper(), ln=True); y += 6; pdf.set_font("Arial", 'B', 8)
    return pdf.output(dest='S').encode('latin-1', 'replace')

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
    pdf.set_font("Arial", '', 11); pdf.cell(95, 8, f"Receipt: {payment['receipt_no']}"); pdf.cell(95, 8, f"Date: {payment['payment_date']}", ln=True, align='R')
    
    pdf.ln(10); pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 10)
    pdf.cell(130, 10, "Description", border=1, fill=True); pdf.cell(60, 10, "Amount (INR)", border=1, fill=True, align='C', ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(130, 20, f"Fees for {clean_pdf_text(student_name)} - {clean_pdf_text(payment['fee_type'])}", border=1)
    pdf.cell(60, 20, f"Rs. {payment['amount_paid']}/-", border=1, align='C', ln=True)
    
    if os.path.exists("signature.png"): pdf.image("signature.png", x=145, y=105, h=30)
    pdf.set_xy(140, 140); pdf.set_font("Arial", 'B', 10); pdf.cell(50, 5, "Authorized Signatory", border='T', align='C')
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 4. APP LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None, 'edit_mode': False, 'edit_student_id': None})

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
            else: st.error("Failed")
else:
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        t1, t2, t3 = st.tabs(["Enroll Student", "Fee Collection", "Master Records & Dashboard"])
        
        with t1:
            with st.form("enroll_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                r, n, crs = c1.text_input("Roll No"), c1.text_input("Name"), c1.selectbox("Course", ["DMLT", "Radiology", "ECG", "Nursing"])
                ph, m_fee, p_set = c1.text_input("WhatsApp"), c2.number_input("Monthly Fee", value=2500), c2.text_input("Password")
                j_date, addr = c2.date_input("Joining Date"), st.text_area("Address")
                up = st.file_uploader("Photo", type=['jpg', 'png'])
                if st.form_submit_button("Save Student"):
                    img = f"data:image/png;base64,{base64.b64encode(up.getvalue()).decode()}" if up else ""
                    supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "password": p_set, "photo_url": img, "is_active": True, "monthly_fee_amount": m_fee, "address": addr, "phone": ph, "joining_date": str(j_date)}).execute()
                    st.success("Enrolled!"); st.rerun()

        with t2:
            st.subheader("💰 Smart Fee Collection")
            students = supabase.table("students").select("*").eq("is_active", True).execute().data
            if students:
                s_dict = {f"{s['name']} (Roll: {s['roll_no']})": s for s in students}
                sel_name = st.selectbox("Select Student", list(s_dict.keys()), key="fee_sel")
                sel_s = s_dict[sel_name]
                
                # Show Joining Date
                st.info(f"📅 Joined OPI on: {sel_s.get('joining_date')}")

                late_fine = (datetime.date.today().day - 10) * 50 if datetime.date.today().day > 10 else 0
                f_cat = st.selectbox("Category", ["Monthly Tuition", "Admission Fee", "Registration Fee", "Examination Fee"])
                c_a, c_b = st.columns(2)
                base_amt = c_a.number_input("Base Amount", value=int(sel_s.get('monthly_fee_amount', 2500)) if f_cat == "Monthly Tuition" else 0)
                fine_app = c_a.number_input("Fine", value=late_fine if f_cat == "Monthly Tuition" else 0)
                f_desc, mode = c_b.text_input("Month/Notes"), c_b.selectbox("Mode", ["Cash", "UPI", "Bank"])
                
                if st.button("Process & Print Receipt"):
                    r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    p_data = {"roll_no": sel_s['roll_no'], "student_name": sel_s['name'], "amount_paid": base_amt + fine_app, "fee_type": f"{f_cat} ({f_desc})", "receipt_no": r_id, "payment_date": str(datetime.date.today()), "payment_mode": mode}
                    supabase.table("fee_records").insert(p_data).execute()
                    st.download_button("📩 Download PDF", create_fee_receipt(sel_s['name'], sel_s['roll_no'], p_data), f"Rec_{r_id}.pdf")

        with t3:
            st.subheader("📋 Institutional Dashboard")
            recs = supabase.table("students").select("*").execute().data
            fees = supabase.table("fee_records").select("*").execute().data
            
            # --- FINANCIAL DASHBOARD ---
            with st.expander("📊 CHECK PENDING FEES (DEFAULTER LIST)"):
                st.write("Calculated based on Admission Date and 'Monthly Tuition' records.")
                for s in recs:
                    if s['is_active']:
                        # Math: How many months passed since joining?
                        j_dt = datetime.datetime.strptime(s['joining_date'], '%Y-%m-%d').date()
                        now = datetime.date.today()
                        months_enrolled = (now.year - j_dt.year) * 12 + now.month - j_dt.month + 1
                        
                        # Math: How many Monthly Tuition receipts exist?
                        paid_months = len([f for f in fees if str(f['roll_no']) == str(s['roll_no']) and "Monthly Tuition" in f['fee_type']])
                        pending = months_enrolled - paid_months
                        
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        col1.write(f"**{s['name']}**")
                        col2.write(f"Paid: {paid_months}")
                        if pending > 0:
                            col3.error(f"⚠️ {pending} Pending")
                            msg = f"Dear {s['name']}, you have {pending} months of fees pending at OPI. Please clear it soon."
                            wa = f"https://wa.me/{s.get('phone')}?text={urllib.parse.quote(msg)}"
                            col4.markdown(f"[📲 Notify]({wa})")
                        else:
                            col3.success("✅ Up to Date")
                st.divider()

            # --- FULL EDIT MODAL ---
            if st.session_state.edit_mode:
                edit_s = next((item for item in recs if str(item["roll_no"]) == str(st.session_state.edit_student_id)), None)
                if edit_s:
                    st.warning(f"Editing: {edit_s['name']} ({edit_s['roll_no']})")
                    with st.form("full_edit_form"):
                        e1, e2 = st.columns(2)
                        new_n = e1.text_input("Full Name", value=edit_s['name'])
                        new_ph = e1.text_input("WhatsApp Number", value=edit_s.get('phone', ''))
                        new_crs = e1.selectbox("Course", ["DMLT", "Radiology", "ECG", "Nursing"], index=["DMLT", "Radiology", "ECG", "Nursing"].index(edit_s['course']))
                        new_pw = e2.text_input("Login Password", value=edit_s['password'])
                        new_fee = e2.number_input("Monthly Fee Amount", value=int(edit_s.get('monthly_fee_amount', 2500)))
                        current_j = datetime.datetime.strptime(edit_s['joining_date'], '%Y-%m-%d').date()
                        new_j = e2.date_input("Correction: Joining Date", value=current_j)
                        new_addr = st.text_area("Address", value=edit_s.get('address', ''))
                        
                        if st.form_submit_button("Update All Student Data"):
                            supabase.table("students").update({"name": new_n, "phone": new_ph, "password": new_pw, "monthly_fee_amount": new_fee, "joining_date": str(new_j), "address": new_addr, "course": new_crs}).eq("roll_no", edit_s['roll_no']).execute()
                            st.session_state.edit_mode = False; st.rerun()
                    if st.button("Cancel & Go Back"):
                        st.session_state.edit_mode = False; st.rerun()
            else:
                # --- MASTER LIST ---
                for row in recs:
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.write(f"**{row['name']}** (Roll: {row['roll_no']})")
                    c2.write(f"PW: `{row['password']}`")
                    if c3.button("Edit ✏️", key=f"ed_btn_{row['roll_no']}"):
                        st.session_state.edit_mode = True
                        st.session_state.edit_student_id = row['roll_no']
                        st.rerun()
                    if c4.button("Delete 🗑️", key=f"del_btn_{row['roll_no']}"):
                        st.session_state.confirm_delete = row['roll_no']
                    
                    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete == row['roll_no']:
                        if st.button(f"⚠️ Confirm Delete {row['roll_no']}?", key=f"f_del_{row['roll_no']}"):
                            supabase.table("fee_records").delete().eq("roll_no", row['roll_no']).execute()
                            supabase.table("students").delete().eq("roll_no", row['roll_no']).execute()
                            del st.session_state['confirm_delete']; st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 {s['name']}")
        col1, col2 = st.columns([1, 2])
        with col1:
            if s.get('photo_url'): st.image(s['photo_url'], width=150)
            st.download_button("🪪 ID Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
        with col2:
            st.subheader("💳 Your Records")
            h = supabase.table("fee_records").select("*").eq("roll_no", str(s['roll_no'])).execute().data
            if h:
                for p in h:
                    st.write(f"**{p['fee_type']}** | Rs. {p['amount_paid']}")
                    st.download_button(f"📄 Rec {p['receipt_no']}", create_fee_receipt(s['name'], s['roll_no'], p), f"OPI_{p['receipt_no']}.pdf", key=f"st_dl_{p['receipt_no']}")
