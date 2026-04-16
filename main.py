import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os

# --- 1. DATABASE CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. ID CARD GENERATOR (A4 FORMAT) ---
def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    ox, oy = 10, 10 # Top-left position
    cw, ch = 85, 55 # ID Card size
    
    # Border & Header
    pdf.set_draw_color(0, 51, 102) # OPI Navy Blue
    pdf.set_line_width(0.5)
    pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(ox, oy, cw, 12, 'F')
    
    # LOGO (Top Left)
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    
    # Header Text
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 9)
    pdf.set_xy(ox + 12, oy + 2)
    pdf.cell(cw - 12, 5, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='L')
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(ox + 12, oy + 7)
    pdf.cell(cw - 12, 3, "GUWAHATI | DHUPDHARA, ASSAM", ln=True, align='L')
    
    # PHOTO PROCESSING
    photo_data = student.get('photo_url')
    if photo_data and "base64," in photo_data:
        try:
            header, encoded = photo_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            img = Image.open(BytesIO(img_bytes))
            temp_path = f"temp_{student['roll_no']}.png"
            img.save(temp_path)
            pdf.image(temp_path, x=ox + 62, y=oy + 15, w=18, h=22)
        except:
            pdf.rect(ox + 62, oy + 15, 18, 22)
    else:
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(ox + 62, oy + 15, 18, 22)

    # DETAILS
    pdf.set_text_color(0, 0, 0)
    def add_line(label, value, y_add):
        pdf.set_xy(ox + 4, oy + y_add)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(18, 5, label)
        pdf.set_font("Arial", '', 8)
        pdf.cell(40, 5, str(value).upper(), ln=True)

    add_line("NAME:", student.get('name', 'N/A'), 18)
    add_line("ROLL NO:", student.get('roll_no', 'N/A'), 24)
    add_line("COURSE:", student.get('course', 'N/A'), 30)
    add_line("SESSION:", student.get('session', 'N/A'), 36)
    add_line("B. GROUP:", student.get('blood_group', 'N/A'), 42)
    
    # ADDRESS
    pdf.set_xy(ox + 4, oy + 47)
    pdf.set_font("Arial", 'B', 7)
    pdf.cell(18, 4, "ADDRESS:", 0)
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(ox + 22, oy + 47)
    pdf.multi_cell(40, 3, student.get('address', 'N/A'))

    return pdf.output(dest='S').encode('latin-1')

# --- 3. ACCESS CONTROL ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

if not st.session_state.auth:
    st.title("🔐 OPI Master Portal")
    uid = st.text_input("User ID / Roll No")
    pwd = st.text_input("Password", type="password")
    if st.button("Enter System"):
        if uid == "admin" and pwd == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'})
            st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", uid).eq("password", pwd).execute()
            if res.data:
                st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]})
                st.rerun()
            else: st.error("Invalid Login Credentials")
else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    # --- ADMIN SIDE ---
    if st.session_state.role == "Admin":
        st.title("👨‍🏫 Administrator Dashboard")
        t1, t2 = st.tabs(["Enroll Student", "Master Database"])
        
        with t1:
            with st.form("enroll_student", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    r = st.text_input("Roll Number")
                    n = st.text_input("Full Name")
                    crs = st.selectbox("Course", ["DMLT", "Radiology", "ECG Technician", "Nursing"])
                    ph = st.text_input("Phone Number")
                with c2:
                    bg = st.selectbox("Blood Group", ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"])
                    sess = st.text_input("Session")
                    p_set = st.text_input("Set Password")
                
                addr = st.text_area("Address")
                up_file = st.file_uploader("Choose Student Photo", type=['jpg', 'png', 'jpeg'])
                
                if st.form_submit_button("Save Record"):
                    img_str = ""
                    if up_file:
                        img_str = f"data:image/png;base64,{base64.b64encode(up_file.getvalue()).decode()}"
                    
                    payload = {
                        "roll_no": r, "name": n, "course": crs, "phone": ph,
                        "blood_group": bg, "session": sess, "address": addr,
                        "password": p_set, "photo_url": img_str
                    }
                    supabase.table("students").insert(payload).execute()
                    st.success(f"Success! {n} is now in the database.")

        with t2:
            st.subheader("📋 Institutional Records")
            records = supabase.table("students").select("*").execute()
            if records.data:
                st.dataframe(records.data)
            else: st.info("No students found.")

    # --- STUDENT SIDE ---
    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 Student Portal: {s['name']}")
        
        col_img, col_info = st.columns([1, 2])
        with col_img:
            if s.get('photo_url') and len(s['photo_url']) > 100:
                st.image(s['photo_url'], width=180)
            else: st.info("Photo not available in records.")
            
        with col_info:
            st.subheader("Academic Details")
            st.write(f"**Roll No:** {s['roll_no']}")
            st.write(f"**Course:** {s['course']}")
            st.write(f"**Address:** {s.get('address', 'N/A')}")
            
            pdf_bytes = create_id_card(s)
            st.download_button(
                label="🪪 Download ID Card (PDF)",
                data=pdf_bytes,
                file_name=f"OPI_ID_{s['roll_no']}.pdf",
                mime="application/pdf"
            )
