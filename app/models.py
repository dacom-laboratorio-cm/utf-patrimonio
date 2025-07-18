from . import db
from datetime import datetime

class ItemPatrimonio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tombo = db.Column(db.String(32), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    valor = db.Column(db.String(32), nullable=False)
    termo_data = db.Column(db.String(32), nullable=False)
    local = db.Column(db.String(32), nullable=False)
    responsavel = db.Column(db.String(128), nullable=False)
    arquivo_pdf = db.Column(db.String(256), nullable=False)

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
    
    def __repr__(self):
        return f'<LogProcessamento {self.arquivo_pdf}>'

class Levantamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    local = db.Column(db.String(32), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    responsavel = db.Column(db.String(128))
    itens = db.relationship('LevantamentoItem', backref='levantamento', lazy=True)

class LevantamentoItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    levantamento_id = db.Column(db.Integer, db.ForeignKey('levantamento.id'))
    tombo = db.Column(db.String(32), nullable=False)
    inconsistencia = db.Column(db.String(32))  # 'ok', 'local_divergente', 'local_divergente_desconhecida', 'faltante', 'sem_etiqueta'
    local_banco = db.Column(db.String(32))  # Local cadastrado no banco (se houver)
    descricao = db.Column(db.Text)  # Descrição do item desconhecido (se fornecida) 