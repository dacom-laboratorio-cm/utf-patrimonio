from .utils import extrair_responsavel, extrair_itens
import pdfplumber
import re

def processar_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    responsavel = extrair_responsavel(full_text)
    qtd_match = re.search(r"Qtd\. de Bens:\s*(\d+)", full_text)
    qtd_bens = int(qtd_match.group(1)) if qtd_match else None
    itens = extrair_itens(full_text, responsavel)
    dados_ok = all(len(item) == 6 and all(item) for item in itens)
    erro = None
    if not dados_ok or not itens:
        erro = "Arquivo não compatível (faltam dados necessários em pelo menos um item)"
    divergencia = (qtd_bens is not None and qtd_bens != len(itens))
    return {
        'responsavel': responsavel,
        'qtd_bens': qtd_bens,
        'itens': itens,
        'divergencia': divergencia,
        'erro': erro
    } 