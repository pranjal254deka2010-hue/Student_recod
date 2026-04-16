import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIG & CONNECTION ---
st.set_page_config(page_title="OPI Master System", layout="wide")

# This connects to the URL we will put in 'Secrets'
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. AUTHENTICATION STATE ---
if 'auth_state' not in st.session_state:
    st.session_state.update({'auth_state': False, 'role': None, 'user_data': None})

def login_logic(user, pw):
    if user == "admin" and pw == "opi2026":
        st.session_state.update({'auth_state': True, 'role': 'Admin', 'user_data': 'Admin'})
        return True
    
    # Read from Google Sheets
    df = conn.read(worksheet="students")
    df['Roll_No'] = df['Roll_No'].astype(str)
    df['Password'] = df['Password'].astype(str)
    
    user_match = df[(df['Roll_No'] == user) & (df['Password'] == pw)]
    if not user_match.empty:
        st.session_state.update({'auth_state': True, 'role': 'Student', 'user_data': user_match.iloc[0]})
        return True
    return False

# --- 3. UI - LOGIN ---
if not st.session_state.auth_state:
    st.markdown("<h2 style='text-align: center;'>OPI Master Portal</h2>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Access System"):
            if login_logic(u, p):
                st.rerun()
            else:
                st.error("Invalid Login")

# --- 4. UI - AUTHORIZED AREA ---
else:
    st.sidebar.title(f"Role: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.session_state.update({'auth_state': False, 'role': None, 'user_data': None})
        st.rerun()

    if st.session_state.role == "Admin":
        menu = st.sidebar.radio("Navigation", ["Registration", "Records"])
        
        if menu == "Registration":
            st.title("📝 Permanent Registration")
            with st.form("reg"):
                # Form fields
                r = st.text_input("Roll Number")
                n = st.text_input("Full Name")
                c = st.selectbox("Course", ["DMLT", "ICU", "ECG"])
                ph = st.text_input("Phone")
                bg = st.selectbox("Blood Group", ["A+", "B+", "O+", "AB+"])
                sess = st.text_input("Session")
                addr = st.text_area("Address")
                p_set = st.text_input("Password")
                
                if st.form_submit_button("Save to Google Drive"):
                    # Fetch current data
                    df = conn.read(worksheet="students")
                    new_data = pd.DataFrame([[r, n, c, ph, bg, sess, addr, p_set]], columns=df.columns)
                    updated_df = pd.concat([df, new_data], ignore_index=True)
                    
                    # Push back to Google Sheets
                    conn.update(worksheet="students", data=updated_df)
                    st.success("Saved permanently!")

        elif menu == "Records":
            st.title("📋 Live Master List")
            df = conn.read(worksheet="students")
            st.dataframe(df)

    elif st.session_state.role == "Student":
        data = st.session_state.user_data
        st.title(f"🎓 Student Dashboard: {data['Name']}")
        st.write(f"Roll: {data['Roll_No']} | Course: {data['Course']}")
