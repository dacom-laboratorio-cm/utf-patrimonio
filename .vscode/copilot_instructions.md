# Instruções para a IA (GitHub Copilot)

Este arquivo serve como uma fonte de verdade e um guia de estilo para o assistente de IA ao trabalhar neste projeto.

## Sobre o Projeto

- **Nome:** Sistema de Gerenciamento de Patrimônio da UTFPR
- **Linguagem Principal:** Python
- **Framework:** Flask
- **Banco de Dados:** SQLite (via Flask-SQLAlchemy)
- **Estilo de Código:** Seguir o guia de estilo PEP 8. Usar o formatador `black` para garantir consistência.

## Regras Gerais

1.  **Clareza e Simplicidade:** Prefira código claro e legível em vez de código excessivamente complexo.
2.  **Comentários:** Adicione comentários explicativos para lógica de negócios complexa ou algoritmos não triviais. Docstrings devem ser usadas em todas as funções e classes públicas.
3.  **Tratamento de Erros:** Sempre inclua tratamento de erros robusto. Use blocos `try...except` de forma apropriada.
4.  **Segurança:** Esteja atento a vulnerabilidades de segurança comuns em aplicações web, como SQL Injection e XSS. Use as funcionalidades do Flask e do SQLAlchemy para prevenir esses ataques.
5.  **Commits:** As mensagens de commit devem seguir o padrão "feat: descreve a nova funcionalidade" ou "fix: descreve a correção de bug".

## Estrutura do Projeto

- `app/`: Contém o código principal da aplicação Flask.
  - `models.py`: Define os modelos do banco de dados (SQLAlchemy).
  - `patrimonio/routes.py`: Contém as rotas (endpoints) da aplicação relacionadas ao patrimônio.
  - `patrimonio/forms.py`: Contém os formulários (WTForms).
  - `templates/`: Contém os templates HTML (Jinja2).
- `migrations/`: Contém os scripts de migração do banco de dados (Alembic).
- `requirements.txt`: Lista as dependências Python do projeto.

## Como me Ajudar

- Ao criar novas rotas, siga o padrão já estabelecido em `app/patrimonio/routes.py`.
- Ao criar novos modelos, adicione-os em `app/models.py` e gere uma nova migração com o Flask-Migrate.
- Sempre que adicionar uma nova dependência, lembre-me de atualizá-la no `requirements.txt`.
