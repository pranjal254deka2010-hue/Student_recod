import streamlit as st
from supabase import create_client, Client

# --- 1. CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. AUTHENTICATION ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

def login(u, p):
    if u == "admin" and p == "opi2026":
        st.session_state.update({'auth': True, 'role': 'Admin'})
        return True
    res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
    if res.data:
        st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]})
        return True
    return False

# --- 3. UI ---
if not st.session_state.auth:
    st.title("🔐 Oxford Paramedical Institute Portal")
    u = st.text_input("Roll Number / Admin")
    p = st.text_input("Password", type="password")
    if st.button("Access Portal"):
        if login(u, p): st.rerun()
        else: st.error("Login Failed")
else:
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Dashboard")
        tab1, tab2 = st.tabs(["Register Student", "Master Records"])
        
        with tab1:
            with st.form("registration", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    r = st.text_input("Roll No")
                    n = st.text_input("Full Name")
                    c = st.selectbox("Course", ["DMLT", "Radiology", "ECG Technician"])
                    ph = st.text_input("Phone Number")
                with col2:
                    bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
                    sess = st.text_input("Session (e.g. 2026)")
                    pic = st.text_input("Photo URL (Link)")
                    pwd = st.text_input("Set Password")
                
                addr = st.text_area("Address")
                
                if st.form_submit_button("Save to Cloud"):
                    data = {
                        "roll_no": r, "name": n, "course": c, 
                        "phone": ph, "blood_group": bg, 
                        "session": sess, "address": addr, 
                        "password": pwd, "photo_url": pic
                    }
                    supabase.table("students").insert(data).execute()
                    st.success(f"Successfully registered {n}!")

        with tab2:
            res = supabase.table("students").select("*").execute()
            st.dataframe(res.data)

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 Welcome, {s['name']}")
        col_a, col_b = st.columns([1, 2])
        with col_a:
            if s.get('photo_url'): st.image(s['photo_url'], width=150)
            else: st.info("No photo uploaded")
        with col_b:
            st.write(f"**Course:** {s['course']}")
            st.write(f"**Roll No:** {s['roll_no']}")
            st.write(f"**Blood Group:** {s['blood_group']}")
            st.write(f"**Address:** {s['address']}")
