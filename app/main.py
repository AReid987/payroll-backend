from fastapi import FastAPI
from .database import engine, Base
from .routers.users import router as users_router, auth_router
from .config import settings

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="A comprehensive FastAPI application for payroll management",
    version="0.1.0",
    debug=settings.debug
)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)

# Import and include other routers
from .routers.processing import router as payroll_router
from .routers.hitl import router as time_router

app.include_router(payroll_router)
app.include_router(time_router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Payroll Backend API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)