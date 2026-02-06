# Python Development Skill

## Project Structure
```
project/
├── src/
│   ├── __init__.py
│   ├── main.py           # Entry point
│   ├── config.py         # Settings (pydantic)
│   ├── api/              # FastAPI routers
│   │   ├── __init__.py
│   │   └── routes/
│   ├── core/             # Business logic
│   │   ├── __init__.py
│   │   └── services/
│   ├── models/           # Database models
│   │   ├── __init__.py
│   │   └── user.py
│   └── schemas/          # Pydantic schemas
│       ├── __init__.py
│       └── user.py
├── tests/
│   ├── conftest.py       # Fixtures
│   ├── test_api/
│   └── test_services/
├── pyproject.toml
└── .env.example
```

## FastAPI Patterns

### Router Structure
```python
# api/routes/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.services.user import UserService
from src.schemas.user import UserCreate, UserResponse
from src.api.deps import get_db, get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    db: Session = Depends(get_db)
):
    service = UserService(db)
    return await service.create(data)
```

### Pydantic Schemas
```python
# schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}
```

### Service Layer
```python
# core/services/user.py
from sqlalchemy.orm import Session
from src.models.user import User
from src.schemas.user import UserCreate
from src.core.security import hash_password

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()
    
    async def create(self, data: UserCreate) -> User:
        user = User(
            email=data.email,
            name=data.name,
            password_hash=hash_password(data.password)
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
```

## SQLAlchemy Patterns

### Model Definition
```python
# models/user.py
from sqlalchemy import Column, Integer, String, DateTime, func
from src.models.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### Database Session
```python
# api/deps.py
from typing import Generator
from src.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Testing Patterns

### Fixtures (conftest.py)
```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.api.deps import get_db
from src.models.base import Base

# Test database
TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/test_db"
engine = create_engine(TEST_DATABASE_URL)
TestingSession = sessionmaker(bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

### Test Structure
```python
# tests/test_api/test_users.py
import pytest

class TestUserEndpoints:
    def test_create_user(self, client):
        response = client.post("/api/users/", json={
            "email": "test@example.com",
            "name": "Test User",
            "password": "SecurePass123"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
    
    def test_create_user_invalid_email(self, client):
        response = client.post("/api/users/", json={
            "email": "invalid",
            "name": "Test User",
            "password": "SecurePass123"
        })
        assert response.status_code == 422
```

## Configuration
```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    model_config = {"env_file": ".env"}

settings = Settings()
```

## Common Commands
```bash
# Install
pip install -e ".[dev]"

# Run
uvicorn src.main:app --reload

# Test
pytest -v --cov=src

# Lint
ruff check .
ruff format .

# Type check
mypy src/
```

## Anti-Patterns to Avoid
- ❌ Business logic in routes (use services)
- ❌ Raw SQL without parameterization
- ❌ Synchronous I/O in async functions
- ❌ No input validation (always use Pydantic)
- ❌ Hardcoded config (use env vars)
