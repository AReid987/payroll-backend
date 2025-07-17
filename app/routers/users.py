from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import User, Employee
from ..schemas import (
    User as UserSchema, UserUpdate,
    Employee as EmployeeSchema, EmployeeCreate, EmployeeUpdate,
    MessageResponse
)
from ..auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/users", tags=["users"])

# User management endpoints
@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """Get current user information from Auth0"""
    return {
        "id": current_user.id,
        "email": getattr(current_user, 'email', None),
        "permissions": getattr(current_user, 'permissions', []),
        "auth0_user": True
    }

@router.put("/me", response_model=UserSchema)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    update_data = user_update.dict(exclude_unset=True)
    user = db.query(User).filter(User.email == current_user['email']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

@router.get("/", response_model=List[UserSchema])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Delete user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

# Employee profile endpoints
@router.get("/me/employee", response_model=EmployeeSchema)
async def get_my_employee_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's employee profile"""
    user = db.query(User).filter(User.email == current_user['email']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    employee = db.query(Employee).filter(Employee.user_id == user.id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    return employee

@router.post("/me/employee", response_model=EmployeeSchema)
async def create_my_employee_profile(
    employee_data: EmployeeCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create employee profile for current user"""
    user = db.query(User).filter(User.email == current_user['email']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(Employee).filter(Employee.user_id == user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee profile already exists")
    employee = Employee(**employee_data.dict(), user_id=user.id)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee
