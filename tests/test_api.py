import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.database import Base,Meta,TABLES,Roster,add_record
from backend.app.main import app,db_session
from backend.app import services
from test_scheduler import fixture_data

@pytest.fixture
def client():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine);Factory=sessionmaker(engine,expire_on_commit=False)
    data,_=fixture_data(3)
    with Factory.begin() as db:
        db.add(Meta(id=1,revision=1))
        for table,items in data.items():
            for item in items:
                body=dict(item);id=body.pop('id');add_record(db,table,body,id)
    def dependency():
        with Factory.begin() as db:yield db
    app.dependency_overrides[db_session]=dependency
    with TestClient(app) as c:yield c
    app.dependency_overrides.clear();engine.dispose()

def test_generate_publish_and_change_transaction(client):
    response=client.post('/api/rosters/generate',json={'month':'2026-11'});assert response.status_code==200,response.text
    r=response.json();assert r['publishable']
    published=client.post(f"/api/rosters/{r['id']}/publish",json={'expected_revision':r['revision']});assert published.status_code==200
    r=published.json();day='2026-11-10';target=next(a for a in r['allocations'] if a['date']==day)
    body={'expected_revision':r['revision'],'employee_id':target['employee_id'],'date':day,'kind':'leave','repair':True}
    p=client.post(f"/api/rosters/{r['id']}/changes/preview",json=body);assert p.status_code==200,p.text
    preview=p.json();assert preview['result']['publishable'];assert any(f['code']=='COVERAGE' for f in preview['before_findings'])
    applied=client.post(f"/api/rosters/{r['id']}/changes/{preview['change_id']}/apply",json={'expected_revision':r['revision']});assert applied.status_code==200,applied.text
    new=applied.json();assert new['revision']==r['revision']+1
    assert [a for a in new['allocations'] if a['date']!=day]==[a for a in r['allocations'] if a['date']!=day]
    assert len(client.get('/api/data').json()['absences'])==1
    again=client.post(f"/api/rosters/{r['id']}/changes/{preview['change_id']}/apply",json={'expected_revision':r['revision']});assert again.status_code==409
    assert client.get(f"/api/rosters/{r['id']}").json()['revision']==new['revision']
    assert 'Employee,Date,Status' in client.get(f"/api/rosters/{r['id']}/export").text

def test_unsafe_manual_edit_blocked_and_no_absence_saved(client):
    r=client.post('/api/rosters/generate',json={'month':'2026-11'}).json();a=next(a for a in r['allocations'] if a['date'] in r['days'])
    p=client.post(f"/api/rosters/{r['id']}/changes/preview",json={'expected_revision':r['revision'],'employee_id':a['employee_id'],'date':a['date'],'kind':'leave','repair':False}).json()
    assert not p['result']['publishable']
    result=client.post(f"/api/rosters/{r['id']}/changes/{p['change_id']}/apply",json={'expected_revision':r['revision']})
    assert result.status_code==409;assert client.get('/api/data').json()['absences']==[]

def test_input_edit_invalidates_preview_and_published_roster(client):
    r=client.post('/api/rosters/generate',json={'month':'2026-11'}).json()
    r=client.post(f"/api/rosters/{r['id']}/publish",json={'expected_revision':r['revision']}).json()
    a=next(a for a in r['allocations'] if a['date']=='2026-11-03')
    p=client.post(f"/api/rosters/{r['id']}/changes/preview",json={'expected_revision':r['revision'],'employee_id':a['employee_id'],'date':a['date']}).json()
    saved=client.post('/api/entities/holidays',json={'name':'New holiday','date':'2026-11-20'});assert saved.status_code==200
    assert client.get(f"/api/rosters/{r['id']}").json()['stale']
    assert client.post(f"/api/rosters/{r['id']}/changes/{p['change_id']}/apply",json={'expected_revision':r['revision']}).status_code==409

def test_relationship_validation_and_crud(client):
    assert client.post('/api/entities/assignments',json={'employee_id':999,'duty_id':1}).status_code==422
    response=client.post('/api/entities/processes',json={'name':'Returns'});assert response.status_code==200
    id=response.json()['id'];assert client.put(f'/api/entities/processes/{id}',json={'name':'Returns handling','active':False}).status_code==200
    assert any(p['name']=='Returns handling' and not p['active'] for p in client.get('/api/data').json()['processes'])
    assert client.post('/api/rosters/generate',json={'month':'2026-99'}).status_code==422
