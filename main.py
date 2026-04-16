import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os

# --- 1. DATABASE CONNECTION ---
# Ensure these secrets are set in your Streamlit Cloud dashboard
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. ID CARD GENERATOR (A4 FORMAT) ---
def create_id_card(student):
    # Create A4 Portrait PDF
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    ox, oy = 10, 10 # Position on the A4 page
    cw, ch = 85, 55 # Standard ID Card size (85mm x 55mm)
    
    # Draw Navy Blue Border
    pdf.set_draw_color(0, 51, 102)
    pdf.set_line_width(0.5)
    pdf.rect(ox, oy, cw, ch)
    
    # Draw Header Background
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(ox, oy, cw, 12, 'F')
    
    # --- LOGO PLACEMENT ---
    # The code looks for 'logo.png' in your GitHub folder
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    
    # --- HEADER TEXT ---
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 9)
    pdf.set_xy(ox + 12, oy + 2.5)
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='L')
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(ox + 12, oy + 7)
    pdf.cell(cw - 12, 3, "GUWAHATI | DHUPDHARA, ASSAM", ln=True, align='L')
    
    # --- PHOTO PROCESSING ---
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try:
            header, encoded = photo_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            img = Image.open(BytesIO(img_bytes))
            temp_path = f"temp_{student.get('roll_no', 'user')}.png"
            img.save(temp_path)
            # Position Photo on the Right
            pdf.image(temp_path, x=ox + 62, y=oy + 15, w=18, h=22)
        except:
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(ox + 62, oy + 15, 18, 22) # Grey box if error
    else:
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(ox + 62, oy + 15, 18, 22)

    # --- STUDENT DETAILS ---
    pdf.set_text_color(0, 0, 0)
    
    def add_line(label, value, y_add):
        pdf.set_xy(ox + 4, oy + y_add)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(18, 5, label)
        pdf.set_font("Arial", '', 8)
        val_str = str(value) if value else "N/A"
        pdf.cell(40, 5, val_str.upper(), ln=True)

    add_line("NAME:", student.get('name'), 18)
    add_line("ROLL NO:", student.get('roll_no'), 24)
    add_line("COURSE:", student.get('course'), 30)
    add_line("SESSION:", student.get('session'), 36)
    add_line("B. GROUP:", student.get('blood_group'), 42)
    
    # --- ADDRESS (Multi-line support) ---
    pdf.set_xy(ox + 4, oy + 47)
    pdf.set_font("Arial", 'B', 7)
    pdf.cell(18, 4, "ADDRESS:", 0)
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(ox + 22, oy + 47)
    
    addr = student.get('address')
    addr_str = str(addr) if addr else "N/A"
    # multi_cell wraps the address text inside the card width
    pdf.multi_cell(40, 3, addr_str)

    return pdf.output(dest='S').encode('latin-1')

# --- 3. LOGIN & AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

if not st.session_state.auth:
    st.title("🔐 OPI Master Portal Login")
    uid = st.text_input("Username / Roll No")
    pwd = st.text_input("Password", type="password")
    if st.button("Access Portal"):
        if uid == "admin" and pwd == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'})
            st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", uid).eq("password", pwd).execute()
            if res.data:
                st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]})
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")
else:
    if st.sidebar.button("Log Out"):
        st.session_state.auth = False
        st.rerun()

    # --- ADMIN VIEW ---
    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control Panel")
        t1, t2 = st.tabs(["Enroll New Student", "Institutional Records"])
        
        with t1:
            with st.form("enrollment_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    r_no = st.text_input("Roll Number")
                    name = st.text_input("Full Name")
                    course = st.selectbox("Course", ["DMLT", "Radiology", "ECG", "Nursing"])
                with col2:
                    bg = st.selectbox("Blood Group", ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"])
                    sess = st.text_input("Academic Session")
                    p_word = st.text_input("Set Login Password")
                
                address_val = st.text_area("Full Address")
                photo_file = st.file_uploader("Upload Student Photo", type=['png', 'jpg', 'jpeg'])
                
                if st.form_submit_button("Confirm Registration"):
                    img_base64 = ""
                    if photo_file:
                        img_base64 = f"data:image/png;base64,{base64.b64encode(photo_file.getvalue()).decode()}"
                    
                    payload = {
                        "roll_no": r_no, "name": name, "course": course,
                        "blood_group": bg, "session": sess, "address": address_val,
                        "password": p_word, "photo_url": img_base64
                    }
                    supabase.table("students").insert(payload).execute()
                    st.success(f"Registered {name} successfully!")

        with t2:
            st.subheader("📋 Student Master List")
            # Pulling all columns from Supabase
            all_records = supabase.table("students").select("*").execute()
            if all_records.data:
                st.dataframe(all_records.data)
            else:
                st.info("No records found in database.")

    # --- STUDENT VIEW ---
    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 Welcome to the Portal, {s.get('name')}")
        
        col_img, col_info = st.columns([1, 2])
        with col_img:
            if s.get('photo_url') and len(str(s['photo_url'])) > 100:
                st.image(s['photo_url'], width=200)
            else:
                st.info("No photo in record.")
                
        with col_info:
            st.subheader("Your Profile Details")
            st.write(f"**Roll No:** {s.get('roll_no')}")
            st.write(f"**Course:** {s.get('course')}")
            st.write(f"**Session:** {s.get('session')}")
            st.write(f"**Address:** {s.get('address', 'N/A')}")
            
            # THE DOWNLOAD BUTTON
            try:
                id_pdf = create_id_card(s)
                st.download_button(
                    label="🪪 Download Official ID Card (PDF)",
                    data=id_pdf,
                    file_name=f"OPI_ID_{s.get('roll_no')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error generating ID: {e}")
