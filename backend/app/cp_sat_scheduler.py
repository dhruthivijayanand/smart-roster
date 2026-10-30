"""Deterministic CP-SAT scheduling and scoped repair. No hard rule is silently relaxed."""
from collections import defaultdict
from datetime import date
from ortools.sat.python import cp_model
from .domain import active,index,absence,demand,eligible,primary,overlap,planning_days,month_days
from .validation import validate,daily_status

def solve(data, month, previous=None, affected_dates=None, force=None, boundary=None):
    days=planning_days(month); visible=month_days(month)
    employees=[e for e in data['employees'] if active(e)]
    duties=[j for j in data['duties'] if active(j)]
    demands={(d,j['id']):demand(data,j,d) for d in days for j in duties}
    assignment_map=defaultdict(list)
    for a in data['assignments']:
        if active(a): assignment_map[(a['employee_id'],a['duty_id'])].append(a)
    old={(a['employee_id'],a['duty_id'],a['date']) for a in previous or []}
    boundary={d:keys for d,keys in (boundary or {}).items() if d in days}
    def build(diagnostic=False):
        model=cp_model.CpModel(); x={}; y={}; shortage=[]; changes=[]; prefs=[]; backup=[]
        for e in employees:
            eid=e['id']
            for d in days:
                y[eid,d]=model.new_bool_var(f'w_{eid}_{d}')
                local=[]; effort=[]
                if not absence(data,e,d):
                    for j in duties:
                        jid=j['id']
                        if demands[d,jid] and any((not a.get('starts') or a['starts']<=d) and (not a.get('ends') or a['ends']>=d) for a in assignment_map[eid,jid]):
                            v=model.new_bool_var(f'x_{eid}_{jid}_{d}'); x[eid,jid,d]=v
                            local.append((j,v)); effort.append(j['effort']*v)
                            if not primary(data,eid,jid,d): backup.append(v)
                model.add(sum(effort)<=e['capacity'])
                if local:
                    for _,v in local: model.add(v<=y[eid,d])
                    model.add(y[eid,d]<=sum(v for _,v in local))
                else: model.add(y[eid,d]==0)
                for n,(j,v) in enumerate(local):
                    for k,w in local[n+1:]:
                        if overlap(j,k): model.add(v+w<=1)
                if date.fromisoformat(d).weekday() in e['preferred_off']: prefs.append(y[eid,d])
            k=e['max_consecutive']
            for n in range(len(days)-k): model.add(sum(y[eid,d] for d in days[n:n+k+1])<=k)
            weeks=defaultdict(list)
            for d in days: weeks[date.fromisoformat(d).isocalendar()[:2]].append(d)
            for ds in weeks.values():
                if len(ds)==7: model.add(sum(y[eid,d] for d in ds)<=7-e['weekly_rest'])
        for (d,j),need in demands.items():
            if not need: continue
            assigned=sum(x.get((e['id'],j,d),0) for e in employees)
            if diagnostic:
                gap=model.new_int_var(0,need,f'gap_{j}_{d}'); shortage.append(gap)
                model.add(assigned+gap==need)
            else: model.add(assigned==need)
        for key,v in x.items():
            if previous is not None:
                if affected_dates is not None and key[2] not in affected_dates: model.add(v==int(key in old))
                else: changes.append(1-v if key in old else v)
            if key[2] in boundary: model.add(v==int(key in boundary[key[2]]))
        for key in old:
            if previous is not None and affected_dates is not None and key[2] not in affected_dates and key not in x: model.add(False)
        for keys in boundary.values():
            for key in keys:
                if key not in x: model.add(False)
        for forced in force or []:
            key=tuple(forced['key']); value=forced['value']
            if key in x: model.add(x[key]==value)
            elif value: model.add(False)
        # Lexicographic phases; no arbitrary weighted mixture of priorities.
        objectives=([sum(shortage)] if diagnostic else [])+([sum(changes)] if changes else [])+[sum(backup),sum(prefs)]
        solver=cp_model.CpSolver(); solver.parameters.num_search_workers=1; solver.parameters.random_seed=7
        solver.parameters.max_deterministic_time=2.0
        completed=[]; last_solution=None; status=cp_model.UNKNOWN; last_good=None
        for objective in objectives:
            model.minimize(objective)
            status=solver.solve(model)
            if status not in (cp_model.FEASIBLE,cp_model.OPTIMAL): break
            last_good=status
            last_solution=[{'employee_id':e,'duty_id':j,'date':d} for (e,j,d),v in x.items() if solver.value(v)]
            if status!=cp_model.OPTIMAL: break
            best=int(round(solver.objective_value)); completed.append(best); model.add(objective==best)
        return ('FEASIBLE' if last_good is not None and status not in (cp_model.FEASIBLE,cp_model.OPTIMAL) else solver.status_name(status)),last_solution,completed
    strict,allocations,objectives=build()
    diagnostic=False
    if strict=='INFEASIBLE':
        diagnostic=True
        diag_status,allocations,objectives=build(True)
    else: diag_status=None
    allocations=allocations or []
    findings=validate(data,days,allocations)
    hard=[f for f in findings if f['severity']=='hard']
    publishable=strict in ('OPTIMAL','FEASIBLE') and not hard
    return {'month':month,'days':visible,'horizon':days,'allocations':allocations,
            'statuses':daily_status(data,visible,allocations),'findings':findings,
            'solver_status':strict,'diagnostic_status':diag_status,'diagnostic':diagnostic,
            'publishable':publishable,'objective_values':objectives,
            'boundary_note':'Adjacent weeks are explicitly planned as provisional context; published neighbouring months are locked when available.',
            'solver_settings':{'seed':7,'workers':1,'deterministic_limit_per_phase':2.0},
            'summary':{'hard':len(hard),'soft':len(findings)-len(hard),
                       'required_slots':sum(v for (d,j),v in demands.items() if d in visible),
                       'covered_slots':sum(1 for a in allocations if a['date'] in visible)}}
