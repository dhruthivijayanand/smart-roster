"""Relational persistence with explicit foreign keys and immutable roster snapshots."""
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, event, Column, Integer, String, JSON, ForeignKey, UniqueConstraint, select, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
load_dotenv()
URL = os.getenv('DATABASE_URL', 'sqlite:///./roster.db')
if URL.startswith('postgres://'):
    URL = URL.replace('postgres://', 'postgresql+psycopg://', 1)
if URL.startswith('postgresql://'):
    URL = URL.replace('postgresql://', 'postgresql+psycopg://', 1)
if os.getenv('APP_ENV') == 'production' and URL.startswith('sqlite'):
    raise RuntimeError('Production requires persistent PostgreSQL via DATABASE_URL')
engine = create_engine(URL, connect_args={'check_same_thread': False} if URL.startswith('sqlite') else {}, pool_pre_ping=True)
if URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
Base = declarative_base()
Session = sessionmaker(engine, expire_on_commit=False)

class Meta(Base):
    __tablename__ = 'metadata_revision'
    id = Column(Integer, primary_key=True)
    revision = Column(Integer, nullable=False, default=1)

TABLES = {}
REFERENCES = {
 'employees': {'pod_id':'pods'}, 'brands': {'calendar_id':'calendars'},
 'duties': {'brand_id':'brands','process_id':'processes','calendar_id':'calendars'},
 'assignments': {'employee_id':'employees','duty_id':'duties'},
 'absences': {'employee_id':'employees'}, 'overrides': {'duty_id':'duties'},
 'pods': {'lead_id':'employees'}}
# Entity attributes live in validated JSON; identity and relationships are real SQL columns.
for name in ['pods','employees','calendars','brands','processes','duties','assignments','absences','holidays','overrides']:
    attrs = {'__tablename__':name,'id':Column(Integer,primary_key=True),'data':Column(JSON,nullable=False)}
    for key, target in REFERENCES.get(name, {}).items():
        attrs[key] = Column(Integer,ForeignKey(target+'.id'),nullable=key in ('lead_id','calendar_id') and name != 'brands',index=True)
    if name == 'duties': attrs['__table_args__'] = (UniqueConstraint('brand_id','process_id'),)
    if name == 'assignments': attrs['__table_args__'] = (UniqueConstraint('employee_id','duty_id'),)
    TABLES[name] = type(name.title(),(Base,),attrs)

class Roster(Base):
    __tablename__ = 'rosters'
    id = Column(Integer,primary_key=True)
    month = Column(String(7),index=True,nullable=False)
    revision = Column(Integer,nullable=False,default=1)
    input_revision = Column(Integer,nullable=False)
    status = Column(String(30),nullable=False,default='draft')
    payload = Column(JSON,nullable=False)
    created_at = Column(String,nullable=False)

class Allocation(Base):
    __tablename__ = 'allocations'
    id = Column(Integer,primary_key=True)
    roster_id = Column(Integer,ForeignKey('rosters.id'),index=True,nullable=False)
    employee_id = Column(Integer,ForeignKey('employees.id'),index=True,nullable=False)
    duty_id = Column(Integer,ForeignKey('duties.id'),index=True,nullable=False)
    date = Column(String(10),index=True,nullable=False)
    __table_args__ = (UniqueConstraint('roster_id','employee_id','duty_id','date'),)

class Change(Base):
    __tablename__ = 'changes'
    id = Column(Integer,primary_key=True)
    roster_id = Column(Integer,ForeignKey('rosters.id'),index=True,nullable=False)
    base_revision = Column(Integer,nullable=False)
    input_revision = Column(Integer,nullable=False)
    status = Column(String(20),nullable=False,default='preview')
    payload = Column(JSON,nullable=False)
    created_at = Column(String,nullable=False)

class Audit(Base):
    __tablename__ = 'audit'
    id = Column(Integer,primary_key=True)
    roster_id = Column(Integer,ForeignKey('rosters.id'),nullable=True,index=True)
    action = Column(String,nullable=False)
    detail = Column(JSON,nullable=False)
    created_at = Column(String,nullable=False)

def now(): return datetime.now(timezone.utc).isoformat()
def snapshot(db):
    return {name:[dict(row.data,id=row.id) for row in db.scalars(select(model).order_by(model.id))] for name,model in TABLES.items()}
def add_record(db, name, data, id=None):
    values = {key:data.get(key) for key in REFERENCES.get(name,{})}
    row = TABLES[name](data=data,**values)
    if id is not None: row.id=id
    db.add(row); db.flush()
    return row

def init_db():
    with engine.begin() as connection:
        if connection.dialect.name == 'postgresql':
            connection.execute(text('SELECT pg_advisory_xact_lock(731923)'))
        Base.metadata.create_all(connection)
        if not connection.execute(select(Meta.id).where(Meta.id == 1)).first():
            connection.execute(Meta.__table__.insert().values(id=1,revision=1))
