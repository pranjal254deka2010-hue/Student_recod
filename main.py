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

# --- 2. ID CARD GENERATOR (A4 FORMAT WITH PHOTO) ---
def create_id_card(student):
    # A4 Page setup
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    ox, oy = 10, 10 # Position on the A4 page
    cw, ch = 85, 55 # ID Card size
    
    # Border & Navy Blue Header
    pdf.set_draw_color(0, 51, 102)
    pdf.set_line_width(0.5)
    pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(ox, oy, cw, 12, 'F')
    
    # Header Text
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_xy(ox, oy + 2)
    pdf.cell(cw, 5, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='C')
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(ox, oy + 7)
    pdf.cell(cw, 3, "GUWAHATI | DHUPDHARA, ASSAM", ln=True, align='C')
    
    # Handle Photo from Database (Base64)
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

    # Student Details
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
    
    # Address
    pdf.set_xy(ox + 4, oy + 48)
    pdf.set_font("Arial", 'B', 7)
    pdf.cell(18, 4, "ADDRESS:", 0)
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(ox + 22, oy + 48)
    pdf.multi_cell(40, 3, student.get('address', 'N/A'))

    return pdf.output(dest='S').encode('latin-1')

# --- 3. LOGIN SYSTEM ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

if not st.session_state.auth:
    st.title("🔐 OPI Master Portal")
    uid = st.text_input("Username / Roll No")
    pwd = st.text_input("Password", type="password")
    if st.button("Access System"):
        if uid == "admin" and pwd == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'})
            st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", uid).eq("password", pwd).execute()
            if res.data:
                st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]})
                st.rerun()
            else: st.error("Access Denied: Invalid Credentials")
else:
    if st.sidebar.button("Log Out"):
        st.session_state.auth = False
        st.rerun()

    # --- ADMIN VIEW ---
    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        t1, t2 = st.tabs(["Register Student", "Master Records"])
        
        with t1:
            with st.form("enroll", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    r = st.text_input("Roll Number")
                    n = st.text_input("Full Name")
                    crs = st.selectbox("Course", ["DMLT", "Radiology", "ECG Technician"])
                    ph = st.text_input("Phone Number")
                with c2:
                    bg = st.selectbox("Blood Group", ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"])
                    sess = st.text_input("Academic Session")
                    p_set = st.text_input("Set Login Password")
                
                addr = st.text_area("Permanent Address")
                up_file = st.file_uploader("Upload Student Photo (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
                
                if st.form_submit_button("Save Student to Cloud"):
                    img_b64 = ""
                    if up_file:
                        img_b64 = f"data:image/png;base64,{base64.b64encode(up_file.getvalue()).decode()}"
                    
                    payload = {
                        "roll_no": r, "name": n, "course": crs, "phone": ph,
                        "blood_group": bg, "session": sess, "address": addr,
                        "password": p_set, "photo_url": img_b64
                    }
                    supabase.table("students").insert(payload).execute()
                    st.success(f"Record created for {n}")

        with t2:
            st.subheader("📋 Complete Student Database")
            records = supabase.table("students").select("*").execute()
            if records.data:
                st.dataframe(records.data)
            else: st.info("Database is currently empty.")

    # --- STUDENT VIEW ---
    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 Student Dashboard: {s['name']}")
        
        col_img, col_data = st.columns([1, 2])
        with col_img:
            if s.get('photo_url') and len(s['photo_url']) > 100:
                st.image(s['photo_url'], width=200)
            else: st.warning("No photo found in records.")
            
        with col_data:
            st.subheader("Your Profile Information")
            st.write(f"**Roll No:** {s['roll_no']}")
            st.write(f"**Course:** {s['course']}")
            st.write(f"**Session:** {s['session']}")
            st.write(f"**Blood Group:** {s['blood_group']}")
            st.info(f"📍 **Address:** {s.get('address', 'N/A')}")
            
            # PDF Download
            pdf_data = create_id_card(s)
            st.download_button(
                label="🪪 Download Official ID Card (PDF)",
                data=pdf_data,
                file_name=f"OPI_ID_{s['roll_no']}.pdf",
                mime="application/pdf"
            )
