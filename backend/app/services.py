"""Transactional management, generation, change preview and apply services."""
from copy import deepcopy
from datetime import date,timedelta
from sqlalchemy import select,update,delete
from fastapi import HTTPException
from .database import TABLES,REFERENCES,Meta,Roster,Allocation,Change,Audit,add_record,snapshot,now
from .schemas import SCHEMAS
from .domain import index,active,month_days,absence,eligible,demand,overlap
from .scheduler import solve
from .validation import validate,daily_status

def fail(message,code=422): raise HTTPException(code,message)
def log(db,action,detail,roster_id=None): db.add(Audit(action=action,detail=detail,roster_id=roster_id,created_at=now()))
def roster_or_404(db,id):
    r=db.get(Roster,id)
    if not r: fail('Roster not found',404)
    return r

def current_revision(db): return db.get(Meta,1).revision

def bump(db,expected):
    changed=db.execute(update(Meta).where(Meta.id==1,Meta.revision==expected).values(revision=expected+1)).rowcount
    if changed!=1: fail('Inputs changed during this operation. Refresh and retry.',409)
    db.expire(db.get(Meta,1))
    db.execute(update(Roster).where(Roster.status=='published').values(status='stale'))
    return expected+1

def check_record(db,table,data,id=None):
    for field,target in REFERENCES.get(table,{}).items():
        if data.get(field) is not None:
            row=db.get(TABLES[target],data[field])
            if not row or not row.data.get('active',True): fail(f'{field} must reference an active {target} record')
    if table=='pods' and data.get('lead_id'):
        lead=db.get(TABLES['employees'],data['lead_id'])
        if id is None or lead.pod_id!=id: fail('Pod lead must belong to this pod')
    if table=='employees' and id:
        for pod in db.scalars(select(TABLES['pods'])):
            if pod.lead_id==id and (not data['active'] or pod.id!=data['pod_id']): fail('Assign another pod lead before deactivating or moving this employee')
    for row in db.scalars(select(TABLES[table])):
        if row.id==id: continue
        other=row.data
        keys={'duties':['brand_id','process_id'],'assignments':['employee_id','duty_id'],'overrides':['duty_id','date'],'holidays':['date']}.get(table)
        if keys and all(other[k]==data[k] for k in keys): fail('This relationship/date already exists; edit the existing record')
        if 'name' in data and other.get('name','').casefold()==data['name'].casefold(): fail('A record with this name already exists')
    if table=='absences' and data['active'] and data['approved']:
        for row in db.scalars(select(TABLES['absences'])):
            o=row.data
            if row.id!=id and o['active'] and o['approved'] and o['employee_id']==data['employee_id'] and max(o['starts'],data['starts'])<=min(o['ends'],data['ends']): fail('An approved absence already covers this date range')
    if not data['active'] and id:
        for source,refs in REFERENCES.items():
            for field,target in refs.items():
                if target==table:
                    for row in db.scalars(select(TABLES[source]).where(getattr(TABLES[source],field)==id)):
                        if row.data.get('active',True): fail(f'Deactivate or reassign dependent {source} records first')

def save_record(db,table,raw,id=None):
    if table not in SCHEMAS: fail('Unknown entity',404)
    data=SCHEMAS[table].model_validate(raw).model_dump(mode='json')
    check_record(db,table,data,id)
    revision=current_revision(db)
    before=None
    if id:
        row=db.get(TABLES[table],id)
        if not row: fail('Record not found',404)
        before=row.data; row.data=data
        for field in REFERENCES.get(table,{}): setattr(row,field,data.get(field))
    else: row=add_record(db,table,data)
    bump(db,revision); log(db,f'{table}.save',{'id':row.id,'before':before,'after':data})
    db.flush(); return dict(data,id=row.id)

def persist_allocations(db,r):
    db.execute(delete(Allocation).where(Allocation.roster_id==r.id))
    db.add_all([Allocation(roster_id=r.id,**a) for a in r.payload['allocations']])

def view(db,r):
    return dict(r.payload,id=r.id,revision=r.revision,input_revision=r.input_revision,status=r.status,
                stale=r.input_revision!=current_revision(db),created_at=r.created_at)

def boundaries(db,month,exclude=None):
    result={}
    for r in db.scalars(select(Roster).where(Roster.status=='published',Roster.month!=month)):
        if r.id==exclude: continue
        for d in r.payload['days']: result[d]={(a['employee_id'],a['duty_id'],a['date']) for a in r.payload['allocations'] if a['date']==d}
    return result

def generate(db,month):
    data=snapshot(db); rev=current_revision(db)
    boundary=boundaries(db,month)
    payload=None
    # A new version need not discard a still-valid allocation. Revalidate against
    # current inputs and published neighbours before preserving it.
    for prior in db.scalars(select(Roster).where(Roster.month==month).order_by(Roster.id.desc()).limit(10)):
        candidate=enrich(data,prior.payload)
        keys={(a['employee_id'],a['duty_id'],a['date']) for a in candidate['allocations']}
        aligned=all(day not in candidate['horizon'] or values=={k for k in keys if k[2]==day} for day,values in boundary.items())
        if candidate['publishable'] and aligned:
            payload=candidate
            payload['solver_status']='FEASIBLE'
            payload['objective_values']=[]
            payload['generation_note']=f'Existing allocations from version {prior.id} were independently revalidated against current inputs and preserved. No new optimisation was needed.'
            payload['reused_from']=prior.id
            break
    if payload is None:
        payload=solve(data,month,boundary=boundary)
    payload['input_snapshot']=data
    if current_revision(db)!=rev: fail('Inputs changed; regenerate',409)
    r=Roster(month=month,input_revision=rev,revision=1,status='draft',payload=payload,created_at=now())
    db.add(r); db.flush(); persist_allocations(db,r)
    log(db,'generate',{'solver_status':payload['solver_status'],'summary':payload['summary']},r.id)
    return view(db,r)

def enrich(data,payload):
    result=deepcopy(payload)
    result['findings']=validate(data,result['horizon'],result['allocations'])
    result['statuses']=daily_status(data,result['days'],result['allocations'])
    hard=sum(f['severity']=='hard' for f in result['findings'])
    result['summary']={**result['summary'],'hard':hard,'soft':len(result['findings'])-hard,
      'covered_slots':sum(a['date'] in result['days'] for a in result['allocations']),
      'required_slots':sum(demand(data,j,d) for j in data['duties'] for d in result['days'])}
    result['publishable']=hard==0 and result['solver_status'] in ('FEASIBLE','OPTIMAL','MANUAL_VALIDATED')
    return result

def preview(db,id,edit):
    r=roster_or_404(db,id)
    if r.revision!=edit.expected_revision: fail('Roster changed. Refresh before editing.',409)
    data=snapshot(db); altered=deepcopy(data); d=edit.date.isoformat(); e=edit.employee_id
    if d not in r.payload['days']: fail('Choose a date inside this roster month')
    employees=index(data,'employees'); duties=index(data,'duties')
    if e not in employees: fail('Employee not found')
    old=r.payload['allocations']; affected=[a for a in old if a['employee_id']==e and a['date']==d]
    absence_record=None; force=None
    changed=deepcopy(old)
    if edit.kind!='allocation':
        absence_record=SCHEMAS['absences'].model_validate({'employee_id':e,'starts':d,'ends':d,'kind':edit.kind}).model_dump(mode='json')
        check_record(db,'absences',absence_record)
        altered['absences'].append(dict(absence_record,id=-1))
        changed=[a for a in changed if not (a['employee_id']==e and a['date']==d)]
        if edit.replacement_id:
            if edit.replacement_id==e: fail('Choose another employee')
            force=[{'key':[edit.replacement_id,a['duty_id'],d],'value':1} for a in affected]
    else:
        if edit.duty_id not in duties: fail('Select a valid process assignment')
        key={'employee_id':e,'duty_id':edit.duty_id,'date':d}
        changed=[a for a in changed if a!=key]
        if not edit.remove: changed.append(key)
        force=[{'key':[e,edit.duty_id,d],'value':int(not edit.remove)}]
    before=enrich(altered,{**r.payload,'allocations':changed})
    if edit.repair:
        scope={d}
        proposed=solve(altered,r.month,previous=old,affected_dates=scope,force=force,boundary=boundaries(db,r.month))
        if proposed['solver_status']=='INFEASIBLE':
            centre=date.fromisoformat(d)
            scope={day for day in r.payload['horizon'] if abs((date.fromisoformat(day)-centre).days)<=7}
            proposed=solve(altered,r.month,previous=old,affected_dates=scope,force=force,boundary=boundaries(db,r.month))
        proposed['repair_scope']={'dates':sorted(scope),'expanded':len(scope)>1,'reason':'A same-day repair was infeasible; up to seven neighbouring days on each side allow rest-day swaps. Review every changed allocation before approval.' if len(scope)>1 else 'Only the affected date was unlocked.'}
    else:
        proposed=enrich(altered,{**r.payload,'allocations':changed,'solver_status':'MANUAL_VALIDATED','diagnostic':False})
    candidates=[]
    for emp in employees.values():
        if emp['id']==e or absence(altered,emp,d): continue
        missing=[a for a in affected if not eligible(altered,emp['id'],a['duty_id'],d)]
        held=[duties[a['duty_id']] for a in old if a['employee_id']==emp['id'] and a['date']==d]
        needed=[duties[a['duty_id']] for a in affected if not any(j['id']==a['duty_id'] for j in held)]
        load=sum(j['effort'] for j in held+needed)
        conflicts=any(overlap(j,k) for n,j in enumerate(held+needed) for k in (held+needed)[n+1:])
        if affected and not missing and load<=emp['capacity'] and not conflicts:
            candidates.append({'employee_id':emp['id'],'name':emp['name'],'resulting_load':load,'capacity':emp['capacity'],'note':'Eligibility/capacity candidate; full rest validation occurs in preview.'})
    proposed['input_snapshot']=altered
    oldkeys={(a['employee_id'],a['duty_id'],a['date']) for a in old}
    newkeys={(a['employee_id'],a['duty_id'],a['date']) for a in proposed['allocations']}
    diff={'removed':[{'employee_id':e,'duty_id':j,'date':d} for e,j,d in sorted(oldkeys-newkeys)],'added':[{'employee_id':e,'duty_id':j,'date':d} for e,j,d in sorted(newkeys-oldkeys)]}
    content={'request':edit.model_dump(mode='json'),'absence':absence_record,'before_findings':[f for f in before['findings'] if f['date']==d],
             'affected':affected,'candidates':candidates,'diff':diff,'result':proposed}
    change=Change(roster_id=id,base_revision=r.revision,input_revision=current_revision(db),status='preview',payload=content,created_at=now())
    db.add(change); db.flush()
    log(db,'preview',{'change_id':change.id,'publishable':proposed['publishable']},id)
    return dict(content,change_id=change.id)

def apply_change(db,id,change_id,expected):
    r=roster_or_404(db,id); c=db.get(Change,change_id)
    if not c or c.roster_id!=id: fail('Change not found',404)
    if c.status!='preview' or r.revision!=expected or c.base_revision!=expected or c.input_revision!=current_revision(db): fail('Preview is stale. Preview again.',409)
    if not c.payload['result']['publishable']: fail('Hard constraints remain. This proposal cannot be applied; configure a qualified replacement or adjust approved operating rules.',409)
    data=snapshot(db)
    if c.payload['absence']: data['absences'].append(dict(c.payload['absence'],id=-1))
    result=enrich(data,c.payload['result'])
    if not result['publishable']: fail('Validation failed; preview again',409)
    oldrev=current_revision(db); newrev=bump(db,oldrev)
    if c.payload['absence']: add_record(db,'absences',c.payload['absence'])
    count=db.execute(update(Roster).where(Roster.id==id,Roster.revision==expected).values(revision=expected+1,input_revision=newrev,status='draft',payload=result)).rowcount
    if count!=1: fail('Concurrent roster change; retry',409)
    db.refresh(r); persist_allocations(db,r); c.status='applied'
    log(db,'apply',{'change_id':c.id,'diff':c.payload['diff'],'validation':result['summary']},id)
    return view(db,r)

def publish(db,id,expected):
    r=roster_or_404(db,id)
    if r.revision!=expected or r.input_revision!=current_revision(db): fail('Roster or inputs changed. Revalidate/regenerate first.',409)
    result=enrich(snapshot(db),r.payload)
    actual={(a['employee_id'],a['duty_id'],a['date']) for a in r.payload['allocations']}
    for day,keys in boundaries(db,r.month).items():
        if day in r.payload['horizon'] and keys!={k for k in actual if k[2]==day}:
            fail('A neighbouring month was published with different boundary assignments. Regenerate this roster.',409)
    if not result['publishable']: fail('Only a roster with all hard constraints satisfied can be published',409)
    # Serialize publication with all input changes, and supersede the previous month version.
    revision=current_revision(db)
    if db.execute(update(Meta).where(Meta.id==1,Meta.revision==revision).values(revision=revision)).rowcount!=1: fail('Inputs changed',409)
    db.execute(update(Roster).where(Roster.month==r.month,Roster.status=='published',Roster.id!=id).values(status='superseded'))
    r.payload=result; r.status='published'; r.revision+=1
    log(db,'publish',{'revision':r.revision},id)
    return view(db,r)
