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
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, inconsistencia='ok', local_banco=local, descricao=descricao))
    # Salva itens encontrados em outro local
    for idx, t in enumerate(encontrados_erro_local):
        if t:
            local_banco = encontrados_erro_local_locais[idx] if idx < len(encontrados_erro_local_locais) else ''
            item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local_banco).first()
            descricao = item_banco.descricao if item_banco else None
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, inconsistencia='local_divergente', local_banco=local_banco, descricao=descricao))
    # Salva desconhecidos
    for idx, t in enumerate(desconhecidos):
        if t:
            descricao = descricoes_desconhecidos[idx] if idx < len(descricoes_desconhecidos) else ''
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, inconsistencia='local_divergente_desconhecida', local_banco=None, descricao=descricao))
    # Salva faltantes
    for t in faltantes:
        if t:
            item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local).first()
            descricao = item_banco.descricao if item_banco else None
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, inconsistencia='nao_encontrado', local_banco=local, descricao=descricao))
    # Salva itens sem etiqueta
    for desc in sem_etiqueta:
        if desc.strip():
            db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo='', inconsistencia='sem_etiqueta', local_banco=None, descricao=desc.strip()))
    db.session.commit()
    flash('Levantamento salvo com sucesso!')
    return redirect(url_for('patrimonio.levantamento_detalhe', levantamento_id=levantamento.id))

@bp.route('/levantamento/manual', methods=['GET', 'POST'])
def levantamento_manual():
    if 'itens' not in session:
        session['itens'] = []
    if 'local_manual' not in session:
        session['local_manual'] = ''
    if 'responsavel_manual' not in session:
        session['responsavel_manual'] = ''
    print('DEBUG[INICIO]: session[local_manual]=', session.get('local_manual'), 'session[itens]=', session.get('itens'), 'session[responsavel_manual]=', session.get('responsavel_manual'))
    mensagem = None
    editar_idx = request.args.get('editar')
    remover_idx = request.args.get('remover')
    # Buscar locais distintos do banco
    locais = db.session.query(ItemPatrimonio.local).distinct().all()
    locais = sorted([l[0] for l in locais if l[0]])
    if remover_idx is not None:
        try:
            idx = int(remover_idx)
            if 0 <= idx < len(session['itens']):
                session['itens'].pop(idx)
                session.modified = True
        except Exception:
            mensagem = 'Erro ao remover item.'
        print('DEBUG[REMOVER]: session[local_manual]=', session.get('local_manual'), 'session[itens]=', session.get('itens'))
        return redirect(url_for('patrimonio.levantamento_manual'))
    if editar_idx is not None:
        try:
            idx = int(editar_idx)
            if 0 <= idx < len(session['itens']):
                item_editar = session['itens'][idx]
            else:
                item_editar = None
        except Exception:
            item_editar = None
    else:
        item_editar = None
    if request.method == 'POST':
        print('DEBUG[POST]: request.form=', dict(request.form))
        if 'add_item' in request.form:
            tombo = request.form.get('tombo', '').strip()
            descricao = request.form.get('descricao', '').strip()
            local = request.form.get('local')
            responsavel = request.form.get('responsavel', '').strip()
            sem_etiqueta_flag = request.form.get('sem_etiqueta')
            # Salva local e responsável apenas no primeiro item
            if not session['local_manual']:
                session['local_manual'] = local
            if not session['responsavel_manual']:
                session['responsavel_manual'] = responsavel
            # Se checkbox sem etiqueta marcado, adiciona como sem etiqueta
            if sem_etiqueta_flag:
                session['itens'].append({'tombo': '', 'descricao': descricao})
                session.modified = True
            # Tombo obrigatório: 6 dígitos
            elif tombo and descricao:
                if not tombo.isdigit() or len(tombo) != 6:
                    mensagem = 'O tombo deve conter exatamente 6 dígitos.'
                else:
                    if request.form.get('editando_idx') != '':
                        try:
                            idx = int(request.form.get('editando_idx'))
                            if 0 <= idx < len(session['itens']):
                                session['itens'][idx] = {'tombo': tombo, 'descricao': descricao}
                                session.modified = True
                        except Exception:
                            mensagem = 'Erro ao editar item.'
                    else:
                        session['itens'].append({'tombo': tombo, 'descricao': descricao})
                        session.modified = True
            else:
                mensagem = 'Informe o número de tombo (6 dígitos) ou marque "Sem etiqueta" e preencha a descrição.'
            print('DEBUG[ADD_ITEM]: session[local_manual]=', session.get('local_manual'), 'session[itens]=', session.get('itens'), 'session[responsavel_manual]=', session.get('responsavel_manual'))
        elif 'salvar' in request.form:
            local = session.get('local_manual', '')
            responsavel = session.get('responsavel_manual', '')
            print('DEBUG[SALVAR]: local_manual=', local, 'session[itens]=', session.get('itens'), 'responsavel_manual=', responsavel)
            if not responsavel:
                mensagem = 'Informe o responsável pelo levantamento.'
                print('DEBUG[SALVAR][ERRO]: responsável não informado')
            elif local and session['itens']:
                # --- NOVA LÓGICA DE CLASSIFICAÇÃO ---
                tombos_lista = [item['tombo'] for item in session['itens'] if item['tombo']]
                descricoes_digitadas = {item['tombo']: item['descricao'] for item in session['itens'] if item['tombo']}
                sem_etiqueta = [item['descricao'] for item in session['itens'] if not item['tombo']]
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
                encontrados_correto = [(t, next((i.descricao for i in itens_banco_local if i.tombo == t), descricoes_digitadas.get(t, ''))) for t in tombos_lista if t in tombos_banco_local]
                # b) Encontrados em outro local
                encontrados_erro_local = [(t, local_erro_dict.get(t, ''), next((i.descricao for i in itens_banco_todos if i.tombo == t), descricoes_digitadas.get(t, ''))) for t in tombos_lista if t in tombos_banco_todos and t not in tombos_banco_local]
                # c) Desconhecidos
                tombos_desconhecidos = [t for t in tombos_lista if t not in tombos_banco_todos]
                desconhecidos = [(t, descricoes_digitadas.get(t, '')) for t in tombos_desconhecidos]
                # d) Faltantes
                faltantes = [(t, next((i.descricao for i in itens_banco_local if i.tombo == t), '')) for t in tombos_banco_local if t not in tombos_set]
                levantamento = Levantamento(local=local, responsavel=responsavel)
                db.session.add(levantamento)
                db.session.commit()
                # Salva encontrados corretos
                for t, descricao in encontrados_correto:
                    db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, descricao=descricao, inconsistencia='ok', local_banco=local))
                # Salva encontrados em outro local
                for t, local_banco, descricao in encontrados_erro_local:
                    db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, descricao=descricao, inconsistencia='local_divergente', local_banco=local_banco))
                # Salva desconhecidos
                for t, descricao in desconhecidos:
                    db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, descricao=descricao, inconsistencia='local_divergente_desconhecida', local_banco=None))
                # Salva faltantes
                for t, descricao in faltantes:
                    db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo=t, descricao=descricao, inconsistencia='nao_encontrado', local_banco=local))
                # Salva itens sem etiqueta
                for desc in sem_etiqueta:
                    if desc.strip():
                        db.session.add(LevantamentoItem(levantamento_id=levantamento.id, tombo='', descricao=desc.strip(), inconsistencia='sem_etiqueta', local_banco=None))
                db.session.commit()
                session.pop('itens')
                session.pop('local_manual')
                session.pop('responsavel_manual')
                print('DEBUG[SALVO]: levantamento_id=', levantamento.id)
                return redirect(url_for('patrimonio.levantamento_detalhe', levantamento_id=levantamento.id))
            else:
                mensagem = 'Informe o local, o responsável e adicione pelo menos um item.'
                print('DEBUG[SALVAR][ERRO]: local_manual=', local, 'session[itens]=', session.get('itens'), 'responsavel_manual=', responsavel)
    ultimo_descricao = session['itens'][-1]['descricao'] if session['itens'] else ''
    return render_template('levantamento_manual.html', itens=session['itens'], ultimo_descricao=ultimo_descricao, mensagem=mensagem, item_editar=item_editar, editando_idx=editar_idx, locais=locais, local_manual=session.get('local_manual', ''), responsavel_manual=session.get('responsavel_manual', ''))

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
    sort = request.args.get('sort', 'id')
    direction = request.args.get('direction', 'asc')
    sort_fields = {
        'tombo': LevantamentoItem.tombo,
        'descricao': LevantamentoItem.descricao,
        'inconsistencia': LevantamentoItem.inconsistencia,
        'local_banco': LevantamentoItem.local_banco,
        'id': LevantamentoItem.id
    }
    sort_col = sort_fields.get(sort, LevantamentoItem.id)
    query = LevantamentoItem.query.filter_by(levantamento_id=levantamento.id)
    if direction == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    itens = query.all()
    return render_template('levantamento_detalhe.html', levantamento=levantamento, itens=itens, sort=sort, direction=direction)

@bp.route('/levantamento/<int:levantamento_id>/editar', methods=['GET', 'POST'])
def editar_levantamento(levantamento_id):
    levantamento = Levantamento.query.get_or_404(levantamento_id)
    if request.method == 'POST':
        local = request.form.get('local', '').strip()
        responsavel = request.form.get('responsavel', '').strip()
        if not local or not responsavel:
            flash('Local e responsável são obrigatórios.')
        else:
            levantamento.local = local
            levantamento.responsavel = responsavel
            db.session.commit()
            flash('Levantamento atualizado com sucesso!')
            return redirect(url_for('patrimonio.levantamento_detalhe', levantamento_id=levantamento.id))
    return render_template('editar_levantamento.html', levantamento=levantamento)

@bp.route('/levantamento/<int:levantamento_id>/remover', methods=['POST'])
def remover_levantamento(levantamento_id):
    levantamento = Levantamento.query.get_or_404(levantamento_id)
    LevantamentoItem.query.filter_by(levantamento_id=levantamento.id).delete()
    db.session.delete(levantamento)
    db.session.commit()
    flash('Levantamento removido com sucesso!')
    return redirect(url_for('patrimonio.levantamentos'))

@bp.route('/levantamento/<int:levantamento_id>/item/<int:item_id>/editar', methods=['GET', 'POST'])
def editar_item_levantamento(levantamento_id, item_id):
    levantamento = Levantamento.query.get_or_404(levantamento_id)
    item = LevantamentoItem.query.get_or_404(item_id)
    if request.method == 'POST':
        tombo = request.form.get('tombo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        status = request.form.get('status', '').strip()
        local_banco = request.form.get('local_banco', '').strip() if status == 'encontrado_erro_local' else levantamento.local
        if status == 'sem_etiqueta':
            tombo = ''
        if status != 'sem_etiqueta' and (not tombo or not tombo.isdigit() or len(tombo) != 6):
            flash('O tombo deve conter exatamente 6 dígitos.')
        elif not descricao:
            flash('Descrição obrigatória.')
        else:
            item.tombo = tombo
            item.descricao = descricao
            item.inconsistencia = status
            item.local_banco = local_banco
            db.session.commit()
            flash('Item atualizado com sucesso!')
            return redirect(url_for('patrimonio.levantamento_detalhe', levantamento_id=levantamento.id))
    return render_template('editar_item_levantamento.html', levantamento=levantamento, item=item)

@bp.route('/levantamento/<int:levantamento_id>/item/<int:item_id>/remover', methods=['POST'])
def remover_item_levantamento(levantamento_id, item_id):
    item = LevantamentoItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item removido com sucesso!')
    return redirect(url_for('patrimonio.levantamento_detalhe', levantamento_id=levantamento_id)) 