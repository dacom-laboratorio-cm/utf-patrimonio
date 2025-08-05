---
applyTo: '**'
---
Provide project context and coding guidelines that AI should follow when generating code, answering questions, or reviewing changes.   

# Flask Rules

Este conjunto de regras guia convenções e boas práticas para aplicações Flask leves e modulares.

* **Use Blueprints** para organizar rotas por feature ou recurso e promover reusabilidade.
* **Use Application Factory** (padrão de criação de app) para inicializar a aplicação com diferentes configurações:

  ```python
  def create_app(config_name=None):
      app = Flask(__name__)
      # Carrega configuração
      if config_name:
          app.config.from_object(config[config_name])
      # Inicializa extensões:
      db.init_app(app)
      migrate.init_app(app, db)
      login.init_app(app)
      # Registra blueprints
      from .main import bp as main_bp
      app.register_blueprint(main_bp)
      return app
  ```
* **Use Flask‑SQLAlchemy** para models e ORM.
* **Use Flask‑Migrate** (Alembic) para migrações de banco.
* **Armazene configuração em variáveis de ambiente** e evite hardcode.
* **Use extensões Flask** (Flask‑Login, Flask‑WTF, Flask‑RESTful, etc.) conforme necessidade.
* **Implement proper error handling**:

  * **Error Handlers** (`@app.errorhandler`) para respostas HTTP customizadas.
  * **Logging** (Python `logging`) para registrar stack traces e alertas.

## Organização de Código e Estrutura

**Estrutura modular recomendada:**

```
project_root/
├─ app/
│  ├─ __init__.py       # application factory + registro de extensões
│  ├─ models.py         # definições de modelo
│  ├─ views.py          # rotas e controllers
│  ├─ auth.py           # lógica de autenticação
│  ├─ utils.py          # helpers
│  ├─ api/
│  │  ├─ __init__.py
│  │  └─ routes.py
│  ├─ templates/        # (opcional para APIs puras)
│  └─ static/           # (assets)
├─ tests/               # pytest/unittest
├─ migrations/          # Alembic
├─ instance/            # configs sensíveis por ambiente
│  └─ app.db
├─ .env                 # env vars locais (não commit)
├─ config.py            # configurações por classe
├─ requirements.txt
└─ run.py               # ponto de entrada
```

* Use nomes consistentes: `models.py`, `routes.py`, `forms.py`, `test_*.py`.
* Separe funcionalidades em módulos e pacotes (use `__init__.py`).
* Aplique **code splitting**: extraia funções reutilizáveis e use lazy loading quando fizer sentido.

## Padrões e Anti‑padrões

* **Padrões específicos Flask:**

  * **Application Factory** (já ilustrado acima).
  * **Blueprints** para features separadas.
* **Tarefas comuns:**

  * **DB:** Flask‑SQLAlchemy.
  * **Forms:** Flask‑WTF (CSRF automático).
  * **Auth:** Flask‑Login, RBAC ou JWT.
  * **APIs:** Flask‑RESTful ou similares (Marshmallow para serialização).
* **Anti‑padrões:**

  * Variáveis globais para estado.
  * Código “gordo” em models ou views.
  * Hardcode de configuração.

## Performance

* **Caching:** Flask‑Caching ou Redis.
* **Otimização DB:** índices e consultas.
* **Profiling:** identifique gargalos.
* **Lazy Loading** de recursos e assets.

## Segurança

* **XSS:** escape em templates (Jinja2 autoescape).
* **SQLi:** ORM/queries parametrizadas.
* **CSRF:** Flask‑WTF.
* **HTTPS:** para APIs e formulários.
* **Armazenamento:** bcrypt para senhas.
* **Rate Limiting** em endpoints críticos.

## Testes

* **Unitários:** pytest/unittest, mocks.
* **Integração:** DB e serviços externos.
* **E2E:** Selenium/Cypress (UI).
* Organize testes por funcionalidade e siga Arrange-Act-Assert.

## Ferramentas e Ambiente

* **venv** para isolamento.
* **pip** ou **poetry** para dependências.
* **Black** para formatação.
* **Flake8/Pylint** para lint.
* **Debugger:** `pdb`/`ipdb`.
* **WSGI:** Gunicorn ou uWSGI em produção.

