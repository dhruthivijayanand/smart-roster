"""Validated management inputs. Calendars use Python weekdays: Monday=0."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator

class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    active: bool = True

class Named(Record):
    name: str = Field(min_length=1, max_length=100)

class Pod(Named):
    lead_id: int | None = None

class Employee(Named):
    pod_id: int
    capacity: int = Field(default=8, ge=1, le=24)
    preferred_off: list[int] = Field(default_factory=lambda: [6])
    fixed_off: list[int] = Field(default_factory=list)
    max_consecutive: int = Field(default=6, ge=1, le=14)
    weekly_rest: int = Field(default=1, ge=0, le=6)
    @model_validator(mode='after')
    def days(self):
        if any(d not in range(7) for d in self.fixed_off + self.preferred_off):
            raise ValueError('Weekdays must be between 0 (Monday) and 6 (Sunday)')
        return self

class Calendar(Named):
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)))
    holidays_off: bool = False
    @model_validator(mode='after')
    def days(self):
        if not self.weekdays or len(set(self.weekdays)) != len(self.weekdays) or any(d not in range(7) for d in self.weekdays):
            raise ValueError('Select unique weekdays from 0 to 6')
        return self

class Brand(Named):
    calendar_id: int

class Process(Named):
    pass

class Duty(Record):
    brand_id: int
    process_id: int
    calendar_id: int | None = None
    minimum: int = Field(default=1, ge=0, le=20)
    effort: int = Field(default=2, ge=1, le=24)
    start_minute: int | None = Field(default=None, ge=0, le=1439)
    end_minute: int | None = Field(default=None, ge=1, le=1440)
    @model_validator(mode='after')
    def interval(self):
        if (self.start_minute is None) != (self.end_minute is None):
            raise ValueError('Provide both interval start and end')
        if self.start_minute is not None and self.end_minute <= self.start_minute:
            raise ValueError('Interval end must follow start; overnight shifts are not supported')
        return self

class Assignment(Record):
    employee_id: int
    duty_id: int
    role: Literal['primary','backup'] = 'primary'
    starts: date | None = None
    ends: date | None = None
    @model_validator(mode='after')
    def range(self):
        if self.starts and self.ends and self.ends < self.starts:
            raise ValueError('End date precedes start')
        return self

class Absence(Record):
    employee_id: int
    starts: date
    ends: date
    kind: Literal['leave','comp_off','unavailable','weekly_off'] = 'leave'
    approved: bool = True
    note: str = Field(default='', max_length=300)
    @model_validator(mode='after')
    def range(self):
        if self.ends < self.starts:
            raise ValueError('End date precedes start')
        return self

class Holiday(Named):
    date: date

class Override(Record):
    duty_id: int
    date: date
    operating: bool = True
    minimum: int = Field(default=1, ge=0, le=20)

SCHEMAS = {'pods': Pod, 'employees': Employee, 'calendars': Calendar, 'brands': Brand,
           'processes': Process, 'duties': Duty, 'assignments': Assignment,
           'absences': Absence, 'holidays': Holiday, 'overrides': Override}

class Generate(BaseModel):
    month: str = Field(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')

class Edit(BaseModel):
    expected_revision: int
    employee_id: int
    date: date
    kind: Literal['leave','comp_off','unavailable','weekly_off','allocation'] = 'leave'
    duty_id: int | None = None
    replacement_id: int | None = None
    remove: bool = True
    repair: bool = True

class Revision(BaseModel):
    expected_revision: int
