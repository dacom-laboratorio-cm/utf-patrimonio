from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from ..models import Usuario

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class RegisterForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=64)])
    nome = StringField('Nome completo', validators=[DataRequired(), Length(min=3, max=128)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmar senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Cadastrar')
    
    def validate_username(self, username):
        user = Usuario.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este usuário já existe.')


class UserForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=64)])
    nome = StringField('Nome completo', validators=[DataRequired(), Length(min=3, max=128)])
    password = PasswordField('Senha (deixe em branco para manter)', validators=[Length(min=6, max=128)])
    submit = SubmitField('Salvar')

    def __init__(self, original_username=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if self.original_username and username.data == self.original_username:
            return
        user = Usuario.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este usuário já existe.')
