def create_id_card(student):
    # Set to A4 Portrait
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # Define ID Card dimensions (standard 85x55mm)
    card_w = 85
    card_h = 55
    offset_x = 10 # 1cm from left
    offset_y = 10 # 1cm from top
    
    # --- DRAW CARD BORDER ---
    pdf.set_draw_color(0, 51, 102) # Navy Blue
    pdf.set_line_width(0.5)
    pdf.rect(offset_x, offset_y, card_w, card_h)
    
    # --- HEADER BAR ---
    pdf.set_fill_color(0, 51, 102)
    pdf.rect(offset_x, offset_y, card_w, 12, 'F')
    
    # --- HEADER TEXT ---
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_xy(offset_x, offset_y + 2)
    pdf.cell(card_w, 5, "OXFORD PARAMEDICAL INSTITUTE", ln=True, align='C')
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(offset_x, offset_y + 7)
    pdf.cell(card_w, 3, "GUWAHATI | DHUPDHARA, ASSAM", ln=True, align='C')
    
    # --- BODY CONTENT ---
    pdf.set_text_color(0, 0, 0)
    
    def add_field(label, value, y_add):
        pdf.set_xy(offset_x + 5, offset_y + y_add)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(20, 5, label, 0)
        pdf.set_font("Arial", '', 8)
        pdf.cell(0, 5, str(value).upper(), ln=True)

    add_field("NAME:", student.get('name', 'N/A'), 18)
    add_field("ROLL NO:", student.get('roll_no', 'N/A'), 24)
    add_field("COURSE:", student.get('course', 'N/A'), 30)
    add_field("SESSION:", student.get('session', 'N/A'), 36)
    add_field("B. GROUP:", student.get('blood_group', 'N/A'), 42)
    
    # Address
    pdf.set_xy(offset_x + 5, offset_y + 48)
    pdf.set_font("Arial", 'B', 7)
    pdf.cell(20, 4, "ADDRESS:", 0)
    pdf.set_font("Arial", '', 6)
    pdf.set_xy(offset_x + 23, offset_y + 48)
    pdf.multi_cell(55, 3, student.get('address', 'N/A'))
    
    return pdf.output(dest='S').encode('latin-1')
