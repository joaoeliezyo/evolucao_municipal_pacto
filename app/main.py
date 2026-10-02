from contextlib import asynccontextmanager
from pathlib import Path
from secrets import token_urlsafe
from time import time
from typing import Literal

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, delete
from sqlalchemy.exc import SQLAlchemyError

from .database import Base, engine, SessionLocal
from .models import ImportacaoPendente, Municipio, Periodo, Posicao
from .services.import_service import MESES, parse_excel, conflicts, persist
from .schemas import ImportResult
from .services.ranking_service import dashboard, history

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title='Dashboard Pacto pelo Piauí', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
app.mount('/assets', StaticFiles(directory=ROOT.parent / 'assets'), name='assets')
templates = Jinja2Templates(directory=ROOT / 'templates')


def render(request, error=None, success=None, preview=None, ano='', mes=0, status=200):
    with SessionLocal() as session:
        periods = session.execute(
            select(Periodo, func.count(Posicao.id)).outerjoin(Posicao, Posicao.periodo_id == Periodo.id)
            .group_by(Periodo.id).order_by(Periodo.ano.desc(), Periodo.mes.desc())
        ).all()
    return templates.TemplateResponse(request=request, name='imports.html', context={
        'meses': MESES, 'periodos': periods, 'error': error, 'success': success,
        'preview': preview, 'ano': ano, 'mes': mes,
    }, status_code=status)


@app.get('/imports', response_class=HTMLResponse)
def index(request: Request):
    return render(request)


def review(filename, records, existing, token):
    return {'arquivo': filename, 'quantidade': len(records),
            'meses': sorted({r['mes'] for r in records}),
            'existentes': sorted(existing), 'token': token}


@app.post('/imports', response_class=HTMLResponse)
async def upload(request: Request, arquivo: UploadFile = File(...), ano: int = Form(...),
                 mes: int = Form(0)):
    try:
        content = await arquivo.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError('O arquivo deve ter no máximo 10 MB.')
        filename = Path(arquivo.filename or '').name
        records = parse_excel(content, filename, ano, mes)
        token = token_urlsafe(32)
        with SessionLocal() as session, session.begin():
            existing = conflicts(session, ano, records)
            session.execute(delete(ImportacaoPendente).where(
                ImportacaoPendente.expira_em <= int(time())))
            session.add(ImportacaoPendente(token=token, arquivo_nome=filename,
                        ano=ano, mes=mes, conteudo=content, expira_em=int(time()) + 1800))
        return render(request, ano=ano, mes=mes,
                      preview=review(filename, records, existing, token))
    except ValueError as exc:
        return render(request, error=str(exc), ano=ano, mes=mes, status=400)
    except SQLAlchemyError:
        return render(request, error='Não foi possível preparar a revisão. Tente novamente.',
                      ano=ano, mes=mes, status=409)
    finally:
        await arquivo.close()


@app.get('/imports/confirm', include_in_schema=False)
def confirmation_page():
    return RedirectResponse(url='/dashboard', status_code=303)


@app.post('/imports/confirm', response_class=HTMLResponse)
def confirm_import(request: Request, token: str = Form(...), substituir: bool = Form(False)):
    preview = None
    ano, mes = '', 0
    try:
        with SessionLocal() as session:
            pending = session.get(ImportacaoPendente, token)
            if pending is None or pending.expira_em <= int(time()):
                raise ValueError('A revisão expirou ou já foi confirmada. Selecione o arquivo e valide novamente.')
            ano, mes, filename = pending.ano, pending.mes, pending.arquivo_nome
            records = parse_excel(pending.conteudo, filename, ano, mes)
            existing = conflicts(session, ano, records)
            preview = review(filename, records, existing, token)
        with SessionLocal() as session:
            persist(session, ano, filename, records, replace=substituir, pending_token=token)
        latest_month = max(r['mes'] for r in records)
        return RedirectResponse(url=f'/dashboard?ano={ano}&mes={latest_month}', status_code=303)
    except ValueError as exc:
        return render(request, error=str(exc), ano=ano, mes=mes, preview=preview, status=400)
    except SQLAlchemyError:
        return render(request, error='Não foi possível gravar os dados. A importação foi cancelada.',
                      ano=ano, mes=mes, preview=preview, status=409)


@app.post('/api/imports', response_model=ImportResult)
async def import_api(arquivo: UploadFile = File(...), ano: int = Form(...),
                     mes: int = Form(0), confirmar: bool = Form(False),
                     substituir: bool = Form(False)):
    """Valida o Excel; confirmar=true grava e substituir=true autoriza substituição."""
    try:
        content = await arquivo.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise HTTPException(status_code=413, detail='O arquivo deve ter no máximo 10 MB.')
        filename = Path(arquivo.filename or '').name
        records = parse_excel(content, filename, ano, mes)
        with SessionLocal() as session:
            existing = sorted(conflicts(session, ano, records))
        if confirmar:
            if existing and not substituir:
                raise HTTPException(status_code=409, detail={
                    'mensagem': 'Confirme a substituição das competências existentes.',
                    'competencias_existentes': existing,
                })
            with SessionLocal() as session:
                persist(session, ano, filename, records, replace=substituir)
        return ImportResult(
            status='importado' if confirmar else 'validado', arquivo=filename,
            ano=ano, quantidade=len(records), meses=sorted({r['mes'] for r in records}),
            competencias_existentes=existing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=409, detail='Não foi possível gravar os dados. A importação foi cancelada.') from exc
    finally:
        await arquivo.close()


def dashboard_context(ano=None, mes=0, municipio_id=0):
    if ano is not None and not 1900 <= ano <= 2100:
        raise HTTPException(400, 'Ano inválido.')
    if not 0 <= mes <= 12:
        raise HTTPException(400, 'Mês inválido.')
    mes = mes or None
    municipio_id = municipio_id or None
    with SessionLocal() as session:
        if municipio_id is not None and session.get(Municipio, municipio_id) is None:
            raise HTTPException(404, 'Município não encontrado.')
        context = dashboard(session, ano, mes, municipio_id)
    return context


@app.get('/', response_class=HTMLResponse)
@app.get('/dashboard', response_class=HTMLResponse)
def dashboard_page(request: Request, ano: int | None = None,
                   mes: int = 0, municipio_id: int = 0):
    context = dashboard_context(ano, mes, municipio_id)
    return templates.TemplateResponse(request=request, name='dashboard.html',
                                      context={**context, 'meses': MESES})


@app.get('/municipios/{municipio_id}', response_class=HTMLResponse)
def municipality_page(request: Request, municipio_id: int):
    with SessionLocal() as session:
        municipality = session.get(Municipio, municipio_id)
        if municipality is None:
            raise HTTPException(404, 'Município não encontrado.')
        rows = history(session, municipio_id)
        name = municipality.nome_exibicao
    points = {(r['ano'] * 12 + r['mes'] - 1): r for r in rows}
    keys = range(min(points), max(points) + 1) if points else []
    chart = dict(nome=name,
                 labels=[f'{MESES[k % 12]}/{k // 12}' for k in keys],
                 values=[points[k]['posicao'] if k in points else None for k in keys])
    return templates.TemplateResponse(request=request, name='municipio.html',
                                      context={'nome': name, 'rows': rows, 'charts': [chart]})


@app.get('/api/exports/{formato}')
def export_dashboard(formato: Literal['png', 'pdf'], ano: int | None = None,
                     mes: int = 0, municipio_id: int = 0):
    from .services.export_service import build_report, render_export, ExportUnavailable
    context = dashboard_context(ano, mes, municipio_id)
    if not context['rows']:
        raise HTTPException(400, 'Não há dados para exportar com os filtros selecionados.')
    prefix = f'pacto-{context["ano"]}-{context["mes"]:02d}'
    if context['municipio_id']:
        prefix += f'-municipio-{context["municipio_id"]}'
    try:
        report = build_report(context, templates.env, ROOT)
        result = render_export(report, formato, prefix)
    except ExportUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    extension = 'zip' if formato == 'png' else 'pdf'
    return Response(content=result, media_type='application/zip' if formato == 'png' else 'application/pdf',
                    headers={'Content-Disposition': f'attachment; filename="{prefix}.{extension}"',
                             'Cache-Control': 'no-store'})
