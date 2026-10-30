"""Independent allocation validator: does not trust the solver's feasibility flag."""
from collections import defaultdict, Counter
from datetime import date
from .domain import index,active,absence,demand,eligible,overlap

def validate(data, days, allocations):
    employees=index(data,'employees'); duties=index(data,'duties')
    brands=index(data,'brands'); processes=index(data,'processes')
    by_duty=defaultdict(set); by_emp=defaultdict(list); findings=[]
    def report(code,day,j=None,e=None,reason='',severity='hard',suggestion='Review eligibility, availability and capacity; approve a qualified replacement.'):
        duty=duties.get(j); required=demand(data,duty,day) if duty else None
        available=sum(active(emp) and not absence(data,emp,day) and eligible(data,emp['id'],j,day) for emp in employees.values()) if duty else None
        findings.append({'code':code,'date':day,'duty_id':j,'employee_id':e,'brand':brands[duty['brand_id']]['name'] if duty else None,
          'process':processes[duty['process_id']]['name'] if duty else None,'required':required,'eligible':available,
          'actual':len(by_duty[(day,j)]) if duty else None,'severity':severity,'reason':reason,'suggestion':suggestion})
    seen=Counter((a['employee_id'],a['duty_id'],a['date']) for a in allocations)
    for a in allocations:
        e,j,d=a['employee_id'],a['duty_id'],a['date']
        if d not in days: report('OUTSIDE_HORIZON',d,reason='Allocation outside the planned horizon.'); continue
        if e not in employees or j not in duties: report('INVALID_REFERENCE',d,reason='Unknown employee or duty.'); continue
        by_duty[(d,j)].add(e); by_emp[(d,e)].append(j)
    for (e,j,d),count in seen.items():
        if count>1: report('DUPLICATE',d,j,e,'Same employee counted twice on the same duty.')
    for (d,e),js in by_emp.items():
        emp=employees[e]
        if absence(data,emp,d): report('UNAVAILABLE',d,js[0],e,f"{emp['name']} is {absence(data,emp,d).replace('_',' ')}; all their duties must be reassigned.")
        if sum(duties[j]['effort'] for j in js)>emp['capacity']:
            report('CAPACITY',d,None,e,f"{emp['name']} exceeds {emp['capacity']} workload units across all brands.")
        for n,j in enumerate(js):
            if not eligible(data,e,j,d): report('INELIGIBLE',d,j,e,'Employee has no active eligibility for this brand-process.')
            if not demand(data,duties[j],d): report('CLOSED_DAY',d,j,e,'Allocation conflicts with the operating calendar or zero demand.')
            for k in js[n+1:]:
                if j!=k and overlap(duties[j],duties[k]): report('OVERLAP',d,j,e,f'Exclusive interval overlaps duty {k}.')
        if date.fromisoformat(d).weekday() in emp['preferred_off']:
            report('PREFERRED_OFF',d,None,e,'Working on a preferred off day; mandatory constraints take priority.','soft','Consider another qualified employee if coverage and rest remain valid.')
    for d in days:
        for j,duty in duties.items():
            need=demand(data,duty,d)
            if len(by_duty[(d,j)])<need:
                report('COVERAGE',d,j,None,f"Requires {need} distinct employees; assigned {len(by_duty[(d,j)])}. Eligible count is individual eligibility, not guaranteed shared capacity.")
    for e,emp in employees.items():
        if not active(emp): continue
        max_run=emp['max_consecutive']; run=0
        weeks=defaultdict(list)
        for d in days:
            worked=bool(by_emp[(d,e)]); run=run+1 if worked else 0
            if run>max_run: report('CONSECUTIVE',d,None,e,f"{emp['name']} exceeds {max_run} consecutive working days.")
            weeks[date.fromisoformat(d).isocalendar()[:2]].append((d,worked))
        for items in weeks.values():
            if len(items)==7 and sum(w for _,w in items)>7-emp['weekly_rest']:
                report('WEEKLY_REST',items[-1][0],None,e,f"{emp['name']} needs {emp['weekly_rest']} rest days in this Monday–Sunday week.")
    return findings

def daily_status(data,days,allocations):
    working={(a['employee_id'],a['date']) for a in allocations}
    result=[]
    for e in data['employees']:
        if not active(e): continue
        for d in days:
            reason=absence(data,e,d)
            status='work' if (e['id'],d) in working else reason or ('holiday' if any(active(h) and h['date']==d for h in data['holidays']) else 'weekly_off')
            result.append({'employee_id':e['id'],'date':d,'status':status})
    return result
