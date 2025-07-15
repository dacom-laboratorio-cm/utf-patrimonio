import re
import pdfplumber

def extrair_responsavel(full_text):
    match = re.search(r"Responsável:\s*(.+)", full_text)
    return match.group(1).strip() if match else ""

def extrair_itens(full_text, responsavel):
    items = []
    for line in full_text.splitlines():
        line = line.strip()
        match = re.match(r"^(\d{6})\s+(.+?)\s+R\$([\d\.,]+)\s+(\d+-\d{2}/\d{2}/\d{4})\s+(\S+)$", line)
        if match:
            tombo = match.group(1)
            descricao = match.group(2).replace(";", ",")
            valor = match.group(3).replace(";", ",")
            termo_data = match.group(4).replace(";", ",")
            local = match.group(5).replace(";", ",").replace("/", "-")
            items.append((tombo, descricao, valor, termo_data, local, responsavel))
    return items

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