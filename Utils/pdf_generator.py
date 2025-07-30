import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.colors import black, gray

def create_epi_ficha(employee_info, epi_records):
    """
    Gera a Ficha de Controle de EPI em PDF.

    Args:
        employee_info (dict): Dicionário com 'nome', 'registro', 'setor', 'cargo'.
        epi_records (list): Lista de dicionários, cada um representando um EPI.
    
    Returns:
        io.BytesIO: O buffer de bytes do PDF gerado.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4  # 595.27, 841.89

    # --- Estilos ---
    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    style_normal.fontName = 'Helvetica'
    style_normal.fontSize = 8
    style_normal.leading = 10

    style_bold_small = styles['Normal']
    style_bold_small.fontName = 'Helvetica-Bold'
    style_bold_small.fontSize = 6
    
    # --- Coordenadas e Margens ---
    margin = 1.5 * cm
    
    # Logo
    try:
        c.drawImage("assets/logo.png", margin, height - 3*cm, width=2.5*cm, preserveAspectRatio=True, mask='auto')
    except:
        c.drawString(margin, height - 2.5*cm, "LOGO")

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 2.5*cm, "FICHA DE CONTROLE DE FORNECIMENTO DE E. P. I.")

    # Caixa de informações do funcionário
    y_start_info = height - 4*cm
    c.roundRect(margin, y_start_info, width - 2*margin, 1.5*cm, 5)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin + 0.2*cm, y_start_info + 1.1*cm, "NOME DO FUNCIONÁRIO:")
    c.drawString(margin + 10*cm, y_start_info + 1.1*cm, "REGISTRO:")
    c.drawString(margin + 0.2*cm, y_start_info + 0.4*cm, "ESTABELECIMENTO: BAERI")
    c.drawString(margin + 6*cm, y_start_info + 0.4*cm, "SETOR:")
    c.drawString(margin + 10*cm, y_start_info + 0.4*cm, "CARGO:")
    c.line(margin, y_start_info + 0.8*cm, width - margin, y_start_info + 0.8*cm)
    
    # Preencher informações do funcionário
    c.setFont("Helvetica", 10)
    c.drawString(margin + 4.5*cm, y_start_info + 1.1*cm, employee_info.get('nome', ''))
    c.drawString(margin + 12*cm, y_start_info + 1.1*cm, employee_info.get('registro', ''))
    c.drawString(margin + 7.2*cm, y_start_info + 0.4*cm, employee_info.get('setor', ''))
    c.drawString(margin + 11.2*cm, y_start_info + 0.4*cm, employee_info.get('cargo', ''))

    # --- Desenhar a Tabela de EPIs ---
    y_table_start = y_start_info - 14*cm
    c.roundRect(margin, y_table_start, width - 2*margin, 13.5*cm, 5)
    
    # Cabeçalhos da tabela
    y_header = y_start_info - 0.5*cm
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(margin + 1*cm, y_header - 0.3*cm, "ITEM")
    c.drawCentredString(margin + 5.5*cm, y_header - 0.3*cm, "RELAÇÃO DOS EQUIPAMENTOS FORNECIDOS")
    c.drawCentredString(margin + 5.5*cm, y_header - 0.7*cm, "(DISCRIMINAÇÃO)")
    c.drawCentredString(margin + 10.5*cm, y_header - 0.3*cm, "DATA DE")
    c.drawCentredString(margin + 10.5*cm, y_header - 0.7*cm, "ENTREGA")
    c.drawCentredString(margin + 12.5*cm, y_header - 0.3*cm, "DATA DE")
    c.drawCentredString(margin + 12.5*cm, y_header - 0.7*cm, "DEVOLUÇÃO")
    c.drawCentredString(margin + 14.5*cm, y_header - 0.3*cm, "TEMPO DE")
    c.drawCentredString(margin + 14.5*cm, y_header - 0.7*cm, "DURAÇÃO")
    c.drawCentredString(margin + 16.2*cm, y_header - 0.3*cm, "Nº C. A.")
    c.drawCentredString(margin + 16.2*cm, y_header - 0.7*cm, "EPI")
    c.drawCentredString(margin + 18.5*cm, y_header - 0.3*cm, "ASSINATURA DO")
    c.drawCentredString(margin + 18.5*cm, y_header - 0.7*cm, "FUNCIONÁRIO")

    c.line(margin, y_start_info - 1*cm, width - margin, y_start_info - 1*cm) # Linha horizontal do header
    col_positions = [2.2, 9, 11.8, 13.5, 15.5, 17.2] # Posições X das linhas verticais
    for x_pos in col_positions:
        c.line(margin + x_pos*cm, y_start_info, margin + x_pos*cm, y_table_start)
    
    c.setFont("Helvetica", 9)
    for i in range(14):
        y_line = y_start_info - (1 + i*0.9)*cm
        c.line(margin, y_line, width - margin, y_line)
        c.drawCentredString(margin + 1*cm, y_line + 0.3*cm, str(i + 1))
        
        if i < len(epi_records):
            record = epi_records[i]
            c.drawString(margin + 2.4*cm, y_line + 0.3*cm, record.get('epi_name', ''))
            c.drawCentredString(margin + 10.5*cm, y_line + 0.3*cm, record.get('date', ''))
            c.drawCentredString(margin + 16.2*cm, y_line + 0.3*cm, record.get('CA', ''))

    y_termo = y_table_start - 0.5*cm
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width/2, y_termo, '"TERMO DE RESPONSABILIDADE"')
    
    termo_text = """
    Declaro para os devidos fins que recebi treinamento quanto à obrigatoriedade e necessidade do uso dos E.P.I.'s recomendados, 
    (NR-6, Item 6.6, subitem 6.6.1, letra "c"); além de estar ciente da responsabilidade pela guarda e conservação dos mesmos 
    (NR-6, Item 6.7, subitem 6.7.1, letras "b"), bem como ter conhecimento das penalidades que me podem ser impostas por 
    não usá-lo adequadamente (C.L.T., Cap. V, Art. 158, § Único, letra "b").
    """
    p = Paragraph(termo_text.replace("\n", " "), style_normal)
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
