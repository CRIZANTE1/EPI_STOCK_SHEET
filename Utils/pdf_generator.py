import io
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from datetime import datetime

def get_logo_from_google_drive(file_id):
    """ Baixa a imagem do Google Drive e retorna um buffer. """
    url = f'https://drive.google.com/uc?export=download&id={file_id}'
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            return io.BytesIO(response.content)
        return None
    except Exception:
        return None

# ----- AQUI ESTÁ A FUNÇÃO QUE ESTAVA FALTANDO -----
def create_epi_ficha_reportlab(employee_info, epi_records):
    """
    Gera a Ficha de Controle de EPI em PDF usando ReportLab.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Estilos
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    style_normal.fontName = 'Helvetica'
    style_normal.fontSize = 8
    style_normal.leading = 10
    
    # Coordenadas e Margens
    margin = 1.5 * cm
    
    # --- Desenhar o Cabeçalho ---
    google_drive_file_id = '1AABdw4iGBJ7tsQ7fR1WGTP5cML3Jlfx_'
    logo_buffer = get_logo_from_google_drive(google_drive_file_id)
    
    if logo_buffer:
        c.drawImage(logo_buffer, margin, height - 3*cm, width=2.5*cm, preserveAspectRatio=True, mask='auto')
    else:
        c.drawString(margin, height - 2.5*cm, "[LOGO]")

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 2.5*cm, "FICHA DE CONTROLE DE FORNECIMENTO DE E. P. I.")

    # --- Caixa de informações do funcionário ---
    y_start_info = height - 4*cm
    c.roundRect(margin, y_start_info, width - 2*margin, 1.5*cm, 5)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin + 0.2*cm, y_start_info + 1.1*cm, "NOME DO FUNCIONÁRIO:")
    c.drawString(margin + 10*cm, y_start_info + 1.1*cm, "REGISTRO:")
    c.drawString(margin + 0.2*cm, y_start_info + 0.4*cm, "ESTABELECIMENTO: BAERI")
    c.drawString(margin + 6*cm, y_start_info + 0.4*cm, "SETOR:")
    c.drawString(margin + 10*cm, y_start_info + 0.4*cm, "CARGO:")
    c.line(margin, y_start_info + 0.8*cm, width - margin, y_start_info + 0.8*cm)
    
    c.setFont("Helvetica", 10)
    c.drawString(margin + 4.5*cm, y_start_info + 1.1*cm, employee_info.get('nome', ''))
    c.drawString(margin + 12*cm, y_start_info + 1.1*cm, employee_info.get('registro', ''))
    c.drawString(margin + 7.2*cm, y_start_info + 0.4*cm, employee_info.get('setor', ''))
    c.drawString(margin + 11.2*cm, y_start_info + 0.4*cm, employee_info.get('cargo', ''))

    # --- Tabela de EPIs ---
    y_table_start = y_start_info - 14*cm
    c.roundRect(margin, y_table_start, width - 2*margin, 13.5*cm, 5)
    
    y_header = y_start_info - 0.5*cm
    c.setFont("Helvetica-Bold", 8)
    headers = [
        (1, "ITEM"), (5.5, "RELAÇÃO DOS EQUIPAMENTOS FORNECIDOS\n(DISCRIMINAÇÃO)"),
        (10.5, "DATA DE\nENTREGA"), (12.5, "DATA DE\nDEVOLUÇÃO"),
        (14.5, "TEMPO DE\nDURAÇÃO"), (16.2, "Nº C. A.\nEPI"),
        (18.5, "ASSINATURA DO\nFUNCIONÁRIO")
    ]
    for x, text in headers:
        lines = text.split('\n')
        y_pos = y_header - 0.5*cm if len(lines) > 1 else y_header - 0.3*cm
        for i, line in enumerate(lines):
            c.drawCentredString(margin + x*cm, y_pos - i * 10, line)

    c.line(margin, y_start_info - 1*cm, width - margin, y_start_info - 1*cm)
    col_positions = [2.2, 9, 11.8, 13.5, 15.5, 17.2]
    for x_pos in col_positions: c.line(margin + x_pos*cm, y_start_info, margin + x_pos*cm, y_table_start)
    
    c.setFont("Helvetica", 9)
    for i in range(14):
        y_line = y_start_info - (1 + i*0.9)*cm
        c.line(margin, y_line, width - margin, y_line)
        c.drawCentredString(margin + 1*cm, y_line + 0.3*cm, str(i + 1))
        if i < len(epi_records):
            record = epi_records[i]
            c.drawString(margin + 2.4*cm, y_line + 0.3*cm, record.get('epi_name', ''))
            c.drawCentredString(margin + 10.5*cm, y_line + 0.3*cm, record.get('date', ''))
            c.drawCentredString(margin + 16.2*cm, y_line + 0.3*cm, str(record.get('CA', '')))

    # --- Termo de Responsabilidade ---
    y_termo = y_table_start - 0.5*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width/2, y_termo, '"TERMO DE RESPONSABILIDADE"')
    
    termo_text = "Declaro para os devidos fins que recebi treinamento quanto à obrigatoriedade e necessidade do uso dos E.P.I.'s recomendados, (NR-6, Item 6.6, subitem 6.6.1, letra \"c\"); além de estar ciente da responsabilidade pela guarda e conservação dos mesmos (NR-6, Item 6.7, subitem 6.7.1, letras \"b\"), bem como ter conhecimento das penalidades que me podem ser impostas por não usá-lo adequadamente (C.L.T., Cap. V, Art. 158, § Único, letra \"b\")."
    p = Paragraph(termo_text, style_normal)
    p.wrapOn(c, width - 2*margin - 0.5*cm, height)
    p.drawOn(c, margin + 0.2*cm, y_termo - 2.2*cm)
    
    c.setFont("Helvetica", 10)
    c.drawString(margin, y_termo - 3.5*cm, f"Local e data: Barueri, SP, {datetime.now().strftime('%d/%m/%Y')}")
    
    c.line(width/2 - 4*cm, y_termo - 5*cm, width/2 + 4*cm, y_termo - 5*cm)
    c.drawCentredString(width/2, y_termo - 5.5*cm, "Assinatura do Funcionário")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
