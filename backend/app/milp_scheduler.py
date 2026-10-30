"""Exact MILP fallback using SciPy/HiGHS, when the optional CP-SAT wheel is unavailable."""
from collections import defaultdict
from datetime import date
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix
from .domain import active,absence,demand,overlap,planning_days,month_days
from .validation import validate,daily_status

class Model:
    def __init__(self):
        self.upper=[];self.rows=[];self.cols=[];self.values=[];self.lower=[];self.higher=[]
    def var(self,upper=1):
        n=len(self.upper);self.upper.append(upper);return n
    def constraint(self,terms,low=-np.inf,high=np.inf):
        row=len(self.lower)
        for col,value in terms.items():
            if value:self.rows.append(row);self.cols.append(col);self.values.append(value)
        self.lower.append(low);self.higher.append(high)
    def optimize(self,objectives):
        last=None;last_status='UNKNOWN';completed=[]
        for terms in objectives:
            cost=np.zeros(len(self.upper))
            for i,c in terms.items():cost[i]=c
            matrix=coo_matrix((self.values,(self.rows,self.cols)),shape=(len(self.lower),len(self.upper))).tocsc()
            result=milp(cost,integrality=np.ones(len(self.upper)),bounds=Bounds(np.zeros(len(self.upper)),np.array(self.upper)),
                constraints=LinearConstraint(matrix,np.array(self.lower),np.array(self.higher)),options={'time_limit':30,'mip_rel_gap':0.0})
            if result.x is not None:
                rounded=np.rint(result.x)
                # Numerical solver incumbents must satisfy integer model tolerances.
                activity=matrix@rounded
                if np.all(activity>=np.array(self.lower)-1e-6) and np.all(activity<=np.array(self.higher)+1e-6):
                    last=rounded;last_status='OPTIMAL' if result.status==0 else 'FEASIBLE'
                else:return 'MODEL_INVALID',None,completed
            if result.status==2:return 'INFEASIBLE',None,completed
            if result.status!=0:return ('FEASIBLE' if last is not None else 'UNKNOWN'),last,completed
            optimum=int(round(result.fun));completed.append(optimum)
            self.constraint(terms,optimum,optimum)
        return last_status,last,completed

def solve(data,month,previous=None,affected_dates=None,force=None,boundary=None):
    days=planning_days(month);visible=month_days(month)
    employees=[e for e in data['employees'] if active(e)]
    duties=[j for j in data['duties'] if active(j)]
    demands={(d,j['id']):demand(data,j,d) for d in days for j in duties}
    assignments=defaultdict(list)
    for a in data['assignments']:
        if active(a):assignments[a['employee_id'],a['duty_id']].append(a)
    old={(a['employee_id'],a['duty_id'],a['date']) for a in previous or []}
    boundary={d:keys for d,keys in (boundary or {}).items() if d in days}
    def build(diagnostic=False):
        model=Model();x={};y={};changes={};prefs={};backups={};gaps={};by_duty=defaultdict(dict)
        for e in employees:
            eid=e['id']
            for d in days:
                w=model.var();y[eid,d]=w;local=[];effort={}
                if not absence(data,e,d):
                    for j in duties:
                        jid=j['id'];choices=[a for a in assignments[eid,jid] if (not a.get('starts') or a['starts']<=d) and (not a.get('ends') or a['ends']>=d)]
                        if demands[d,jid] and choices:
                            v=model.var();x[eid,jid,d]=v;local.append((j,v));effort[v]=j['effort'];by_duty[d,jid][v]=1
                            model.constraint({v:1,w:-1},high=0)
                            if not any(a['role']=='primary' for a in choices):backups[v]=1
                model.constraint(effort,high=e['capacity'])
                model.constraint({w:1,**{v:-1 for _,v in local}},high=0)
                for n,(j,v) in enumerate(local):
                    for k,z in local[n+1:]:
                        if overlap(j,k):model.constraint({v:1,z:1},high=1)
                if date.fromisoformat(d).weekday() in e['preferred_off']:prefs[w]=1
            k=e['max_consecutive']
            for n in range(len(days)-k):model.constraint({y[eid,d]:1 for d in days[n:n+k+1]},high=k)
            weeks=defaultdict(list)
            for d in days:weeks[date.fromisoformat(d).isocalendar()[:2]].append(d)
            for ds in weeks.values():
                if len(ds)==7:model.constraint({y[eid,d]:1 for d in ds},high=7-e['weekly_rest'])
        for (d,j),need in demands.items():
            if not need:continue
            terms=dict(by_duty[d,j])
            if diagnostic:
                gap=model.var(need);terms[gap]=1;gaps[gap]=1
            model.constraint(terms,need,need)
        for key,v in x.items():
            if previous is not None:
                if affected_dates is not None and key[2] not in affected_dates:model.constraint({v:1},int(key in old),int(key in old))
                else:changes[v]=-1 if key in old else 1
            if key[2] in boundary:model.constraint({v:1},int(key in boundary[key[2]]),int(key in boundary[key[2]]))
        for key in old:
            if affected_dates is not None and key[2] not in affected_dates and key not in x:model.constraint({},1,1)
        for keys in boundary.values():
            for key in keys:
                if key not in x:model.constraint({},1,1)
        for item in force or []:
            key=tuple(item['key']);value=item['value']
            if key in x:model.constraint({x[key]:1},value,value)
            elif value:model.constraint({},1,1)
        objectives=([gaps] if diagnostic else [])+([changes] if changes else [])+[backups,prefs]
        status,values,objectives=model.optimize(objectives)
        allocations=[] if values is None else [{'employee_id':e,'duty_id':j,'date':d} for (e,j,d),v in x.items() if values[v]>.5]
        return status,allocations,objectives
    strict,allocations,objectives=build();diagnostic=strict=='INFEASIBLE';diag_status=None
    if diagnostic:diag_status,allocations,objectives=build(True)
    findings=validate(data,days,allocations);hard=[f for f in findings if f['severity']=='hard']
    return {'month':month,'days':visible,'horizon':days,'allocations':allocations,
        'statuses':daily_status(data,visible,allocations),'findings':findings,'solver_name':'SciPy HiGHS MILP',
        'solver_status':strict,'diagnostic_status':diag_status,'diagnostic':diagnostic,
        'publishable':strict in ('OPTIMAL','FEASIBLE') and not hard,'objective_values':objectives,
        'boundary_note':'Adjacent weeks are explicitly planned as provisional context; published neighbouring months are locked when available.',
        'solver_settings':{'backend':'HiGHS','time_limit_per_phase':30,'relative_gap':0},
        'summary':{'hard':len(hard),'soft':len(findings)-len(hard),'required_slots':sum(v for (d,j),v in demands.items() if d in visible),'covered_slots':sum(a['date'] in visible for a in allocations)}}
