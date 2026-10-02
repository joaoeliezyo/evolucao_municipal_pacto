"""Consultas do dashboard; evolução compara meses consecutivos, inclusive entre anos."""
from statistics import median

from sqlalchemy import select

from ..models import Municipio, Periodo, Posicao
from .import_service import MESES


def history(session, municipio_id=None):
    query = (select(Municipio.id, Municipio.nome_exibicao, Periodo.ano,
                    Periodo.mes, Posicao.posicao)
             .join(Posicao, Posicao.municipio_id == Municipio.id)
             .join(Periodo, Periodo.id == Posicao.periodo_id)
             .order_by(Periodo.ano, Periodo.mes, Municipio.nome_exibicao))
    if municipio_id is not None:
        query = query.where(Municipio.id == municipio_id)
    rows, previous = [], {}
    for mid, name, year, month, position in session.execute(query):
        key = year * 12 + month
        prior = previous.get((mid, key - 1))
        rows.append(dict(municipio_id=mid, nome=name, ano=year, mes=month,
                         periodo=f'{MESES[month - 1]}/{year}', posicao=position,
                         anterior=prior, evolucao=None if prior is None else prior - position))
        previous[mid, key] = position
    return rows


def evolution_order(row):
    return (row['evolucao'] is None, -(row['evolucao'] or 0), row['posicao'], row['nome'])


def dashboard(session, ano=None, mes=None, municipio_id=None):
    periods = session.execute(select(Periodo.ano, Periodo.mes)
                              .order_by(Periodo.ano, Periodo.mes)).all()
    years = sorted({p.ano for p in periods}, reverse=True)
    selected_year = ano if ano is not None else (years[0] if years else None)
    months = [p.mes for p in periods if p.ano == selected_year]
    selected_month = mes if mes is not None else (max(months) if months else None)
    municipalities = session.scalars(select(Municipio).order_by(Municipio.nome_exibicao)).all()
    all_rows = history(session)
    period_rows = [r for r in all_rows if r['ano'] == selected_year and r['mes'] == selected_month]
    period_ranking = sorted((r for r in period_rows if r['evolucao'] is not None),
                            key=evolution_order)
    ranks = {r['municipio_id']: index for index, r in enumerate(period_ranking, 1)}
    for row in period_rows:
        row['ranking_evolucao'] = ranks.get(row['municipio_id'])
    rows = [r for r in period_rows if municipio_id is None or r['municipio_id'] == municipio_id]
    rows.sort(key=evolution_order)
    table_rows = rows
    ranking = sorted((r for r in rows if r['evolucao'] is not None),
                     key=evolution_order)
    positive = [r for r in ranking if r['evolucao'] > 0]
    negative = sorted((r for r in ranking if r['evolucao'] < 0),
                      key=lambda r: (r['evolucao'], r['nome']))
    comparisons = [r['evolucao'] for r in ranking]
    counts = {'melhoraram': len(positive), 'pioraram': len(negative),
              'estaveis': sum(value == 0 for value in comparisons)}
    first_positions = {}
    year_counts = {}
    selected_ids = {r['municipio_id'] for r in rows}
    for point in all_rows:
        mid = point['municipio_id']
        if mid in selected_ids and point['ano'] == selected_year and point['mes'] <= selected_month:
            first_positions.setdefault(mid, point['posicao'])
            year_counts[mid] = year_counts.get(mid, 0) + 1
    accumulated = [first_positions[r['municipio_id']] - r['posicao'] for r in rows
                   if year_counts.get(r['municipio_id'], 0) > 1]
    kpis = dict(comparaveis=len(comparisons), sem_comparacao=len(rows) - len(comparisons),
                contagens=counts,
                percentuais={key: count * 100 / len(comparisons) if comparisons else None
                             for key, count in counts.items()},
                mediana=median(comparisons) if comparisons else None,
                melhor_posicao=min(rows, key=lambda r: (r['posicao'], r['nome'])) if rows else None,
                acumulada=median(accumulated) if accumulated else None,
                acumulada_comparaveis=len(accumulated),
                acumulada_sem_comparacao=len(rows) - len(accumulated))
    charts = []
    for row in rows:
        points = [r for r in all_rows if r['municipio_id'] == row['municipio_id']
                  and r['ano'] == selected_year and r['mes'] <= selected_month]
        by_month = {p['mes']: p['posicao'] for p in points}
        charts.append(dict(nome=row['nome'], labels=[MESES[m - 1] for m in range(1, selected_month + 1)],
                           values=[by_month.get(m) for m in range(1, selected_month + 1)]))
    return dict(anos=years, meses_disponiveis=months, ano=selected_year, mes=selected_month,
                municipios=municipalities, municipio_id=municipio_id, rows=rows, table_rows=table_rows,
                ranking=ranking, subida=positive[0] if positive else None,
                queda=negative[0] if negative else None, charts=charts, kpis=kpis)
