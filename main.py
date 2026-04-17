import streamlit as st
from supabase import create_client, Client
from fpdf import FPDF
import base64
from io import BytesIO
from PIL import Image
import os
import datetime
import urllib.parse

# --- 1. DATABASE CONNECTION ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="OPI Master Portal", layout="wide")

# --- 2. HELPERS & CONSTANTS ---
COURSES = [
    "DMLT First Year", "DMLT Second Year", 
    "ICU Technician", "First AID and Patient Care", 
    "X Ray Technology"
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"]

def clean_pdf_text(text):
    if not text: return ""
    return str(text).replace("₹", "Rs. ").encode('ascii', 'ignore').decode('ascii')

# --- 3. PDF GENERATORS ---

def create_id_card(student):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
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
        ("NAME:", student.get('name')), 
        ("ROLL NO:", student.get('roll_no')), 
        ("COURSE:", student.get('course')),
        ("BLOOD GP:", student.get('blood_group', 'N/A')) # BLOOD GROUP ADDED HERE
    ]
    y = oy + 15
    for lbl, val in fields:
        pdf.set_xy(ox + 4, y); pdf.cell(18, 5, lbl); pdf.set_font("Arial", '', 8)
        pdf.cell(40, 5, clean_pdf_text(val).upper(), ln=True); y += 5.5; pdf.set_font("Arial", 'B', 8)
    
    pdf.set_xy(ox + 4, oy + 47); pdf.set_font("Arial", 'B', 7); pdf.cell(15, 4, "ADDR:")
    pdf.set_font("Arial", '', 6); pdf.multi_cell(45, 3, clean_pdf_text(student.get('address', 'N/A')))
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

def create_admit_card(student, exam):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    pdf.set_draw_color(0, 51, 102); pdf.rect(10, 10, 190, 160) 
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 25, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=13, y=12, h=20)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 15); pdf.set_xy(40, 13); pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE")
    pdf.set_font("Arial", 'B', 10); pdf.set_xy(40, 21); pdf.cell(0, 5, "OFFICIAL EXAMINATION ADMIT CARD")
    
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 11); pdf.set_xy(15, 42); pdf.cell(0, 8, f"EXAM: {clean_pdf_text(exam['exam_name']).upper()}")
    
    photo_data = student.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try: pdf.image(BytesIO(base64.b64decode(photo_data.split(",")[1])), x=150, y=42, w=40, h=45)
        except: pdf.rect(150, 42, 40, 45)
    
    pdf.set_font("Arial", '', 11)
    pdf.set_xy(15, 52); pdf.cell(0, 8, f"Candidate: {clean_pdf_text(student['name'])}")
    pdf.set_xy(15, 60); pdf.cell(0, 8, f"Roll No: {student['roll_no']}")
    pdf.set_xy(15, 68); pdf.cell(0, 8, f"Course: {student['course']}")
    pdf.set_xy(15, 76); pdf.cell(0, 8, f"Blood Group: {student.get('blood_group', 'N/A')}")

    # --- FIXED SUBJECT TABLE LOGIC ---
    pdf.set_xy(15, 95); pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 10, "Subject Name", border=1, fill=True, align='C'); pdf.cell(45, 10, "Date", border=1, fill=True, align='C', ln=True)
    pdf.set_font("Arial", '', 10)
    
    details = exam.get('subject_details', "")
    if details:
        for line in details.split("\n"):
            if ":" in line:
                p = line.split(":", 1); pdf.set_x(15); pdf.cell(100, 9, clean_pdf_text(p[0].strip()), border=1); pdf.cell(45, 9, clean_pdf_text(p[1].strip()), border=1, align='C', ln=True)
    
    pdf.ln(10); pdf.set_x(15); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, f"Reporting Time: {clean_pdf_text(exam['reporting_time'])}"); pdf.ln(6); pdf.set_x(15); pdf.cell(0, 7, f"Venue: {clean_pdf_text(exam['venue'])}")
    if os.path.exists("signature.png"): pdf.image("signature.png", x=150, y=145, h=15)
    pdf.set_xy(150, 162); pdf.set_font("Arial", 'B', 8); pdf.cell(40, 5, "Controller of Exams", border='T', align='C')
    return pdf.output(dest='S').encode('latin-1', 'replace')

def create_fee_receipt(student_name, roll_no, payment):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 32, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=15, y=12, h=28)
    pdf.set_text_color(255, 255, 255); pdf.set_xy(50, 15); pdf.set_font("Arial", 'B', 18); pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    pdf.set_font("Arial", '', 11); pdf.set_x(50); pdf.cell(0, 6, "Near Daily Bazar, Dhupdhara 783123", ln=True)
    pdf.set_text_color(0, 0, 0); pdf.set_xy(10, 50); pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "OFFICIAL MONEY RECEIPT", ln=True, align='C')
    pdf.set_font("Arial", '', 11); pdf.cell(95, 8, f"Receipt: {payment['receipt_no']}"); pdf.cell(95, 8, f"Date: {payment['payment_date']}", ln=True, align='R')
    pdf.ln(10); pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", 'B', 10); pdf.cell(130, 10, "Description", border=1, fill=True); pdf.cell(60, 10, "Amount (INR)", border=1, fill=True, align='C', ln=True)
    pdf.set_font("Arial", '', 11); pdf.cell(130, 20, f"Fees for {clean_pdf_text(student_name)} - {clean_pdf_text(payment['fee_type'])}", border=1); pdf.cell(60, 20, f"Rs. {payment['amount_paid']}/-", border=1, align='C', ln=True)
    if os.path.exists("signature.png"): pdf.image("signature.png", x=145, y=105, h=30)
    pdf.set_xy(140, 140); pdf.set_font("Arial", 'B', 10); pdf.cell(50, 5, "Authorized Signatory", border='T', align='C')
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 4. APP LOGIC ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None, 'edit_id': None})

if not st.session_state.auth:
    st.title("🔐 OPI Master Portal")
    u, p = st.text_input("User ID"), st.text_input("Password", type="password")
    if st.button("Access"):
        if u == "admin" and p == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'}); st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
            if res.data: st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]}); st.rerun()
            else: st.error("Login Failed")
else:
    if st.sidebar.button("Logout"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

    if st.session_state.role == "Admin":
        st.title("👨‍🏫 OPI Admin Control")
        tabs = st.tabs(["Enroll Student", "Fee Collection", "Exam Management", "Records & Defaulters"])
        
        with tabs[0]: # ENROLLMENT
            with st.form("enroll_form"):
                c1, c2 = st.columns(2)
                r, n = c1.text_input("Roll No"), c1.text_input("Name")
                crs = c1.selectbox("Course", COURSES)
                bg = c1.selectbox("Blood Group", BLOOD_GROUPS) # ADDED HERE
                ph, m_fee, pw = c1.text_input("WhatsApp"), c2.number_input("Monthly Fee", value=2500), c2.text_input("Password")
                j_dt, addr = c2.date_input("Joining Date", datetime.date.today()), st.text_area("Address")
                up = st.file_uploader("Upload Photo", type=['jpg', 'png'])
                if st.form_submit_button("Save"):
                    img = f"data:image/png;base64,{base64.b64encode(up.getvalue()).decode()}" if up else ""
                    supabase.table("students").insert({"roll_no": r, "name": n, "course": crs, "blood_group": bg, "password": pw, "photo_url": img, "is_active": True, "monthly_fee_amount": m_fee, "address": addr, "phone": ph, "joining_date": str(j_dt), "exam_cleared": False}).execute()
                    st.success("Enrolled!"); st.rerun()

        with tabs[1]: # FEE COLLECTION
            st.subheader("💰 Smart Fee Ledger")
            students = supabase.table("students").select("*").eq("is_active", True).execute().data
            if students:
                s_dict = {f"{s['name']} (ID: {s['roll_no']})": s for s in students}
                sel_s = s_dict[st.selectbox("Select Student", list(s_dict.keys()), key="fee_sel")]
                f_cat = st.selectbox("Fee Type", ["Monthly Tuition", "Admission Fee", "Exam Fee"])
                c_a, c_b = st.columns(2)
                base = c_a.number_input("Amount", value=int(sel_s.get('monthly_fee_amount', 2500)) if f_cat == "Monthly Tuition" else 0)
                f_desc, mode = c_b.text_input("Notes"), c_b.selectbox("Mode", ["Cash", "UPI"])
                if st.button("Generate Receipt"):
                    r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    p_data = {"roll_no": sel_s['roll_no'], "student_name": sel_s['name'], "amount_paid": base, "fee_type": f"{f_cat} ({f_desc})", "receipt_no": r_id, "payment_date": str(datetime.date.today()), "payment_mode": mode}
                    supabase.table("fee_records").insert(p_data).execute()
                    st.download_button("📩 Download PDF", create_fee_receipt(sel_s['name'], sel_s['roll_no'], p_data), f"Rec_{r_id}.pdf")

        with tabs[2]: # EXAM MANAGEMENT
            st.subheader("📅 Publish & Manage Examinations")
            with st.form("exam_form_new"):
                e_crs = st.selectbox("Course Target", COURSES)
                e_nm = st.text_input("Exam Heading")
                e_subs = st.text_area("Schedule (Format: Subject : Date)")
                c_x, c_y = st.columns(2)
                e_tm, e_vn = c_x.text_input("Reporting Time", value="09:30 AM"), c_y.text_input("Venue", value="OPI Hall")
                if st.form_submit_button("Publish"):
                    supabase.table("exam_schedules").insert({"course": e_crs, "exam_name": e_nm, "subject_details": e_subs, "reporting_time": e_tm, "venue": e_vn}).execute()
                    st.success("Published!"); st.rerun()
            
            all_ex = supabase.table("exam_schedules").select("*").order('id', desc=True).execute().data
            for ex in all_ex:
                c_info, c_del = st.columns([4, 1])
                c_info.write(f"📌 **{ex['exam_name']}** - {ex['course']}")
                if c_del.button("Delete 🗑️", key=f"del_ex_{ex['id']}"):
                    supabase.table("exam_schedules").delete().eq("id", ex['id']).execute(); st.rerun()

        with tabs[3]: # RECORDS & EDIT
            recs = supabase.table("students").select("*").execute().data
            fees = supabase.table("fee_records").select("*").execute().data
            with st.expander("📊 Defaulter Dashboard"):
                for s in recs:
                    if s['is_active']:
                        j_dt = datetime.datetime.strptime(s['joining_date'], '%Y-%m-%d').date()
                        due_m = (datetime.date.today().year - j_dt.year) * 12 + datetime.date.today().month - j_dt.month + 1
                        paid_m = len([f for f in fees if str(f['roll_no']) == str(s['roll_no']) and "Monthly Tuition" in f['fee_type']])
                        pending = due_m - paid_m
                        c1, c2 = st.columns([3, 1])
                        c1.write(f"**{s['name']}** - Pending: {pending} Months")
                        if pending > 0: c2.markdown(f"[📲 WA](https://wa.me/{s.get('phone')}?text=Dues: {pending} Months)")
            
            if st.session_state.edit_id:
                t = next((s for s in recs if str(s['roll_no']) == str(st.session_state.edit_id)), None)
                if t:
                    with st.form("edit_stu"):
                        en = st.text_input("Name", value=t['name'])
                        ec = st.selectbox("Course", COURSES, index=COURSES.index(t['course']) if t['course'] in COURSES else 0)
                        ebg = st.selectbox("Blood Group", BLOOD_GROUPS, index=BLOOD_GROUPS.index(t.get('blood_group', 'Unknown')))
                        if st.form_submit_button("Update"):
                            supabase.table("students").update({"name": en, "course": ec, "blood_group": ebg}).eq("roll_no", t['roll_no']).execute()
                            st.session_state.edit_id = None; st.rerun()
                    if st.button("Cancel"): st.session_state.edit_id = None; st.rerun()
            else:
                for row in recs:
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    c1.write(f"**{row['name']}**")
                    clr = "✅ Shared" if row['exam_cleared'] else "❌ Locked"
                    if c2.button(clr, key=f"cl_{row['roll_no']}"): supabase.table("students").update({"exam_cleared": not row['exam_cleared']}).eq("roll_no", row['roll_no']).execute(); st.rerun()
                    if c3.button("Edit", key=f"ed_{row['roll_no']}"): st.session_state.edit_id = row['roll_no']; st.rerun()
                    if c4.button("Del", key=f"dl_{row['roll_no']}"):
                        supabase.table("fee_records").delete().eq("roll_no", row['roll_no']).execute()
                        supabase.table("students").delete().eq("roll_no", row['roll_no']).execute(); st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user; st.title(f"👋 {s['name']}")
        col1, col2 = st.columns([1, 2])
        with col1:
            if s.get('photo_url'): st.image(s['photo_url'], width=150)
            st.download_button("🪪 ID Card", create_id_card(s), f"ID_{s['roll_no']}.pdf")
            st.divider()
            exams = supabase.table("exam_schedules").select("*").eq("course", s['course']).order('id', desc=True).execute().data
            if exams:
                ex = exams[0]
                if s.get('exam_cleared', False):
                    st.success(f"Exam: {ex['exam_name']}")
                    st.download_button("📄 Download Admit Card", create_admit_card(s, ex), f"Admit_{s['roll_no']}.pdf")
                else: st.error("🔒 Locked. Contact Office.")
        with col2:
            st.subheader("💳 Payments")
            h = supabase.table("fee_records").select("*").eq("roll_no", str(s['roll_no'])).execute().data
            for p in h:
                st.write(f"**{p['fee_type']}** | Rs. {p['amount_paid']}")
                st.download_button(f"📄 Rec {p['receipt_no']}", create_fee_receipt(s['name'], s['roll_no'], p), f"OPI_{p['receipt_no']}.pdf", key=f"st_{p['receipt_no']}")
