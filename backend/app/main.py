from contextlib import asynccontextmanager
from pathlib import Path
import os,secrets,threading,csv,io
from fastapi import FastAPI,HTTPException,Header,Depends
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .database import init_db,Session,Meta,Roster,Audit,snapshot
from .seed import seed
from .schemas import Generate,Edit,Revision
from . import services
from .domain import month_days

@asynccontextmanager
async def lifespan(app):
    init_db()
    if os.getenv('DEMO_SEED','true').lower()=='true':
        with Session.begin() as db: seed(db)
    yield

app=FastAPI(title='DataStraw Smart Roster',version='1.0.0',lifespan=lifespan)
solver_lock=threading.Lock()

def db_session():
    with Session.begin() as db:
        try: yield db
        except ValidationError as e: raise HTTPException(422,str(e))
        except IntegrityError: raise HTTPException(409,'Record conflicts with a relationship or uniqueness constraint')

def manager(x_manager_token: str | None=Header(default=None)):
    token=os.getenv('MANAGER_TOKEN','')
    if token and not secrets.compare_digest(token,x_manager_token or ''): raise HTTPException(401,'Manager token required')

@app.get('/api/health')
def health(db=Depends(db_session)):
    return {'status':'ok','database':bool(db.get(Meta,1)),'authentication':bool(os.getenv('MANAGER_TOKEN'))}

@app.get('/api/data')
def data(db=Depends(db_session)):
    return {**snapshot(db),'revision':services.current_revision(db)}

@app.post('/api/entities/{table}',dependencies=[Depends(manager)])
def create(table:str,body:dict,db=Depends(db_session)):
    return services.save_record(db,table,body)

@app.put('/api/entities/{table}/{id}',dependencies=[Depends(manager)])
def edit(table:str,id:int,body:dict,db=Depends(db_session)):
    return services.save_record(db,table,body,id)

@app.get('/api/rosters')
def rosters(month:str|None=None,db=Depends(db_session)):
    q=select(Roster).order_by(Roster.id.desc())
    if month: q=q.where(Roster.month==month)
    return [{'id':r.id,'month':r.month,'status':r.status,'revision':r.revision,'created_at':r.created_at,'summary':r.payload['summary']} for r in db.scalars(q)]

@app.get('/api/rosters/{id}')
def roster(id:int,db=Depends(db_session)): return services.view(db,services.roster_or_404(db,id))

@app.post('/api/rosters/generate',dependencies=[Depends(manager)])
def generate(body:Generate,db=Depends(db_session)):
    try: month_days(body.month)
    except ValueError as e: raise HTTPException(422,str(e))
    if not solver_lock.acquire(blocking=False): raise HTTPException(429,'A roster is being generated. Please retry shortly.')
    try: return services.generate(db,body.month)
    finally: solver_lock.release()

@app.post('/api/rosters/{id}/validate')
def validate_roster(id:int,db=Depends(db_session)):
    r=services.roster_or_404(db,id)
    result=services.enrich(snapshot(db),r.payload)
    return dict(result,stale=r.input_revision!=services.current_revision(db))

@app.post('/api/rosters/{id}/changes/preview',dependencies=[Depends(manager)])
def preview(id:int,body:Edit,db=Depends(db_session)):
    if not solver_lock.acquire(blocking=False): raise HTTPException(429,'Solver is busy. Retry shortly.')
    try: return services.preview(db,id,body)
    finally: solver_lock.release()

@app.post('/api/rosters/{id}/changes/{change_id}/apply',dependencies=[Depends(manager)])
def apply(id:int,change_id:int,body:Revision,db=Depends(db_session)): return services.apply_change(db,id,change_id,body.expected_revision)

@app.post('/api/rosters/{id}/publish',dependencies=[Depends(manager)])
def publish(id:int,body:Revision,db=Depends(db_session)): return services.publish(db,id,body.expected_revision)

@app.get('/api/audit')
def audit(db=Depends(db_session)):
    return [{'id':r.id,'roster_id':r.roster_id,'action':r.action,'detail':r.detail,'created_at':r.created_at} for r in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(100))]

@app.get('/api/rosters/{id}/export')
def export(id:int,db=Depends(db_session)):
    r=services.roster_or_404(db,id); data=snapshot(db)
    names={e['id']:e['name'] for e in data['employees']}
    buf=io.StringIO(); writer=csv.writer(buf); writer.writerow(['Employee','Date','Status'])
    for item in r.payload['statuses']:
        name=names[item['employee_id']]
        if name.startswith(('=','+','-','@')): name="'"+name
        writer.writerow([name,item['date'],item['status']])
    return Response(buf.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename=roster-{r.month}.csv'})

DIST=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if DIST.exists():
    app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')
    @app.get('/')
    def home(): return FileResponse(DIST/'index.html')
