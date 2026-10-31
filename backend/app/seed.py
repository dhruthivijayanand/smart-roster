"""Reproducible fictional data: 36 employees, 25 brands, 80% single primary owner."""
from .database import add_record,TABLES
from .schemas import SCHEMAS
from sqlalchemy import select, text

def seed(db):
    if db.bind.dialect.name == 'postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(731924)'))
    if db.scalar(select(TABLES['employees'].id).limit(1)): return
    def add(table, **data):
        obj=SCHEMAS[table].model_validate(data).model_dump(mode='json')
        return add_record(db,table,obj).id
    pods=[add('pods',name=name) for name in ['North studio','Growth desk','Care collective']]
    calendars=[]
    calendars.append(add('calendars',name='Every day',weekdays=list(range(7)),holidays_off=False))
    calendars.append(add('calendars',name='Daily except holidays',weekdays=list(range(7)),holidays_off=True))
    calendars.append(add('calendars',name='Monday–Saturday',weekdays=list(range(6)),holidays_off=True))
    names=['Aarav Mehta','Ananya Rao','Dev Shah','Isha Nair','Kabir Sen','Leela Das','Mira Kapoor','Neel Bose','Ojas Patel','Pia Jain','Ravi Menon','Sara Roy','Tara Sethi','Vihaan Joshi','Yash Arora','Zoya Khan','Aditi Rao','Arjun Das','Diya Sen','Kiran Nair','Maya Shah','Nikhil Bose','Pari Mehta','Rehan Jain','Sana Kapoor','Tanvi Menon','Ved Roy','Zara Patel','Ira Sethi','Rohan Joshi','Anika Arora','Dhruv Khan','Esha Rao','Farhan Das','Gauri Sen','Harsh Nair']
    employees=[add('employees',name=name,pod_id=pods[i//12],preferred_off=[i%7]) for i,name in enumerate(names)]
    for i,lead in enumerate([1,13,25],1):
        pod=db.get(TABLES['pods'],pods[i-1]); pod.data={**pod.data,'lead_id':employees[lead-1]}; pod.lead_id=employees[lead-1]
    processes=[add('processes',name=name) for name in ['Customer Support','Abandoned Cart','Retention','NDR']]
    brands=['Cedar & Clay','Northform','Luma Skin','Moss & Moon','Kettle Club','Sunday Loom','Pawfolk','Rooted Ritual','Aero Lane','Kindred Home','Bloom Theory','Daily Grain','Halo Goods','Indigo Nest','Juniper Labs','Kin Supply','Little Orbit','Meridian Co','Nectar Works','Oak & Ember','Prism Living','Quiet Coast','Riverstone','Solstice Wear','Terra Table']
    for i,name in enumerate(brands):
        bid=add('brands',name=name,calendar_id=calendars[0 if i<8 else (1 if i<14 else 2)])
        for p in range(1,5):
            jid=add('duties',brand_id=bid,process_id=processes[p-1],calendar_id=calendars[2] if p==4 and i%3==0 else None,minimum=2 if i==20 and p==1 else 1,effort=1 if i<20 else 2)
            if i<20: owners=[i+1]
            else:
                team=[[21,22,23],[24,25],[26,27],[28,29,30],[31,32]][i-20]
                owners=team[:2] if i==20 and p==1 else [team[(p-1)%len(team)]]
            for e in owners: add('assignments',employee_id=employees[e-1],duty_id=jid)
            for e in [33,34,35,36]: add('assignments',employee_id=employees[e-1],duty_id=jid,role='backup')
    add('holidays',name='Demo holiday (fictional)',date='2026-11-12')
    add('absences',employee_id=employees[1],starts='2026-11-10',ends='2026-11-10',kind='leave')
    add('absences',employee_id=employees[23],starts='2026-11-18',ends='2026-11-18',kind='comp_off')
    add('absences',employee_id=employees[35],starts='2026-11-06',ends='2026-11-06',kind='unavailable')
