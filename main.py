import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import os

# --- 1. DATABASE CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Management System", layout="wide")

# --- 2. CONSTANTS ---
COURSES = ["DMLT First Year", "DMLT Second Year", "ICU Technician", "First AID and Patient Care", "X Ray Technology"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "N/A"]

# --- 3. HELPER: TEXT CLEANER ---
def safe_str(text):
    if text is None or text == "": return "N/A"
    return str(text).replace("₹", "Rs. ").encode('ascii', 'ignore').decode('ascii')

# --- 4. RECEIPT GENERATOR ---
def create_receipt(student_name, roll_no, payment):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 32, 'F')
    
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 18); pdf.set_xy(15, 15)
    pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    pdf.set_font("Arial", '', 11); pdf.set_x(15); pdf.cell(0, 6, "Near Daily Bazar, Dhupdhara 783123", ln=True)
    
    pdf.set_text_color(0, 0, 0); pdf.set_xy(10, 50); pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "OFFICIAL MONEY RECEIPT", ln=True, align='C')
    
    pdf.set_font("Arial", '', 11); pdf.ln(5)
    pdf.cell(95, 8, f"Receipt: {payment['receipt_no']}")
    pdf.cell(95, 8, f"Date: {payment['payment_date']}", ln=True, align='R')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10); pdf.cell(130, 10, "Description", border=1); pdf.cell(60, 10, "Amount", border=1, ln=True, align='C')
    pdf.set_font("Arial", '', 11); pdf.cell(130, 20, f"Fees for {safe_str(student_name)} - {safe_str(payment['fee_type'])}", border=1)
    pdf.cell(60, 20, f"Rs. {payment['amount_paid']}/-", border=1, align='C', ln=True)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 5. APP LOGIC ---
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

st.sidebar.title("🏥 OPI Command Center")
menu = st.sidebar.selectbox("Go To", ["Enrollment", "Fee Collection", "View & Edit Records"])

# --- TAB 1: ENROLLMENT ---
if menu == "Enrollment":
    st.header("📝 New Student Registration")
    with st.form("enroll_form"):
        c1, c2 = st.columns(2)
        r_no = c1.text_input("Roll No")
        name = c1.text_input("Full Name")
        crs = c1.selectbox("Course", COURSES)
        bg = c1.selectbox("Blood Group", BLOOD_GROUPS)
        ses = c1.text_input("Session")
        
        ph = c2.text_input("WhatsApp")
        emg = c2.text_input("Emergency Contact")
        fee = c2.number_input("Monthly Fee", value=2500)
        pw = c2.text_input("Password", type="password")
        addr = st.text_area("Address")
        
        if st.form_submit_button("Save Student"):
            data = {"roll_no": r_no, "name": name, "course": crs, "blood_group": bg, "academic_session": ses, "phone": ph, "emergency_contact": emg, "monthly_fee_amount": fee, "password": pw, "address": addr, "is_active": True, "joining_date": str(datetime.date.today())}
            supabase.table("students").insert(data).execute()
            st.success("Student Enrolled!")

# --- TAB 2: FEE COLLECTION ---
elif menu == "Fee Collection":
    st.header("💰 Fee Collection")
    students = supabase.table("students").select("roll_no, name").eq("is_active", True).execute().data
    
    if students:
        stu_list = {f"{s['name']} ({s['roll_no']})": s['roll_no'] for s in students}
        sel_name = st.selectbox("Select Student", list(stu_list.keys()))
        sel_roll = stu_list[sel_name]
        
        with st.form("fee_form"):
            f_type = st.selectbox("Category", ["Monthly Tuition", "Admission Fee", "Registration Fee", "Exam Fee"])
            f_amt = st.number_input("Amount", min_value=0)
            f_note = st.text_input("Month/Notes")
            
            if st.form_submit_button("Process Payment"):
                r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                p_data = {"roll_no": sel_roll, "amount_paid": f_amt, "fee_type": f"{f_type} ({f_note})", "receipt_no": r_id, "payment_date": str(datetime.date.today())}
                supabase.table("fee_records").insert(p_data).execute()
                st.success("Payment Recorded!")
                st.download_button("📩 Download Receipt", create_receipt(sel_name.split(" (")[0], sel_roll, p_data), f"Rec_{r_id}.pdf")

# --- TAB 3: VIEW & EDIT RECORDS ---
elif menu == "View & Edit Records":
    st.header("📋 Student Records")
    stu_list = supabase.table("students").select("*").execute().data
    
    if st.session_state.edit_id:
        # PULL FULL INFORMATION FOR THE SELECTED STUDENT
        curr = next((s for s in stu_list if s['roll_no'] == st.session_state.edit_id), None)
        if curr:
            st.warning(f"Editing Record for: {curr['name']}")
            with st.form("edit_form"):
                e_name = st.text_input("Name", value=curr['name'])
                e_crs = st.selectbox("Course", COURSES, index=COURSES.index(curr['course']) if curr['course'] in COURSES else 0)
                e_ses = st.text_input("Session", value=curr.get('academic_session', ''))
                e_emg = st.text_input("Emergency Contact", value=curr.get('emergency_contact', ''))
                e_addr = st.text_area("Address", value=curr.get('address', ''))
                
                if st.form_submit_button("Update Student Information"):
                    supabase.table("students").update({"name": e_name, "course": e_crs, "academic_session": e_ses, "emergency_contact": e_emg, "address": e_addr}).eq("roll_no", curr['roll_no']).execute()
                    st.session_state.edit_id = None
                    st.success("Information Updated!")
                    st.rerun()
            if st.button("Cancel Edit"):
                st.session_state.edit_id = None
                st.rerun()
    else:
        for s in stu_list:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{s['name']}** - {s['course']} ({s.get('academic_session', 'N/A')})")
            if c2.button("Edit ⚙️", key=f"ed_{s['roll_no']}"):
                st.session_state.edit_id = s['roll_no']
                st.rerun()
            if c3.button("Delete 🗑️", key=f"dl_{s['roll_no']}"):
                supabase.table("students").delete().eq("roll_no", s['roll_no']).execute()
                st.rerun()
