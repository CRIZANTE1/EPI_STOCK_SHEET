# Utils/pdf_generator.py

import io
import requests
import base64
from weasyprint import HTML
from datetime import datetime

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

    # Template HTML com CSS embutido. É longo, mas é o layout do seu PDF.
    html_template = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ margin: 1.5cm; }}
            body {{ font-family: 'Helvetica', sans-serif; font-size: 10px; color: #333; }}
            .header {{ display: flex; align-items: center; margin-bottom: 1cm; }}
            .logo {{ width: 100px; margin-right: 20px; }}
            .title {{ font-size: 18px; font-weight: bold; text-align: center; flex-grow: 1; }}
            .info-box {{ border: 1px solid black; border-radius: 5px; padding: 10px; font-size: 10px; }}
            .info-box .row {{ display: flex; }}
            .info-box .col {{ flex: 1; padding: 2px 5px; }}
            .info-box .separator {{ border-top: 1px solid black; margin: 5px 0; }}
            .bold {{ font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; border: 1px solid black; margin-top: 1cm; }}
            th, td {{ border: 1px solid black; padding: 4px; text-align: left; font-size: 9px; word-wrap: break-word; }}
            th {{ font-weight: bold; text-align: center; background-color: #f2f2f2; }}
            .center {{ text-align: center; }}
            .termo {{ margin-top: 2cm; text-align: center; }}
            .termo-texto {{ font-size: 9px; text-align: justify; margin-top: 0.5cm; }}
            .assinatura {{ margin-top: 3cm; text-align: center; }}
            .assinatura-linha {{ border-top: 1px solid black; width: 250px; margin: 0 auto; }}
        </style>
    </head>
    <body>
        <div class="header">
            <img class="logo" src="{logo_base64_src if logo_base64_src else ''}">
            <div class="title">FICHA DE CONTROLE DE FORNECIMENTO DE E. P. I.</div>
        </div>
        <div class="info-box">
            <div class="row">
                <div class="col"><span class="bold">NOME DO FUNCIONÁRIO:</span> {employee_info.get('nome', '')}</div>
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
                    <th style="width: 5%;">ITEM</th>
                    <th style="width: 30%;">RELAÇÃO DOS EQUIPAMENTOS FORNECIDOS (DISCRIMINAÇÃO)</th>
                    <th style="width: 10%;">DATA DE ENTREGA</th>
                    <th style="width: 10%;">DATA DE DEVOLUÇÃO</th>
                    <th style="width: 10%;">TEMPO DE DURAÇÃO</th>
                    <th style="width: 10%;">Nº C. A. EPI</th>
                    <th style="width: 25%;">ASSINATURA DO FUNCIONÁRIO</th>
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
            <p>Local e data: Barueri, SP, {datetime.now().strftime('%d/%m/%Y')}</p>
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
