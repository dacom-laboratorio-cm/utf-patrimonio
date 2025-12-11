from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    nome = db.Column(db.String(128), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Usuario {self.username}>'

class ItemPatrimonio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tombo = db.Column(db.String(32), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    valor = db.Column(db.String(32), nullable=False)
    termo_data = db.Column(db.String(32), nullable=False)
    local = db.Column(db.String(32), nullable=False)
    responsavel = db.Column(db.String(128), nullable=False)
    observacao = db.Column(db.String(256), nullable=True)

    def __repr__(self):
        return f'<ItemPatrimonio {self.tombo} - {self.local}>'

class LogProcessamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    arquivo_pdf = db.Column(db.String(256), nullable=False)
    responsavel = db.Column(db.String(128), nullable=True)
    qtd_bens_pdf = db.Column(db.Integer, nullable=True)
    qtd_itens_extraidos = db.Column(db.Integer, nullable=True)
    divergencia = db.Column(db.Boolean, default=False)
    erro = db.Column(db.Text, nullable=True)
    local = db.Column(db.String(32), nullable=True)
    
    def __repr__(self):
        return f'<LogProcessamento {self.arquivo_pdf}>'

class ConferenciaPatrimonial(db.Model):
    __tablename__ = 'conferencia_patrimonial'
    id = db.Column(db.Integer, primary_key=True)
    local = db.Column(db.String(32), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    responsavel = db.Column(db.String(128))
    itens = db.relationship('ConferenciaPatrimonialItem', backref='conferencia', lazy=True)

class ConferenciaPatrimonialItem(db.Model):
    __tablename__ = 'conferencia_patrimonial_item'
    id = db.Column(db.Integer, primary_key=True)
    conferencia_id = db.Column(db.Integer, db.ForeignKey('conferencia_patrimonial.id'))
    item_patrimonio_id = db.Column(db.Integer, db.ForeignKey('item_patrimonio.id'), nullable=True)
    inconsistencia = db.Column(db.String(32))
    local_banco = db.Column(db.String(32))
    descricao = db.Column(db.Text)
    item_patrimonio = db.relationship('ItemPatrimonio', backref='conferencia_itens') 