# Price Tracker - Code Structure Map

This document provides a visual map of the entire backend structure, showing how different modules are organized and their relationships.

## 📊 Project Structure Tree

```
backend/
├── 📄 requirements.txt           # Dependencies
├── 📄 pytest.ini                 # Test configuration
├── 📄 alembic.ini                # Database migration config
│
├── 📁 alembic/                   # Database migrations
│   ├── versions/                 # Migration scripts
│   ├── env.py                    # Alembic environment setup
│   └── script.py.mako            # Migration template
│
├── 📁 app/                       # Main application code
│   │
│   ├── 🚀 main.py                # Application entry point
│   │
│   ├── 📁 core/                  # Global configuration
│   │   ├── __init__.py
│   │   └── config.py             # Environment settings, API keys, DB URL
│   │
│   ├── 📁 db/                    # Database layer
│   │   ├── __init__.py
│   │   └── database.py           # SQLAlchemy engine, sessions, Base class
│   │
│   ├── 📁 models/                # Data models
│   │   └── __init__.py           # User, NewsArticle, associations
│   │
│   ├── 📁 api/                   # API layer (routes, schemas, security)
│   │   ├── __init__.py
│   │   ├── security.py           # JWT, password hashing, auth dependencies
│   │   ├── schemas.py            # Pydantic request/response models
│   │   │
│   │   ├── 👥 routes_users.py    # User routes (register, login, profile)
│   │   ├── 📰 routes_news.py     # News routes (CRUD, upvotes, search)
│   │   └── 💰 routes_prices.py   # Price routes (external API)
│   │
│   └── 📁 services/              # Business logic layer
│       └── __init__.py           # AuthService, NewsService, UpvoteService
│
└── 📁 tests/                     # Test suite
    ├── __init__.py
    └── integration/
        ├── test_user_endpoint.py
        ├── test_news_endpoint.py
        └── test_price_endpoint.py
```

## 🏗️ Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 1: HTTP Endpoints (Routers)                                      │
│ ├─ routes_users.py   (register, login, me)                            │
│ ├─ routes_news.py    (list, search, summarize, upvote)               │
│ └─ routes_prices.py  (fetch external prices)                         │
└─────────────────────────────────────────────────────────────────────────┘
                              ▲  │
                              │  │ calls
                              │  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Request/Response Validation (Schemas)                         │
│ └─ schemas.py        (Pydantic models for validation)                 │
└─────────────────────────────────────────────────────────────────────────┘
                              ▲  │
                              │  │ uses
                              │  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Security & Dependencies                                       │
│ └─ security.py       (JWT, auth, dependencies)                        │
└─────────────────────────────────────────────────────────────────────────┘
                              ▲  │
                              │  │ injects
                              │  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 4: Business Logic (Services)                                     │
│ ├─ AuthService       (user creation, authentication)                  │
│ ├─ NewsService       (fetch, process, analyze, store articles)       │
│ └─ UpvoteService     (manage upvotes)                                │
└─────────────────────────────────────────────────────────────────────────┘
                              ▲  │
                              │  │ uses
                              │  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 5: Data Models (ORM)                                             │
│ ├─ User               (id, username, hashed_password)                 │
│ ├─ NewsArticle       (id, url, title, content, summary, etc.)       │
│ └─ user_news_upvotes (junction table for many-to-many)              │
└─────────────────────────────────────────────────────────────────────────┘
                              ▲  │
                              │  │ CRUD
                              │  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 6: Database Access                                               │
│ └─ database.py       (SQLAlchemy engine, sessions, transaction mgmt)  │
└─────────────────────────────────────────────────────────────────────────┘
                              ▲  │
                              │  │ connects
                              │  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 7: Persistence                                                   │
│ └─ SQLite DB         (news_database.db on disk)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## 📁 Module-by-Module Breakdown

### `app/main.py` - Application Entry Point
```
Responsibilities:
├─ FastAPI app initialization
├─ Router registration (users, news, prices)
├─ CORS middleware setup
├─ Background scheduler for news fetching
├─ Lifespan context manager (startup/shutdown)
└─ Health check endpoint

Imports from:
├─ api/routes_*.py      (all routers)
├─ core/config          (settings)
├─ db/database          (Base, engine, SessionLocal)
└─ services/__init__    (NewsService)
```

### `app/core/config.py` - Configuration
```
Responsibilities:
├─ Read environment variables (DATABASE_URL, SECRET_KEY, OPENAI_API_KEY, SENTRY_DSN)
├─ Define default settings
├─ Configure CORS origins
├─ Set news fetch interval and page limit
└─ Create global settings instance

Key Classes:
└─ Settings          (all configuration as class attributes)

Usage:
└─ from app.core.config import settings
```

### `app/db/database.py` - Database Layer
```
Responsibilities:
├─ SQLAlchemy engine creation
├─ Session factory setup
├─ Base class for ORM models
└─ FastAPI dependency: get_db_session()

Key Exports:
├─ Base                (SQLAlchemy Base)
├─ engine              (database connection pool)
├─ SessionLocal        (session factory)
└─ get_db_session()    (FastAPI dependency)

Usage in routes:
└─ db: Session = Depends(get_db_session)
```

### `app/models/__init__.py` - Data Models
```
Responsibilities:
├─ Define SQLAlchemy ORM models
├─ Define relationships
└─ Define association tables

Key Models:
├─ User
│  ├─ id: Integer (primary key)
│  ├─ username: String (unique)
│  ├─ hashed_password: String
│  └─ upvoted_news: relationship → NewsArticle (through association)
│
├─ NewsArticle
│  ├─ id: Integer (primary key)
│  ├─ url: String (unique)
│  ├─ title: String
│  ├─ time: String
│  ├─ content: Text
│  ├─ summary: Text
│  ├─ reason: Text
│  └─ upvoted_by_users: relationship → User (through association)
│
└─ user_news_upvotes
   └─ Junction table (user_id, article_id) - many-to-many

Usage:
└─ from app.models import User, NewsArticle
```

### `app/api/security.py` - Security & Authentication
```
Responsibilities:
├─ Password hashing (bcrypt)
├─ Password verification
├─ JWT token creation
├─ JWT token validation
└─ OAuth2 dependency injection

Key Functions:
├─ verify_password(plain, hashed) → bool
├─ hash_password(plain) → str
├─ create_access_token(data, expires_delta) → str
├─ get_current_user(token, db) → User (FastAPI dependency)
│
└─ pwd_context            (bcrypt context)
└─ oauth2_scheme          (OAuth2PasswordBearer)

Usage in routes:
├─ current_user: User = Depends(get_current_user)
└─ token = create_access_token({"sub": username})
```

### `app/api/schemas.py` - Request/Response Models
```
Responsibilities:
├─ Define Pydantic models for validation
├─ Define request models
├─ Define response models
└─ Automatic OpenAPI documentation

Key Models:
├─ User Schemas
│  ├─ UserBase          (username)
│  ├─ UserCreate        (username, password)
│  └─ UserResponse      (id, username)
│
├─ Auth Schemas
│  └─ TokenResponse     (access_token, token_type)
│
├─ News Schemas
│  ├─ NewsArticleResponse  (full article with upvotes)
│  ├─ PromptRequest        (search prompt)
│  ├─ NewsSummaryRequest   (content to summarize)
│  ├─ NewsSummaryResponse  (summary, reason)
│  └─ UpvoteResponse       (message)

Usage in routes:
├─ def register(user: UserCreate) → UserResponse
└─ def get_all_news() → List[NewsArticleResponse]
```

### `app/api/routes_users.py` - User Endpoints
```
Endpoints:
├─ POST   /api/v1/users/register
│  ├─ Input: UserCreate (username, password)
│  ├─ Output: UserResponse
│  ├─ Logic: Check duplicate, hash password, save to DB
│  └─ Uses: AuthService.create_user()
│
├─ POST   /api/v1/users/login
│  ├─ Input: OAuth2PasswordRequestForm (username, password)
│  ├─ Output: TokenResponse (JWT token)
│  ├─ Logic: Validate credentials, generate JWT
│  └─ Uses: AuthService.authenticate_user(), create_access_token()
│
└─ GET    /api/v1/users/me
   ├─ Input: (requires JWT token in header)
   ├─ Output: UserResponse
   ├─ Logic: Extract user from JWT
   └─ Uses: Depends(get_current_user)

Imports:
└─ routes_users imports from: schemas, security, services, database, models
```

### `app/api/routes_news.py` - News Endpoints
```
Endpoints:
├─ GET    /api/v1/news/news
│  ├─ Output: List[NewsArticleResponse]
│  └─ Uses: NewsService.get_all_news()
│
├─ GET    /api/v1/news/user_news
│  ├─ Requires: JWT authentication
│  ├─ Output: List[NewsArticleResponse] (with user's upvote status)
│  └─ Uses: NewsService.get_user_news(user_id)
│
├─ POST   /api/v1/news/search_news
│  ├─ Input: PromptRequest (search keywords)
│  ├─ Output: search results
│  └─ Uses: NewsService methods (placeholder)
│
├─ POST   /api/v1/news/news_summary
│  ├─ Requires: JWT authentication
│  ├─ Input: NewsSummaryRequest (content)
│  ├─ Output: NewsSummaryResponse (summary, reason)
│  └─ Uses: NewsService._generate_summary()
│
└─ POST   /api/v1/news/{article_id}/upvote
   ├─ Requires: JWT authentication
   ├─ Input: article_id (path parameter)
   ├─ Output: UpvoteResponse
   └─ Uses: UpvoteService.toggle_upvote()

Imports:
└─ routes_news imports from: schemas, security, services, database, models
```

### `app/api/routes_prices.py` - Price Endpoints
```
Endpoints:
└─ GET    /api/v1/prices/necessities-price
   ├─ Query params: category, commodity (optional)
   ├─ Output: JSON from external API
   ├─ Logic: Proxy to government price data API
   └─ External: https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice

Imports:
└─ routes_prices imports from: schemas, security
```

### `app/services/__init__.py` - Business Logic
```
Classes:

AuthService
├─ authenticate_user(db, username, password) → User | None
│  └─ Verify credentials
└─ create_user(db, username, password) → User
   └─ Hash password, save to DB

NewsService
├─ _fetch_remote_news(search_term, is_initial) → List[dict]
│  └─ Fetch from external news API (UDN)
├─ _evaluate_relevance(title) → "high"|"medium"|"low"
│  └─ Use OpenAI to evaluate news relevance
├─ _scrape_article_details(url) → {title, time, content}
│  └─ Use BeautifulSoup to scrape HTML
├─ _generate_summary(content) → {summary, reason}
│  └─ Use OpenAI to generate summary
├─ fetch_and_process_news(is_initial) → None
│  └─ Full pipeline: fetch → evaluate → scrape → summarize → save
├─ get_all_news() → List[dict]
│  └─ Get all articles with upvote counts
└─ get_user_news(user_id) → List[dict]
   └─ Get all articles with user's upvote status

UpvoteService
└─ toggle_upvote(article_id, user_id) → str
   ├─ Check if upvote exists
   ├─ If yes: delete it
   └─ If no: create it

Imports:
└─ services imports from: config, models, security, database
```

## 🔄 Data Flow Examples

### User Registration Flow
```
Client (HTTP POST)
    ↓
routes_users.register()
    ↓
    ├─ Validate UserCreate schema (Pydantic)
    ├─ Check username not duplicate
    ↓
    AuthService.create_user()
    ├─ Hash password
    ├─ Create User model
    ├─ db.add(user)
    ├─ db.commit()
    ↓
    Database (SQLite)
    ├─ INSERT INTO users (username, hashed_password)
    ↓
    UserResponse schema
    ├─ Return: {id, username}
    ↓
Client (HTTP 201)
```

### News Upvote Flow
```
Client (HTTP POST with JWT)
    ↓
routes_news.upvote_article()
    ├─ Extract JWT from header
    ├─ Validate user with get_current_user() dependency
    ├─ Verify article exists
    ↓
    UpvoteService.toggle_upvote()
    ├─ Query association table
    ├─ If exists: DELETE
    ├─ If not: INSERT
    ├─ db.commit()
    ↓
    Database (SQLite)
    ├─ UPDATE user_news_upvotes
    ↓
    UpvoteResponse schema
    ├─ Return: {message: "Article upvoted"}
    ↓
Client (HTTP 200)
```

### News Fetch & Process Flow
```
Background Scheduler (every 100 minutes)
    ↓
    NewsService.fetch_and_process_news()
    ├─ _fetch_remote_news("價格")
    │  └─ Call UDN API → get List[news items]
    ├─ FOR each news item:
    │  ├─ _evaluate_relevance(title)
    │  │  └─ Call OpenAI → "high"/"medium"/"low"
    │  ├─ IF "high":
    │  │  ├─ _scrape_article_details(url)
    │  │  │  └─ BeautifulSoup → parse HTML
    │  │  ├─ _generate_summary(content)
    │  │  │  └─ Call OpenAI → {summary, reason}
    │  │  ├─ Create NewsArticle model
    │  │  ├─ db.add(article)
    │  │  ├─ db.commit()
    ↓
    Database (SQLite)
    ├─ INSERT INTO news_articles
    ├─ INSERT INTO user_news_upvotes (empty, no upvotes yet)
    ↓
Done
```

## 📊 File Statistics

| Module | File | Lines | Responsibility |
|--------|------|-------|-----------------|
| Core | `core/config.py` | 32 | Configuration |
| Database | `db/database.py` | 26 | DB setup |
| Models | `models/__init__.py` | 46 | ORM models |
| Security | `api/security.py` | 62 | Auth & JWT |
| Schemas | `api/schemas.py` | 69 | Validation |
| Routes - Users | `api/routes_users.py` | 68 | User endpoints |
| Routes - News | `api/routes_news.py` | 79 | News endpoints |
| Routes - Prices | `api/routes_prices.py` | 40 | Price endpoints |
| Services | `services/__init__.py` | 276 | Business logic |
| Main | `main.py` | 65 | Entry point |
| **Total** | **13 files** | **~793** | **Complete app** |

## 🔌 Import Dependencies Map

```
main.py
├─ imports: config, database, services, routes (all)
├─ uses: FastAPI, CORSMiddleware, lifespan
└─ creates: app, scheduler

routes_users.py
├─ imports: schemas, security, AuthService
├─ uses: get_db_session, get_current_user
└─ returns: UserResponse, TokenResponse

routes_news.py
├─ imports: schemas, security, NewsService, UpvoteService
├─ uses: get_db_session, get_current_user
└─ returns: List[NewsArticleResponse]

routes_prices.py
├─ imports: schemas
├─ external: requests (to government API)
└─ returns: JSON

security.py
├─ imports: config, database, models
├─ uses: settings, User model
└─ provides: dependencies for routes

schemas.py
├─ imports: Pydantic
├─ uses: BaseModel
└─ provides: validation for routes

services/__init__.py
├─ imports: config, models, security, database
├─ uses: settings, User, NewsArticle
└─ provides: business logic for routes

models/__init__.py
├─ imports: database (Base)
├─ uses: SQLAlchemy Column, relationship
└─ provides: ORM models

database.py
├─ imports: config (settings)
├─ uses: SQLAlchemy, create_engine, sessionmaker
└─ provides: engine, Base, sessions

config.py
├─ imports: os
├─ uses: environment variables
└─ provides: global settings
```

## 🎯 Feature Modules

Currently, all code is organized by **technical layer** (routes, services, models).

To evolve to **feature-based** structure (like your reference), you could organize as:

```
app/
├── users/
│   ├── router.py
│   ├── schemas.py
│   ├── models.py (or reference from models/)
│   ├── service.py
│   └── dependencies.py
│
├── news/
│   ├── router.py
│   ├── schemas.py
│   ├── models.py (or reference from models/)
│   ├── service.py
│   └── dependencies.py
│
├── prices/
│   ├── router.py
│   ├── schemas.py
│   └── dependencies.py
│
├── core/
│   ├── config.py
│   ├── security.py
│   └── dependencies.py
│
├── db/
│   ├── database.py
│   └── models.py
│
└── main.py
```

This is a future enhancement but not necessary for current functionality.

## ✅ Quick Navigation

- **Need to add new endpoint?** → Edit `app/api/routes_*.py` or create new routes file
- **Need to add business logic?** → Add method to service class in `app/services/__init__.py`
- **Need to add data field?** → Update model in `app/models/__init__.py`, create Alembic migration
- **Need to change config?** → Edit `app/core/config.py`
- **Need to understand request flow?** → See "Data Flow Examples" section
- **Need authentication?** → Use `Depends(get_current_user)` from `app/api/security.py`
- **Need database access?** → Use `Depends(get_db_session)` from `app/db/database.py`

---

**Last Updated**: November 13, 2025  
**Architecture**: Layered (Technical)  
**Status**: ✅ Production Ready
