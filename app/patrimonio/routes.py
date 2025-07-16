from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
from .. import db
from ..models import ItemPatrimonio, LogProcessamento, Levantamento, LevantamentoItem
from . import bp
from .services import processar_pdf
from .forms import UploadPDFForm, FiltroItensForm, LevantamentoForm
import csv
from io import StringIO, TextIOWrapper
from zoneinfo import ZoneInfo

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def index():
    return render_template('index.html')

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
                    'erro': resultado['erro'],
                    'itens': resultado['itens']  # Lista de tuplas (tombo, descricao, ...)
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
        tombos_lista = []
        descricoes_csv = {}
        sem_etiqueta = []
        # Processar CSV se enviado
        if form.csvfile.data:
            file = form.csvfile.data
            stream = TextIOWrapper(file.stream, encoding='utf-8')
            reader = csv.reader(stream)
            header = next(reader, None)  # Ignora o cabeçalho
            for row in reader:
                if not row or len(row) < 2:
                    continue
                tombo = row[0].strip()
                descricao = row[1].strip()
                if tombo.isdigit():
                    tombos_lista.append(tombo)
                    if descricao:
                        descricoes_csv[tombo] = descricao
                else:
                    # Item sem etiqueta de tombo
                    sem_etiqueta.append(descricao or '(sem descrição)')
            print('DEBUG - Tombos lidos do CSV:', tombos_lista)
            print('DEBUG - Descrições lidas do CSV:', descricoes_csv)
            print('DEBUG - Itens sem etiqueta:', sem_etiqueta)
        # Processar tombos do textarea (adiciona ao que veio do CSV)
        tombos_input = form.tombos.data.replace(',', '\n') if form.tombos.data else ''
        for t in [t.strip() for t in tombos_input.split('\n') if t.strip()]:
            if t not in tombos_lista:
                tombos_lista.append(t)
        tombos_set = set(tombos_lista)
        # Buscar todos os itens do local no banco
        itens_banco_local = ItemPatrimonio.query.filter_by(local=local).all()
        tombos_banco_local = set(i.tombo for i in itens_banco_local)
        # Buscar todos os tombos do banco
        itens_banco_todos = ItemPatrimonio.query.filter(ItemPatrimonio.tombo.in_(tombos_set)).all()
        tombos_banco_todos = set(i.tombo for i in itens_banco_todos)
        # Para mostrar o local real dos encontrados em outro local
        local_erro_dict = {i.tombo: i.local for i in itens_banco_todos if i.tombo in [t for t in tombos_lista if t in tombos_banco_todos and t not in tombos_banco_local]}
        # a) Encontrados no local correto
        encontrados_correto = [(t, next((i.descricao for i in itens_banco_local if i.tombo == t), '')) for t in tombos_lista if t in tombos_banco_local]
        # b) Encontrados em outro local
        encontrados_erro_local = [(t, local_erro_dict.get(t, ''), next((i.descricao for i in itens_banco_todos if i.tombo == t), '')) for t in tombos_lista if t in tombos_banco_todos and t not in tombos_banco_local]
        # c) Desconhecidos
        tombos_desconhecidos = [t for t in tombos_lista if t not in tombos_banco_todos]
        desconhecidos = [(t, descricoes_csv.get(t, '')) for t in tombos_desconhecidos]
        # d) Faltantes
        faltantes = [(t, next((i.descricao for i in itens_banco_local if i.tombo == t), '')) for t in tombos_banco_local if t not in tombos_set]
        relatorio = {
            'local': local,
            'responsavel': responsavel,
            'encontrados_correto': encontrados_correto,
            'encontrados_erro_local': encontrados_erro_local,
            'desconhecidos': desconhecidos,
            'faltantes': faltantes,
            'tombos_digitados': tombos_lista,
            'sem_etiqueta': sem_etiqueta
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
    desconhecidos_raw = request.form.get('desconhecidos', '')
    desconhecidos = []
    descricoes_desconhecidos = []
    if desconhecidos_raw:
        for item in desconhecidos_raw.split(';'):
            if not item.strip():
                continue
            parts = item.split('|', 1)
            desconhecidos.append(parts[0])
            descricoes_desconhecidos.append(parts[1] if len(parts) > 1 else '')
    faltantes = request.form.get('faltantes', '').split(',') if request.form.get('faltantes') else []
    sem_etiqueta = request.form.get('sem_etiqueta', '').split(';') if request.form.get('sem_etiqueta') else []
    # Cria levantamento
    levantamento = Levantamento(local=local, responsavel=responsavel)
    db.session.add(levantamento)
    db.session.commit()
    # Salva itens encontrados corretos
    for t in encontrados_correto:
        if t:
            item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local).first()
            descricao = item_banco.descricao if item_banco else None
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, status='encontrado_correto', local_banco=local, descricao=descricao))
    # Salva itens encontrados em outro local
    for idx, t in enumerate(encontrados_erro_local):
        if t:
            local_banco = encontrados_erro_local_locais[idx] if idx < len(encontrados_erro_local_locais) else ''
            item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local_banco).first()
            descricao = item_banco.descricao if item_banco else None
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, status='encontrado_erro_local', local_banco=local_banco, descricao=descricao))
    # Salva desconhecidos
    for idx, t in enumerate(desconhecidos):
        if t:
            descricao = descricoes_desconhecidos[idx] if idx < len(descricoes_desconhecidos) else ''
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, status='desconhecido', local_banco=None, descricao=descricao))
    # Salva faltantes
    for t in faltantes:
        if t:
            item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local).first()
            descricao = item_banco.descricao if item_banco else None
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, status='faltante', local_banco=local, descricao=descricao))
    # Salva itens sem etiqueta
    for desc in sem_etiqueta:
        if desc.strip():
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo='', status='sem_etiqueta', local_banco=None, descricao=desc.strip()))
    db.session.commit()
    flash('Levantamento salvo com sucesso!')
    return redirect(url_for('patrimonio.levantamento_detalhe', levantamento_id=levantamento.id))

@bp.route('/levantamentos')
def levantamentos():
    lista = Levantamento.query.order_by(Levantamento.data.desc()).all()
    for l in lista:
        if l.data.tzinfo is None:
            l.data = l.data.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('America/Sao_Paulo'))
        else:
            l.data = l.data.astimezone(ZoneInfo('America/Sao_Paulo'))
    return render_template('levantamentos.html', levantamentos=lista)

@bp.route('/levantamento/<int:levantamento_id>')
def levantamento_detalhe(levantamento_id):
    levantamento = Levantamento.query.get_or_404(levantamento_id)
    if levantamento.data.tzinfo is None:
        levantamento.data = levantamento.data.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('America/Sao_Paulo'))
    else:
        levantamento.data = levantamento.data.astimezone(ZoneInfo('America/Sao_Paulo'))
    itens = LevantamentoItem.query.filter_by(levantamento_id=levantamento.id).all()
    return render_template('levantamento_detalhe.html', levantamento=levantamento, itens=itens) 