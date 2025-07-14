from pydantic import BaseModel, Field
from typing import Annotated
from pydantic.functional_validators import AfterValidator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


# Enums
class EmploymentType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"


class PayrollStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    paid = "paid"


class TimeEntryStatus(str, Enum):
    active = "active"
    completed = "completed"
    approved = "approved"


# Custom email type that allows .local domains
def validate_email(v: str) -> str:
    if "@" not in v:
        raise ValueError("Invalid email format")
    return v

Email = Annotated[str, AfterValidator(validate_email)]

# User Schemas
class UserBase(BaseModel):
    email: Email
    username: str
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[Email] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    id: int
    is_admin: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class User(UserInDB):
    pass


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Employee Schemas
class EmployeeBase(BaseModel):
    employee_id: str
    department: str
    position: str
    hire_date: date
    salary: float
    hourly_rate: Optional[float] = None
    employment_type: EmploymentType = EmploymentType.full_time
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    user_id: int


class EmployeeUpdate(BaseModel):
    department: Optional[str] = None
    position: Optional[str] = None
    salary: Optional[float] = None
    hourly_rate: Optional[float] = None
    employment_type: Optional[EmploymentType] = None
    is_active: Optional[bool] = None


class Employee(EmployeeBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class EmployeeWithUser(Employee):
    user: User


# Payroll Schemas
class PayrollRecordBase(BaseModel):
    pay_period_start: date
    pay_period_end: date
    gross_pay: float
    tax_deductions: float = 0.0
    other_deductions: float = 0.0
    net_pay: float
    hours_worked: float = 0.0
    overtime_hours: float = 0.0
    status: PayrollStatus = PayrollStatus.pending


class PayrollRecordCreate(PayrollRecordBase):
    employee_id: int


class PayrollRecordUpdate(BaseModel):
    gross_pay: Optional[float] = None
    tax_deductions: Optional[float] = None
    other_deductions: Optional[float] = None
    net_pay: Optional[float] = None
    hours_worked: Optional[float] = None
    overtime_hours: Optional[float] = None
    status: Optional[PayrollStatus] = None


class PayrollRecord(PayrollRecordBase):
    id: int
    employee_id: int
    employee_user_id: int
    processed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PayrollRecordWithEmployee(PayrollRecord):
    employee: Employee


# Time Entry Schemas
class TimeEntryBase(BaseModel):
    date: date
    clock_in: datetime
    clock_out: Optional[datetime] = None
    break_duration: int = 0  # in minutes
    notes: Optional[str] = None
    status: TimeEntryStatus = TimeEntryStatus.active


class TimeEntryCreate(TimeEntryBase):
    employee_id: int


class TimeEntryUpdate(BaseModel):
    clock_out: Optional[datetime] = None
    break_duration: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[TimeEntryStatus] = None


class TimeEntry(TimeEntryBase):
    id: int
    employee_id: int
    total_hours: Optional[float]
    overtime_hours: float
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Department Schemas
class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    budget: Optional[float] = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    manager_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    manager_id: Optional[int] = None
    budget: Optional[float] = None
    is_active: Optional[bool] = None


class Department(DepartmentBase):
    id: int
    manager_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Response Schemas
class MessageResponse(BaseModel):
    message: str


class PayrollSummary(BaseModel):
    total_employees: int
    total_gross_pay: float
    total_net_pay: float
    pending_records: int
    approved_records: int
    paid_records: int