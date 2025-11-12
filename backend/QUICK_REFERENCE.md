# FastAPI Project - Quick Reference Card

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# View API docs
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc

# Run tests
pytest tests/

# Build Docker image
docker build -t price-tracker .
```

## 📁 File Guide

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `main.py` | Entry point | `app`, `lifespan`, `health_check()` |
| `core/config.py` | Settings | `Settings`, `settings` |
| `db/database.py` | Database | `engine`, `SessionLocal`, `Base`, `get_db_session()` |
| `models/__init__.py` | ORM Models | `User`, `NewsArticle`, `user_news_association_table` |
| `api/security.py` | Auth | `verify_password()`, `create_access_token()`, `get_current_user()` |
| `api/schemas.py` | Validation | `UserResponse`, `TokenResponse`, `NewsArticleResponse`, etc. |
| `api/routes_users.py` | User routes | `register()`, `login()`, `get_user_me()` |
| `api/routes_news.py` | News routes | `get_all_news()`, `get_user_news_articles()`, `upvote_article()` |
| `api/routes_prices.py` | Price routes | `get_necessities_prices()` |
| `services/__init__.py` | Business logic | `AuthService`, `NewsService`, `UpvoteService` |

## 🔌 Common Tasks

### Add New Endpoint

```python
# Create app/api/routes_items.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db_session

router = APIRouter(prefix="/api/v1/items", tags=["items"])

@router.get("/")
def list_items(db: Session = Depends(get_db_session)):
    # Your code here
    return []

# Add to main.py:
from app.api import routes_items
app.include_router(routes_items.router)
```

### Add New Service

```python
# In app/services/__init__.py, add:
class ItemService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_items(self):
        # Business logic here
        pass
    
    def create_item(self, name: str):
        # Business logic here
        pass

# Use in routes:
from app.services import ItemService

@router.post("/")
def create(name: str, db: Session = Depends(get_db_session)):
    service = ItemService(db)
    return service.create_item(name)
```

### Add New Model

```python
# In app/models/__init__.py, add:
class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)

# Then create migration (if using Alembic):
alembic revision --autogenerate -m "Add items table"
alembic upgrade head
```

### Add New Schema

```python
# In app/api/schemas.py, add:
from pydantic import BaseModel

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    
    class Config:
        from_attributes = True

# Use in routes:
@router.post("/", response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db_session)):
    # Your code
    pass
```

## 🔐 Authentication

### Protected Routes

```python
from app.api.security import get_current_user
from app.models import User

@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    # current_user is automatically injected
    return {"username": current_user.username}
```

### Login Flow

```python
# 1. Client posts credentials
POST /api/v1/users/login
Content-Type: application/x-www-form-urlencoded

username=user&password=pass

# 2. Server returns token
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}

# 3. Client uses token in requests
GET /api/v1/users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## 🗄️ Database Operations

### Create Database Sessions

```python
# In routes (automatic via dependency):
@router.get("/")
def list_items(db: Session = Depends(get_db_session)):
    items = db.query(Item).all()
    return items

# In services:
def __init__(self, db: Session):
    self.db = db

def get_items(self):
    return self.db.query(Item).all()

# In background tasks:
from app.db.database import SessionLocal
db = SessionLocal()
try:
    # Use db
    pass
finally:
    db.close()
```

### Query Examples

```python
from app.models import User, NewsArticle

# Get all
users = db.query(User).all()

# Get one
user = db.query(User).filter(User.username == "john").first()

# Get by ID
user = db.query(User).filter(User.id == 1).first()

# Count
count = db.query(User).count()

# Order by
users = db.query(User).order_by(User.username).all()

# Filter with multiple conditions
articles = db.query(NewsArticle).filter(
    NewsArticle.title.contains("price")
).filter(
    NewsArticle.summary != ""
).all()
```

## 📊 API Response Format

All responses follow this pattern:

### Success (2xx)
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com"
}
```

### Error (4xx/5xx)
```json
{
  "detail": "Error message here"
}
```

## 🧪 Testing

```python
# tests/test_users.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register():
    response = client.post(
        "/api/v1/users/register",
        json={"username": "test", "password": "pass123"}
    )
    assert response.status_code == 201
    assert response.json()["username"] == "test"

def test_login():
    response = client.post(
        "/api/v1/users/login",
        data={"username": "test", "password": "pass123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_protected_route():
    # Get token
    login_response = client.post(
        "/api/v1/users/login",
        data={"username": "test", "password": "pass123"}
    )
    token = login_response.json()["access_token"]
    
    # Use token
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
```

## 🔧 Environment Variables

```bash
# .env file
DATABASE_URL=sqlite:///news_database.db
SECRET_KEY=your-secret-key-here-change-in-production
OPENAI_API_KEY=sk-...
SENTRY_DSN=https://...@ingest.sentry.io/...
```

## 📈 Project Statistics

- **Files**: 13 Python files
- **Lines**: ~793 (well-organized)
- **Classes**: 8 (User, NewsArticle, services)
- **Routes**: 9 endpoints
- **Services**: 3 (Auth, News, Upvote)
- **Models**: 2 (User, NewsArticle)

## ✅ Checklist for New Features

- [ ] Create service class (if business logic needed)
- [ ] Create model class (if data storage needed)
- [ ] Create schema classes (for validation)
- [ ] Create route functions (for endpoints)
- [ ] Add route to main.py
- [ ] Write tests
- [ ] Update documentation

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| Import errors | Check file paths, ensure `__init__.py` exists |
| 404 on endpoints | Router not included in main.py |
| 401 on protected routes | Missing/invalid token or expired |
| Database errors | Check DATABASE_URL env var, ensure DB initialized |
| Type errors | Check type hints match actual types |

## 📚 Resources

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Pydantic: https://docs.pydantic.dev/
- Project docs: See `ARCHITECTURE.md` and `REFACTORING_GUIDE.md`

---

**Last Updated**: November 13, 2025  
**Status**: ✅ Production Ready
