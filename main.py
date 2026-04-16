import streamlit as st
import pandas as pd
import os
from PIL import Image

# --- 1. CONFIG & DATA STORAGE ---
st.set_page_config(page_title="OPI Master System", layout="wide")
DATA_FILE = "opi_master_records.csv"

# Ensure all columns exist in the CSV
COLUMNS = ["Roll_No", "Name", "Course", "Phone", "Blood_Group", "Session", "Address", "Password"]

if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=COLUMNS)
    df.to_csv(DATA_FILE, index=False)

# --- 2. AUTHENTICATION STATE ---
if 'auth_state' not in st.session_state:
    st.session_state.update({'auth_state': False, 'role': None, 'user_data': None})

def login_logic(user, pw):
    if user == "admin" and pw == "opi2026":
        st.session_state.update({'auth_state': True, 'role': 'Admin', 'user_data': 'Admin'})
        return True
    
    df = pd.read_csv(DATA_FILE)
    # Ensure strings for comparison
    df['Roll_No'] = df['Roll_No'].astype(str)
    df['Password'] = df['Password'].astype(str)
    
    user_match = df[(df['Roll_No'] == user) & (df['Password'] == pw)]
    
    if not user_match.empty:
        st.session_state.update({'auth_state': True, 'role': 'Student', 'user_data': user_match.iloc[0]})
        return True
    return False

# --- 3. UI - LOGIN ---
if not st.session_state.auth_state:
    st.markdown("<h2 style='text-align: center;'>OPI Portal Login</h2>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Username (Admin or Roll No)")
            p = st.text_input("Password", type="password")
            if st.button("Enter Portal", use_container_width=True):
                if login_logic(u, p):
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")

# --- 4. UI - AUTHORIZED AREA ---
else:
    st.sidebar.title(f"Logged in as: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth_state': False, 'role': None, 'user_data': None})
        st.rerun()

    # --- ADMIN VIEW ---
    if st.session_state.role == "Admin":
        menu = st.sidebar.radio("Navigation", ["Dashboard", "Register Student", "Master Records"])
        
        if menu == "Dashboard":
            st.title("📊 OPI Master Dashboard")
            df = pd.read_csv(DATA_FILE)
            st.metric("Total Students Registered", len(df))
            st.dataframe(df, use_container_width=True)

        elif menu == "Register Student":
            st.title("📝 Detailed Student Registration")
            with st.form("reg", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    r = st.text_input("Roll Number (Unique ID)")
                    n = st.text_input("Full Student Name")
                    c = st.selectbox("Course", ["DMLT", "ICU Technology", "ECG Technician", "Radiology", "Nursing"])
                    ph = st.text_input("Phone Number")
                with col2:
                    bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
                    sess = st.text_input("Academic Session (e.g., 2026-2028)")
                    addr = st.text_area("Permanent Address")
                    p_set = st.text_input("Set Student Password")
                
                # Photo Upload (Informational for now)
                uploaded_photo = st.file_uploader("Upload Student Photo", type=['jpg', 'png', 'jpeg'])
                
                if st.form_submit_button("Save to Master Record"):
                    if r and n and p_set:
                        df = pd.read_csv(DATA_FILE)
                        if r in df['Roll_No'].astype(str).values:
                            st.error("Roll Number already exists!")
                        else:
                            new_row = pd.DataFrame([[r, n, c, ph, bg, sess, addr, p_set]], columns=COLUMNS)
                            new_row.to_csv(DATA_FILE, mode='a', header=False, index=False)
                            st.success(f"Registered {n} successfully!")
                    else:
                        st.warning("Roll No, Name, and Password are required.")

    # --- STUDENT VIEW ---
    elif st.session_state.role == "Student":
        data = st.session_state.user_data
        st.title(f"🎓 Student Portal: {data['Name']}")
        
        tab_profile, tab_docs = st.tabs(["My Profile", "Downloads"])
        
        with tab_profile:
            col_left, col_right = st.columns([1, 2])
            with col_left:
                st.image("https://via.placeholder.com/150", caption="Student Photo") # Placeholder
            with col_right:
                st.subheader("Academic & Personal Details")
                st.write(f"**Roll Number:** {data['Roll_No']}")
                st.write(f"**Course:** {data['Course']}")
                st.write(f"**Session:** {data['Session']}")
                st.write(f"**Blood Group:** {data['Blood_Group']}")
                st.write(f"**Phone:** {data['Phone']}")
                st.write(f"**Address:** {data['Address']}")
        
        with tab_docs:
            st.subheader("Available Documents")
            st.button("📄 Download ID Card")
            st.button("📝 Download Admit Card")
