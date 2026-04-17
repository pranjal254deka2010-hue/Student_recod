import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os
import datetime
import urllib.parse

# --- 1. CONFIGURATION & DATABASE ---
st.set_page_config(page_title="OPI Master Portal", layout="wide", page_icon="🏥")

# Custom CSS for a professional look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #003366; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; background-color: #28a745; color: white; }
    </style>
    """, unsafe_byte_尊=True)

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. CONSTANTS ---
COURSES = [
    "DMLT First Year", "DMLT Second Year", 
    "ICU Technician", "First AID and Patient Care", 
    "X Ray Technology"
]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "N/A"]

# --- 3. CORE HELPERS ---
def clean_pdf_text(text):
    if not text: return "N/A"
    return str(text).replace("₹", "Rs. ").encode('ascii', 'ignore').decode('ascii')

# --- 4. PROFESSIONAL PDF ENGINE ---

def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    # ID Card Dimensions
    ox, oy, cw, ch = 10, 10, 85, 55
    pdf.set_draw_color(0, 51, 102); pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102); pdf.rect(ox, oy, cw, 12, 'F')
    
    if os.path.exists("logo.png"): pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 9); pdf.set_xy(ox + 12, oy + 4)
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='L')
    
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try: pdf.image(BytesIO(base64.b64decode(photo_data.split(",")[1])), x=ox + 62, y=oy + 15, w=18, h=22)
        except: pdf.rect(ox + 62, oy + 15, 18, 22)
        
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 8)
    fields = [
        ("NAME", student.get('name')), 
        ("ROLL NO", student.get('roll_no')), 
        ("COURSE", student.get('course')),
        ("BLOOD GP", student.get('blood_group', 'N/A'))
    ]
    y = oy + 16
    for lbl, val in fields:
        pdf.set_xy(ox + 4, y); pdf.cell(20, 5, f"{lbl}:"); pdf.set_font("Arial", '', 8)
        pdf.cell(35, 5, clean_pdf_text(val).upper(), ln=True); y += 5.5; pdf.set_font("Arial", 'B', 8)
    
    pdf.set_xy(ox + 4, oy + 46); pdf.set_font("Arial", 'B', 7); pdf.cell(10, 4, "ADDR:")
    pdf.set_font("Arial", '', 6); pdf.multi_cell(48, 3, clean_pdf_text(student.get('address', 'N/A')))
    return pdf.output(dest='S').encode('latin-1', 'replace')

def create_admit_card(student, exam):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    pdf.set_draw_color(0, 51, 102); pdf.set_line_width(0.5); pdf.rect(10, 10, 190, 165) 
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 28, 'F')
    
    if os.path.exists("logo.png"): pdf.image("logo.png", x=15, y=12, h=22)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 16); pdf.set_xy(45, 14)
    pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE")
    pdf.set_font("Arial", '', 10); pdf.set_xy(45, 22); pdf.cell(0, 5, "AN AKANKSHI FOUNDATION TRUST INITIATIVE")
    
    pdf.set_text_color(0, 0, 0); pdf.set_xy(10, 45); pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, clean_pdf_text(exam['exam_name']).upper(), ln=True, align='C')
    
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try: pdf.image(BytesIO(base64.b64decode(photo_data.split(",")[1])), x=155, y=58, w=35, h=42)
        except: pdf.rect(155, 58, 35, 42)
    
    pdf.set_font("Arial", 'B', 11); pdf.set_xy(15, 60)
    pdf.cell(40, 8, "Candidate Name:"); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, clean_pdf_text(student['name']), ln=True)
    pdf.set_font("Arial", 'B', 11); pdf.set_x(15); pdf.cell(40, 8, "Roll Number:"); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, str(student['roll_no']), ln=True)
    pdf.set_font("Arial", 'B', 11); pdf.set_x(15); pdf.cell(40, 8, "Course/Year:"); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, str(student['course']), ln=True)
    pdf.set_font("Arial", 'B', 11); pdf.set_x(15); pdf.cell(40, 8, "Blood Group:"); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, str(student.get('blood_group', 'N/A')), ln=True)

    pdf.set_xy(15, 105); pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(240, 240, 240)
    pdf.cell(110, 10, "Subject / Paper", border=1, fill=True, align='C'); pdf.cell(50, 10, "Date", border=1, fill=True, align='C', ln=True)
    pdf.set_font("Arial", '', 10)
    for line in exam.get('subject_details', "").split("\n"):
        if ":" in line:
            p = line.split(":", 1); pdf.set_x(15); pdf.cell(110, 9, clean_pdf_text(p[0].strip()), border=1)
            pdf.cell(50, 9, clean_pdf_text(p[1].strip()), border=1, align='C', ln=True)
    
    pdf.set_xy(15, 150); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 5, f"Reporting: {clean_pdf_text(exam['reporting_time'])}")
    pdf.set_xy(15, 156); pdf.cell(0, 5, f"Venue: {clean_pdf_text(exam['venue'])}")
    
    if os.path.exists("signature.png"): pdf.image("signature.png", x=155, y=148, h=15)
    pdf.set_xy(155, 166); pdf.set_font("Arial", 'B', 8); pdf.cell(35, 5, "Authorized Sign", border='T', align='C')
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 5. AUTH & NAVIGATION ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None, 'edit_id': None})

if not st.session_state.auth:
    st.title("🏥 OPI Master Management Portal")
    col_l, col_r = st.columns(2)
    u = col_l.text_input("Username / Roll No")
    p = col_l.text_input("Password", type="password")
    if col_l.button("Login"):
        if u == "admin" and p == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'}); st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
            if res.data: st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]}); st.rerun()
            else: st.error("Invalid Credentials")
else:
    st.sidebar.title(f"Logged in: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 Administrative Dashboard")
        t = st.tabs(["Enrollment", "Finance", "Examinations", "Records"])
        
        with t[0]:
            with st.form("enroll_pro"):
                c1, c2 = st.columns(2)
                r_no = c1.text_input("Enrollment ID (Roll No)")
                s_name = c1.text_input("Student Full Name")
                s_course = c1.selectbox("Course / Year", COURSES)
                s_bg = c1.selectbox("Blood Group", BLOOD_GROUPS)
                s_ph = c1.text_input("WhatsApp Number")
                s_fee = c2.number_input("Standard Monthly Fee", value=2500)
                s_pw = c2.text_input("Portal Password")
                s_date = c2.date_input("Enrollment Date")
                s_addr = st.text_area("Permanent Address")
                s_up = st.file_uploader("Candidate Photograph", type=['jpg', 'png'])
                if st.form_submit_button("Complete Enrollment"):
                    img = f"data:image/png;base64,{base64.b64encode(s_up.getvalue()).decode()}" if s_up else ""
                    supabase.table("students").insert({"roll_no": r_no, "name": s_name, "course": s_course, "blood_group": s_bg, "password": s_pw, "photo_url": img, "is_active": True, "monthly_fee_amount": s_fee, "address": s_addr, "phone": s_ph, "joining_date": str(s_date), "exam_cleared": False}).execute()
                    st.success("Candidate Registered Successfully!")

        with t[1]:
            st.subheader("💰 Institutional Fee Ledger")
            raw_s = supabase.table("students").select("*").eq("is_active", True).execute().data
            if raw_s:
                s_lookup = {f"{x['name']} ({x['roll_no']})": x for x in raw_s}
                target = s_lookup[st.selectbox("Select Candidate", list(s_lookup.keys()))]
                f_type = st.selectbox("Transaction Category", ["Monthly Tuition", "Admission Fee", "Registration Fee", "Exam Fee"])
                ca, cb = st.columns(2)
                amt = ca.number_input("Amount (INR)", value=int(target.get('monthly_fee_amount', 2500)) if f_type == "Monthly Tuition" else 0)
                note = cb.text_input("Period / Description (e.g. May 2026)")
                if st.button("Generate Official Receipt"):
                    r_no = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    p_rec = {"roll_no": target['roll_no'], "student_name": target['name'], "amount_paid": amt, "fee_type": f"{f_type} - {note}", "receipt_no": r_no, "payment_date": str(datetime.date.today()), "payment_mode": "Office Record"}
                    supabase.table("fee_records").insert(p_rec).execute()
                    st.download_button("📩 Download PDF Receipt", create_admit_card(target, {"exam_name": "Receipt Check", "subject_details": ""}), f"Rec_{r_no}.pdf")

        with t[2]:
            st.subheader("📝 Exam Scheduling")
            with st.form("exam_pro"):
                ex_crs = st.selectbox("Target Course", COURSES)
                ex_nm = st.text_input("Examination Name")
                ex_subs = st.text_area("Schedule (Format: Subject : Date)")
                cl1, cl2 = st.columns(2)
                ex_tm, ex_vn = cl1.text_input("Reporting Time"), cl2.text_input("Venue")
                if st.form_submit_button("Publish Exam Schedule"):
                    supabase.table("exam_schedules").insert({"course": ex_crs, "exam_name": ex_nm, "subject_details": ex_subs, "reporting_time": ex_tm, "venue": ex_vn}).execute()
                    st.success("Exam Published!")
            
            st.divider()
            exs = supabase.table("exam_schedules").select("*").order('id', desc=True).execute().data
            for e in exs:
                c_i, c_d = st.columns([4, 1])
                c_i.write(f"📅 **{e['exam_name']}** - {e['course']}")
                if c_d.button("Delete Schedule", key=f"d_e_{e['id']}"):
                    supabase.table("exam_schedules").delete().eq("id", e['id']).execute(); st.rerun()

        with t[3]:
            st.subheader("📋 Master Student Records")
            stu_data = supabase.table("students").select("*").execute().data
            fee_data = supabase.table("fee_records").select("*").execute().data
            
            # Defaulter Check
            with st.expander("🔍 View Defaulter List"):
                for s in stu_data:
                    j = datetime.datetime.strptime(s['joining_date'], '%Y-%m-%d').date()
                    due = (datetime.date.today().year - j.year) * 12 + datetime.date.today().month - j.month + 1
                    paid = len([f for f in fee_data if str(f['roll_no']) == str(s['roll_no']) and "Monthly Tuition" in f['fee_type']])
                    diff = due - paid
                    if diff > 0:
                        st.warning(f"⚠️ {s['name']} (ID: {s['roll_no']}) - {diff} Months Pending")
            
            st.divider()
            if st.session_state.edit_id:
                curr = next((s for s in stu_data if str(s['roll_no']) == str(st.session_state.edit_id)), None)
                if curr:
                    with st.form("edit_pro"):
                        st.info(f"Modifying Record: {curr['name']}")
                        en_n = st.text_input("Name", value=curr['name'])
                        en_c = st.selectbox("Course", COURSES, index=COURSES.index(curr['course']) if curr['course'] in COURSES else 0)
                        en_bg = st.selectbox("Blood Group", BLOOD_GROUPS, index=BLOOD_GROUPS.index(curr.get('blood_group', 'N/A')))
                        en_jd = st.date_input("Joining Date", value=datetime.datetime.strptime(curr['joining_date'], '%Y-%m-%d').date())
                        if st.form_submit_button("Update Record"):
                            supabase.table("students").update({"name": en_n, "course": en_c, "blood_group": en_bg, "joining_date": str(en_jd)}).eq("roll_no", curr['roll_no']).execute()
                            st.session_state.edit_id = None; st.rerun()
                    if st.button("Cancel"): st.session_state.edit_id = None; st.rerun()
            else:
                for row in stu_data:
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.write(f"**{row['name']}**")
                    clr = "🟢 Shared" if row['exam_cleared'] else "🔴 Locked"
                    if c2.button(clr, key=f"cl_{row['roll_no']}"):
                        supabase.table("students").update({"exam_cleared": not row['exam_cleared']}).eq("roll_no", row['roll_no']).execute(); st.rerun()
                    if c3.button("Edit ⚙️", key=f"ed_{row['roll_no']}"):
                        st.session_state.edit_id = row['roll_no']; st.rerun()
                    if c4.button("Delete 🗑️", key=f"dl_{row['roll_no']}"):
                        supabase.table("students").delete().eq("roll_no", row['roll_no']).execute(); st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 Welcome, {s['name']}")
        col1, col2 = st.columns([1, 2])
        with col1:
            if s.get('photo_url'): st.image(s['photo_url'], width=180)
            st.download_button("🪪 Download Official ID", create_id_card(s), f"ID_{s['roll_no']}.pdf")
            st.divider()
            exs = supabase.table("exam_schedules").select("*").eq("course", s['course']).order('id', desc=True).execute().data
            if exs:
                e = exs[0]
                if s.get('exam_cleared', False):
                    st.success(f"Exam Notice: {e['exam_name']}")
                    st.download_button("📄 Get Admit Card", create_admit_card(s, e), f"Admit_{s['roll_no']}.pdf")
                else: st.error("🔒 Examination access restricted. Contact Office.")
        with col2:
            st.subheader("📊 Payment History")
            h = supabase.table("fee_records").select("*").eq("roll_no", str(s['roll_no'])).execute().data
            if h:
                for p in h:
                    st.write(f"✅ **{p['fee_type']}** | INR {p['amount_paid']} | {p['payment_date']}")
            else: st.info("No transaction records found.")
