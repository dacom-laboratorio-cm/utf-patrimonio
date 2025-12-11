from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired

class UploadPDFForm(FlaskForm):
    pdfs = FileField('Selecione um ou mais arquivos PDF', validators=[DataRequired()])
    submit = SubmitField('Importar')

class FiltroPatrimoniosForm(FlaskForm):
    local = SelectField('Local', choices=[], validate_choice=False)
    responsavel = SelectField('Responsável', choices=[], validate_choice=False)
    tombo = StringField('Tombo')
    submit = SubmitField('Filtrar')

class ConferenciaPatrimonialForm(FlaskForm):
    local = SelectField('Local', choices=[], validate_choice=False)
    novo_local = StringField('Cadastrar novo local (opcional)')
    responsavel = SelectField('Responsável', choices=[], validators=[DataRequired()], validate_choice=False)
    csvfile = FileField('Importar CSV de tombos (cabeçalho: tombo,descricao)')
    submit = SubmitField('Processar conferência') 