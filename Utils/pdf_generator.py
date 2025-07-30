import io
from weasyprint import HTML
from Utils.html_generator import generate_shelters_html # Importa sua função!

def create_shelters_pdf(df_shelters, df_inspections, df_actions):
    """
    Gera o PDF do relatório de abrigos.
    Passo 1: Gera o HTML usando sua função.
    Passo 2: Converte o HTML para PDF usando WeasyPrint.
    """
    # Passo 1: Gerar o conteúdo HTML
    html_string = generate_shelters_html(df_shelters, df_inspections, df_actions)

    # Passo 2: Converter o HTML para PDF em memória
    pdf_bytes = HTML(string=html_string).write_pdf()

    return io.BytesIO(pdf_bytes)
