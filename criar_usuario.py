#!/usr/bin/env python3
"""
Script para criar usuário admin inicial
"""
from app import create_app, db
from app.models import Usuario

def criar_usuario_admin():
    app = create_app()
    with app.app_context():
        username = input('Username: ')
        nome = input('Nome completo: ')
        password = input('Senha: ')
        
        if Usuario.query.filter_by(username=username).first():
            print(f'Usuário {username} já existe.')
            return
        
        user = Usuario(username=username, nome=nome)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f'Usuário {username} criado com sucesso!')

if __name__ == '__main__':
    criar_usuario_admin()
