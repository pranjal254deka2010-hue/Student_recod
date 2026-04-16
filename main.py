import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF

# --- 1. CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. ID CARD GENERATOR FUNCTION ---
def create_id_card(student):
    # Standard CR80 ID Card size in mm (85.6 x 54)
    pdf = FPDF(orientation='L', unit='mm', format=(85, 55))
    pdf.add_page()
    
    # Background Border
    pdf.set_draw_color(0, 51, 102) # Navy Blue
    pdf.rect(1, 1, 83, 53)
    
    # Header Bar
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(1, 1, 83, 12, 'F')
    
    # Header Text
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_xy(1, 2)
    pdf.cell(83, 5, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='C')
    pdf.set_font("Arial", '', 6)
    pdf.cell(83, 3, "Guwahati | Dhupdhara, Assam", ln=True, align='C')
    
    # Body Content
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)
    
    # Info Labels & Data
    def add_field(label, value, y_pos):
        pdf.set_xy(5, y_pos)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(20, 5, label, 0)
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 5, str(value).upper(), ln=True)

    add_field("NAME:", student.get('name', 'N/A'), 18)
    add_field("ROLL NO:", student.get('roll_no', 'N/A'), 23)
    add_field("COURSE:", student.get('course', 'N/A'), 28)
    add_field("SESSION:", student.get('session', 'N/A'), 33)
    add_field("B. GROUP:", student.get('blood_group', 'N/A'), 38)
    
    # Address (Smaller font for longer text)
    pdf.set_xy(5, 43)
    pdf.set_font("Arial", 'B', 7)
    pdf.cell(20, 4, "ADDRESS:", 0)
    pdf.set_font("Arial", '', 6)
    pdf.multi_cell(55, 3, student.get('address', 'N/A'))
    
    # Signature Line
    pdf.set_font("Arial", 'B', 5)
    pdf.set_xy(60, 48)
    pdf.cell(20, 3, "Principal Signature", border='T', align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 3. AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

def login(u, p):
    if u == "admin" and p == "opi2026":
        st.session_state.update({'auth': True, 'role': 'Admin'})
        return True
    try:
        res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
        if res.data:
            st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]})
            return True
    except:
        pass
    return False

# --- 4. UI ---
if not st.session_state.auth:
    st.title("🔐 OPI Student & Admin Portal")
    u = st.text_input("Username / Roll No")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        if login(u, p): st.rerun()
        else: st.error("Invalid Credentials")
else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        t1, t2 = st.tabs(["Enroll Student", "Master List"])
        
        with t1:
            with st.form("enrollment"):
                c1, c2 = st.columns(2)
                with c1:
                    r = st.text_input("Roll No")
                    n = st.text_input("Full Name")
                    crs = st.selectbox("Course", ["DMLT", "Radiology", "ECG Technician"])
                    ph = st.text_input("Phone")
                with c2:
                    bg = st.selectbox("Blood Group", ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"])
                    sess = st.text_input("Session (e.g. 2026-27)")
                    pwd = st.text_input("Set Password")
                    pic = st.text_input("Photo URL (Optional)")
                addr = st.text_area("Permanent Address")
                
                if st.form_submit_button("Save to Database"):
                    data = {"roll_no": r, "name": n, "course": crs, "phone": ph, "blood_group": bg, "session": sess, "address": addr, "password": pwd, "photo_url": pic}
                    supabase.table("students").insert(data).execute()
                    st.success(f"Student {n} enrolled successfully!")

        with t2:
            res = supabase.table("students").select("*").execute()
            st.dataframe(res.data)

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 Welcome, {s['name']}")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            if s.get('photo_url'): st.image(s['photo_url'], width=150)
            else: st.info("No Photo Available")
            
        with col2:
            st.subheader("Your Profile")
            st.write(f"**Course:** {s['course']}")
            st.write(f"**Roll No:** {s['roll_no']}")
            st.write(f"**Session:** {s['session']}")
            
            # THE DOWNLOAD BUTTON
            pdf_bytes = create_id_card(s)
            st.download_button(
                label="🪪 Download Your ID Card (PDF)",
                data=pdf_bytes,
                file_name=f"OPI_ID_{s['roll_no']}.pdf",
                mime="application/pdf"
            )
