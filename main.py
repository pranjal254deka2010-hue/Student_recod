import streamlit as st
import pandas as pd
import os

# --- 1. CONFIG & DATA STORAGE ---
st.set_page_config(page_title="OPI Master System", layout="wide")
DATA_FILE = "opi_master_records.csv"

# Initialize the CSV file if it doesn't exist
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["Roll_No", "Name", "Course", "Phone", "Blood_Group", "Session", "Password"])
    df.to_csv(DATA_FILE, index=False)

# --- 2. AUTHENTICATION ---
if 'auth_state' not in st.session_state:
    st.session_state.auth_state = False

def login():
    st.markdown("<h2 style='text-align: center;'>OPI Admin Control</h2>", unsafe_allow_html=True)
    with st.container():
        user = st.text_input("Admin Username")
        pw = st.text_input("Password", type="password")
        if st.button("Login to Master System"):
            if user == "admin" and pw == "opi2026": # You can change this
                st.session_state.auth_state = True
                st.rerun()
            else:
                st.error("Access Denied")

# --- 3. MAIN APPLICATION ---
if not st.session_state.auth_state:
    login()
else:
    st.sidebar.title("OPI Navigation")
    menu = st.sidebar.radio("Go To", ["Dashboard", "Register New Student", "View Records", "Logout"])

    if menu == "Logout":
        st.session_state.auth_state = False
        st.rerun()

    elif menu == "Dashboard":
        st.title("📊 OPI Master Dashboard")
        df = pd.read_csv(DATA_FILE)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Students", len(df))
        col2.metric("DMLT Students", len(df[df['Course'] == 'DMLT']))
        col3.metric("New Admissions (2026)", len(df[df['Session'].str.contains('2026', na=False)]))

    elif menu == "Register New Student":
        st.title("📝 Student Registration")
        with st.form("registration_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                roll = st.text_input("Roll Number (Unique ID)")
                name = st.text_input("Full Name")
                course = st.selectbox("Course", ["DMLT", "ICU Technology", "ECG Technician", "Nursing"])
            with col_b:
                phone = st.text_input("Phone Number")
                bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
                sess = st.text_input("Academic Session (e.g., 2026-2028)")
            
            # This password will be used by the student for their portal later
            std_pass = st.text_input("Set Student Portal Password", type="password")
            
            submit = st.form_submit_button("Save to Master Record")
            
            if submit:
                if roll and name and std_pass:
                    # Load existing data
                    df = pd.read_csv(DATA_FILE)
                    
                    # Check if Roll No exists
                    if roll in df['Roll_No'].values:
                        st.error(f"Error: Roll Number {roll} is already registered!")
                    else:
                        # Append new data
                        new_entry = pd.DataFrame([[roll, name, course, phone, bg, sess, std_pass]], 
                                                 columns=df.columns)
                        new_entry.to_csv(DATA_FILE, mode='a', header=False, index=False)
                        st.success(f"Successfully Registered: {name}")
                else:
                    st.warning("Please fill Roll No, Name, and Password.")

    elif menu == "View Records":
        st.title("📋 Master Student List")
        df = pd.read_csv(DATA_FILE)
        
        # Search Bar
        search = st.text_input("Search by Name or Roll No")
        if search:
            df = df[df['Name'].str.contains(search, case=False) | df['Roll_No'].str.contains(search, case=False)]
            
        st.dataframe(df, use_container_width=True)
        
        # Download Option
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Export Master List (CSV)", csv, "OPI_Master_Records.csv", "text/csv")
