import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image

# --- 1. DATABASE CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. ID CARD GENERATOR (PROCESSED FROM DATABASE) ---
def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    ox, oy = 10, 10 # Top-left offset
    cw, ch = 85, 55 # ID Card Dimensions
    
    # Draw Navy Border & Header
    pdf.set_draw_color(0, 51, 102)
    pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(ox, oy, cw, 12, 'F')
    
    # Header Text
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_xy(ox, oy + 2)
    pdf.cell(cw, 5, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='C')
    
    # PHOTO PROCESSING
    photo_data = student.get('photo_url')
    if photo_data and "base64," in photo_data:
        try:
            # Decode the image saved in Supabase
            header, encoded = photo_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            img = Image.open(BytesIO(img_bytes))
            
            # Save temporary file for FPDF to pick up
            temp_path = f"temp_{student['roll_no']}.png"
            img.save(temp_path)
            
            # Place Photo on Card
            pdf.image(temp_path, x=ox + 62, y=oy + 15, w=18, h=22)
        except:
            pdf.rect(ox + 62, oy + 15, 18, 22) # Placeholder if photo fails
    else:
        pdf.rect(ox + 62, oy + 15, 18, 22) # Placeholder

    # STUDENT DETAILS
    pdf.set_text_color(0, 0, 0)
    fields = [
        ("NAME:", student.get('name', 'N/A')),
        ("ROLL NO:", student.get('roll_no', 'N/A')),
        ("COURSE:", student.get('course', 'N/A')),
        ("SESSION:", student.get('session', 'N/A')),
        ("B. GROUP:", student.get('blood_group', 'N/A'))
    ]
    
    current_y = oy + 18
    for label, val in fields:
        pdf.set_xy(ox + 4, current_y)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(15, 5, label)
        pdf.set_font("Arial", '', 8)
        pdf.cell(40, 5, str(val).upper(), ln=True)
        current_y += 7

    return pdf.output(dest='S').encode('latin-1')

# --- 3. LOGIN SYSTEM ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

if not st.session_state.auth:
    st.title("🔐 OPI Portal")
    u_in = st.text_input("User ID / Roll No")
    p_in = st.text_input("Password", type="password")
    if st.button("Login"):
        if u_in == "admin" and p_in == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'})
            st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", u_in).eq("password", p_in).execute()
            if res.data:
                st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]})
                st.rerun()
            else: st.error("Incorrect Credentials")
else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    # --- ADMIN VIEW ---
    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        t1, t2 = st.tabs(["Student Enrollment", "Database View"])
        
        with t1:
            with st.form("enroll_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    r = st.text_input("Roll Number")
                    n = st.text_input("Full Name")
                    c = st.selectbox("Course", ["DMLT", "Radiology", "ECG Technician"])
                with col2:
                    bg = st.selectbox("Blood Group", ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"])
                    sess = st.text_input("Session")
                    pwd = st.text_input("Student Password")
                
                # THE FILE UPLOADER
                up_file = st.file_uploader("Upload Passport Photo", type=['jpg', 'png', 'jpeg'])
                
                if st.form_submit_button("Register & Save"):
                    img_str = ""
                    if up_file:
                        # Convert image to Base64 to save in Supabase
                        base64_img = base64.b64encode(up_file.getvalue()).decode()
                        img_str = f"data:image/png;base64,{base64_img}"
                    
                    payload = {
                        "roll_no": r, "name": n, "course": c, 
                        "blood_group": bg, "session": sess, 
                        "password": pwd, "photo_url": img_str
                    }
                    supabase.table("students").insert(payload).execute()
                    st.success(f"Successfully enrolled {n} with photo!")

        with t2:
            st.dataframe(supabase.table("students").select("roll_no", "name", "course", "session").execute().data)

    # --- STUDENT VIEW ---
    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 Welcome, {s['name']}")
        st.write(f"Logged in as: {s['roll_no']} | Course: {s['course']}")
        
        pdf_file = create_id_card(s)
        st.download_button(
            label="🪪 Download Your ID Card", 
            data=pdf_file, 
            file_name=f"OPI_ID_{s['roll_no']}.pdf", 
            mime="application/pdf"
        )
