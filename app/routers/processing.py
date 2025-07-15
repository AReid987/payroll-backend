from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from datetime import datetime, date, timedelta

from ..database import get_db
from ..models import User, Employee, PayrollRecord, TimeEntry
from ..schemas import (
    PayrollRecord as PayrollRecordSchema,
    PayrollRecordCreate, PayrollRecordUpdate, PayrollRecordWithEmployee,
    TimeEntry as TimeEntrySchema, TimeEntryCreate, TimeEntryUpdate,
    PayrollSummary, MessageResponse, PayrollStatus
)
from ..auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/payroll", tags=["payroll"])


def calculate_payroll(employee: Employee, hours_worked: float, overtime_hours: float = 0.0) -> dict:
    """Calculate payroll for an employee"""
    regular_hours = min(hours_worked, 40.0)  # Standard 40-hour work week
    overtime_hours = max(0, hours_worked - 40.0) if overtime_hours == 0 else overtime_hours
    
    if employee.employment_type == "hourly" and employee.hourly_rate:
        regular_pay = regular_hours * employee.hourly_rate
        overtime_pay = overtime_hours * employee.hourly_rate * 1.5  # 1.5x overtime rate
        gross_pay = regular_pay + overtime_pay
    else:
        # Salary-based calculation
        weekly_salary = employee.salary / 52  # Assuming annual salary
        gross_pay = weekly_salary
        if overtime_hours > 0:
            hourly_equivalent = weekly_salary / 40
            overtime_pay = overtime_hours * hourly_equivalent * 1.5
            gross_pay += overtime_pay
    
    # Simple tax calculation (this should be more sophisticated in production)
    tax_rate = 0.25  # 25% tax rate
    tax_deductions = gross_pay * tax_rate
    
    # Other deductions (health insurance, etc.)
    other_deductions = gross_pay * 0.05  # 5% for other deductions
    
    net_pay = gross_pay - tax_deductions - other_deductions
    
    return {
        "gross_pay": round(gross_pay, 2),
        "tax_deductions": round(tax_deductions, 2),
        "other_deductions": round(other_deductions, 2),
        "net_pay": round(net_pay, 2),
        "hours_worked": hours_worked,
        "overtime_hours": overtime_hours
    }


@router.post("/records", response_model=PayrollRecordSchema)
async def create_payroll_record(
    payroll_data: PayrollRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create a new payroll record (admin only)"""
    # Verify employee exists
    employee = db.query(Employee).filter(Employee.id == payroll_data.employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    # Check for duplicate payroll record for the same period
    existing = db.query(PayrollRecord).filter(
        and_(
            PayrollRecord.employee_id == payroll_data.employee_id,
            PayrollRecord.pay_period_start == payroll_data.pay_period_start,
            PayrollRecord.pay_period_end == payroll_data.pay_period_end
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payroll record already exists for this period"
        )
    
    # Create payroll record
    payroll_record = PayrollRecord(
        **payroll_data.dict(),
        employee_user_id=employee.user_id
    )
    
    db.add(payroll_record)
    db.commit()
    db.refresh(payroll_record)
    return payroll_record


@router.get("/records", response_model=List[PayrollRecordSchema])
async def get_payroll_records(
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = Query(None),
    status_filter: Optional[PayrollStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get payroll records"""
    query = db.query(PayrollRecord)
    
    # Non-admin users can only see their own records
    if not current_user.is_admin:
        query = query.filter(PayrollRecord.employee_user_id == current_user.id)
    elif employee_id:
        query = query.filter(PayrollRecord.employee_id == employee_id)
    
    if status_filter:
        query = query.filter(PayrollRecord.status == status_filter)
    
    records = query.offset(skip).limit(limit).all()
    return records


@router.get("/records/me", response_model=List[PayrollRecordSchema])
async def get_my_payroll_records(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's payroll records"""
    records = db.query(PayrollRecord).filter(
        PayrollRecord.employee_user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return records


@router.get("/records/{record_id}", response_model=PayrollRecordWithEmployee)
async def get_payroll_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific payroll record"""
    record = db.query(PayrollRecord).filter(PayrollRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found"
        )
    
    # Non-admin users can only see their own records
    if not current_user.is_admin and record.employee_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this record"
        )
    
    return record


@router.put("/records/{record_id}", response_model=PayrollRecordSchema)
async def update_payroll_record(
    record_id: int,
    payroll_update: PayrollRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update payroll record (admin only)"""
    record = db.query(PayrollRecord).filter(PayrollRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll record not found"
        )
    
    # Update fields
    update_data = payroll_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    
    # Update processed timestamp if status changed to approved or paid
    if "status" in update_data and update_data["status"] in ["approved", "paid"]:
        record.processed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(record)
    return record


@router.post("/calculate", response_model=dict)
async def calculate_employee_payroll(
    employee_id: int,
    hours_worked: float,
    overtime_hours: float = 0.0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Calculate payroll for an employee"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found"
        )
    
    calculation = calculate_payroll(employee, hours_worked, overtime_hours)
    return {
        "employee_id": employee_id,
        "employee_name": employee.user.full_name,
        **calculation
    }


@router.post("/process-period")
async def process_payroll_period(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Process payroll for all employees for a given period"""
    if start_date >= end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    # Get all active employees
    employees = db.query(Employee).filter(Employee.is_active == True).all()
    processed_records = []
    
    for employee in employees:
        # Check if payroll already exists for this period
        existing = db.query(PayrollRecord).filter(
            and_(
                PayrollRecord.employee_id == employee.id,
                PayrollRecord.pay_period_start == start_date,
                PayrollRecord.pay_period_end == end_date
            )
        ).first()
        
        if existing:
            continue  # Skip if already processed
        
        # Calculate hours from time entries
        time_entries = db.query(TimeEntry).filter(
            and_(
                TimeEntry.employee_id == employee.id,
                TimeEntry.date >= start_date,
                TimeEntry.date <= end_date,
                TimeEntry.status == "approved"
            )
        ).all()
        
        total_hours = sum(entry.total_hours or 0 for entry in time_entries)
        total_overtime = sum(entry.overtime_hours or 0 for entry in time_entries)
        
        # Calculate payroll
        calculation = calculate_payroll(employee, total_hours, total_overtime)
        
        # Create payroll record
        payroll_record = PayrollRecord(
            employee_id=employee.id,
            employee_user_id=employee.user_id,
            pay_period_start=start_date,
            pay_period_end=end_date,
            **calculation
        )
        
        db.add(payroll_record)
        processed_records.append({
            "employee_id": employee.id,
            "employee_name": employee.user.full_name,
            **calculation
        })
    
    db.commit()
    
    return {
        "message": f"Processed payroll for {len(processed_records)} employees",
        "period": f"{start_date} to {end_date}",
        "records": processed_records
    }


@router.get("/summary", response_model=PayrollSummary)
async def get_payroll_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get payroll summary statistics"""
    query = db.query(PayrollRecord)
    
    if start_date:
        query = query.filter(PayrollRecord.pay_period_start >= start_date)
    if end_date:
        query = query.filter(PayrollRecord.pay_period_end <= end_date)
    
    records = query.all()
    
    total_employees = len(set(record.employee_id for record in records))
    total_gross_pay = sum(record.gross_pay for record in records)
    total_net_pay = sum(record.net_pay for record in records)
    
    pending_records = len([r for r in records if r.status == "pending"])
    approved_records = len([r for r in records if r.status == "approved"])
    paid_records = len([r for r in records if r.status == "paid"])
    
    return PayrollSummary(
        total_employees=total_employees,
        total_gross_pay=total_gross_pay,
        total_net_pay=total_net_pay,
        pending_records=pending_records,
        approved_records=approved_records,
        paid_records=paid_records
    )