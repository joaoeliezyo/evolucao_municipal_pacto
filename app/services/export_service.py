"""Relatórios 16:10 com textos HTML/SVG pesquisáveis e captura PNG."""
import base64
from datetime import datetime
from html import escape
from io import BytesIO
from math import ceil
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore
from zipfile import ZipFile, ZIP_DEFLATED
from zoneinfo import ZoneInfo

from markupsafe import Markup
from playwright.sync_api import sync_playwright, Error as BrowserError

from .import_service import MESES

COLORS = ['#1558b0', '#15803d', '#be123c', '#7c3aed', '#b45309', '#0e7490',
          '#4338ca', '#a21caf', '#4d7c0f', '#c2410c', '#334155', '#047857']
EXPORT_SLOTS = BoundedSemaphore(2)


class ExportUnavailable(Exception):
    pass


def svg_chart(series, mini=False):
    width, height = (440, 90) if mini else (800, 640)
    positions = [v for s in series for v in s['values'] if v is not None]
    highest = max(positions, default=1)
    lowest = min(positions, default=1)
    spread = max(highest - lowest, 20)
    low = max(1, lowest - spread * .4) if mini else 1 - max(2, highest * .12)
    high = highest + spread * (.5 if mini else .08)
    left, right, top = (26, 26, 20) if mini else (62, 30, 30)
    bottom = height - (24 if mini else 145)
    n = len(series[0]['labels']) if series else 0
    x = lambda i: left + (width - left - right) * (i / (n - 1) if n > 1 else .5)
    y = lambda value: top + (bottom - top) * (value - low) / (high - low)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Histórico das posições">']
    out.append('<g font-family="Inter, Arial, sans-serif" fill="#21135b">')
    if not mini:
        for i in range(6):
            value = round(1 + (highest - 1) * i / 5)
            py = y(value)
            out.append(f'<line x1="{left}" y1="{py:.2f}" x2="{width-right}" y2="{py:.2f}" stroke="#e5e7eb"/>')
            out.append(f'<text x="{left-12}" y="{py+5:.2f}" text-anchor="end" font-size="16">{value}</text>')
    out.append(f'<line x1="{left}" y1="{bottom}" x2="{width-right}" y2="{bottom}" stroke="#e5e7eb"/>')
    for i, label in enumerate(series[0]['labels'] if series else []):
        out.append(f'<text x="{x(i):.2f}" y="{bottom+22}" text-anchor="middle" font-size="{12 if mini else 16}">{escape(label[:3].title())}</text>')
    for index, item in enumerate(series):
        color = '#1e40af' if mini else COLORS[index % len(COLORS)]
        path = []
        connected = False
        for i, value in enumerate(item['values']):
            if value is None:
                connected = False
                continue
            path.append(f'{"L" if connected else "M"}{x(i):.2f},{y(value):.2f}')
            connected = True
        out.append(f'<path d="{" ".join(path)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for i, value in enumerate(item['values']):
            if value is None:
                continue
            out.append(f'<circle cx="{x(i):.2f}" cy="{y(value):.2f}" r="{4 if mini else 3}" fill="{color}"/>')
            if mini:
                out.append(f'<text x="{x(i):.2f}" y="{y(value)-10:.2f}" text-anchor="middle" font-size="12" font-weight="bold">{value}º</text>')
    if not mini:
        for i, item in enumerate(sorted(enumerate(series), key=lambda pair: pair[1]['nome'])):
            index, data = item
            px, py = 24 + i % 3 * 260, height - 96 + i // 3 * 24
            out.append(f'<line x1="{px}" y1="{py}" x2="{px+20}" y2="{py}" stroke="{COLORS[index % len(COLORS)]}" stroke-width="3"/>')
            out.append(f'<text x="{px+26}" y="{py+4}" font-size="12">{escape(data["nome"])}</text>')
    out.append('</g></svg>')
    return Markup(''.join(out))


def build_report(context, templates, root):
    context = dict(context)
    context['meses'] = MESES
    context['history_svg'] = svg_chart(context['charts'])
    context['mini_svgs'] = [svg_chart([item], mini=True) for item in context['charts']]
    context['card_rows'] = max(1, ceil(len(context['rows']) / 3))
    context['card_columns'] = min(3, len(context['rows']))
    context['period_label'] = f'{MESES[context["mes"] - 1]} / {context["ano"]}'
    selected = next((m.nome_exibicao for m in context['municipios'] if m.id == context['municipio_id']), None)
    context['filter_label'] = selected or 'Todos os municípios'
    context['generated_at'] = datetime.now(ZoneInfo('America/Fortaleza')).strftime('%d/%m/%Y %H:%M')
    context['report_fonts'] = Markup((root / 'static' / 'fonts' / 'fonts.css').read_text().replace('url(./', f'url({(root / "static" / "fonts").as_uri()}/'))
    context['report_css'] = Markup((root / 'static' / 'report.css').read_text())
    html = templates.get_template('report.html').render(**context)
    for medal in ('ouro', 'prata', 'bronze'):
        data = base64.b64encode((root.parent / 'assets' / f'{medal}.svg').read_bytes()).decode()
        html = html.replace(f'/assets/{medal}.svg', f'data:image/svg+xml;base64,{data}')
    image = base64.b64encode((root / 'static' / 'brand' / 'brasao-pi.png').read_bytes()).decode()
    html = html.replace('/static/brand/brasao-pi.png', f'data:image/png;base64,{image}')
    return html


def render_export(html, format_name, filename_prefix):
    if not EXPORT_SLOTS.acquire(blocking=False):
        raise ExportUnavailable('Há exportações em andamento. Aguarde alguns segundos e tente novamente.')
    try:
        with TemporaryDirectory(prefix='pacto-export-') as temporary, sync_playwright() as playwright:
            executable = os.getenv('EXPORT_BROWSER_PATH') or next(
                (path for name in ('google-chrome', 'chromium', 'chromium-browser') if (path := shutil.which(name))), None)
            browser = playwright.chromium.launch(executable_path=executable, headless=True)
            try:
                page = browser.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=1)
                page.set_default_timeout(30000)
                page.route('http://**/*', lambda route: route.abort())
                page.route('https://**/*', lambda route: route.abort())
                report = Path(temporary) / 'report.html'
                report.write_text(html)
                page.goto(report.as_uri(), wait_until='load')
                page.evaluate('document.fonts.ready')
                # A missing card or clipped text must not produce an incomplete report.
                overflow = page.locator('.report-body').evaluate_all(
                    '(items) => items.some(item => item.scrollHeight > item.clientHeight + 2 || item.scrollWidth > item.clientWidth + 2)')
                if overflow:
                    raise ExportUnavailable('O conteúdo não coube no relatório. Tente filtrar um município.')
                if format_name == 'pdf':
                    return page.pdf(width='1600px', height='1000px', print_background=True,
                                    prefer_css_page_size=True, margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
                output = BytesIO()
                with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
                    for index, name in enumerate(('kpis', 'posicoes-historico', 'municipios')):
                        image = page.locator('.report-page').nth(index).screenshot(type='png', animations='disabled')
                        archive.writestr(f'{filename_prefix}-{index+1}-{name}.png', image)
                return output.getvalue()
            finally:
                browser.close()
    except BrowserError as exc:
        raise ExportUnavailable('Não foi possível gerar o relatório. Verifique a instalação do navegador de exportação.') from exc
    finally:
        EXPORT_SLOTS.release()
