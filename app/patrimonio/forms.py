from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired

class UploadPDFForm(FlaskForm):
    pdfs = FileField('Selecione um ou mais arquivos PDF', validators=[DataRequired()])
    submit = SubmitField('Importar')

class FiltroItensForm(FlaskForm):
    local = SelectField('Local', choices=[], validate_choice=False)
    responsavel = SelectField('Responsável', choices=[], validate_choice=False)
    tombo = StringField('Tombo')
    submit = SubmitField('Filtrar')

class ConferenciaPatrimonialForm(FlaskForm):
    local = SelectField('Local', choices=[], validators=[DataRequired()])
    responsavel = StringField('Responsável', validators=[DataRequired()])
    tombos = TextAreaField('Tombos encontrados (um por linha ou separados por vírgula)', validators=[])
    csvfile = FileField('Importar CSV de tombos (cabeçalho: tombo,descricao)')
    submit = SubmitField('Processar conferência') 