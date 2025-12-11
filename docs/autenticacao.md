# Autenticação

Sistema de autenticação minimalista para o projeto UTF-Patrimônio.

## Recursos

- Login/logout de usuários
- Cadastro de novos usuários
- Proteção de rotas com `@login_required`
- Senha criptografada com Werkzeug
- Sessões com "lembrar-me"

## Estrutura

```
app/
├── auth/
│   ├── __init__.py
│   ├── forms.py       # Formulários de login e cadastro
│   └── routes.py      # Rotas de autenticação
├── models.py          # Modelo Usuario
└── extensions.py      # LoginManager
```

## Uso

### Criar primeiro usuário

```bash
python3 criar_usuario.py
```

### Proteger rotas

```python
from flask_login import login_required

@bp.route('/rota-protegida')
@login_required
def minha_rota():
    return render_template('template.html')
```

### Acessar usuário logado

```python
from flask_login import current_user

@bp.route('/perfil')
@login_required
def perfil():
    return f'Olá, {current_user.nome}!'
```

## Rotas

- `/login` - Página de login
- `/logout` - Encerrar sessão
- `/register` - Cadastro de novos usuários

## Configuração

O sistema usa as configurações padrão do Flask-Login:

- `login_view`: `'auth.login'` - Rota de redirecionamento
- `login_message`: Mensagem exibida ao tentar acessar rota protegida
