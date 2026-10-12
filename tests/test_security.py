from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.main import app
from app.services import import_service


def excel(rows):
    workbook = Workbook()
    workbook.active.title = 'Planilha1'
    workbook.active.append(('MUNICIPIO', 'POSIÇÃO', 'MÊS'))
    for row in rows:
        workbook.active.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_compressed_archive_is_bounded(monkeypatch):
    monkeypatch.setattr(import_service, 'MAX_EXPANDED_BYTES', 1024)
    data = BytesIO()
    with ZipFile(data, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('xl/sharedStrings.xml', b'a' * 2048)
    assert len(data.getvalue()) < 1024
    with pytest.raises(ValueError, match='descompactado'):
        import_service.parse_excel(data.getvalue(), 'bomb.xlsx', 2026, 0)


def test_archive_entry_count_is_bounded(monkeypatch):
    monkeypatch.setattr(import_service, 'MAX_ARCHIVE_ENTRIES', 1)
    with pytest.raises(ValueError, match='descompactado'):
        import_service.parse_excel(excel([('BETANIA', 1, 'JANEIRO')]), 'a.xlsx', 2026, 0)


def test_xml_entities_are_rejected():
    content = excel([('BETANIA', 1, 'JANEIRO')])
    data = BytesIO()
    with ZipFile(BytesIO(content)) as original, ZipFile(data, 'w', ZIP_DEFLATED) as archive:
        for entry in original.infolist():
            payload = original.read(entry)
            if entry.filename == 'xl/worksheets/sheet1.xml':
                payload = b'<!DOCTYPE worksheet [<!ENTITY injected "BETANIA">]>' + payload.replace(b'BETANIA', b'&injected;')
            archive.writestr(entry, payload)
    with pytest.raises(ValueError, match='Excel'):
        import_service.parse_excel(data.getvalue(), 'a.xlsx', 2026, 0)


def test_forged_sheet_dimensions_do_not_hide_extra_rows(monkeypatch):
    content = excel([('BETANIA', 1, 'JANEIRO'), ('BETANIA', 2, 'FEVEREIRO')])
    data = BytesIO()
    with ZipFile(BytesIO(content)) as original, ZipFile(data, 'w', ZIP_DEFLATED) as archive:
        for entry in original.infolist():
            payload = original.read(entry).replace(b'ref="A1:C3"', b'ref="A1:C1"')
            archive.writestr(entry, payload)
    monkeypatch.setattr(import_service, 'MAX_ROWS', 2)
    with pytest.raises(ValueError, match='linhas'):
        import_service.parse_excel(data.getvalue(), 'a.xlsx', 2026, 0)


def test_position_cannot_overflow_sqlite():
    with pytest.raises(ValueError, match='limite permitido'):
        import_service.parse_excel(excel([('BETANIA', 2**64, 'JANEIRO')]), 'a.xlsx', 2026, 0)


def test_security_headers_and_no_cache_for_review():
    with TestClient(app) as client:
        response = client.post('/imports/confirm', data={'token': 'unknown'})
        assert response.headers['x-content-type-options'] == 'nosniff'
        assert response.headers['x-frame-options'] == 'DENY'
        assert response.headers['referrer-policy'] == 'same-origin'
        assert response.headers['cache-control'] == 'no-store'
