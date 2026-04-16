import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF

# --- 1. CONNECTION ---
# Make sure these match your Streamlit Secrets exactly
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. A4 ID CARD GENERATOR ---
def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # ID Dimensions
    cw, ch = 85, 55
    ox, oy = 10, 10
    
    # Border & Header
    pdf.set_draw_color(0, 51, 102)
    pdf.set_line_width(0.5)
    pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(ox, oy, cw, 12, 'F')
    
    # Text
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_xy(ox, oy + 2)
    pdf.cell(cw, 5, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 8)
    
    # Info rows
    fields = [
        ("NAME:", student.get('name', 'N/A')),
        ("ROLL NO:", student.get('roll_no', 'N/A')),
        ("COURSE:", student.get('course', 'N/A')),
        ("SESSION:", student.get('session', 'N/A')),
        ("B. GROUP:", student.get('blood_group', 'N/A'))
    ]
    
    start_y = oy + 18
    for label, val in fields:
        pdf.set_xy(ox + 5, start_y)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(20, 5, label)
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 5, str(val).upper(), ln=True)
        start_y += 6

    return pdf.output(dest='S').encode('latin-1')

# --- 3. AUTH LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

def login_user(u, p):
    if u == "admin" and p == "opi2026":
        st.session_state.update({'auth': True, 'role': 'Admin'})
        return True
    try:
        res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
        if res.data:
            st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]})
            return True
    except: pass
    return False

# --- 4. UI ---
if not st.session_state.auth:
    st.title("🔐 OPI Portal")
    user_in = st.text_input("Username / Roll No")
    pass_in = st.text_input("Password", type="password")
    if st.button("Login"):
        if login_user(user_in, pass_in): st.rerun()
        else: st.error("Check ID/Password")
else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 Admin Control")
        t1, t2 = st.tabs(["Enroll", "Records"])
        with t1:
            with st.form("enroll_form"):
                r = st.text_input("Roll No")
                n = st.text_input("Name")
                c = st.selectbox("Course", ["DMLT", "Radiology", "ECG"])
                bg = st.selectbox("B.Group", ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"])
                sess = st.text_input("Session")
                pwd = st.text_input("Password")
                addr = st.text_area("Address")
                if st.form_submit_button("Save"):
                    d = {"roll_no": r, "name": n, "course": c, "blood_group": bg, "session": sess, "address": addr, "password": pwd}
                    supabase.table("students").insert(d).execute()
                    st.success("Done!")
        with t2:
            st.dataframe(supabase.table("students").select("*").execute().data)

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 Welcome {s['name']}")
        st.write(f"Course: {s['course']}")
        if st.download_button("🪪 Download ID Card", data=create_id_card(s), file_name="ID.pdf"):
            st.balloons()
