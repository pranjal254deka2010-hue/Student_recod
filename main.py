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

# --- 3. HELPER: TEXT CLEANER & LATE FINE ---
def safe_str(text):
    if text is None or text == "": return "N/A"
    return str(text).replace("₹", "Rs. ").encode('ascii', 'ignore').decode('ascii')

def calculate_late_fine():
    day = datetime.date.today().day
    if day > 10:
        return (day - 10) * 50
    return 0

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
menu = st.sidebar.selectbox("Go To", ["Enrollment", "Fee Collection", "Defaulter & Master Records"])

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
        ph = c2.text_input("WhatsApp Number (e.g. 91...)")
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
    fine = calculate_late_fine()
    if fine > 0: st.warning(f"⚠️ Late fine applicable today: Rs. {fine}")
    
    students = supabase.table("students").select("roll_no, name, monthly_fee_amount").eq("is_active", True).execute().data
    if students:
        stu_list = {f"{s['name']} ({s['roll_no']})": s for s in students}
        sel_key = st.selectbox("Select Student", list(stu_list.keys()))
        target_stu = stu_list[sel_key]
        
        with st.form("fee_form"):
            f_type = st.selectbox("Category", ["Monthly Tuition", "Admission Fee", "Registration Fee", "Exam Fee"])
            base_amt = st.number_input("Amount", value=int(target_stu['monthly_fee_amount']) if f_type == "Monthly Tuition" else 0)
            applied_fine = st.number_input("Fine Added", value=fine if f_type == "Monthly Tuition" else 0)
            f_note = st.text_input("For Month/Notes")
            
            if st.form_submit_button("Record Payment"):
                total = base_amt + applied_fine
                r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                p_data = {"roll_no": target_stu['roll_no'], "amount_paid": total, "fee_type": f"{f_type} ({f_note})", "receipt_no": r_id, "payment_date": str(datetime.date.today())}
                supabase.table("fee_records").insert(p_data).execute()
                st.success(f"Payment of Rs. {total} recorded!")
                st.download_button("📩 Download Receipt", create_receipt(target_stu['name'], target_stu['roll_no'], p_data), f"Rec_{r_id}.pdf")

# --- TAB 3: DEFAULTERS & MASTER RECORDS ---
elif menu == "Defaulter & Master Records":
    st.header("📋 Student Records & Defaulter Dashboard")
    stu_list = supabase.table("students").select("*").execute().data
    fee_list = supabase.table("fee_records").select("*").execute().data
    
    with st.expander("🚨 CHECK PENDING PAYMENTS (DEFAULTERS)"):
        for s in stu_list:
            # Calculation: Months since joining vs Monthly Tuition records found
            join_dt = datetime.datetime.strptime(s['joining_date'], '%Y-%m-%d').date()
            months_passed = (datetime.date.today().year - join_dt.year) * 12 + datetime.date.today().month - join_dt.month + 1
            paid_count = len([f for f in fee_list if str(f['roll_no']) == str(s['roll_no']) and "Monthly Tuition" in f['fee_type']])
            pending = months_passed - paid_count
            
            if pending > 0:
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.error(f"**{s['name']}** - {pending} Months Pending")
                c2.write(f"ID: {s['roll_no']}")
                # WhatsApp Link
                msg = f"Dear {s['name']}, this is a reminder from OPI regarding your pending fees for {pending} months. Please clear the dues to avoid late fines."
                wa_url = f"https://wa.me/{s.get('phone')}?text={urllib.parse.quote(msg)}"
                c3.markdown(f"[📲 Notify on WA]({wa_url})")
            else:
                st.write(f"✅ {s['name']} - Fees Clear")

    st.divider()
    # Edit Logic
    if st.session_state.edit_id:
        curr = next((s for s in stu_list if s['roll_no'] == st.session_state.edit_id), None)
        if curr:
            with st.form("edit_form"):
                en_n = st.text_input("Name", value=curr['name'])
                en_s = st.text_input("Session", value=curr.get('academic_session', ''))
                en_a = st.text_area("Address", value=curr.get('address', ''))
                if st.form_submit_button("Update Student"):
                    supabase.table("students").update({"name": en_n, "academic_session": en_s, "address": en_a}).eq("roll_no", curr['roll_no']).execute()
                    st.session_state.edit_id = None; st.rerun()
            if st.button("Cancel"): st.session_state.edit_id = None; st.rerun()
    else:
        for s in stu_list:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{s['name']}** ({s['course']})")
            if c2.button("Edit", key=f"e_{s['roll_no']}"): st.session_state.edit_id = s['roll_no']; st.rerun()
            if c3.button("Del", key=f"d_{s['roll_no']}"): supabase.table("students").delete().eq("roll_no", s['roll_no']).execute(); st.rerun()
