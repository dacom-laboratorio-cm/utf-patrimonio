from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from .. import db
from ..models import ItemPatrimonio, LogProcessamento, ConferenciaPatrimonial, ConferenciaPatrimonialItem, Usuario
from . import bp
from .services import processar_pdf
from .forms import UploadPDFForm, ConferenciaPatrimonialForm, FiltroPatrimoniosForm
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
@login_required
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
                    erro=resultado['erro'],
                    local=resultado['itens'][0][4] if resultado['itens'] else None
                )
                db.session.add(log)
                db.session.commit()
                # Salvar itens se não houver erro
                if not resultado['erro']:
                    for item in resultado['itens']:
                        existe = ItemPatrimonio.query.filter_by(
                            tombo=item[0], local=item[4], observacao=filename
                        ).first()
                        if not existe:
                            db.session.add(ItemPatrimonio(
                                tombo=item[0], descricao=item[1], valor=item[2],
                                termo_data=item[3], local=item[4], responsavel=item[5],
                                observacao=filename
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
@login_required
def logs():
    sort = request.args.get('sort', 'id')
    direction = request.args.get('direction', 'desc')
    sort_fields = {
        'id': LogProcessamento.id,
        'arquivo_pdf': LogProcessamento.arquivo_pdf,
        'local': LogProcessamento.local,
        'responsavel': LogProcessamento.responsavel,
        'qtd_bens_pdf': LogProcessamento.qtd_bens_pdf,
        'qtd_itens_extraidos': LogProcessamento.qtd_itens_extraidos,
        'divergencia': LogProcessamento.divergencia,
        'erro': LogProcessamento.erro
    }
    sort_col = sort_fields.get(sort, LogProcessamento.id)
    if direction == 'asc':
        query = LogProcessamento.query.order_by(sort_col.asc())
    else:
        query = LogProcessamento.query.order_by(sort_col.desc())
    logs = query.all()
    return render_template('logs.html', logs=logs, sort=sort, direction=direction)

@bp.route('/patrimonios/', defaults={'local': None, 'responsavel': None})
@bp.route('/patrimonios/local/<local>/', defaults={'responsavel': None})
@bp.route('/patrimonios/responsavel/<responsavel>/', defaults={'local': None})
@bp.route('/patrimonios/local/<local>/responsavel/<responsavel>/')
@login_required
def patrimonios(local, responsavel):
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
        'observacao': ItemPatrimonio.observacao,
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
    patrimonios = pagination.items
    locais = db.session.query(ItemPatrimonio.local).distinct().all()
    responsaveis = db.session.query(ItemPatrimonio.responsavel).distinct().all()
    locais = sorted([l[0] for l in locais])
    responsaveis = sorted([r[0] for r in responsaveis])
    filtro_form = FiltroPatrimoniosForm()
    filtro_form.local.choices = [('', 'Todos')] + [(l, l) for l in locais]
    filtro_form.responsavel.choices = [('', 'Todos')] + [(r, r) for r in responsaveis]
    return render_template('patrimonios.html', patrimonios=patrimonios, locais=locais, responsaveis=responsaveis, pagination=pagination, sort=sort, direction=direction, filtro_local=local, filtro_responsavel=responsavel, filtro_form=filtro_form, tombo=tombo)

@bp.route('/conferencia_patrimonial', methods=['GET', 'POST'])
@login_required
def conferencia_patrimonial():
    locais = db.session.query(ItemPatrimonio.local).distinct().all()
    locais = sorted([l[0] for l in locais if l[0]])
    form = ConferenciaPatrimonialForm()
    usuarios = Usuario.query.order_by(Usuario.nome.asc()).all()
    form.responsavel.choices = [(u.nome, u.nome) for u in usuarios] or [(current_user.nome, current_user.nome)]
    if not form.responsavel.data:
        form.responsavel.data = current_user.nome
    form.local.choices = [(l, l) for l in locais] + [('Outro', 'Outro')]
    relatorio = None
    if form.validate_on_submit():
        local_input = form.novo_local.data.strip() if form.novo_local.data else ''
        local = local_input or form.local.data
        responsavel = form.responsavel.data
        if not local:
            flash('Informe um local ou cadastre um novo.')
            return render_template('conferencia_patrimonial.html', form=form, relatorio=None)
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
    return render_template('conferencia_patrimonial.html', form=form, relatorio=relatorio)

@bp.route('/conferencia_patrimonial/salvar', methods=['POST'])
@login_required
def salvar_conferencia_patrimonial():
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
    # Cria conferencia_patrimonial
    conferencia_patrimonial = ConferenciaPatrimonial(local=local, responsavel=responsavel)
    db.session.add(conferencia_patrimonial)
    db.session.commit()
    # Salva itens encontrados corretos
    for t in encontrados_correto:
        if t:
            item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local).first()
            if not item_banco:
                # Cria o item se não existir
                item_banco = ItemPatrimonio(tombo=t, descricao='', valor='0', termo_data='', local=local, responsavel='', observacao='obtido de conferência manual')
                db.session.add(item_banco)
                db.session.flush()
            db.session.add(ConferenciaPatrimonialItem(conferencia_id=conferencia_patrimonial.id, item_patrimonio_id=item_banco.id, inconsistencia='ok', local_banco=local, descricao=item_banco.descricao))
    # Salva itens encontrados em outro local
    for idx, t in enumerate(encontrados_erro_local):
        if t:
            local_banco = encontrados_erro_local_locais[idx] if idx < len(encontrados_erro_local_locais) else ''
            item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local_banco).first()
            if not item_banco:
                item_banco = ItemPatrimonio(tombo=t, descricao='', valor='0', termo_data='', local=local_banco, responsavel='', observacao='obtido de conferência manual')
                db.session.add(item_banco)
                db.session.flush()
            db.session.add(ConferenciaPatrimonialItem(conferencia_id=conferencia_patrimonial.id, item_patrimonio_id=item_banco.id, inconsistencia='local_divergente', local_banco=local_banco, descricao=item_banco.descricao))
    # Salva desconhecidos
    for idx, t in enumerate(desconhecidos):
        if t:
            descricao = descricoes_desconhecidos[idx] if idx < len(descricoes_desconhecidos) else ''
            item_banco = ItemPatrimonio.query.filter_by(tombo=t).first()
            if not item_banco:
                item_banco = ItemPatrimonio(
                    tombo=t, 
                    descricao=descricao, 
                    valor='0', 
                    termo_data='', 
                    local=local, 
                    responsavel=responsavel, 
                    observacao='Item identificado em conferência'
                )
                db.session.add(item_banco)
                db.session.flush()
            db.session.add(ConferenciaPatrimonialItem(
                conferencia_id=conferencia_patrimonial.id, 
                item_patrimonio_id=item_banco.id, 
                inconsistencia='item_novo', 
                local_banco=None, 
                descricao=descricao
            ))
    # Salva faltantes
    for t in faltantes:
        if t:
            item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local).first()
            if not item_banco:
                item_banco = ItemPatrimonio(tombo=t, descricao='', valor='0', termo_data='', local=local, responsavel='', observacao='obtido de conferência manual')
                db.session.add(item_banco)
                db.session.flush()
            db.session.add(ConferenciaPatrimonialItem(conferencia_id=conferencia_patrimonial.id, item_patrimonio_id=item_banco.id, inconsistencia='nao_encontrado', local_banco=local, descricao=item_banco.descricao))
    # Salva itens sem etiqueta
    for desc in sem_etiqueta:
        if desc.strip():
            # Para itens sem etiqueta, não há tombo, então não cria ItemPatrimonio
            db.session.add(ConferenciaPatrimonialItem(conferencia_id=conferencia_patrimonial.id, item_patrimonio_id=None, inconsistencia='sem_etiqueta', local_banco=None, descricao=desc.strip()))
    db.session.commit()
    flash('Conferencia Patrimonial salva com sucesso!')
    return redirect(url_for('patrimonio.conferencia_patrimonial_detalhe', conferencia_patrimonial_id=conferencia_patrimonial.id))

@bp.route('/conferencia_patrimonial/manual', methods=['GET', 'POST'])
@login_required
def conferencia_patrimonial_manual():
    if 'itens' not in session:
        session['itens'] = []
    if 'local_manual' not in session:
        session['local_manual'] = ''
    if 'responsavel_manual' not in session:
        session['responsavel_manual'] = current_user.nome
    print('DEBUG[INICIO]: session[local_manual]=', session.get('local_manual'), 'session[itens]=', session.get('itens'), 'session[responsavel_manual]=', session.get('responsavel_manual'))
    mensagem = None
    editar_idx = request.args.get('editar')
    remover_idx = request.args.get('remover')
    # Buscar locais distintos do banco
    locais = db.session.query(ItemPatrimonio.local).distinct().all()
    locais = sorted([l[0] for l in locais if l[0]])
    usuarios = Usuario.query.order_by(Usuario.nome.asc()).all()
    if remover_idx is not None:
        try:
            idx = int(remover_idx)
            if 0 <= idx < len(session['itens']):
                session['itens'].pop(idx)
                session.modified = True
        except Exception:
            mensagem = 'Erro ao remover item.'
        print('DEBUG[REMOVER]: session[local_manual]=', session.get('local_manual'), 'session[itens]=', session.get('itens'))
        return redirect(url_for('patrimonio.conferencia_patrimonial_manual'))
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
            novo_local = request.form.get('novo_local', '').strip()
            responsavel = request.form.get('responsavel', '').strip()
            sem_etiqueta_flag = request.form.get('sem_etiqueta')
            # Prioriza novo local informado
            if novo_local:
                local = novo_local
            # Salva local e responsável apenas no primeiro item
            if not session['local_manual'] and local:
                session['local_manual'] = local
            if responsavel:
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
                mensagem = 'Informe o responsável pela conferencia_patrimonial.'
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
                conferencia_patrimonial = ConferenciaPatrimonial(local=local, responsavel=responsavel)
                db.session.add(conferencia_patrimonial)
                db.session.commit()
                
                # Salva encontrados corretos
                for t, descricao in encontrados_correto:
                    item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local).first()
                    db.session.add(ConferenciaPatrimonialItem(
                        conferencia_id=conferencia_patrimonial.id, 
                        item_patrimonio_id=item_banco.id if item_banco else None,
                        descricao=descricao, 
                        inconsistencia='ok', 
                        local_banco=local
                    ))
                
                # Salva encontrados em outro local
                for t, local_banco, descricao in encontrados_erro_local:
                    item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local_banco).first()
                    db.session.add(ConferenciaPatrimonialItem(
                        conferencia_id=conferencia_patrimonial.id, 
                        item_patrimonio_id=item_banco.id if item_banco else None,
                        descricao=descricao, 
                        inconsistencia='local_divergente', 
                        local_banco=local_banco
                    ))
                
                # Salva desconhecidos - Cria ItemPatrimonio primeiro
                for t, descricao in desconhecidos:
                    novo_item = ItemPatrimonio(
                        tombo=t,
                        descricao=descricao,
                        valor='0',
                        termo_data='',
                        local=local,
                        responsavel=responsavel,
                        observacao='Item identificado em conferência manual'
                    )
                    db.session.add(novo_item)
                    db.session.flush()
                    db.session.add(ConferenciaPatrimonialItem(
                        conferencia_id=conferencia_patrimonial.id, 
                        item_patrimonio_id=novo_item.id,
                        descricao=descricao, 
                        inconsistencia='item_novo', 
                        local_banco=None
                    ))
                
                # Salva faltantes
                for t, descricao in faltantes:
                    item_banco = ItemPatrimonio.query.filter_by(tombo=t, local=local).first()
                    db.session.add(ConferenciaPatrimonialItem(
                        conferencia_id=conferencia_patrimonial.id, 
                        item_patrimonio_id=item_banco.id if item_banco else None,
                        descricao=descricao, 
                        inconsistencia='nao_encontrado', 
                        local_banco=local
                    ))
                
                # Salva itens sem etiqueta - não cria ItemPatrimonio
                for desc in sem_etiqueta:
                    if desc.strip():
                        db.session.add(ConferenciaPatrimonialItem(
                            conferencia_id=conferencia_patrimonial.id, 
                            item_patrimonio_id=None,
                            descricao=desc.strip(), 
                            inconsistencia='sem_etiqueta', 
                            local_banco=None
                        ))
                
                db.session.commit()
                session.pop('itens')
                session.pop('local_manual')
                session.pop('responsavel_manual')
                print('DEBUG[SALVO]: conferencia_patrimonial_id=', conferencia_patrimonial.id)
                return redirect(url_for('patrimonio.conferencia_patrimonial_detalhe', conferencia_patrimonial_id=conferencia_patrimonial.id))
            else:
                mensagem = 'Informe o local, o responsável e adicione pelo menos um item.'
                print('DEBUG[SALVAR][ERRO]: local_manual=', local, 'session[itens]=', session.get('itens'), 'responsavel_manual=', responsavel)
    ultimo_descricao = session['itens'][-1]['descricao'] if session['itens'] else ''
    return render_template('conferencia_patrimonial_manual.html', itens=session['itens'], ultimo_descricao=ultimo_descricao, mensagem=mensagem, item_editar=item_editar, editando_idx=editar_idx, locais=locais, local_manual=session.get('local_manual', ''), responsavel_manual=session.get('responsavel_manual', ''), usuarios=usuarios)

@bp.route('/conferencias_patrimoniais')
@login_required
def conferencias_patrimoniais():
    sort = request.args.get('sort', 'data')
    direction = request.args.get('direction', 'desc')
    sort_fields = {
        'id': ConferenciaPatrimonial.id,
        'local': ConferenciaPatrimonial.local,
        'responsavel': ConferenciaPatrimonial.responsavel,
        'data': ConferenciaPatrimonial.data
    }
    sort_col = sort_fields.get(sort, ConferenciaPatrimonial.data)
    if direction == 'asc':
        query = ConferenciaPatrimonial.query.order_by(sort_col.asc())
    else:
        query = ConferenciaPatrimonial.query.order_by(sort_col.desc())
    lista = query.all()
    for l in lista:
        if l.data.tzinfo is None:
            l.data = l.data.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('America/Sao_Paulo'))
        else:
            l.data = l.data.astimezone(ZoneInfo('America/Sao_Paulo'))
    return render_template('conferencias_patrimoniais.html', conferencias_patrimoniais=lista, sort=sort, direction=direction)

@bp.route('/conferencia_patrimonial/<int:conferencia_patrimonial_id>')
@login_required
def conferencia_patrimonial_detalhe(conferencia_patrimonial_id):
    conferencia_patrimonial = ConferenciaPatrimonial.query.get_or_404(conferencia_patrimonial_id)
    if conferencia_patrimonial.data.tzinfo is None:
        conferencia_patrimonial.data = conferencia_patrimonial.data.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('America/Sao_Paulo'))
    else:
        conferencia_patrimonial.data = conferencia_patrimonial.data.astimezone(ZoneInfo('America/Sao_Paulo'))
    sort = request.args.get('sort', 'id')
    direction = request.args.get('direction', 'asc')
    sort_fields = {
        # 'tombo': ConferenciaPatrimonialItem.tombo,  # Removido pois não existe mais
        'descricao': ConferenciaPatrimonialItem.descricao,
        'inconsistencia': ConferenciaPatrimonialItem.inconsistencia,
        'local_banco': ConferenciaPatrimonialItem.local_banco,
        'id': ConferenciaPatrimonialItem.id
    }
    sort_col = sort_fields.get(sort, ConferenciaPatrimonialItem.id)
    query = ConferenciaPatrimonialItem.query.filter_by(conferencia_id=conferencia_patrimonial.id)
    if direction == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    itens = query.all()
    return render_template('conferencia_patrimonial_detalhe.html', conferencia_patrimonial=conferencia_patrimonial, itens=itens, sort=sort, direction=direction)

@bp.route('/conferencia_patrimonial/<int:conferencia_patrimonial_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_conferencia_patrimonial(conferencia_patrimonial_id):
    conferencia_patrimonial = ConferenciaPatrimonial.query.get_or_404(conferencia_patrimonial_id)
    if request.method == 'POST':
        local = request.form.get('local', '').strip()
        responsavel = request.form.get('responsavel', '').strip()
        if not local or not responsavel:
            flash('Local e responsável são obrigatórios.')
        else:
            conferencia_patrimonial.local = local
            conferencia_patrimonial.responsavel = responsavel
            db.session.commit()
            flash('Conferencia Patrimonial atualizada com sucesso!')
            return redirect(url_for('patrimonio.conferencia_patrimonial_detalhe', conferencia_patrimonial_id=conferencia_patrimonial.id))
    return render_template('editar_conferencia_patrimonial.html', conferencia_patrimonial=conferencia_patrimonial)

@bp.route('/conferencia_patrimonial/<int:conferencia_patrimonial_id>/remover', methods=['POST'])
@login_required
def remover_conferencia_patrimonial(conferencia_patrimonial_id):
    conferencia_patrimonial = ConferenciaPatrimonial.query.get_or_404(conferencia_patrimonial_id)
    ConferenciaPatrimonialItem.query.filter_by(conferencia_id=conferencia_patrimonial.id).delete()
    db.session.delete(conferencia_patrimonial)
    db.session.commit()
    flash('Conferencia Patrimonial removida com sucesso!')
    return redirect(url_for('patrimonio.conferencias_patrimoniais'))

@bp.route('/conferencia_patrimonial/<int:conferencia_patrimonial_id>/item/<int:item_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_item_conferencia_patrimonial(conferencia_patrimonial_id, item_id):
    conferencia_patrimonial = ConferenciaPatrimonial.query.get_or_404(conferencia_patrimonial_id)
    item = ConferenciaPatrimonialItem.query.get_or_404(item_id)
    if request.method == 'POST':
        tombo = request.form.get('tombo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        status = request.form.get('status', '').strip()
        local_banco = request.form.get('local_banco', '').strip() if status == 'encontrado_erro_local' else conferencia_patrimonial.local
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
            return redirect(url_for('patrimonio.conferencia_patrimonial_detalhe', conferencia_patrimonial_id=conferencia_patrimonial.id))
    return render_template('editar_item_conferencia_patrimonial.html', conferencia_patrimonial=conferencia_patrimonial, item=item)

@bp.route('/conferencia_patrimonial/<int:conferencia_patrimonial_id>/item/<int:item_id>/remover', methods=['POST'])
@login_required
def remover_item_conferencia_patrimonial(conferencia_patrimonial_id, item_id):
    item = ConferenciaPatrimonialItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item removido com sucesso!')
    return redirect(url_for('patrimonio.conferencia_patrimonial_detalhe', conferencia_patrimonial_id=conferencia_patrimonial_id)) 