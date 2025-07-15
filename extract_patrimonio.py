import pdfplumber
import csv
import re
import sys
import os
import glob

# Função para extrair responsável do texto
def extrair_responsavel(full_text):
    match = re.search(r"Responsável:\s*(.+)", full_text)
    return match.group(1).strip() if match else ""

# Função para extrair itens do texto
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

def main():
    # 1. Listar todos os PDFs
    pdf_files = glob.glob("patrimonio/*.pdf")
    pdf_files.sort()  # Ordenar alfabeticamente
    agrupados_por_local = {}
    duplicidades = []
    tombos_por_local = {}

    # 2. Processar cada PDF
    for pdf_path in pdf_files:
        print("------")
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        responsavel = extrair_responsavel(full_text)
        # Extrair Qtd. de Bens informada no PDF
        qtd_match = re.search(r"Qtd\. de Bens:\s*(\d+)", full_text)
        qtd_bens = int(qtd_match.group(1)) if qtd_match else None
        itens = extrair_itens(full_text, responsavel)
        print(f"Arquivo processado: {pdf_path}")
        print(f"Responsável: {responsavel}")
        print(f"Qtd. de Bens informada no PDF: {qtd_bens if qtd_bens is not None else 'Não encontrada'} | Itens extraídos: {len(itens)}")
        if qtd_bens is not None and qtd_bens != len(itens):
            print(f"[ATENÇÃO] Divergência: Qtd. de Bens informada ({qtd_bens}) diferente da quantidade de itens extraídos ({len(itens)})!")
        # Verificar se todos os itens possuem todos os campos necessários
        dados_ok = all(len(item) == 6 and all(item) for item in itens)
        if not dados_ok or not itens:
            print(f"[ERRO] Arquivo não compatível: {pdf_path} (faltam dados necessários em pelo menos um item)")
            continue
        for item in itens:
            local = item[4]
            tombo = item[0]
            if local not in agrupados_por_local:
                agrupados_por_local[local] = []
                tombos_por_local[local] = set()
            # Verificar duplicidade no agrupamento atual
            if tombo in tombos_por_local[local]:
                duplicidades.append(item)
            else:
                agrupados_por_local[local].append(item)
                tombos_por_local[local].add(tombo)

    # 3. Garantir que a pasta csv/ existe
    os.makedirs("csv", exist_ok=True)

    # 4. Para cada local, salvar/adicionar no CSV
    for local, itens in agrupados_por_local.items():
        # Substituir '/' por '-' no nome do arquivo
        local_filename = local.replace('/', '-')
        csv_path = f"csv/{local_filename}.csv"
        tombos_existentes = set()
        linhas_existentes = []
        # Se o arquivo já existe, ler tombos já presentes
        if os.path.exists(csv_path):
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=';')
                next(reader, None)  # pular cabeçalho
                for row in reader:
                    if row:
                        tombos_existentes.add(row[0])
                        linhas_existentes.append(tuple(row))
        # Adicionar apenas novos tombos
        novos_itens = []
        for item in itens:
            if item[0] not in tombos_existentes:
                novos_itens.append(item)
            else:
                duplicidades.append(item)
        # Escrever arquivo (mantendo os já existentes + novos)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["tombo", "descricao", "valor", "termo/data", "local", "responsavel"])
            for row in linhas_existentes:
                writer.writerow(row)
            for item in novos_itens:
                writer.writerow(item)

    # 5. Salvar duplicidades em inconsistencia.csv
    if duplicidades:
        inc_path = "csv/inconsistencia.csv"
        inc_existentes = set()
        # Se já existe, evitar duplicidade no arquivo de inconsistência
        if os.path.exists(inc_path):
            with open(inc_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=';')
                next(reader, None)
                for row in reader:
                    if row:
                        inc_existentes.add(tuple(row))
        with open(inc_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["tombo", "descricao", "valor", "termo/data", "local", "responsavel"])
            for row in inc_existentes:
                writer.writerow(row)
            for item in duplicidades:
                if item not in inc_existentes:
                    writer.writerow(item)

if __name__ == "__main__":
    main()
