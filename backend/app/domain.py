"""Pure calendar, eligibility and resource rules shared as domain primitives."""
from datetime import date, timedelta
import calendar

def month_days(month):
    y,m=map(int,month.split('-'))
    if not 2020 <= y <= 2100: raise ValueError('Choose a year from 2020 to 2100')
    return [date(y,m,d).isoformat() for d in range(1,calendar.monthrange(y,m)[1]+1)]

def index(data, name): return {x['id']:x for x in data[name]}
def active(x): return x.get('active',True)
def in_range(item, day): return (not item.get('starts') or item['starts']<=day) and (not item.get('ends') or item['ends']>=day)

def demand(data, duty, day):
    brands=index(data,'brands'); processes=index(data,'processes'); calendars=index(data,'calendars')
    brand=brands[duty['brand_id']]
    if not all(active(x) for x in [duty,brand,processes[duty['process_id']]]): return 0
    override=next((x for x in data['overrides'] if active(x) and x['duty_id']==duty['id'] and x['date']==day),None)
    if override: return override['minimum'] if override['operating'] else 0
    cal=calendars[duty.get('calendar_id') or brand['calendar_id']]
    holiday=any(active(x) and x['date']==day for x in data['holidays'])
    return duty['minimum'] if active(cal) and date.fromisoformat(day).weekday() in cal['weekdays'] and not (holiday and cal['holidays_off']) else 0

def absence(data, employee, day):
    if not active(employee): return 'inactive'
    found=next((x for x in data['absences'] if active(x) and x['approved'] and x['employee_id']==employee['id'] and in_range(x,day)),None)
    if found: return found['kind']
    if date.fromisoformat(day).weekday() in employee['fixed_off']: return 'weekly_off'
    return None

def eligible(data,e,j,day):
    return any(active(a) and a['employee_id']==e and a['duty_id']==j and in_range(a,day) for a in data['assignments'])

def primary(data,e,j,day):
    return any(active(a) and a['employee_id']==e and a['duty_id']==j and a['role']=='primary' and in_range(a,day) for a in data['assignments'])

def overlap(a,b):
    return a.get('start_minute') is not None and b.get('start_minute') is not None and max(a['start_minute'],b['start_minute']) < min(a['end_minute'],b['end_minute'])

def planning_days(month):
    days=month_days(month)
    # Plan complete boundary weeks plus enough lookahead/lookbehind for rolling rest.
    first=date.fromisoformat(days[0])-timedelta(days=14)
    last=date.fromisoformat(days[-1])+timedelta(days=14)
    first-=timedelta(days=first.weekday())
    last+=timedelta(days=6-last.weekday())
    return [(first+timedelta(days=i)).isoformat() for i in range((last-first).days+1)]
