from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import auth
from app.database import get_db
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    hashed_password = auth.hash_password(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    return db_user

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = auth.create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/password-reset-request")
def password_reset_request(request: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = auth.create_password_reset_token(user.email)
    user.reset_token = token
    db.commit()
    # In production, send token via email. Here, return for testing.
    return {"reset_token": token}

@router.post("/password-reset-confirm")
def password_reset_confirm(confirm: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    email = auth.verify_password_reset_token(confirm.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(models.User).filter(models.User.email == email, models.User.reset_token == confirm.token).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found or invalid token")
    user.hashed_password = auth.hash_password(confirm.new_password)
    user.reset_token = None
    db.commit()
    return {"msg": "Password reset successful"}
