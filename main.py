import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import os
import urllib.parse

# --- 1. DATABASE CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Management System", layout="wide")

# --- 2. CONSTANTS ---
COURSES = ["DMLT First Year", "DMLT Second Year", "ICU Technician", "First AID and Patient Care", "X Ray Technology"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "N/A"]

# --- 3. HELPERS ---
def safe_str(text):
    if text is None or text == "": return "N/A"
    return str(text).replace("₹", "Rs. ").encode('ascii', 'ignore').decode('ascii')

def calculate_late_fine():
    day = datetime.date.today().day
    return (day - 10) * 50 if day > 10 else 0

# --- 4. RECEIPT GENERATOR ---
def create_receipt(student_name, roll_no, payment):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 32, 'F')
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 18); pdf.set_xy(15, 15)
    pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    pdf.set_text_color(0, 0, 0); pdf.set_xy(10, 50); pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "OFFICIAL MONEY RECEIPT", ln=True, align='C')
    pdf.set_font("Arial", '', 11); pdf.ln(5)
    pdf.cell(95, 8, f"Receipt: {payment['receipt_no']}"); pdf.cell(95, 8, f"Date: {payment['payment_date']}", ln=True, align='R')
    pdf.ln(10); pdf.set_font("Arial", 'B', 10); pdf.cell(130, 10, "Description", border=1); pdf.cell(60, 10, "Amount", border=1, ln=True, align='C')
    pdf.set_font("Arial", '', 11); pdf.cell(130, 20, f"Fees: {safe_str(student_name)} - {safe_str(payment['fee_type'])}", border=1)
    pdf.cell(60, 20, f"Rs. {payment['amount_paid']}/-", border=1, align='C', ln=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 5. APP LOGIC ---
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

menu = st.sidebar.selectbox("Go To", ["Enrollment", "Fee Collection", "Defaulter & Master Records"])

if menu == "Enrollment":
    st.header("📝 New Enrollment")
    with st.form("enroll_f"):
        c1, c2 = st.columns(2)
        r_no, n_i = c1.text_input("Roll No"), c1.text_input("Full Name")
        c_i, b_i = c1.selectbox("Course", COURSES), c1.selectbox("Blood Group", BLOOD_GROUPS)
        ses_i, ph_i = c1.text_input("Session"), c2.text_input("WhatsApp (e.g. 91...)")
        em_i, f_i = c2.text_input("Emergency No"), c2.number_input("Monthly Fee", value=2500)
        pw_i, a_i = c2.text_input("Password"), st.text_area("Address")
        if st.form_submit_button("Save Student"):
            supabase.table("students").insert({"roll_no": r_no, "name": n_i, "course": c_i, "blood_group": b_i, "academic_session": ses_i, "phone": ph_i, "emergency_contact": em_i, "monthly_fee_amount": f_i, "password": pw_i, "address": a_i, "is_active": True, "joining_date": str(datetime.date.today())}).execute()
            st.success("Enrolled!")

elif menu == "Fee Collection":
    st.header("💰 Fee Collection")
    fine = calculate_late_fine()
    if fine > 0: st.warning(f"⚠️ Late fine applicable: Rs. {fine}")
    
    stus = supabase.table("students").select("roll_no, name, monthly_fee_amount").eq("is_active", True).execute().data
    if stus:
        s_map = {f"{x['name']} ({x['roll_no']})": x for x in stus}
        sel = st.selectbox("Select Student", list(s_map.keys()))
        t_s = s_map[sel]
        
        with st.form("fee_f"):
            f_t = st.selectbox("Type", ["Monthly Tuition", "Admission Fee", "Exam Fee"])
            b_a = st.number_input("Base Amount", value=int(t_s['monthly_fee_amount']) if f_t == "Monthly Tuition" else 0)
            a_f = st.number_input("Fine", value=fine if f_t == "Monthly Tuition" else 0)
            note = st.text_input("Month/Notes")
            if st.form_submit_button("Process Payment"):
                total = b_a + a_f
                r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                p_d = {"roll_no": t_s['roll_no'], "amount_paid": total, "fee_type": f"{f_t} ({note})", "receipt_no": r_id, "payment_date": str(datetime.date.today())}
                supabase.table("fee_records").insert(p_d).execute()
                st.success("Recorded!"); st.download_button("📩 Download Receipt", create_receipt(t_s['name'], t_s['roll_no'], p_d), f"Rec_{r_id}.pdf")

elif menu == "Defaulter & Master Records":
    st.header("📋 Records & Defaulter List")
    stus = supabase.table("students").select("*").execute().data
    fees = supabase.table("fee_records").select("*").execute().data
    
    with st.expander("🚨 CHECK DEFAULTERS"):
        for s in stus:
            try:
                # Robust date parsing
                j_str = s.get('joining_date', str(datetime.date.today()))
                j_dt = datetime.datetime.strptime(j_str, '%Y-%m-%d').date()
                months_passed = (datetime.date.today().year - j_dt.year) * 12 + datetime.date.today().month - j_dt.month + 1
                paid_c = len([f for f in fees if str(f['roll_no']) == str(s['roll_no']) and "Monthly Tuition" in f['fee_type']])
                pending = months_passed - paid_c
                
                if pending > 0:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.error(f"**{s['name']}** - {pending} Months Pending")
                    msg = f"Dear {s['name']}, this is a reminder regarding your pending fees for {pending} months."
                    wa_url = f"https://wa.me/{s.get('phone')}?text={urllib.parse.quote(msg)}"
                    c3.markdown(f"[📲 Notify]({wa_url})")
            except:
                st.write(f"⚠️ Error calculating for {s['name']} (Check Joining Date)")

    st.divider()
    if st.session_state.edit_id:
        curr = next((s for s in stus if s['roll_no'] == st.session_state.edit_id), None)
        if curr:
            with st.form("edit_stu"):
                en_n = st.text_input("Name", value=curr['name'])
                en_s = st.text_input("Session", value=curr.get('academic_session', ''))
                en_a = st.text_area("Address", value=curr.get('address', ''))
                if st.form_submit_button("Update"):
                    supabase.table("students").update({"name": en_n, "academic_session": en_s, "address": en_a}).eq("roll_no", curr['roll_no']).execute()
                    st.session_state.edit_id = None; st.rerun()
            if st.button("Cancel"): st.session_state.edit_id = None; st.rerun()
    else:
        for s in stus:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{s['name']}** ({s['course']})")
            if c2.button("Edit", key=f"e_{s['roll_no']}"): st.session_state.edit_id = s['roll_no']; st.rerun()
            if c3.button("Del", key=f"d_{s['roll_no']}"): supabase.table("students").delete().eq("roll_no", s['roll_no']).execute(); st.rerun()
