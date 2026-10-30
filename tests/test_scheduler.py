import os
os.environ['DATABASE_URL']='sqlite://'
os.environ['DEMO_SEED']='false'
from copy import deepcopy
import pytest
from backend.app.schemas import SCHEMAS
from backend.app.scheduler import solve
from backend.app.validation import validate
from backend.app.domain import demand,month_days

def fixture_data(n=2):
    data={k:[] for k in SCHEMAS}
    def add(table,**kw):
        item=SCHEMAS[table](**kw).model_dump(mode='json');item['id']=len(data[table])+1;data[table].append(item);return item
    add('pods',name='Test pod')
    add('calendars',name='Every day')
    add('brands',name='Test brand',calendar_id=1)
    add('processes',name='Support')
    add('duties',brand_id=1,process_id=1,effort=4)
    for i in range(n):
        add('employees',name=f'Employee {i}',pod_id=1,preferred_off=[6])
        add('assignments',employee_id=i+1,duty_id=1,role='primary' if i==0 else 'backup')
    return data,add

def hard(r):return [f for f in r['findings'] if f['severity']=='hard']

def test_single_owner_seven_days_without_backup_infeasible():
    d,_=fixture_data(1);r=solve(d,'2026-11');assert r['solver_status']=='INFEASIBLE';assert not r['publishable'];assert any(f['code']=='COVERAGE' for f in hard(r))

def test_backup_makes_coverage_feasible_and_deterministic():
    d,_=fixture_data();a=solve(d,'2026-11');b=solve(d,'2026-11');assert a['publishable'];assert not hard(a);assert a['allocations']==b['allocations']

def test_three_employees_distinct_processes():
    d,add=fixture_data(3)
    for i in (2,3):
        add('processes',name=f'Process {i}');add('duties',brand_id=1,process_id=i,effort=2)
        add('assignments',employee_id=i,duty_id=i)
        add('assignments',employee_id=1,duty_id=i,role='backup')
    assert solve(d,'2026-11')['publishable']

def test_shared_process_requires_distinct_people():
    d,_=fixture_data(3);d['duties'][0]['minimum']=2
    r=solve(d,'2026-11');assert r['publishable']
    assert all(len({a['employee_id'] for a in r['allocations'] if a['date']==day})==2 for day in r['days'])

def test_cross_brand_capacity_and_compatible_processes():
    d,add=fixture_data(2);add('brands',name='Second',calendar_id=1);add('duties',brand_id=2,process_id=1,effort=4)
    for e in (1,2):add('assignments',employee_id=e,duty_id=2)
    r=solve(d,'2026-11');assert r['publishable'];assert not hard(r)
    d['duties'][1]['effort']=5
    assert solve(d,'2026-11')['solver_status']=='INFEASIBLE'

def test_approved_leave_and_comp_off_never_assigned():
    d,add=fixture_data(3)
    for kind,day in [('leave','2026-11-10'),('comp_off','2026-11-11')]:add('absences',employee_id=1,starts=day,ends=day,kind=kind)
    r=solve(d,'2026-11');assert r['publishable'];assert not any(a['employee_id']==1 and a['date'] in ('2026-11-10','2026-11-11') for a in r['allocations'])

@pytest.mark.parametrize('weekdays,holidays_off,day,expected',[(list(range(6)),True,'2026-11-01',0),(list(range(7)),True,'2026-11-01',1),(list(range(7)),True,'2026-11-12',0),(list(range(7)),False,'2026-11-12',1)])
def test_calendars(weekdays,holidays_off,day,expected):
    d,add=fixture_data();d['calendars'][0].update(weekdays=weekdays,holidays_off=holidays_off);add('holidays',name='Test',date='2026-11-12')
    assert demand(d,d['duties'][0],day)==expected

def test_day_override_and_process_calendar_precedence():
    d,add=fixture_data();add('calendars',name='Weekdays',weekdays=list(range(5)));d['duties'][0]['calendar_id']=2
    assert demand(d,d['duties'][0],'2026-11-01')==0
    add('overrides',duty_id=1,date='2026-11-01',minimum=2)
    assert demand(d,d['duties'][0],'2026-11-01')==2

def test_validator_detects_manual_off_cross_brand_gap_duplicates():
    d,add=fixture_data();r=solve(d,'2026-11');a=next(a for a in r['allocations'] if a['date']=='2026-11-02')
    add('absences',employee_id=a['employee_id'],starts=a['date'],ends=a['date'],kind='weekly_off')
    findings=validate(d,r['horizon'],r['allocations']+[a]);codes={f['code'] for f in findings}
    assert {'UNAVAILABLE','DUPLICATE'}<=codes
    allocations=[x for x in r['allocations'] if x!=a]
    assert any(f['code']=='COVERAGE' for f in validate(d,r['horizon'],allocations))

def test_repair_preserves_other_dates():
    d,add=fixture_data(3);r=solve(d,'2026-11');day='2026-11-10';a=next(a for a in r['allocations'] if a['date']==day)
    add('absences',employee_id=a['employee_id'],starts=day,ends=day)
    repaired=solve(d,'2026-11',previous=r['allocations'],affected_dates={day})
    assert repaired['publishable'];assert [a for a in r['allocations'] if a['date']!=day]==[a for a in repaired['allocations'] if a['date']!=day]

def test_exclusive_overlap_and_capacity_detected():
    d,add=fixture_data();add('processes',name='NDR');add('duties',brand_id=1,process_id=2,effort=5,start_minute=540,end_minute=1020)
    d['duties'][0].update(start_minute=600,end_minute=900)
    add('assignments',employee_id=1,duty_id=2)
    a=[{'employee_id':1,'duty_id':j,'date':'2026-11-02'} for j in (1,2)]
    codes={f['code'] for f in validate(d,['2026-11-02'],a)}
    assert {'OVERLAP','CAPACITY'}<=codes

def test_soft_preferences_do_not_make_hard_model_invalid():
    d,_=fixture_data();d['employees'][0]['preferred_off']=list(range(7));d['employees'][1]['preferred_off']=list(range(7))
    r=solve(d,'2026-11');assert r['publishable'];assert any(f['severity']=='soft' for f in r['findings'])

def test_leap_year_and_separate_months():
    assert len(month_days('2028-02'))==29
    d,_=fixture_data();one=solve(d,'2026-11');saved=deepcopy(one);two=solve(d,'2026-12');assert one==saved;assert len(two['days'])==31

def test_invalid_configuration():
    with pytest.raises(ValueError):SCHEMAS['employees'](name='X',pod_id=1,capacity=0)
    with pytest.raises(ValueError):SCHEMAS['absences'](employee_id=1,starts='2026-11-10',ends='2026-11-01')
    with pytest.raises(ValueError):SCHEMAS['duties'](brand_id=1,process_id=1,start_minute=1000,end_minute=500)

def test_unqualified_replacement_never_forced():
    d,add=fixture_data();add('employees',name='Unqualified',pod_id=1)
    r=solve(d,'2026-11',force=[{'key':[3,1,'2026-11-02'],'value':1}]);assert not r['publishable']
