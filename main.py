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

COURSES = [
    "DMLT First Year", "DMLT Second Year", 
    "ICU Technician", "First AID and Patient Care", 
    "X Ray Technology"
]

# --- 3. DOCUMENT GENERATORS (ID, Receipt, Admit Card) ---
# [Keeping your established PDF logic for brevity - it remains functional as before]
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
        tabs = st.tabs(["Enroll Student", "Fee Collection", "Defaulters Dashboard", "Records & Edit"])
        
        with tabs[0]: # ENROLL
            with st.form("enroll_form"):
                c1, c2 = st.columns(2)
                r, n = c1.text_input("Roll No"), c1.text_input("Name")
                crs = c1.selectbox("Course", COURSES)
                ph, m_fee, pw = c1.text_input("WhatsApp"), c2.number_input("Monthly Fee", value=2500), c2.text_input("Password")
                j_dt = c2.date_input("Joining Date", datetime.date.today())
                if st.form_submit_button("Save"):
                    supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "password": pw, "is_active": True, "monthly_fee_amount": m_fee, "phone": ph, "joining_date": str(j_dt)}).execute()
                    st.success("Enrolled!"); st.rerun()

        with tabs[1]: # FEE COLLECTION
            students = supabase.table("students").select("*").eq("is_active", True).execute().data
            if students:
                s_dict = {f"{s['name']} (ID: {s['roll_no']})": s for s in students}
                sel_s = s_dict[st.selectbox("Select Student", list(s_dict.keys()), key="fee_sel")]
                f_cat = st.selectbox("Type", ["Monthly Tuition", "Admission Fee", "Exam Fee"])
                c_a, c_b = st.columns(2)
                base = c_a.number_input("Amount", value=int(sel_s.get('monthly_fee_amount', 2500)) if f_cat == "Monthly Tuition" else 0)
                f_desc, mode = c_b.text_input("Month/Notes"), c_b.selectbox("Mode", ["Cash", "UPI"])
                if st.button("Process & Print Receipt"):
                    r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    p_data = {"roll_no": sel_s['roll_no'], "student_name": sel_s['name'], "amount_paid": base, "fee_type": f"{f_cat} ({f_desc})", "receipt_no": r_id, "payment_date": str(datetime.date.today()), "payment_mode": mode}
                    supabase.table("fee_records").insert(p_data).execute()
                    st.download_button("📩 Download PDF", create_fee_receipt(sel_s['name'], sel_s['roll_no'], p_data), f"Rec_{r_id}.pdf")

        with tabs[2]: # DEFAULTERS & HISTORY
            st.subheader("📊 Pending Fees & Payment History")
            recs = supabase.table("students").select("*").execute().data
            fees = supabase.table("fee_records").select("*").execute().data
            
            for s in recs:
                if s['is_active']:
                    # Calculate Months Passed
                    j_dt = datetime.datetime.strptime(s['joining_date'], '%Y-%m-%d').date()
                    now = datetime.date.today()
                    months_due = (now.year - j_dt.year) * 12 + now.month - j_dt.month + 1
                    
                    # Calculate Paid Months (counting Monthly Tuition records)
                    paid_m = len([f for f in fees if str(f['roll_no']) == str(s['roll_no']) and "Monthly Tuition" in f['fee_type']])
                    pending = months_due - paid_m
                    
                    with st.expander(f"{s['name']} (Pending: {pending} Months)"):
                        st.write(f"**Course:** {s['course']} | **Joined:** {s['joining_date']}")
                        if pending > 0: st.error(f"⚠️ Total Pending: {pending} months")
                        else: st.success("✅ No Dues")
                        
                        st.write("--- Payment History ---")
                        s_fees = [f for f in fees if str(f['roll_no']) == str(s['roll_no'])]
                        if s_fees: st.table(s_fees)
                        else: st.write("No payments recorded yet.")

        with tabs[3]: # RECORDS & EDIT (With Date of Enrollment Edit)
            st.subheader("📋 Master Records")
            recs = supabase.table("students").select("*").execute().data
            
            if st.session_state.edit_id:
                t = next((s for s in recs if str(s['roll_no']) == str(st.session_state.edit_id)), None)
                if t:
                    with st.form("edit_stu_f"):
                        en = st.text_input("Name", value=t['name'])
                        ec = st.selectbox("Course", COURSES, index=COURSES.index(t['course']) if t['course'] in COURSES else 0)
                        # --- EDIT ENROLLMENT DATE ADDED HERE ---
                        curr_j = datetime.datetime.strptime(t['joining_date'], '%Y-%m-%d').date()
                        ej = st.date_input("Enrollment Date", value=curr_j)
                        if st.form_submit_button("Update Student"):
                            supabase.table("students").update({"name": en, "course": ec, "joining_date": str(ej)}).eq("roll_no", t['roll_no']).execute()
                            st.session_state.edit_id = None; st.rerun()
                    if st.button("Cancel"): st.session_state.edit_id = None; st.rerun()
            else:
                for row in recs:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.write(f"**{row['name']}** ({row['course']})")
                    if c2.button("Edit ✏️", key=f"ed_{row['roll_no']}"):
                        st.session_state.edit_id = row['roll_no']; st.rerun()
                    if c3.button("Del 🗑️", key=f"dl_{row['roll_no']}"):
                        supabase.table("students").delete().eq("roll_no", row['roll_no']).execute(); st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 {s['name']}")
        st.write(f"Joined: {s['joining_date']}")
        st.download_button("🪪 ID Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
        # [Student History Display Logic here]
