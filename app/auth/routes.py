from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from .. import db
from ..models import Usuario
from . import bp
from .forms import LoginForm, RegisterForm, UserForm

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('patrimonio.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos.')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('patrimonio.index')
        return redirect(next_page)
    
    return render_template('login.html', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('patrimonio.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = Usuario(username=form.username.data, nome=form.nome.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Cadastro realizado com sucesso!')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)


@bp.route('/usuarios')
@login_required
def usuarios():
    usuarios = Usuario.query.order_by(Usuario.username.asc()).all()
    return render_template('usuarios.html', usuarios=usuarios)


@bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
def usuario_novo():
    form = UserForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash('Senha obrigatória para novo usuário.')
            return render_template('usuario_form.html', form=form, titulo='Novo usuário')
        user = Usuario(username=form.username.data, nome=form.nome.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Usuário criado com sucesso.')
        return redirect(url_for('auth.usuarios'))
    return render_template('usuario_form.html', form=form, titulo='Novo usuário')


@bp.route('/usuarios/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
def usuario_editar(user_id):
    user = Usuario.query.get_or_404(user_id)
    form = UserForm(original_username=user.username, obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.nome = form.nome.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('Usuário atualizado com sucesso.')
        return redirect(url_for('auth.usuarios'))
    return render_template('usuario_form.html', form=form, titulo='Editar usuário')


@bp.route('/usuarios/<int:user_id>/remover', methods=['POST'])
@login_required
def usuario_remover(user_id):
    user = Usuario.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Usuário removido com sucesso.')
    return redirect(url_for('auth.usuarios'))
