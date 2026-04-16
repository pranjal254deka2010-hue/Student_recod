    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Dashboard")
        tab1, tab2 = st.tabs(["Register New Student", "Master Records"])
        
        with tab1:
            st.subheader("Student Enrollment Form")
            with st.form("registration_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    r = st.text_input("Roll Number (Unique ID)")
                    n = st.text_input("Full Name")
                    c = st.selectbox("Course", ["DMLT", "Radiology", "ECG Technician", "Nursing", "Other"])
                    ph = st.text_input("Mobile Number")
                
                with col2:
                    bg = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
                    sess = st.text_input("Academic Session (e.g., 2026-27)")
                    pic = st.text_input("Photo URL (Link to image)")
                    pwd = st.text_input("Set Student Password", type="password")
                
                addr = st.text_area("Permanent Address")
                
                if st.form_submit_button("Confirm Registration"):
                    if r and n and pwd:
                        # Ensure column names match your Supabase SQL exactly
                        data = {
                            "roll_no": r, 
                            "name": n, 
                            "course": c, 
                            "phone": ph, 
                            "blood_group": bg, 
                            "session": sess, 
                            "address": addr, 
                            "password": pwd,
                            "photo_url": pic # Ensure you added this column to Supabase
                        }
                        try:
                            supabase.table("students").insert(data).execute()
                            st.success(f"Successfully registered {n}!")
                        except Exception as e:
                            st.error(f"Database Error: {e}")
                    else:
                        st.warning("Please fill in Roll No, Name, and Password.")
