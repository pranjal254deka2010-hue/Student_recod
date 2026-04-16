import streamlit as st
import pandas as pd
import os

# --- 1. CONFIG & DATA STORAGE ---
st.set_page_config(page_title="OPI Master System", layout="wide")
DATA_FILE = "opi_master_records.csv"

if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Roll_No", "Name", "Course", "Phone", "Blood_Group", "Session", "Password"])
    df.to_csv(DATA_FILE, index=False)

# --- 2. AUTHENTICATION STATE ---
if 'auth_state' not in st.session_state:
    st.session_state.update({'auth_state': False, 'role': None, 'user_data': None})

def login_logic(user, pw):
    # Check Admin first
    if user == "admin" and pw == "opi2026":
        st.session_state.update({'auth_state': True, 'role': 'Admin', 'user_data': 'Admin'})
        return True
    
    # Check Student Records
    df = pd.read_csv(DATA_FILE)
    # Filter by Roll_No and Password
    user_match = df[(df['Roll_No'] == user) & (df['Password'].astype(str) == pw)]
    
    if not user_match.empty:
        st.session_state.update({'auth_state': True, 'role': 'Student', 'user_data': user_match.iloc[0]})
        return True
    return False

# --- 3. UI - LOGIN ---
if not st.session_state.auth_state:
    st.markdown("<h2 style='text-align: center;'>OPI Portal Login</h2>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Username (Admin or Roll No)")
        p = st.text_input("Password", type="password")
        if st.button("Enter Portal"):
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
            st.dataframe(df)

        elif menu == "Register Student":
            st.title("📝 New Registration")
            with st.form("reg"):
                r = st.text_input("Roll Number")
                n = st.text_input("Full Name")
                c = st.selectbox("Course", ["DMLT", "ICU", "ECG"])
                p_set = st.text_input("Set Student Password")
                if st.form_submit_button("Save Student"):
                    df = pd.read_csv(DATA_FILE)
                    new_row = pd.DataFrame([[r, n, c, "N/A", "N/A", "2026", p_set]], columns=df.columns)
                    new_row.to_csv(DATA_FILE, mode='a', header=False, index=False)
                    st.success("Student Added!")

    # --- STUDENT VIEW ---
    elif st.session_state.role == "Student":
        data = st.session_state.user_data
        st.title(f"🎓 Welcome, {data['Name']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Your Profile")
            st.write(f"**Roll Number:** {data['Roll_No']}")
            st.write(f"**Course:** {data['Course']}")
            st.write(f"**Session:** {data['Session']}")
        
        with col2:
            st.subheader("Your Documents")
            st.info("Admit Card: Pending Release")
            st.info("ID Card: Ready for Collection")
