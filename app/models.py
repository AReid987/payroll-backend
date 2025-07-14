from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    employee_profile = relationship("Employee", back_populates="user", uselist=False)
    payroll_records = relationship("PayrollRecord", back_populates="employee_user")


class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    department = Column(String, nullable=False)
    position = Column(String, nullable=False)
    hire_date = Column(Date, nullable=False)
    salary = Column(Float, nullable=False)
    hourly_rate = Column(Float, nullable=True)
    employment_type = Column(String, default="full_time")  # full_time, part_time, contract
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="employee_profile")
    payroll_records = relationship("PayrollRecord", back_populates="employee")
    time_entries = relationship("TimeEntry", back_populates="employee")


class PayrollRecord(Base):
    __tablename__ = "payroll_records"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    employee_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pay_period_start = Column(Date, nullable=False)
    pay_period_end = Column(Date, nullable=False)
    gross_pay = Column(Float, nullable=False)
    tax_deductions = Column(Float, default=0.0)
    other_deductions = Column(Float, default=0.0)
    net_pay = Column(Float, nullable=False)
    hours_worked = Column(Float, default=0.0)
    overtime_hours = Column(Float, default=0.0)
    status = Column(String, default="pending")  # pending, approved, paid
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    employee = relationship("Employee", back_populates="payroll_records")
    employee_user = relationship("User", back_populates="payroll_records")


class TimeEntry(Base):
    __tablename__ = "time_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    clock_in = Column(DateTime, nullable=False)
    clock_out = Column(DateTime, nullable=True)
    break_duration = Column(Integer, default=0)  # in minutes
    total_hours = Column(Float, nullable=True)
    overtime_hours = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    status = Column(String, default="active")  # active, completed, approved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    employee = relationship("Employee", back_populates="time_entries")


class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    budget = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())