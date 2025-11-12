# FastAPI Project Structure

## Overview
Your FastAPI application has been refactored to follow best practices with proper separation of concerns.

## Project Structure

```
backend/app/
├── main.py                 # Application entry point - FastAPI app initialization
├── core/
│   ├── __init__.py
│   └── config.py          # Settings/Configuration from environment variables
├── db/
│   ├── __init__.py
│   └── database.py        # Database setup, session management, Base class
├── models/
│   └── __init__.py        # SQLAlchemy models (User, NewsArticle)
├── api/
│   ├── __init__.py
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── security.py        # Authentication, JWT, password hashing
│   ├── routes_users.py    # User registration, login, profile endpoints
│   ├── routes_news.py     # News articles, upvotes, summarization endpoints
│   └── routes_prices.py   # Price data endpoints
└── services/
    └── __init__.py        # Business logic services (Auth, News, Upvote)
```

## Module Responsibilities

### `core/config.py` - Settings
- Centralizes environment variable configuration
- Contains `Settings` class with defaults
- Accessed via `from app.core.config import settings`

### `db/database.py` - Database
- Creates SQLAlchemy engine and session factory
- Provides `get_db_session()` dependency for FastAPI
- Exports `Base` and `engine` for model initialization

### `models/__init__.py` - Data Models
- `User` - Represents application users
- `NewsArticle` - Represents news articles
- `user_news_association_table` - Many-to-many relationship for upvotes

### `api/schemas.py` - Request/Response Validation
- Pydantic models for all API inputs/outputs
- Includes: `UserResponse`, `TokenResponse`, `NewsArticleResponse`, etc.
- Used for automatic OpenAPI documentation

### `api/security.py` - Authentication & Security
- Password hashing and verification (`verify_password`, `hash_password`)
- JWT token creation (`create_access_token`)
- Current user dependency (`get_current_user`)
- OAuth2 scheme setup

### `api/routes_*.py` - API Endpoints
- **routes_users.py**: `/api/v1/users/*` - Register, Login, Get Profile
- **routes_news.py**: `/api/v1/news/*` - Get news, upvote, summarize
- **routes_prices.py**: `/api/v1/prices/*` - Get price data

### `services/__init__.py` - Business Logic
- **AuthService** - User authentication and creation
- **NewsService** - News fetching, processing, summarization, retrieval
- **UpvoteService** - Toggle upvotes on articles

### `main.py` - Application Entry Point
- Initializes FastAPI app with lifespan context manager
- Sets up CORS middleware
- Includes all routers
- Manages background scheduler for news fetching
- Health check endpoint

## Key Features

✅ **Proper Separation of Concerns**
- Each module has a single responsibility
- Easy to test, maintain, and extend

✅ **Dependency Injection**
- Database sessions via `Depends(get_db_session)`
- Current user via `Depends(get_current_user)`
- Testable and flexible

✅ **Type Safety**
- All functions have type hints
- Pydantic schemas for validation
- Better IDE autocomplete and error detection

✅ **Clean API Structure**
- Routers organized by resource (users, news, prices)
- Consistent endpoint naming
- Proper HTTP status codes and error handling

✅ **Security**
- Password hashing with bcrypt
- JWT token-based authentication
- OAuth2 security scheme

✅ **Scalability**
- Easy to add new routes (create new file in `api/`)
- Easy to add new services (add to `services/`)
- Clean database layer for migrations

## Running the Application

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

## API Endpoints

### Users (`/api/v1/users`)
- `POST /register` - Create new user
- `POST /login` - Get JWT token
- `GET /me` - Get current user info (requires auth)

### News (`/api/v1/news`)
- `GET /news` - Get all articles
- `GET /user_news` - Get articles with user's upvote status (requires auth)
- `POST /search_news` - Search articles by keyword
- `POST /news_summary` - Generate AI summary (requires auth)
- `POST /{article_id}/upvote` - Toggle upvote (requires auth)

### Prices (`/api/v1/prices`)
- `GET /necessities-price` - Get price data by category/commodity

### Health
- `GET /health` - Health check

## Configuration

Set environment variables:
```bash
DATABASE_URL=sqlite:///news_database.db
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
SENTRY_DSN=your-sentry-dsn
```

## Next Steps

1. **Run tests**: `pytest tests/`
2. **Add more services**: Create new files in `services/`
3. **Add more routes**: Create new files in `api/`
4. **Database migrations**: Use Alembic with the existing setup
5. **API documentation**: Automatically available at `/docs` (Swagger UI) and `/redoc` (ReDoc)
