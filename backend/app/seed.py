"""Reproducible fictional data: 36 employees, 25 brands, 80% single primary owner."""
from .database import add_record,TABLES
from .schemas import SCHEMAS
from sqlalchemy import select

def seed(db):
    if db.scalar(select(TABLES['employees'].id).limit(1)): return
    def add(table, **data):
        obj=SCHEMAS[table].model_validate(data).model_dump(mode='json')
        return add_record(db,table,obj).id
    for name in ['North studio','Growth desk','Care collective']: add('pods',name=name)
    add('calendars',name='Every day',weekdays=list(range(7)),holidays_off=False)
    add('calendars',name='Daily except holidays',weekdays=list(range(7)),holidays_off=True)
    add('calendars',name='Monday–Saturday',weekdays=list(range(6)),holidays_off=True)
    names=['Aarav Mehta','Ananya Rao','Dev Shah','Isha Nair','Kabir Sen','Leela Das','Mira Kapoor','Neel Bose','Ojas Patel','Pia Jain','Ravi Menon','Sara Roy','Tara Sethi','Vihaan Joshi','Yash Arora','Zoya Khan','Aditi Rao','Arjun Das','Diya Sen','Kiran Nair','Maya Shah','Nikhil Bose','Pari Mehta','Rehan Jain','Sana Kapoor','Tanvi Menon','Ved Roy','Zara Patel','Ira Sethi','Rohan Joshi','Anika Arora','Dhruv Khan','Esha Rao','Farhan Das','Gauri Sen','Harsh Nair']
    for i,name in enumerate(names): add('employees',name=name,pod_id=i//12+1,preferred_off=[i%7])
    for i,lead in enumerate([1,13,25],1):
        pod=db.get(TABLES['pods'],i); pod.data={**pod.data,'lead_id':lead}; pod.lead_id=lead
    for name in ['Customer Support','Abandoned Cart','Retention','NDR']: add('processes',name=name)
    brands=['Cedar & Clay','Northform','Luma Skin','Moss & Moon','Kettle Club','Sunday Loom','Pawfolk','Rooted Ritual','Aero Lane','Kindred Home','Bloom Theory','Daily Grain','Halo Goods','Indigo Nest','Juniper Labs','Kin Supply','Little Orbit','Meridian Co','Nectar Works','Oak & Ember','Prism Living','Quiet Coast','Riverstone','Solstice Wear','Terra Table']
    for i,name in enumerate(brands):
        bid=add('brands',name=name,calendar_id=1 if i<8 else (2 if i<14 else 3))
        for p in range(1,5):
            jid=add('duties',brand_id=bid,process_id=p,calendar_id=3 if p==4 and i%3==0 else None,minimum=2 if i==20 and p==1 else 1,effort=1 if i<20 else 2)
            if i<20: owners=[i+1]
            else:
                team=[[21,22,23],[24,25],[26,27],[28,29,30],[31,32]][i-20]
                owners=team[:2] if i==20 and p==1 else [team[(p-1)%len(team)]]
            for e in owners: add('assignments',employee_id=e,duty_id=jid)
            for e in [33,34,35,36]: add('assignments',employee_id=e,duty_id=jid,role='backup')
    add('holidays',name='Demo holiday (fictional)',date='2026-11-12')
    add('absences',employee_id=2,starts='2026-11-10',ends='2026-11-10',kind='leave')
    add('absences',employee_id=24,starts='2026-11-18',ends='2026-11-18',kind='comp_off')
    add('absences',employee_id=36,starts='2026-11-06',ends='2026-11-06',kind='unavailable')
