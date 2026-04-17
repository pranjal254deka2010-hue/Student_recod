import streamlit as st
from supabase import create_client, Client
import datetime

# --- 1. DATABASE CONNECTION ---
# Use your existing secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Enrollment System", layout="wide")

# --- 2. CONSTANTS ---
COURSES = [
    "DMLT First Year", "DMLT Second Year", 
    "ICU Technician", "First AID and Patient Care", 
    "X Ray Technology"
]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "N/A"]

# --- 3. APP INTERFACE ---
st.title("🏥 OPI Student Enrollment")

# Simple Sidebar for Navigation
menu = st.sidebar.selectbox("Menu", ["New Enrollment", "View Students"])

if menu == "New Enrollment":
    st.subheader("📝 Register New Student")
    with st.form("enroll_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        # Column 1: Basic Info
        roll_no = col1.text_input("Roll No / Enrollment ID")
        name = col1.text_input("Student Full Name")
        course = col1.selectbox("Course & Year", COURSES)
        blood_gp = col1.selectbox("Blood Group", BLOOD_GROUPS)
        session = col1.text_input("Academic Session (e.g., 2024-2026)")
        
        # Column 2: Contact & Admin
        whatsapp = col2.text_input("WhatsApp Number")
        emergency = col2.text_input("Emergency Contact Number")
        monthly_fee = col2.number_input("Standard Monthly Fee", value=2500)
        password = col2.text_input("Portal Password", type="password")
        joining_date = col2.date_input("Joining Date", datetime.date.today())
        
        # Address at bottom
        address = st.text_area("Permanent Address")
        
        submit = st.form_submit_button("Save Student Record")
        
        if submit:
            if not roll_no or not name:
                st.error("Roll No and Name are required!")
            else:
                data = {
                    "roll_no": roll_no,
                    "name": name,
                    "course": course,
                    "blood_group": blood_gp,
                    "academic_session": session,
                    "phone": whatsapp,
                    "emergency_contact": emergency,
                    "monthly_fee_amount": monthly_fee,
                    "password": password,
                    "address": address,
                    "joining_date": str(joining_date),
                    "is_active": True
                }
                try:
                    supabase.table("students").insert(data).execute()
                    st.success(f"Student {name} enrolled successfully!")
                except Exception as e:
                    st.error(f"Database Error: {e}")

elif menu == "View Students":
    st.subheader("📋 Registered Students")
    try:
        res = supabase.table("students").select("*").execute()
        if res.data:
            st.dataframe(res.data)
        else:
            st.info("No students found.")
    except Exception as e:
        st.error(f"Error fetching data: {e}")
