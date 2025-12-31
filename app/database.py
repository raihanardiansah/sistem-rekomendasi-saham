"""
Database Module - SQLite/PostgreSQL dengan SQLAlchemy
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool, NullPool
from datetime import datetime
import os
from pathlib import Path

Base = declarative_base()

# Global variables untuk lazy initialization
_engine = None
_SessionLocal = None


def get_database_url():
    """Get database URL dari berbagai sumber"""
    database_url = None
    
    # 1. Coba dari Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
            database_url = st.secrets["DATABASE_URL"]
    except:
        pass
    
    # 2. Fallback ke environment variable
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
    
    # 3. Fallback ke SQLite lokal
    if not database_url:
        base_dir = Path(__file__).resolve().parent.parent
        data_dir = base_dir / "app" / "data"
        os.makedirs(data_dir, exist_ok=True)
        database_url = f"sqlite:///{data_dir / 'stocks.db'}"
    
    # Fix untuk Heroku/Railway format
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return database_url


def get_engine():
    """Get atau create database engine (lazy initialization)"""
    global _engine
    
    if _engine is None:
        database_url = get_database_url()
        
        if "sqlite" in database_url:
            # SQLite - untuk local development
            _engine = create_engine(
                database_url, 
                echo=False,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
        else:
            # PostgreSQL - untuk production dengan NullPool untuk serverless
            _engine = create_engine(
                database_url, 
                echo=False, 
                pool_pre_ping=True,
                poolclass=NullPool  # Lebih baik untuk serverless seperti Streamlit Cloud
            )
    
    return _engine


def get_session_local():
    """Get SessionLocal class"""
    global _SessionLocal
    
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    
    return _SessionLocal


class Stock(Base):
    """Model untuk data saham"""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    kode = Column(String(10), unique=True, index=True, nullable=False)
    nama = Column(String(255), nullable=False)
    sektor = Column(String(100))
    sub_sektor = Column(String(100))
    index_member = Column(String(255))  # IHSG, LQ45, dll (comma separated)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    news = relationship("News", back_populates="stock")
    
    def __repr__(self):
        return f"<Stock(kode='{self.kode}', nama='{self.nama}')>"


class News(Base):
    """Model untuk berita saham"""
    __tablename__ = "news"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=True)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    summary = Column(Text)
    url = Column(String(500), unique=True)
    source = Column(String(100))  # kontan, cnbc, dll
    published_date = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # NLP Results
    sentiment_score = Column(Float)  # -1 to 1
    sentiment_label = Column(String(20))  # positif, negatif, netral
    keywords = Column(Text)  # JSON array of keywords
    
    # Relationship
    stock = relationship("Stock", back_populates="news")
    
    def __repr__(self):
        return f"<News(title='{self.title[:50]}...')>"


class StockAnalysis(Base):
    """Model untuk hasil analisis saham"""
    __tablename__ = "stock_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    analysis_date = Column(DateTime, default=datetime.utcnow)
    
    # Sentiment Summary
    avg_sentiment = Column(Float)
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    total_news = Column(Integer, default=0)
    
    # Recommendation Score
    recommendation_score = Column(Float)
    recommendation_label = Column(String(50))  # Strong Buy, Buy, Hold, Sell, Strong Sell
    
    # TF-IDF Vector (stored as JSON string)
    tfidf_vector = Column(Text)
    
    def __repr__(self):
        return f"<StockAnalysis(stock_id={self.stock_id}, score={self.recommendation_score})>"


def init_db():
    """Inisialisasi database - buat semua tabel"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("✅ Database berhasil diinisialisasi!")


def get_db():
    """Get database session"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    """Get database session (non-generator)"""
    SessionLocal = get_session_local()
    return SessionLocal()


if __name__ == "__main__":
    init_db()
