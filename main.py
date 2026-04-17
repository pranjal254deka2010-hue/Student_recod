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

# Connection with Error Handling
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Database Connection Failed. Check Secrets.")

# --- 2. CONSTANTS ---
COURSES = [
    "DMLT First Year", "DMLT Second Year", 
    "ICU Technician", "First AID and Patient Care", 
    "X Ray Technology"
]
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "N/A"]

# --- 3. THE "CRASH-PROOF" TEXT CLEANER ---
def safe_str(text):
    """Strips all non-standard characters that crash PDF generation."""
    if text is None: return "N/A"
    s = str(text).replace("₹", "Rs. ")
    # Keep only standard letters, numbers, and basic punctuation
    return "".join(c for c in s if ord(c) < 128)

# --- 4. PDF GENERATION ENGINE ---

def create_id_card(s):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    ox, oy, cw, ch = 10, 10, 85, 55
    pdf.set_draw_color(0, 51, 102); pdf.rect(ox, oy, cw, ch)
    pdf.set_fill_color(0, 51, 102); pdf.rect(ox, oy, cw, 12, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=ox + 2, y=oy + 1.5, h=9)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 9); pdf.set_xy(ox + 12, oy + 4)
    pdf.cell(cw - 12, 4, "OXFORD PARAMEDICAL INSTITUTE", ln=True)
    
    photo_data = s.get('photo_url', "")
    if photo_data and "base64," in str(photo_data):
        try: pdf.image(BytesIO(base64.b64decode(photo_data.split(",")[1])), x=ox + 62, y=oy + 15, w=18, h=22)
        except: pdf.rect(ox + 62, oy + 15, 18, 22)
        
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 8)
    y_pos = oy + 16
    details = [("NAME", s['name']), ("ROLL", s['roll_no']), ("COURSE", s['course']), ("BLOOD", s.get('blood_group', 'N/A'))]
    for lbl, val in details:
        pdf.set_xy(ox + 4, y_pos); pdf.cell(15, 5, f"{lbl}:"); pdf.set_font("Arial", '', 8)
        pdf.cell(40, 5, safe_str(val).upper(), ln=True); y_pos += 5.5; pdf.set_font("Arial", 'B', 8)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

def create_admit_card(s, exam):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    pdf.set_draw_color(0, 51, 102); pdf.rect(10, 10, 190, 160) 
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 25, 'F')
    if os.path.exists("logo.png"): pdf.image("logo.png", x=13, y=12, h=18)
    pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 15); pdf.set_xy(40, 14); pdf.cell(0, 8, "OXFORD PARAMEDICAL INSTITUTE")
    
    pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", 'B', 12); pdf.set_xy(10, 40)
    pdf.cell(190, 10, safe_str(exam['exam_name']).upper(), ln=True, align='C')
    
    pdf.set_font("Arial", '', 11); pdf.set_xy(15, 55)
    pdf.cell(0, 7, f"Name: {safe_str(s['name'])}", ln=True)
    pdf.set_x(15); pdf.cell(0, 7, f"Roll No: {s['roll_no']}", ln=True)
    pdf.set_x(15); pdf.cell(0, 7, f"Course: {s['course']}", ln=True)
    pdf.set_x(15); pdf.cell(0, 7, f"Blood Group: {s.get('blood_group', 'N/A')}", ln=True)

    # Subject Table
    pdf.set_xy(15, 90); pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(240, 240, 240)
    pdf.cell(100, 10, "Subject Name", border=1, fill=True); pdf.cell(50, 10, "Date", border=1, fill=True, ln=True)
    pdf.set_font("Arial", '', 10)
    
    for line in str(exam.get('subject_details', "")).split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            pdf.set_x(15); pdf.cell(100, 9, safe_str(parts[0]), border=1)
            pdf.cell(50, 9, safe_str(parts[1]), border=1, ln=True)
            
    if os.path.exists("signature.png"): pdf.image("signature.png", x=155, y=140, h=15)
    pdf.set_xy(15, 145); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, f"Venue: {safe_str(exam['venue'])}")
    return pdf.output(dest='S').encode('latin-1', 'replace')

def create_receipt(name, roll, p):
    pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
    pdf.set_fill_color(0, 51, 102); pdf.rect(10, 10, 190, 30, 'F')
    pdf.set_text_color(255, 255, 255); pdf.set_xy(50, 15); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 8, "OFFICIAL MONEY RECEIPT")
    pdf.set_text_color(0, 0, 0); pdf.set_xy(15, 50); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Name: {safe_str(name)} | Roll: {roll}", ln=True)
    pdf.cell(0, 10, f"Description: {safe_str(p['fee_type'])}", ln=True)
    pdf.cell(0, 10, f"Amount: Rs. {p['amount_paid']}/-", ln=True)
    pdf.cell(0, 10, f"Date: {p['payment_date']}", ln=True)
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 5. MAIN APP INTERFACE ---
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'role': None, 'user': None, 'edit_id': None})

if not st.session_state.auth:
    st.title("🏥 OPI Master Portal")
    u, p = st.text_input("User ID"), st.text_input("Password", type="password")
    if st.button("Login"):
        if u == "admin" and p == "opi2026":
            st.session_state.update({'auth': True, 'role': 'Admin'}); st.rerun()
        else:
            res = supabase.table("students").select("*").eq("roll_no", u).eq("password", p).execute()
            if res.data: st.session_state.update({'auth': True, 'role': 'Student', 'user': res.data[0]}); st.rerun()
            else: st.error("Access Denied")
else:
    if st.sidebar.button("Logout"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

    if st.session_state.role == "Admin":
        t = st.tabs(["Enroll", "Fees", "Exams", "Management"])
        
        with t[0]: # ENROLL
            with st.form("enroll_f"):
                c1, c2 = st.columns(2)
                r_i = c1.text_input("Roll No")
                n_i = c1.text_input("Full Name")
                c_i = c1.selectbox("Course", COURSES)
                b_i = c1.selectbox("Blood Group", BLOOD_GROUPS)
                p_i = c2.text_input("WhatsApp")
                f_i = c2.number_input("Monthly Fee", value=2500)
                pw_i = c2.text_input("Password")
                up_i = st.file_uploader("Photo", type=['jpg', 'png'])
                if st.form_submit_button("Save Student"):
                    img_str = f"data:image/png;base64,{base64.b64encode(up_i.getvalue()).decode()}" if up_i else ""
                    try:
                        supabase.table("students").insert({"roll_no": r_i, "name": n_i, "course": c_i, "blood_group": b_i, "password": pw_i, "photo_url": img_str, "phone": p_i, "monthly_fee_amount": f_i, "is_active": True, "joining_date": str(datetime.date.today())}).execute()
                        st.success("Enrolled Successfully!")
                    except Exception as ex: st.error(f"Save Error: {ex}")

        with t[1]: # FEES
            raw_s = supabase.table("students").select("*").eq("is_active", True).execute().data
            if raw_s:
                s_map = {f"{x['name']} ({x['roll_no']})": x for x in raw_s}
                target = s_map[st.selectbox("Select Student", list(s_map.keys()))]
                f_type = st.selectbox("Category", ["Monthly Tuition", "Admission Fee", "Exam Fee"])
                amt = st.number_input("Amount", value=int(target.get('monthly_fee_amount', 2500)))
                if st.button("Process Fee"):
                    r_id = f"OPI-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                    p_rec = {"roll_no": target['roll_no'], "amount_paid": amt, "fee_type": f_type, "receipt_no": r_id, "payment_date": str(datetime.date.today())}
                    supabase.table("fee_records").insert(p_rec).execute()
                    st.download_button("📩 Download Receipt", create_receipt(target['name'], target['roll_no'], p_rec), f"Rec_{r_id}.pdf")

        with t[2]: # EXAMS
            with st.form("ex_f"):
                ex_c = st.selectbox("For Course", COURSES)
                ex_n = st.text_input("Exam Name")
                ex_s = st.text_area("Schedule (Subject : Date)")
                ex_v = st.text_input("Venue", value="OPI Campus")
                if st.form_submit_button("Publish"):
                    supabase.table("exam_schedules").insert({"course": ex_c, "exam_name": ex_n, "subject_details": ex_s, "venue": ex_v, "reporting_time": "09:30 AM"}).execute()
                    st.success("Published!")
            
            exs = supabase.table("exam_schedules").select("*").order('id', desc=True).execute().data
            for e in exs:
                c_a, c_b = st.columns([4, 1])
                c_a.write(f"📅 **{e['exam_name']}** ({e['course']})")
                if c_b.button("Delete", key=f"d_{e['id']}"):
                    supabase.table("exam_schedules").delete().eq("id", e['id']).execute(); st.rerun()

        with t[3]: # MANAGEMENT
            stu_list = supabase.table("students").select("*").execute().data
            for s in stu_list:
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.write(f"**{s['name']}**")
                clr = "✅ Shared" if s.get('exam_cleared') else "❌ Locked"
                if c2.button(clr, key=f"c_{s['roll_no']}"):
                    supabase.table("students").update({"exam_cleared": not s.get('exam_cleared', False)}).eq("roll_no", s['roll_no']).execute(); st.rerun()
                if c3.button("Edit", key=f"e_{s['roll_no']}"):
                    st.session_state.edit_id = s['roll_no']; st.rerun()
                if c4.button("Delete", key=f"del_{s['roll_no']}"):
                    supabase.table("students").delete().eq("roll_no", s['roll_no']).execute(); st.rerun()
            
            if st.session_state.edit_id:
                curr = next((x for x in stu_list if x['roll_no'] == st.session_state.edit_id), None)
                if curr:
                    with st.form("ed"):
                        new_n = st.text_input("Edit Name", value=curr['name'])
                        new_c = st.selectbox("Edit Course", COURSES, index=COURSES.index(curr['course']))
                        if st.form_submit_button("Update"):
                            supabase.table("students").update({"name": new_n, "course": new_c}).eq("roll_no", curr['roll_no']).execute()
                            st.session_state.edit_id = None; st.rerun()

    elif st.session_state.role == "Student":
        s = st.session_state.user
        st.title(f"👋 {s['name']}")
        col_a, col_b = st.columns([1, 2])
        with col_a:
            if s.get('photo_url'): st.image(s['photo_url'], width=150)
            st.download_button("🪪 My ID", create_id_card(s), f"ID_{s['roll_no']}.pdf")
            st.divider()
            exs = supabase.table("exam_schedules").select("*").eq("course", s['course']).order('id', desc=True).execute().data
            if exs:
                e = exs[0]
                if s.get('exam_cleared'):
                    st.download_button("📄 My Admit Card", create_admit_card(s, e), f"Admit_{s['roll_no']}.pdf")
                else: st.error("Admit Card Locked.")
        with col_b:
            st.subheader("💳 Payments")
            h = supabase.table("fee_records").select("*").eq("roll_no", str(s['roll_no'])).execute().data
            for x in h: st.write(f"✅ {x['fee_type']} - Rs. {x['amount_paid']}")
