import io
import requests
import base64
from weasyprint import HTML
from datetime import datetime
import markdown 

def get_logo_base64(file_id):
    """ Baixa uma imagem do Google Drive e a converte para uma string Base64. """
    url = f'https://drive.google.com/uc?export=download&id={file_id}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            encoded_string = base64.b64encode(response.content).decode('utf-8')
            return f"data:image/png;base64,{encoded_string}"
        return None
    except Exception:
        return None

def create_epi_ficha_html(employee_info, epi_records):
    """ Gera a Ficha de Controle de EPI em PDF a partir de um template HTML. """
    google_drive_file_id = '1AABdw4iGBJ7tsQ7fR1WGTP5cML3Jlfx_'
    logo_base64_src = get_logo_base64(google_drive_file_id)
    
    epi_rows_html = ""
    for i in range(14):
        if i < len(epi_records):
            record = epi_records[i]
            epi_rows_html += f"""
            <tr>
                <td class="center">{i + 1}</td>
                <td>{record.get('epi_name', '')}</td>
                <td class="center">{record.get('date', '')}</td>
                <td class="center"></td>
                <td class="center"></td>
                <td class="center">{record.get('CA', '')}</td>
                <td></td>
            </tr>
            """
        else:
            epi_rows_html += f'<tr><td class="center">{i + 1}</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>'

    # Template HTML com CSS atualizado
    html_template = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            /* MODIFICADO: Define a orientação da página e as margens */
            @page {{
                size: A4 landscape;
                margin: 1cm;
            }}
            body {{ font-family: 'Helvetica', sans-serif; font-size: 9px; color: #333; }}
            
            /* NOVO: Estilo para o cabeçalho superior */
            .top-header {{
                text-align: right;
                font-size: 10px;
                color: #555;
                margin-bottom: 10px;
            }}

            .main-header {{ display: flex; align-items: center; margin-bottom: 1cm; }}
            .logo {{ width: 100px; margin-right: 20px; flex-shrink: 0; }}
            .title-block {{ text-align: center; flex-grow: 1; }}
            .main-title {{ font-size: 16px; font-weight: bold; }}
            .info-box {{ border: 1px solid black; border-radius: 5px; padding: 10px; font-size: 9px; }}
            .info-box .row {{ display: flex; }}
            .info-box .col {{ flex: 1; padding: 2px 5px; }}
            .info-box .separator {{ border-top: 1px solid black; margin: 5px 0; }}
            .bold {{ font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; border: 1px solid black; margin-top: 1cm; }}
            th, td {{ border: 1px solid black; padding: 4px; text-align: left; font-size: 8px; word-wrap: break-word; }}
            th {{ font-weight: bold; text-align: center; background-color: #f2f2f2; }}
            .center {{ text-align: center; }}
            .termo {{ margin-top: 1.5cm; text-align: center; }}
            .termo-texto {{ font-size: 8px; text-align: justify; margin-top: 0.5cm; }}
            .assinatura {{ margin-top: 2cm; text-align: center; }}
            .assinatura-linha {{ border-top: 1px solid black; width: 250px; margin: 0 auto; }}
        </style>
    </head>
    <body>
        <!-- NOVO: Bloco para o cabeçalho superior -->
        <div class="top-header">
            Padrão 040.010.060.006.PR - EPI<br>
            ANEXO A – Ficha de Controle de Fornecimento de EPI<br>
            Corporativo
        </div>

        <div class="main-header">
            <img class="logo" src="{logo_base64_src if logo_base64_src else ''}">
            <div class="title-block">
                <div class="main-title">FICHA DE CONTROLE DE FORNECIMENTO DE E. P. I.</div>
            </div>
        </div>

        <div class="info-box">
            <div class="row">
                <div class="col" style="flex-grow: 2;"><span class="bold">NOME DO FUNCIONÁRIO:</span> {employee_info.get('nome', '')}</div>
                <div class="col"><span class="bold">REGISTRO:</span> {employee_info.get('registro', '')}</div>
            </div>
            <div class="separator"></div>
            <div class="row">
                <div class="col"><span class="bold">ESTABELECIMENTO:</span> BAERI</div>
                <div class="col"><span class="bold">SETOR:</span> {employee_info.get('setor', '')}</div>
                <div class="col"><span class="bold">CARGO:</span> {employee_info.get('cargo', '')}</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 4%;">ITEM</th>
                    <th style="width: 26%;">RELAÇÃO DOS EQUIPAMENTOS FORNECIDOS (DISCRIMINAÇÃO)</th>
                    <th style="width: 10%;">DATA DE ENTREGA</th>
                    <th style="width: 10%;">DATA DE DEVOLUÇÃO</th>
                    <th style="width: 10%;">TEMPO DE DURAÇÃO</th>
                    <th style="width: 10%;">Nº C. A. EPI</th>
                    <th style="width: 30%;">ASSINATURA DO FUNCIONÁRIO</th>
                </tr>
            </thead>
            <tbody>
                {epi_rows_html}
            </tbody>
        </table>

        <div class="termo">
            <div class="bold">"TERMO DE RESPONSABILIDADE"</div>
            <div class="termo-texto">
                Declaro para os devidos fins que recebi treinamento quanto à obrigatoriedade e necessidade do uso dos E.P.I.'s recomendados, (NR-6, Item 6.6, subitem 6.6.1, letra "c"); além de estar ciente da responsabilidade pela guarda e conservação dos mesmos (NR-6, Item 6.7, subitem 6.7.1, letras "b"), bem como ter conhecimento das penalidades que me podem ser impostas por não usá-lo adequadamente (C.L.T., Cap. V, Art. 158, § Único, letra "b").
            </div>
            <p style="margin-top: 10px;">Local e data: Barueri, SP, {datetime.now().strftime('%d/%m/%Y')}</p>
        </div>
        
        <div class="assinatura">
            <div class="assinatura-linha"></div>
            <p>Assinatura do Funcionário</p>
        </div>
    </body>
    </html>
    """
    
    # Converte o HTML em PDF e retorna como um buffer de bytes
    pdf_bytes = HTML(string=html_template).write_pdf()
    
    return io.BytesIO(pdf_bytes)



def create_forecast_pdf_from_report(report_markdown_text: str):
    """
    Pega um texto em formato Markdown, converte para HTML, aplica um template
    profissional e gera um PDF.
    """
    # 1. Converter o texto do relatório (Markdown) para HTML
    # A extensão 'tables' é crucial para formatar as tabelas corretamente.
    html_body = markdown.markdown(report_markdown_text, extensions=['tables'])

    # 2. Obter o logo (reutilizando a função existente)
    google_drive_file_id = '1AABdw4iGBJ7tsQ7fR1WGTP5cML3Jlfx_'
    logo_base64_src = get_logo_base64(google_drive_file_id)

    # 3. Definir o CSS para o template do relatório
    css_styles = """
        @page { size: A4 portrait; margin: 2cm; }
        body { font-family: 'Helvetica', sans-serif; font-size: 11pt; color: #333; }
        .header { display: flex; align-items: center; border-bottom: 2px solid #004a99; padding-bottom: 10px; }
        .logo { width: 80px; margin-right: 20px; }
        .header-title { font-size: 24pt; font-weight: bold; color: #004a99; }
        .content { margin-top: 20px; }
        h1, h2, h3 { color: #004a99; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 9pt; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; font-weight: bold; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .footer { position: fixed; bottom: 0; left: 0; right: 0; text-align: center; font-size: 8pt; color: #777; }
    """

    # 4. Montar o template HTML final
    html_template = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>{css_styles}</style>
    </head>
    <body>
        <div class="header">
            <img class="logo" src="{logo_base64_src if logo_base64_src else ''}">
            <div class="header-title">Relatório de Previsão Orçamentária</div>
        </div>

        <div class="content">
            {html_body}
        </div>

        <div class="footer">
            Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} pelo Sistema de Gestão de EPIs.
        </div>
    </body>
    </html>
    """

    # 5. Converter o HTML para PDF e retornar os bytes
    pdf_bytes = HTML(string=html_template).write_pdf()
    return io.BytesIO(pdf_bytes)    
