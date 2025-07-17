from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from .models import User, Employee, Department
from passlib.context import CryptContext
from datetime import date

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(db: Session, user_data: dict):
    """Create a new user with hashed password"""
    hashed_password = pwd_context.hash(user_data["password"])
    user = User(
        username=user_data["username"],
        email=user_data["email"],
        hashed_password=hashed_password,
        full_name=user_data["full_name"],
        is_active=user_data.get("is_active", True),
        is_admin=user_data.get("is_admin", False)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def init_database():
    """Initialize database with tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")


def create_admin_user(
    username: str = "admin",
    email: str = "admin@payroll.local",
    password: str = "admin123",
    full_name: str = "System Administrator"
):
    """Create an admin user"""
    db = SessionLocal()
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == username).first()
        if existing_admin:
            print(f"Admin user '{username}' already exists!")
            return existing_admin
        
        # Create admin user
        admin_data = {
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name,
            "is_active": True,
            "is_admin": True
        }
        
        admin_user = create_user(db, admin_data)
        print(f"Admin user '{username}' created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        return admin_user
        
    finally:
        db.close()


def create_sample_data():
    """Create sample departments and users for testing"""
    db = SessionLocal()
    try:
        # Create departments
        departments = [
            {"name": "Human Resources", "description": "HR Department", "budget": 100000.0},
            {"name": "Engineering", "description": "Software Development", "budget": 500000.0},
            {"name": "Sales", "description": "Sales and Marketing", "budget": 200000.0},
            {"name": "Finance", "description": "Finance and Accounting", "budget": 150000.0}
        ]
        
        for dept_data in departments:
            existing = db.query(Department).filter(Department.name == dept_data["name"]).first()
            if not existing:
                dept = Department(**dept_data)
                db.add(dept)
                print(f"Created department: {dept_data['name']}")
        
        # Create sample users
        sample_users = [
            {
                "username": "john.doe",
                "email": "john.doe@payroll.local",
                "password": "password123",
                "full_name": "John Doe",
                "is_admin": False
            },
            {
                "username": "jane.smith",
                "email": "jane.smith@payroll.local", 
                "password": "password123",
                "full_name": "Jane Smith",
                "is_admin": False
            },
            {
                "username": "bob.wilson",
                "email": "bob.wilson@payroll.local",
                "password": "password123", 
                "full_name": "Bob Wilson",
                "is_admin": False
            }
        ]
        
        for user_data in sample_users:
            existing = db.query(User).filter(User.username == user_data["username"]).first()
            if not existing:
                user = create_user(db, user_data)
                print(f"Created user: {user_data['username']}")
                
                # Create employee profile
                employee_data = {
                    "user_id": user.id,
                    "employee_id": f"EMP{user.id:03d}",
                    "department": "Engineering" if "john" in user_data["username"] else "Sales",
                    "position": "Software Developer" if "john" in user_data["username"] else "Sales Representative",
                    "hire_date": date(2024, 1, 15),
                    "salary": 75000.0,
                    "hourly_rate": 36.06,  # ~75k annually
                    "employment_type": "full_time"
                }
                
                employee = Employee(**employee_data)
                db.add(employee)
                print(f"Created employee profile for: {user_data['full_name']}")
        
        db.commit()
        print("Sample data created successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating sample data: {e}")
    finally:
        db.close()


def setup_payroll_system():
    """Complete setup of the payroll system"""
    print("Setting up Payroll System...")
    print("=" * 50)
    
    # Initialize database
    init_database()
    
    # Create admin user
    admin = create_admin_user()
    
    # Create sample data
    create_sample_data()
    
    print("=" * 50)
    print("Setup completed successfully!")
    print("\nYou can now:")
    print("1. Start the server: pdm run dev")
    print("2. Visit the API docs: http://localhost:8000/docs")
    print("3. Login with admin credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\nSample users created:")
    print("   - john.doe / password123")
    print("   - jane.smith / password123") 
    print("   - bob.wilson / password123")


if __name__ == "__main__":
    setup_payroll_system()