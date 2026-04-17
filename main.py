import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os
import datetime
import urllib.parse

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="OPI Master Portal", layout="wide", page_icon="🏥")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. CONSTANTS ---
COURSES = ["DMLT First Year", "DMLT Second Year", "ICU Technician", "First AID and Patient Care", "X Ray Technology"]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "N/A"]

# --- 3. CRASH-PROOF TEXT CLEANER ---
def safe_str(text):
    if text is None or text == "": return "N/A"
    # Replace Rupee and non-ASCII chars to prevent PDF encoding errors
    s = str(text).replace("₹", "Rs. ")
    return "".join(c for c in s if ord(c) < 128)

# --- 4. REDESIGNED PDF ENGINE ---

def create_id_card(s):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    ox, oy, cw, ch = 10, 10, 85, 55 # ID Card Box Dimensions
    
    # Header & Styling
    pdf.set_draw_color(0, 51, 102); pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102); pdf.rect(ox, oy, cw, 12, 'F')
    
    if os.path.exists("logo.png"): pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 8.5); pdf.set_xy(ox + 12, oy + 4)
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    
    # --- PHOTO LOGIC (THE FIX) ---
    photo_data = s.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try:
            # Decode base64 to PIL Image to ensure it's valid
            header, encoded = photo_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            pil_img = Image.open(BytesIO(img_bytes)).convert("RGB")
            
            # Save temporarily to a buffer and feed to PDF
            temp_buffer = BytesIO()
            pil_img.save(temp_buffer, format="JPEG")
            temp_buffer.seek(0)
            
            pdf.image(temp_buffer, x=ox + 64, y=oy + 14, w=17, h=21)
        except Exception as e:
            # Draw a box if photo fails so we know it's missing
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(ox + 64, oy + 14, 17, 21)
    else:
        pdf.set_draw_color(200, 200, 200); pdf.rect(ox + 64, oy + 14, 17, 21)
        
    # Student Details
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 7.5)
    y_pos = oy + 14
    details = [
        ("NAME", s.get('name')), 
        ("ROLL NO", s.get('roll_no')), 
        ("COURSE", s.get('course')), 
        ("SESSION", s.get('academic_session', 'N/A')),
        ("BLOOD GP", s.get('blood_group', 'N/A')),
        ("EMG NO", s.get('emergency_contact', 'N/A'))
    ]
    
    for lbl, val in details:
        pdf.set_xy(ox + 3, y_pos); pdf.cell(16, 4.5, f"{lbl}:"); pdf.set_font("Arial", '', 7.5)
        pdf.cell(40, 4.5, safe_str(val).upper(), ln=True); y_pos += 4.5; pdf.set_font("Arial", 'B', 7.5)
    
    # Address Section
    pdf.set_xy(ox + 3, oy + 43); pdf.set_font("Arial", 'B', 6.5); pdf.cell(10, 3, "ADDR:")
    pdf.set_font("Arial", '', 6); pdf.set_xy(ox + 13, oy + 43)
    pdf.multi_cell(68, 2.8, safe_str(s.get('address', 'N/A')))
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# (create_admit_card and create_receipt remain the same as previous stable versions)

# --- 5. APP LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None, 'edit_id': None})

if not st.session_state.auth:
    st.title("🏥 OPI Master Portal")
    u, p = st.text_input("User ID / Roll No"), st.text_input("Password", type="password")
    if st.button("Access Portal"):
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
        t = st.tabs(["New Enrollment", "Fee Collection", "Exam Center", "Record Management"])
        
        with t[0]: # ENROLLMENT FORM
            with st.form("enroll_f", clear_on_submit=True):
                c1, c2 = st.columns(2)
                r_i, n_i = c1.text_input("Roll No"), c1.text_input("Student Full Name")
                c_i, b_i = c1.selectbox("Course", COURSES), c1.selectbox("Blood Group", BLOOD_GROUPS)
                ses_i = c1.text_input("Academic Session (e.g., 2024-2026)")
                
                ph_i = c2.text_input("WhatsApp Number")
                emg_i = c2.text_input("Emergency Contact Number")
                f_i = c2.number_input("Standard Monthly Fee", value=2500)
                pw_i = c2.text_input("Portal Password")
                
                a_i = st.text_area("Permanent Address")
                up_i = st.file_uploader("Candidate Photo (JPG/PNG)", type=['jpg', 'png'])
                
                if st.form_submit_button("Complete Enrollment"):
                    if up_i:
                        img_str = f"data:image/png;base64,{base64.b64encode(up_i.getvalue()).decode()}"
                    else:
                        img_str = ""
                    
                    try:
                        supabase.table("students").insert({
                            "roll_no": r_i, "name": n_i, "course": c_i, "blood_group": b_i, 
                            "academic_session": ses_i, "emergency_contact": emg_i,
                            "password": pw_i, "photo_url": img_str, "phone": ph_i, 
                            "monthly_fee_amount": f_i, "address": a_i, "is_active": True, 
                            "joining_date": str(datetime.date.today())
                        }).execute()
                        st.success("Student Enrolled Successfully!")
                    except Exception as ex: st.error("Database Error: Check Roll No uniqueness or data types.")

        with t[3]: # MANAGEMENT
            st.subheader("📋 Student Records")
            stu_list = supabase.table("students").select("*").execute().data
            if stu_list:
                for s in stu_list:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.write(f"**{s['name']}** - {s['course']} ({s.get('academic_session', 'N/A')})")
                    if c2.button("Edit ⚙️", key=f"e_{s['roll_no']}"):
                        st.session_state.edit_id = s['roll_no']; st.rerun()
                    if c3.button("Delete 🗑️", key=f"d_{s['roll_no']}"):
                        supabase.table("students").delete().eq("roll_no", s['roll_no']).execute(); st.rerun()
            else:
                st.info("No students registered yet.")

    elif st.session_state.role == "Student":
        s = st.session_state.user; st.title(f"👋 {s['name']}")
        st.write(f"Session: {s.get('academic_session', 'N/A')} | Course: {s['course']}")
        st.download_button("🪪 Download Official Identity Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
