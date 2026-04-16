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
    
    # Check Supabase Table
    res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
    if res.data:
        st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]})
        return True
    return False

# --- 3. UI ---
if not st.session_state.auth:
    st.title("🔐 OPI Portal Login")
    u = st.text_input("Roll Number / Admin")
    p = st.text_input("Password", type="password")
    if st.button("Access Portal"):
        if login(u, p): st.rerun()
        else: st.error("Login Failed")
else:
    st.sidebar.title(f"Role: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 Admin Dashboard")
        tab1, tab2 = st.tabs(["Register Student", "Master Records"])
        
        with tab1:
            with st.form("reg"):
                r = st.text_input("Roll No")
                n = st.text_input("Full Name")
                c = st.selectbox("Course", ["DMLT", "Radiology", "ECG"])
                ph = st.text_input("Phone")
                pwd = st.text_input("Set Password")
                if st.form_submit_button("Save to Cloud"):
                    data = {"roll_no": r, "name": n, "course": c, "phone": ph, "password": pwd}
                    supabase.table("students").insert(data).execute()
                    st.success("Student Saved Permanently!")
        
        with tab2:
            res = supabase.table("students").select("*").execute()
            if res.data:
                st.dataframe(res.data)
            else:
                st.write("No students registered yet.")

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 Welcome, {s['name']}")
        st.subheader("Your Academic Record")
        st.write(f"**Course:** {s['course']}")
        st.write(f"**Roll No:** {s['roll_no']}")
        st.info("Download buttons for ID cards will appear here soon.")
