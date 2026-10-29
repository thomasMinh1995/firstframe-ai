from copy import deepcopy
from io import BytesIO
from unicodedata import normalize
from uuid import uuid4

import pytest
from pypdf import PdfReader
from test_draft_runs import drafting, begin, complete
from test_projects import project_client
from test_screenplay_selection import written, select
from test_screenplays import edit
from app.api.routes import projects
from app.application import screenplay_pdf


def exported(client,p,selection=None):
    return client.get(f"/api/projects/{p['id']}/screenplay-selections/{selection or p['screenplay_handoff']['id']}/pdf")


def test_export_selected_snapshot_is_offline_immutable_and_deterministic(written):
    client,provider,p=written
    p=select(client,p)[0].json();original=deepcopy(p);calls=len(provider.requests)
    result=exported(client,p);assert result.status_code==200,result.text
    assert result.headers['content-type']=='application/pdf'
    assert result.headers['cache-control']=='no-store'
    assert result.headers['content-disposition'].endswith(p['screenplay_handoff']['id']+'.pdf"')
    pdf=PdfReader(BytesIO(result.content));text='\n'.join(page.extract_text() for page in pdf.pages)
    assert pdf.metadata.title==p['screenplay']['source_outline']['source']['draft']['title']
    assert 'Cha đặt thư.' in text and 'Không sao đâu cha ạ…' in text
    assert text.index('Cha đặt thư.') < text.index('Không sao đâu cha ạ…')
    assert 'Con gái' in text
    for page in pdf.pages:
        fonts=page['/Resources']['/Font'].get_object()
        assert any('/FontFile2' in font.get_object().get('/FontDescriptor',{}).get_object() for font in fonts.values() if font.get_object().get('/FontDescriptor'))
    data=edit(p);data['title']='Tên dự án mới không dùng';data['draft']['title']='Tên plan mới không dùng'
    data['screenplay']['scenes'][0]['blocks'][0]['text']='Nội dung mới không dùng'
    p=client.put(f"/api/projects/{p['id']}",json=data).json()
    assert exported(client,p).content==result.content
    assert client.get(f"/api/projects/{p['id']}").json()==p
    assert len(provider.requests)==calls
    history=next(v for v in p['screenplay_versions'] if v['screenplay']==original['screenplay'])
    p=select(client,p,history['id'])[0].json()
    assert exported(client,p).content==result.content
    assert exported(client,p,original['screenplay_handoff']['id']).content==result.content


def test_long_dialogue_repeats_speaker_and_keeps_vietnamese_and_literal_markup(written):
    client,_,p=written
    data=edit(p);scene=data['screenplay']['scenes'][1]
    scene['blocks'][0]['speaker']='Mẹ'
    scene['blocks'][0]['text']=normalize('NFD','Đừng vội, mẹ vẫn ở đây. ')*180+'<giữ nguyên & kết mở>'
    p=client.put(f"/api/projects/{p['id']}",json=data).json();p=select(client,p)[0].json()
    result=exported(client,p);assert result.status_code==200,result.text
    pages=PdfReader(BytesIO(result.content)).pages
    assert len(pages)>2
    assert 'Mẹ' in pages[0].extract_text(), 'long first block must use remaining space on the first page'
    for page in pages:
        text=page.extract_text()
        if 'Đừng' in text or '<giữ' in text:
            assert 'Mẹ' in text
        assert '\ufffd' not in text and '\u25a0' not in text
    text=' '.join(page.extract_text() for page in pages)
    assert 'Đừng vội, mẹ vẫn ở đây.' in text
    assert '<giữ nguyên & kết mở>' in text
    assert client.get(f"/api/projects/{p['id']}").json()==p


def test_missing_title_uses_only_snapshot_and_neutral_filename(written):
    client,_,p=written;p=select(client,p)[0].json()
    store=projects.get_project_store();raw=store.get(p['id'])
    raw['screenplay_selections'][0]['screenplay']['source_outline']['source']['draft']['title']=''
    store.save(raw,raw['revision']);p=client.get(f"/api/projects/{p['id']}").json()
    result=exported(client,p);assert result.status_code==200
    assert 'filename="screenplay-' in result.headers['content-disposition']
    assert not PdfReader(BytesIO(result.content)).metadata.title
    assert p['title'] not in PdfReader(BytesIO(result.content)).pages[0].extract_text()


def test_unknown_selection_and_export_failure_do_not_write(written,monkeypatch):
    client,_,p=written;p=select(client,p)[0].json()
    assert exported(client,p,str(uuid4())).status_code==404
    other=client.post('/api/projects').json()
    assert exported(client,other,p['screenplay_handoff']['id']).status_code==404
    def fail(_):raise OSError('Missing bundled font')
    monkeypatch.setattr(screenplay_pdf,'render_pdf',fail)
    assert exported(client,p).status_code==503
    assert client.get(f"/api/projects/{p['id']}").json()==p


def test_unsupported_glyph_is_reported_without_silent_replacement(written):
    client,_,p=written;data=edit(p)
    data['screenplay']['scenes'][0]['blocks'][0]['text']='Ký tự chưa hỗ trợ \U0001fae0'
    p=client.put(f"/api/projects/{p['id']}",json=data).json();p=select(client,p)[0].json()
    assert exported(client,p).status_code==422
    assert client.get(f"/api/projects/{p['id']}").json()==p


def test_idea_to_reviewed_draft_to_selected_pdf(drafting):
    client,providers,p,base,url,body=begin(drafting)
    run,candidate=complete(client,url)
    p=client.post(url+'/adopt',json={'revision':p['revision'],'candidate_revision':candidate['revision']}).json()
    assert p['screenplay_reviews']
    calls=[len(provider.requests) for provider in providers]
    p=select(client,p)[0].json()
    response=exported(client,p)
    assert response.status_code==200,response.text
    assert PdfReader(BytesIO(response.content)).pages
    assert [len(provider.requests) for provider in providers]==calls
    assert client.get(f"/api/projects/{p['id']}").json()==p


def test_bundled_fonts_cover_complete_vietnamese_alphabet():
    from reportlab.pdfbase import pdfmetrics
    screenplay_pdf.fonts()
    for name in ('Screenplay','ScreenplayBold'):
        glyphs=pdfmetrics.getFont(name).face.charToGlyph
        assert all(n in glyphs for n in [ord('đ'),ord('Đ'),*range(0x1ea0,0x1efa)])
