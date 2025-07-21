# Sistema de Inventário de Patrimônio

## Visão Geral

Este projeto é um sistema web para controle, conferência e inventário de patrimônio institucional, desenvolvido em Flask. Permite importar dados de PDFs, consultar e filtrar itens, realizar conferências patrimoniais por sala/local, gerar relatórios de conferência e manter histórico de conferências.

---

## Funcionalidades

- **Importação de PDFs**: Extração automática de itens de patrimônio a partir de arquivos PDF.
- **Consulta e Filtros**: Visualização dos itens cadastrados, com filtros por local, responsável e número do tombo.
- **Conferência Patrimonial**: Realize conferências por sala, digitando os tombos encontrados e gerando relatório de conferência.
- **Histórico de Conferências**: Salve e consulte conferências anteriores, com detalhamento dos itens encontrados, faltantes, desconhecidos e em local divergente.
- **Logs de Processamento**: Acompanhe o resultado da importação de PDFs.

---

## Requisitos

- Python 3.8+
- SQLite (padrão, já incluso)

### Bibliotecas Python
Veja `requirements.txt`:
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-WTF
- WTForms
- pdfplumber
- Werkzeug

---

## Instalação

1. Clone o repositório:
   ```bash
   git clone <url-do-repositorio>
   cd utf-patrimonio
   ```
2. Crie e ative um ambiente virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure a aplicação (opcional: `.env` ou variáveis de ambiente).

---

## Migração do Banco de Dados

1. Inicialize as migrações (apenas na primeira vez):
   ```bash
   flask db init
   ```
2. Gere as migrações:
   ```bash
   flask db migrate -m "Criação das tabelas iniciais"
   ```
3. Aplique as migrações:
   ```bash
   flask db upgrade
   ```

---

## Como Usar

1. Execute a aplicação:
   ```bash
   python run.py
   ```
2. Acesse no navegador:
   - Importar PDFs: `http://localhost:5000/upload`
   - Itens: `http://localhost:5000/itens`
   - Conferências: `http://localhost:5000/conferencias_patrimoniais`
   - Nova Conferência: `http://localhost:5000/conferencia_patrimonial`
   - Logs: `http://localhost:5000/logs`

---

## Estrutura do Projeto

```
utf-patrimonio/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models.py
│   ├── patrimonio/
│   │   ├── __init__.py
│   │   ├── forms.py
│   │   ├── routes.py
│   │   ├── services.py
│   │   └── utils.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── upload.html
│   │   ├── itens.html
│   │   ├── logs.html
│   │   ├── conferencia_patrimonial.html
│   │   ├── conferencias_patrimoniais.html
│   │   ├── conferencia_patrimonial_detalhe.html
│   │   ├── conferencia_patrimonial_manual.html
│   │   ├── editar_conferencia_patrimonial.html
│   │   ├── editar_item_conferencia_patrimonial.html
│   │   ├── 404.html
│   │   └── 500.html
│   └── static/
├── instance/
│   └── app.db
├── migrations/
├── uploads/
├── requirements.txt
├── run.py
└── README.md
```

---

## Diagrama do Banco de Dados

```mermaid
erDiagram
    ItemPatrimonio {
        Integer id PK
        String tombo
        Text descricao
        String valor
        String termo_data
        String local
        String responsavel
        String observacao
    }
    LogProcessamento {
        Integer id PK
        String arquivo_pdf
        String responsavel
        Integer qtd_bens_pdf
        Integer qtd_itens_extraidos
        Boolean divergencia
        Text erro
        String local
    }
    ConferenciaPatrimonial {
        Integer id PK
        String local
        DateTime data
        String responsavel
    }
    ConferenciaPatrimonialItem {
        Integer id PK
        Integer conferencia_patrimonial_id FK
        Integer item_patrimonio_id FK
        String inconsistencia
        String local_banco
        Text descricao
    }
    ConferenciaPatrimonial ||--o{ ConferenciaPatrimonialItem : "possui"
    ConferenciaPatrimonialItem }o--|| ConferenciaPatrimonial : "pertence a"
    ItemPatrimonio |o--o{ ConferenciaPatrimonialItem : "referenciado por"
    ConferenciaPatrimonialItem }o--o| ItemPatrimonio : "referencia"
```

---

## Observações
- O sistema utiliza SQLite por padrão, mas pode ser adaptado para outros bancos.
- O upload de PDFs e o processamento dependem do layout dos arquivos.
- A conferência patrimonial permite salvar e consultar históricos para auditoria.

---

## Regras de Negócio

### 1. Cadastro e Importação de Itens

- **Importação de PDFs:**
  - O sistema permite importar arquivos PDF contendo listas de bens patrimoniais.
  - Cada item extraído do PDF é cadastrado como um `ItemPatrimonio`, contendo: tombo, descrição, valor, termo/data, local, responsável e observação (nome do PDF ou outra informação relevante).
  - Se um item já existe (mesmo tombo, local e observação), não é duplicado.

- **Cadastro Manual:**
  - É possível cadastrar itens manualmente durante a conferência patrimonial.
  - Para itens sem etiqueta (sem tombo), apenas a descrição é obrigatória.
  - Para itens novos, o campo `observacao` recebe "obtido de conferência manual".

### 2. Conferência Patrimonial

- **Processo de Conferência:**
  - O usuário informa o local, responsável e a lista de tombos (via campo de texto ou importação de CSV).
  - O sistema compara os tombos informados com os itens cadastrados no banco para aquele local.

- **Classificação dos Itens na Conferência:**
  - **Encontrado no local correto:**
    - O tombo informado existe no banco e está cadastrado para o local da conferência.
    - `inconsistencia = 'ok'`
  - **Encontrado em outro local:**
    - O tombo existe no banco, mas está cadastrado para outro local.
    - `inconsistencia = 'local_divergente'`
  - **Encontrado, mas origem desconhecida:**
    - O tombo existe no banco, mas não foi possível determinar o local de origem.
    - `inconsistencia = 'local_divergente_desconhecida'`
  - **Não encontrado:**
    - O tombo informado não existe no banco.
    - `inconsistencia = 'nao_encontrado'`
  - **Sem etiqueta:**
    - O item foi informado sem tombo (apenas descrição).
    - `inconsistencia = 'sem_etiqueta'`

- **Regras de Referência:**
  - Todo item de conferência (`ConferenciaPatrimonialItem`) sempre referencia um `ItemPatrimonio` existente.
  - Se o tombo não existe, o sistema cria o `ItemPatrimonio` antes de referenciar.

### 3. Logs de Processamento

- Cada importação de PDF gera um registro de log (`LogProcessamento`), contendo:
  - Nome do arquivo importado
  - Responsável
  - Quantidade de bens informada no PDF
  - Quantidade de itens extraídos
  - Divergência (se houver diferença entre quantidade informada e extraída)
  - Erro (se houver)
  - Local (extraído do PDF)

### 4. Visualização e Filtros

- **Itens do Patrimônio:**
  - Podem ser filtrados por tombo, local e responsável.
  - Permite ordenação por qualquer campo, inclusive observação.

- **Conferências Patrimoniais:**
  - Histórico de todas as conferências realizadas, com detalhamento dos itens classificados em cada uma.
  - Permite ordenação por ID, local, responsável e data.

### 5. Exclusão e Edição

- **Itens:**
  - Não podem ser excluídos automaticamente ao remover uma conferência, pois podem estar referenciados em outros históricos.
- **Conferências:**
  - Ao remover uma conferência, todos os itens associados a ela são removidos da tabela de itens de conferência, mas os itens patrimoniais permanecem.

### 6. Observações Gerais

- O campo `observacao` de `ItemPatrimonio` armazena o nome do PDF de origem ou a informação "obtido de conferência manual".
- O sistema não permite duplicidade de tombos para o mesmo local e observação.
- Todas as ações relevantes são registradas para auditoria e histórico.

---

## Licença

Este projeto é acadêmico e pode ser adaptado conforme necessidade institucional. 