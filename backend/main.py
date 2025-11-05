import json
import sentry_sdk
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.middleware.cors import CORSMiddleware
import itertools
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, sessionmaker
from typing import List, Optional
import requests
from fastapi import APIRouter, HTTPException, Query, Depends, status, FastAPI
import os
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from pydantic import BaseModel, Field, AnyHttpUrl
from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

import os
from openai import OpenAI

from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

Base = declarative_base()
engine = create_engine("sqlite:///news_database.db", echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

user_news_association_table = Table(
    "user_news_upvotes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column(
        "news_articles_id", Integer, ForeignKey("news_articles.id"), primary_key=True
    ),
)

# from pydantic import BaseModel


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    upvoted_news = relationship(
        "NewsArticle",
        secondary=user_news_association_table,
        back_populates="upvoted_by_users",
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    time = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    upvoted_by_users = relationship(
        "User", secondary=user_news_association_table, back_populates="upvoted_news"
)
Base.metadata.create_all(engine)

app = FastAPI()
scheduler = BackgroundScheduler()

app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")
_id_counter = itertools.count(start=1000000)
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "xxx"))

sentry_sdk.init(
    dsn="https://4001ffe917ccb261aa0e0c34026dc343@o4505702629834752.ingest.us.sentry.io/4507694792704000",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

class UserAuthSchema(BaseModel):
    username: str
    password: str

class PromptRequest(BaseModel):
    prompt: str

class NewsSummaryRequestSchema(BaseModel):
    content: str


def get_db_session():
    db_session = SessionLocal(bind=engine)
    try:
        yield db_session
    finally:
        db_session.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        return db.query(User).filter(User.username == username).first()
    except:
        return None

class NewsManager:
    def __init__(self, db: Session):
        self.db = db

    def add_article_to_db(self, news_data:dict):
        self.db.add(
            NewsArticle(
                url=news_data["url"],
                title=news_data["title"],
                time=news_data["time"],
                content=" ".join(news_data["content"]),  
                summary=news_data["summary"],
                reason=news_data["reason"],
            )
        )
        self.db.commit()

    def fetch_news_list(self, search_term:str, is_initial=False) -> List[dict]:
        all_news_data = []
        if is_initial:
            pages_data = []
            for p in range(1, 10):
                page_params_detail = {
                    "page": p,
                    "id": f"search:{quote(search_term)}",
                    "channelId": 2,
                    "type": "searchword",
                }
                response = requests.get("https://udn.com/api/more", params=page_params_detail)
                pages_data.append(response.json()["lists"])

            for l in pages_data:
                all_news_data.append(l)
        else:
            params = {
                "page": 1,
                "id": f"search:{quote(search_term)}",
                "channelId": 2,
                "type": "searchword",
            }
            response = requests.get("https://udn.com/api/more", params=params)

            all_news_data = response.json()["lists"]
        return all_news_data

    def fetch_and_process_news(self, is_initial=False):
        news_data = self.fetch_news_list("價格", is_initial=is_initial)
        for news in news_data:
            title = news["title"]
            prompt_message = [
                {
                    "role": "system",
                    "content": "你是一個關聯度評估機器人，請評估新聞標題是否與「民生用品的價格變化」相關，並給予'high'、'medium'、'low'評價。(僅需回答'high'、'medium'、'low'三個詞之一)",
                },
                {"role": "user", "content": f"{title}"},
            ]
            ai = OpenAI(api_key="xxx").chat.completions.create(
                model="gpt-3.5-turbo",
                messages=prompt_message,
            )
            relevance = ai.choices[0].message.content
            if relevance == "high":
                response = requests.get(news["titleLink"])
                soup = BeautifulSoup(response.text, "html.parser")
                # 標題
                title = soup.find("h1", class_="article-content__title").text
                time = soup.find("time", class_="article-content__time").text
                # 定位到包含文章内容的 <section>
                content_section = soup.find("section", class_="article-content__editor")

                paragraphs = [
                    p.text
                    for p in content_section.find_all("p")
                    if p.text.strip() != "" and "▪" not in p.text
                ]
                detailed_news = {
                    "url": news["titleLink"],
                    "title": title,
                    "time": time,
                    "content": paragraphs,
                }
                m = [
                    {
                        "role": "system",
                        "content": "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})",
                    },
                    {"role": "user", "content": " ".join(detailed_news["content"])},
                ]

                completion = OpenAI(api_key="xxx").chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=prompt_message,
                )
                result = completion
    
    def get_all_news(self):
        return self.db.query(NewsArticle).order_by(NewsArticle.time.desc()).all()

    def get_user_news(self, user_id: int):
        articles = self.get_all_news()
        upvote_manager = UpvoteManager(self.db)
        result = []
        for article in articles:
            upvotes, is_upvoted = upvote_manager.get_article_upvote_details(article.id, user_id)
            result.append({**article.__dict__, "upvotes": upvotes, "is_upvoted": is_upvoted})
        return result
    
    def news_exists(self, article_id: int):
        return self.db.query(NewsArticle).filter_by(id=article_id).first() is not None
    

    
class UserManager:
    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    def create_user(self, username: str, password: str) -> User:
        hashed_password = pwd_context.hash(password)
        user = User(username=username, hashed_password=hashed_password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    


class UpvoteManager:
    def __init__(self, db: Session):
        self.db = db

    def toggle_upvote(self, article_id: int, user_id: int) -> str:
        existing_upvote = self.db.execute(
            select(user_news_association_table).where(
                user_news_association_table.c.news_articles_id == article_id,
                user_news_association_table.c.user_id == user_id
            )
        ).scalar()
        if existing_upvote:
            self.db.execute(
                delete(user_news_association_table).where(
                    user_news_association_table.c.news_articles_id == article_id,
                    user_news_association_table.c.user_id == user_id
                )
            )
            self.db.commit()
            return "Upvote removed"
        else:
            self.db.execute(
                insert(user_news_association_table).values(
                    news_articles_id=article_id, user_id=user_id
                )
            )
            self.db.commit()
            return "Article upvoted"

    def get_article_upvote_details(self, article_id: int, user_id: Optional[int]):
        count = self.db.query(user_news_association_table).filter_by(news_articles_id=article_id).count()
        voted = False
        if user_id:
            voted = self.db.query(user_news_association_table).filter_by(
                news_articles_id=article_id, user_id=user_id
            ).first() is not None
        return count, voted



@app.post("/api/v1/users/register")
def register_user(user: UserAuthSchema, db: Session = Depends(get_db_session)):
    manager = UserManager(db)
    return manager.create_user(user.username, user.password)


@app.post("/api/v1/users/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db_session)):
    manager = UserManager(db)
    user = manager.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=timedelta(minutes=30)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/v1/news/news")
async def get_news(db: Session = Depends(get_db_session)):
    manager = NewsManager(db)
    articles = manager.get_all_news()
    return articles  # 或加上 upvote 資訊也在 manager 裡處理

@app.get("/api/v1/news/user_news")
async def get_user_news(user: User = Depends(get_current_user), db: Session = Depends(get_db_session)):
    manager = NewsManager(db)
    return manager.get_user_news(user.id)

@app.post("/api/v1/news/{id}/upvote")
def upvote_article(id: int, db: Session = Depends(get_db_session), user: User = Depends(get_current_user)):
    upvote_mgr = UpvoteManager(db)
    return {"message": upvote_mgr.toggle_upvote(id, user.id)}

@app.post("/api/v1/news/{article_id}/upvote")
async def toggle_upvote(article_id: int, db: Session = Depends(get_db_session), user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    upvote_manager = UpvoteManager(db)
    message = upvote_manager.toggle_upvote(article_id, user.id)
    return {"message": message}



@app.get("/api/v1/users/me")
async def read_users_me(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"username": user.username}

@app.post("/api/v1/news/search_news")
async def search_news(request: PromptRequest, db: Session = Depends(get_db_session)):
    news_manager = NewsManager(db)
    return await news_manager.fetch_and_process_news(request.prompt, _id_counter)

@app.post("/api/v1/news/news_summary")
async def news_summary(payload: NewsSummaryRequestSchema, user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    news_manager = NewsManager(SessionLocal())
    return await news_manager.generate_summary(payload.content)


@app.get("/api/v1/prices/necessities-price")
async def get_necessities_prices(category=Query(None), commodity=Query(None)):
    response = requests.get(
        "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice",
        params={"CategoryName": category, "Name": commodity},
    )
    return response.json()



@app.on_event("startup")
def start_background_jobs():
    db = SessionLocal()
    manager = NewsManager(db)
    if db.query(NewsArticle).count() == 0:
        manager.fetch_and_process_news(is_initial=True)
    db.close()
    scheduler.add_job(lambda: NewsManager(SessionLocal()).fetch_and_process_news(), "interval", minutes=100)
    scheduler.start()

@app.on_event("shutdown")
def shutdown_background_jobs():
    scheduler.shutdown()





# def generate_summary(content):
#     m = [
#         {
#             "role": "system",
#             "content": "你是一個新聞摘要生成機器人，請統整新聞中提及的影響及主要原因 (影響、原因各50個字，請以json格式回答 {'影響': '...', '原因': '...'})",
#         },
#         {"role": "user", "content": f"{content}"},
#     ]
#
#     completion = OpenAI(api_key="xxx").chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=m,
#     )
#     return completion.choices[0].message.content

#
# def extract_search_keywords(content):
#     m = [
#         {
#             "role": "system",
#             "content": "你是一個關鍵字提取機器人，用戶將會輸入一段文字，表示其希望看見的新聞內容，請提取出用戶希望看見的關鍵字，請截取最重要的關鍵字即可，避免出現「新聞」、「資訊」等混淆搜尋引擎的字詞。(僅須回答關鍵字，若有多個關鍵字，請以空格分隔)",
#         },
#         {"role": "user", "content": f"{content}"},
#     ]
#
#     completion = OpenAI(api_key="xxx").chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=m,
#     )
#     return completion.choices[0].message.content
