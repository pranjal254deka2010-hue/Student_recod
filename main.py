import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os
import datetime

# --- 1. DATABASE CONNECTION ---
# These must be set as st.secrets in your Streamlit dashboard settings
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. LAYOUT CONFIGURATION ---
st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 3. DOCUMENT GENERATORS ---

def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    ox, oy = 10, 10 # Position on the A4 page
    cw, ch = 85, 55 # ID Card size (85x55mm)
    
    # 1. Draw Navy Border & Header
    pdf.set_draw_color(0, 51, 102) # OPI Navy Blue
    pdf.set_line_width(0.5)
    pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(ox, oy, cw, 12, 'F')
    
    # 🏛️ INSTITUTION LOGO (Top Left Header)
    # The code looks for 'logo.png' in your GitHub main folder
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9) 
    
    # 🏛️ HEADER TEXT
    pdf.set_text_color(255, 255, 255) # White
    pdf.set_font("Arial", 'B', 9)
    pdf.set_xy(ox + 12, oy + 2.5) 
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='L')
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(ox + 12, oy + 7)
    pdf.cell(cw - 12, 3, "Near Daily Bazar, Dhupdhara 783123", ln=True, align='L')
    
    # 📸 STUDENT PHOTO (Processed from Database)
    photo_data = student.get('photo_url')
    if photo_data and "base64," in photo_data:
        try:
            # Decode image saved in Supabase
            header, encoded = photo_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            img = Image.open(BytesIO(img_bytes))
            
            # Temporary file save for FPDF
            temp_path = f"temp_{student['roll_no']}.png"
            img.save(temp_path)
            
            # Position Photo on Card (Right Side)
            pdf.image(temp_path, x=ox + 62, y=oy + 15, w=18, h=22)
        except:
            pdf.rect(ox + 62, oy + 15, 18, 22) # Grey placeholder on failure
    else:
        pdf.rect(ox + 62, oy + 15, 18, 22) # Grey placeholder

    # 📝 STUDENT DETAILS
    pdf.set_text_color(0, 0, 0) # Black
    
    def add_field(label, value, y_add):
        pdf.set_xy(ox + 4, oy + y_add)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(15, 5, label)
        pdf.set_font("Arial", '', 8)
        pdf.cell(40, 5, str(value if value else "N/A").upper(), ln=True)

    add_field("NAME:", student.get('name'), 18)
    add_field("ROLL NO:", student.get('roll_no'), 24)
    add_field("COURSE:", student.get('course'), 30)
    add_field("SESSION:", student.get('session'), 36)
    add_field("B. GROUP:", student.get('blood_group'), 42)
    
    # ADDRESS Handling (Wrapped Text)
    pdf.set_xy(ox + 4, oy + 47)
    pdf.set_font("Arial", 'B', 7)
    pdf.cell(15, 4, "ADDRESS:", 0)
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(ox + 20, oy + 47)
    pdf.multi_cell(42, 3, str(student.get('address', 'N/A')))
    
    return pdf.output(dest='S').encode('latin-1')

def create_fee_receipt(student_name, roll_no, payment):
    # A4 Portrait Page
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # 🏛️ INSTITUTION HEADER (Color Bar)
    pdf.set_fill_color(0, 51, 102) # Navy Blue
    pdf.rect(10, 10, 190, 32, 'F') # Large bar (32mm height)
    
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=15, y=12, h=28) # Large Logo (28mm height)
    
    pdf.set_text_color(255, 255, 255) # White
    pdf.set_xy(50, 15)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.set_x(50)
    pdf.cell(0, 6, "Near Daily Bazar, Dhupdhara 783123", ln=True)
    
    # 📄 RECEIPT INFO
    pdf.set_text_color(0, 0, 0) # Black
    pdf.set_xy(10, 50)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "OFFICIAL MONEY RECEIPT", ln=True, align='C')
    
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 8, f"Receipt No: {payment['receipt_no']}")
    pdf.cell(95, 8, f"Date: {payment['payment_date']}", ln=True, align='R')
    
    # --- 💰 PAYMENT TABLE (Complicated Monthly Logic) ---
    pdf.ln(10) # 10mm gap
    pdf.set_fill_color(240, 240, 240) # Light Grey
    pdf.set_font("Arial", 'B', 10)
    # Large width (130mm) for description, small width (60mm) for amount
    pdf.cell(130, 10, "Description / Particulars", border=1, fill=True)
    pdf.cell(60, 10, "Amount (INR)", border=1, fill=True, align='C', ln=True)
    
    pdf.set_font("Arial", '', 11)
    # multi_cell to handle 'Category - Month' on multiple lines
    pdf.cell(130, 20, f"Fees for {student_name} - {payment['fee_type']}", border=1)
    # Centered Amount with RS sign
    pdf.cell(60, 20, f"Rs. {payment['amount_paid']}/-", border=1, align='C', ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, f"Payment Mode: {payment['payment_mode']}", ln=True)
    
    # --- ✍️ AUTHORIZED SIGNATORY (Shifted and Made Bigger) ---
    # Moved Y-coordinate from 105 down to 110 to avoid overlap
    footer_y = 110
    
    # Looks for signature.png (Transparent PNG works best)
    if os.path.exists("signature.png"):
        # Position signature stamp further down (Y=115) and make it taller (30mm)
        pdf.image("signature.png", x=145, y=115, h=30) 
    
    # Authorised Signatory Text (Bottom Right)
    pdf.set_xy(140, 145); # Shifted text way below the actual signature
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(50, 5, "Authorized Signatory", border='T', align='C') # Border 'T' is the line for the signature
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. ACCESS CONTROL (Auth Logic) ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None})

# Login Page UI
if not st.session_state.auth:
    st.title("🔐 OPI Master Portal")
    col1, _ = st.columns([1, 2])
    with col1:
        u_in = st.text_input("User ID / Roll No")
        p_in = st.text_input("Password", type="password")
        if st.button("Enter System"):
            # Admin Login Check (Fixed Credentials)
            if u_in == "admin" and p_in == "opi2026":
                st.session_state.update({'auth': True, 'role': 'Admin'})
                st.rerun()
            # Student Login Check (Database Lookup)
            else:
                try:
                    res = supabase.table("students").select("*").eq("roll_no", u_in).eq("password", p_in).execute()
                    if res.data:
                        st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]})
                        st.rerun()
                    else: st.error("Login Failed: Check Credentials")
                except: st.error("Database connection issue")
else:
    # Handle Logout
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    # ==================================
    # ===       👨‍🏫 ADMIN VIEW         ===
    # ==================================
    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control Panel")
        t1, t2, t3 = st.tabs(["Enroll New Student", "Collect Fees (Monthly)", "Institutional Records"])
        
        # TAB 1: Registration Form
        with t1:
            with st.form("enroll", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    r = st.text_input("Roll No")
                    n = st.text_input("Full Name")
                    crs = st.selectbox("Course", ["DMLT", "Radiology", "ECG Technician", "Nursing Assistant"])
                    addr = st.text_area("Permanent Address")
                with c2:
                    bg = st.selectbox("Blood Group", ["A+", "B+", "O+", "AB+", "A-", "B-", "O-", "AB-"])
                    sess = st.text_input("Academic Session (e.g., 2026-27)")
                    pwd = st.text_input("Set Login Password")
                    # Special Uploader that converts file to base64 text for storage
                    up = st.file_uploader("Upload Student Photo (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
                
                if st.form_submit_button("✅ Save to Database"):
                    img_str = ""
                    if up:
                        img_str = f"data:image/png;base64,{base64.b64encode(up.getvalue()).decode()}"
                    
                    try:
                        # Insert standard details and base64 photo text
                        supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "blood_group": bg, "session": sess, "address": addr, "password": pwd, "photo_url": img_str}).execute()
                        st.success(f"Success! {n} is now enrolled.")
                    except: st.error("Could not save. Roll No might be taken.")

        # TAB 2: Fee Ledger
        with t2:
            st.subheader("💰 Monthly Tuition Ledger")
            
            try:
                # 1. Select a student from database
                students_raw = supabase.table("students").select("roll_no", "name").execute().data
                if students_raw:
                    # Create dictionary of Name(Roll) -> Roll for selection
                    s_dict = {f"{s['name']} ({s['roll_no']})": s['roll_no'] for s in students_raw}
                    sel_s = st.selectbox("Select Student", list(s_dict.keys()))
                    
                    c_x, c_y = st.columns(2)
                    with c_x:
                        # 2. Enter Amount (Monthly is usually fixed, but can vary)
                        amt = st.number_input("Amount Collected (INR)", min_value=0, step=100)
                        f_cat = st.selectbox("Fee Category", ["Monthly Tuition", "Admission Fee", "Exam Fee", "Registration"])
                    with c_y:
                        # 3. Enter the month (Tricky Part: requires monthly updates)
                        f_desc = st.text_input("Month Description (e.g. May 2026 / Installment 1)")
                        # How it was paid (ledger requirement)
                        mode = st.selectbox("Payment Mode", ["Cash at Institute", "UPI (GPay/PhonePe)", "Bank Transfer"])
                    
                    if st.button("✅ Collect & Generate Receipt"):
                        # Automatic "OPI-YYMMDD..." Receipt ID with Timestamp
                        r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                        
                        # Data structure for the Fee Ledger table
                        p_data = {
                            "roll_no": s_dict[sel_s],
                            "student_name": sel_s.split(" (")[0],
                            "amount_paid": amt,
                            "fee_type": f"{f_cat}: {f_desc}", # Combines category and specific month
                            "payment_mode": mode,
                            "receipt_no": r_id,
                            "payment_date": str(datetime.date.today()) # Today's date
                        }
                        
                        # Save transaction to cloud
                        supabase.table("fee_records").insert(p_data).execute()
                        
                        st.success(f"Fees Recorded for {p_data['fee_type']}. Receipt generated!")
                        
                        # Generate PDF and provide download button for Admin
                        ledger_pdf = create_fee_receipt(p_data['student_name'], p_data['roll_no'], p_data)
                        st.download_button("📩 Download & Print Receipt", ledger_pdf, f"Receipt_{r_id}.pdf", key=f"rec_down_{r_id}")
            except: st.error("Could not load ledger.")

        # TAB 3: Complete Database View (Tricky Part: shows all columns)
        with t3:
            st.subheader("📋 OPI Complete Records")
            try:
                # Fetching * selects all columns
                records_res = supabase.table("students").select("*").execute()
                if records_res.data:
                    st.dataframe(records_res.data) # Streamlit automatically renders interactive table
                else: st.info("No records found.")
            except: st.error("Could not fetch records.")

    # ==================================
    # ===      🧑‍🎓 STUDENT VIEW       ===
    # ==================================
    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 OPI Portal: {s['name']}")
        
        c_left, c_right = st.columns([1, 2])
        
        # Left Side: Photo & ID Card
        with c_left:
            # Check base64 photo text exists and is long enough
            if s.get('photo_url') and len(str(s['photo_url'])) > 100:
                st.image(s['photo_url'], width=180)
            else:
                st.warning("Photo not found in record.")
            
            # THE DOWNLOAD ID CARD BUTTON
            try:
                # Generate ID Card PDF data
                pdf_bin = create_id_card(s)
                
                # Tricky Part: Downloaded file sits in downloads folder
                st.download_button(
                    label="🪪 Download OPI ID Card (PDF)", 
                    data=pdf_bin, 
                    file_name=f"OPI_ID_{s['roll_no']}.pdf", 
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error generating ID: {e}")
            
        # Right Side: Profile & Payment History
        with c_right:
            st.subheader("OPI Institutional Profile")
            st.write(f"**Roll No:** {s.get('roll_no')}")
            st.write(f"**Course:** {s.get('course')}")
            st.write(f"**Session:** {s.get('session')}")
            # Use get for safety if Address isn't required in Database
            st.info(f"📍 **Permanent Address:** {s.get('address', 'N/A')}")
            
            st.subheader("💳 Digital Ledger: Payment History")
            try:
                # Fetch only this student's fee records from ledger
                ledger_res = supabase.table("fee_records").select("*").eq("roll_no", s['roll_no']).execute()
                
                if ledger_res.data:
                    # Sort history by date (newest first)
                    ledger_res.data.sort(key=lambda x: x['payment_date'], reverse=True)
                    
                    # Display each payment receipt with its own download button
                    # The Tricky Part: Generating multiple receipts dynamically
                    for payment in ledger_res.data:
                        col_p, col_d = st.columns([3, 1])
                        # Ledger Info line
                        col_p.write(f"**{payment['fee_type']}** | ₹{payment['amount_paid']}/- paid via {payment['payment_mode']} on {payment['payment_date']}")
                        
                        # Independent download button for this specific payment
                        # Use unique key (receipt_no) so buttons don't conflict
                        col_d.download_button(
                            label="📄 PDF",
                            data=create_fee_receipt(s['name'], s['roll_no'], payment),
                            file_name=f"Rec_{payment['receipt_no']}.pdf",
                            mime="application/pdf",
                            key=payment['receipt_no']
                        )
                else:
                    st.success("You are all clear! No payment records found.")
            except:
                st.error("Could not fetch payment history.")
