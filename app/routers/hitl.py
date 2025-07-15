from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from datetime import datetime, date, timedelta

from ..database import get_db
from ..models import User, Employee, TimeEntry
from ..schemas import (
    TimeEntry as TimeEntrySchema,
    TimeEntryCreate, TimeEntryUpdate,
    MessageResponse, TimeEntryStatus
)
from ..auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/time", tags=["time-tracking"])


def calculate_hours(clock_in: datetime, clock_out: datetime, break_duration: int = 0) -> tuple:
    """Calculate total hours and overtime hours"""
    if clock_out <= clock_in:
        raise ValueError("Clock out time must be after clock in time")
    
    # Calculate total time worked minus breaks
    total_minutes = (clock_out - clock_in).total_seconds() / 60
    total_minutes -= break_duration
    total_hours = total_minutes / 60
    
    # Calculate overtime (anything over 8 hours per day)
    regular_hours = min(total_hours, 8.0)
    overtime_hours = max(0, total_hours - 8.0)
    
    return round(total_hours, 2), round(overtime_hours, 2)


@router.post("/entries", response_model=TimeEntrySchema)
async def clock_in(
    time_entry: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clock in - create a new time entry"""
    # Get employee profile
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found. Please create an employee profile first."
        )
    
    # Check if there's already an active time entry for today
    existing = db.query(TimeEntry).filter(
        and_(
            TimeEntry.employee_id == employee.id,
            TimeEntry.date == time_entry.date,
            TimeEntry.status == "active"
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already clocked in for today. Please clock out first."
        )
    
    # Create time entry
    entry = TimeEntry(
        **time_entry.dict(),
        employee_id=employee.id
    )
    
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/entries/{entry_id}/clock-out", response_model=TimeEntrySchema)
async def clock_out(
    entry_id: int,
    clock_out_time: datetime,
    break_duration: Optional[int] = 0,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clock out - update time entry with clock out time"""
    # Get employee profile
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    # Get time entry
    entry = db.query(TimeEntry).filter(
        and_(
            TimeEntry.id == entry_id,
            TimeEntry.employee_id == employee.id
        )
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    if entry.clock_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already clocked out"
        )
    
    # Calculate hours
    try:
        total_hours, overtime_hours = calculate_hours(
            entry.clock_in, 
            clock_out_time, 
            break_duration or entry.break_duration
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Update entry
    entry.clock_out = clock_out_time
    entry.break_duration = break_duration or entry.break_duration
    entry.total_hours = total_hours
    entry.overtime_hours = overtime_hours
    entry.status = "completed"
    if notes:
        entry.notes = notes
    
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/entries/me", response_model=List[TimeEntrySchema])
async def get_my_time_entries(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's time entries"""
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    query = db.query(TimeEntry).filter(TimeEntry.employee_id == employee.id)
    
    if start_date:
        query = query.filter(TimeEntry.date >= start_date)
    if end_date:
        query = query.filter(TimeEntry.date <= end_date)
    
    entries = query.order_by(TimeEntry.date.desc()).offset(skip).limit(limit).all()
    return entries


@router.get("/entries", response_model=List[TimeEntrySchema])
async def get_time_entries(
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    status_filter: Optional[TimeEntryStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get time entries (admin only)"""
    query = db.query(TimeEntry)
    
    if employee_id:
        query = query.filter(TimeEntry.employee_id == employee_id)
    if start_date:
        query = query.filter(TimeEntry.date >= start_date)
    if end_date:
        query = query.filter(TimeEntry.date <= end_date)
    if status_filter:
        query = query.filter(TimeEntry.status == status_filter)
    
    entries = query.order_by(TimeEntry.date.desc()).offset(skip).limit(limit).all()
    return entries


@router.get("/entries/{entry_id}", response_model=TimeEntrySchema)
async def get_time_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific time entry"""
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    # Non-admin users can only see their own entries
    if not current_user.is_admin:
        employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not employee or entry.employee_id != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this entry"
            )
    
    return entry


@router.put("/entries/{entry_id}", response_model=TimeEntrySchema)
async def update_time_entry(
    entry_id: int,
    entry_update: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update time entry"""
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    # Check permissions
    if not current_user.is_admin:
        employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not employee or entry.employee_id != employee.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this entry"
            )
        
        # Non-admin users can't approve their own entries
        if entry_update.status == "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot approve your own time entry"
            )
    
    # Update fields
    update_data = entry_update.dict(exclude_unset=True)
    
    # Recalculate hours if clock_out or break_duration changed
    if "clock_out" in update_data or "break_duration" in update_data:
        clock_out = update_data.get("clock_out", entry.clock_out)
        break_duration = update_data.get("break_duration", entry.break_duration)
        
        if clock_out:
            try:
                total_hours, overtime_hours = calculate_hours(
                    entry.clock_in, clock_out, break_duration
                )
                update_data["total_hours"] = total_hours
                update_data["overtime_hours"] = overtime_hours
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
    
    for field, value in update_data.items():
        setattr(entry, field, value)
    
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", response_model=MessageResponse)
async def delete_time_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete time entry (admin only)"""
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found"
        )
    
    db.delete(entry)
    db.commit()
    return {"message": "Time entry deleted successfully"}


@router.get("/summary/me")
async def get_my_time_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get time summary for current user"""
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    query = db.query(TimeEntry).filter(TimeEntry.employee_id == employee.id)
    
    if start_date:
        query = query.filter(TimeEntry.date >= start_date)
    if end_date:
        query = query.filter(TimeEntry.date <= end_date)
    
    entries = query.all()
    
    total_hours = sum(entry.total_hours or 0 for entry in entries)
    total_overtime = sum(entry.overtime_hours or 0 for entry in entries)
    total_days = len(set(entry.date for entry in entries))
    
    return {
        "total_hours": total_hours,
        "total_overtime_hours": total_overtime,
        "total_regular_hours": total_hours - total_overtime,
        "total_days_worked": total_days,
        "average_hours_per_day": round(total_hours / total_days, 2) if total_days > 0 else 0,
        "period": {
            "start_date": start_date,
            "end_date": end_date
        }
    }