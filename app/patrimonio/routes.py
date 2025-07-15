from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
from .. import db
from ..models import ItemPatrimonio, LogProcessamento, Levantamento, LevantamentoItem
from . import bp
from .services import processar_pdf
from .forms import UploadPDFForm, FiltroItensForm, LevantamentoForm

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def index():
    return redirect(url_for('patrimonio.itens'))

@bp.route('/upload', methods=['GET', 'POST'])
def upload():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    logs = []
    form = UploadPDFForm()
    if form.validate_on_submit():
        files = request.files.getlist('pdfs')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                resultado = processar_pdf(filepath)
                # Salvar log
                log = LogProcessamento(
                    arquivo_pdf=filename,
                    responsavel=resultado['responsavel'],
                    qtd_bens_pdf=resultado['qtd_bens'],
                    qtd_itens_extraidos=len(resultado['itens']),
                    divergencia=resultado['divergencia'],
                    erro=resultado['erro']
                )
                db.session.add(log)
                db.session.commit()
                # Salvar itens se não houver erro
                if not resultado['erro']:
                    for item in resultado['itens']:
                        existe = ItemPatrimonio.query.filter_by(
                            tombo=item[0], local=item[4], arquivo_pdf=filename
                        ).first()
                        if not existe:
                            db.session.add(ItemPatrimonio(
                                tombo=item[0], descricao=item[1], valor=item[2],
                                termo_data=item[3], local=item[4], responsavel=item[5],
                                arquivo_pdf=filename
                            ))
                    db.session.commit()
                logs.append({
                    'arquivo': filename,
                    'responsavel': resultado['responsavel'],
                    'qtd_bens': resultado['qtd_bens'],
                    'qtd_itens': len(resultado['itens']),
                    'divergencia': resultado['divergencia'],
                    'erro': resultado['erro']
                })
        flash('Processamento concluído!')
        return render_template('upload.html', logs=logs, form=form)
    return render_template('upload.html', logs=None, form=form)

@bp.route('/logs')
def logs():
    logs = LogProcessamento.query.order_by(LogProcessamento.id.desc()).all()
    return render_template('logs.html', logs=logs)

@bp.route('/itens/', defaults={'local': None, 'responsavel': None})
@bp.route('/itens/local/<local>/', defaults={'responsavel': None})
@bp.route('/itens/responsavel/<responsavel>/', defaults={'local': None})
@bp.route('/itens/local/<local>/responsavel/<responsavel>/')
def itens(local, responsavel):
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'id')
    direction = request.args.get('direction', 'desc')
    query = ItemPatrimonio.query
    if local:
        query = query.filter_by(local=local)
    if responsavel:
        query = query.filter_by(responsavel=responsavel)
    sort_fields = {
        'tombo': ItemPatrimonio.tombo,
        'descricao': ItemPatrimonio.descricao,
        'valor': ItemPatrimonio.valor,
        'termo_data': ItemPatrimonio.termo_data,
        'local': ItemPatrimonio.local,
        'responsavel': ItemPatrimonio.responsavel,
        'arquivo_pdf': ItemPatrimonio.arquivo_pdf,
        'id': ItemPatrimonio.id
    }
    sort_col = sort_fields.get(sort, ItemPatrimonio.id)
    if direction == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    tombo = request.args.get('tombo')
    if tombo:
        query = query.filter(ItemPatrimonio.tombo.contains(tombo))
    pagination = query.paginate(page=page, per_page=100, error_out=False)
    itens = pagination.items
    locais = db.session.query(ItemPatrimonio.local).distinct().all()
    responsaveis = db.session.query(ItemPatrimonio.responsavel).distinct().all()
    locais = sorted([l[0] for l in locais])
    responsaveis = sorted([r[0] for r in responsaveis])
    filtro_form = FiltroItensForm()
    filtro_form.local.choices = [('', 'Todos')] + [(l, l) for l in locais]
    filtro_form.responsavel.choices = [('', 'Todos')] + [(r, r) for r in responsaveis]
    return render_template('itens.html', itens=itens, locais=locais, responsaveis=responsaveis, pagination=pagination, sort=sort, direction=direction, filtro_local=local, filtro_responsavel=responsavel, filtro_form=filtro_form, tombo=tombo)

@bp.route('/levantamento', methods=['GET', 'POST'])
def levantamento():
    locais = db.session.query(ItemPatrimonio.local).distinct().all()
    locais = sorted([l[0] for l in locais])
    form = LevantamentoForm()
    form.local.choices = [(l, l) for l in locais]
    relatorio = None
    if form.validate_on_submit():
        local = form.local.data
        responsavel = form.responsavel.data
        # Processar tombos: aceita um por linha ou separados por vírgula
        tombos_input = form.tombos.data.replace(',', '\n')
        tombos_lista = [t.strip() for t in tombos_input.split('\n') if t.strip()]
        tombos_set = set(tombos_lista)
        # Buscar todos os itens do local no banco
        itens_banco_local = ItemPatrimonio.query.filter_by(local=local).all()
        tombos_banco_local = set(i.tombo for i in itens_banco_local)
        # Buscar todos os tombos do banco
        itens_banco_todos = ItemPatrimonio.query.filter(ItemPatrimonio.tombo.in_(tombos_set)).all()
        tombos_banco_todos = set(i.tombo for i in itens_banco_todos)
        # a) Encontrados no local correto
        encontrados_correto = [t for t in tombos_lista if t in tombos_banco_local]
        # b) Encontrados em outro local
        encontrados_erro_local = [t for t in tombos_lista if t in tombos_banco_todos and t not in tombos_banco_local]
        # c) Desconhecidos
        desconhecidos = [t for t in tombos_lista if t not in tombos_banco_todos]
        # d) Faltantes
        faltantes = [t for t in tombos_banco_local if t not in tombos_set]
        # Para mostrar o local real dos encontrados em outro local
        local_erro_dict = {i.tombo: i.local for i in itens_banco_todos if i.tombo in encontrados_erro_local}
        relatorio = {
            'local': local,
            'responsavel': responsavel,
            'encontrados_correto': encontrados_correto,
            'encontrados_erro_local': [(t, local_erro_dict.get(t, '')) for t in encontrados_erro_local],
            'desconhecidos': desconhecidos,
            'faltantes': faltantes,
            'tombos_digitados': tombos_lista
        }
    return render_template('levantamento.html', form=form, relatorio=relatorio)

@bp.route('/levantamento/salvar', methods=['POST'])
def salvar_levantamento():
    # Recebe dados do formulário oculto
    local = request.form.get('local')
    responsavel = request.form.get('responsavel')
    encontrados_correto = request.form.get('encontrados_correto', '').split(',') if request.form.get('encontrados_correto') else []
    encontrados_erro_local = request.form.get('encontrados_erro_local', '').split(',') if request.form.get('encontrados_erro_local') else []
    encontrados_erro_local_locais = request.form.get('encontrados_erro_local_locais', '').split(',') if request.form.get('encontrados_erro_local_locais') else []
    desconhecidos = request.form.get('desconhecidos', '').split(',') if request.form.get('desconhecidos') else []
    faltantes = request.form.get('faltantes', '').split(',') if request.form.get('faltantes') else []
    # Cria levantamento
    levantamento = Levantamento(local=local, responsavel=responsavel)
    db.session.add(levantamento)
    db.session.commit()
    # Salva itens encontrados corretos
    for t in encontrados_correto:
        if t:
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, status='encontrado_correto', local_banco=local))
    # Salva itens encontrados em outro local
    for idx, t in enumerate(encontrados_erro_local):
        if t:
            local_banco = encontrados_erro_local_locais[idx] if idx < len(encontrados_erro_local_locais) else ''
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, status='encontrado_erro_local', local_banco=local_banco))
    # Salva desconhecidos
    for t in desconhecidos:
        if t:
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, status='desconhecido', local_banco=None))
    # Salva faltantes
    for t in faltantes:
        if t:
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, status='faltante', local_banco=local))
    db.session.commit()
    flash('Levantamento salvo com sucesso!')
    return redirect(url_for('patrimonio.levantamento_detalhe', levantamento_id=levantamento.id))

@bp.route('/levantamentos')
def levantamentos():
    lista = Levantamento.query.order_by(Levantamento.data.desc()).all()
    return render_template('levantamentos.html', levantamentos=lista)

@bp.route('/levantamento/<int:levantamento_id>')
def levantamento_detalhe(levantamento_id):
    levantamento = Levantamento.query.get_or_404(levantamento_id)
    itens = LevantamentoItem.query.filter_by(levantamento_id=levantamento.id).all()
    return render_template('levantamento_detalhe.html', levantamento=levantamento, itens=itens) 