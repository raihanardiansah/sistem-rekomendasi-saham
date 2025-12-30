"""
Konfigurasi Aplikasi Sistem Rekomendasi Saham
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database Configuration
# Untuk local: gunakan SQLite
# Untuk production: gunakan PostgreSQL dari environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Production (PostgreSQL)
    # Railway/Heroku format: postgres:// -> postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    # Local development (SQLite)
    DATABASE_PATH = BASE_DIR / "app" / "data" / "stocks.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Data Files
DATA_DIR = BASE_DIR / "app" / "data"
STOCKS_LIST_PATH = DATA_DIR / "stocks_list.csv"

# News API (optional - sebagai alternatif scraping)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Scraper Configuration
SCRAPER_CONFIG = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "timeout": 30,
    "max_retries": 3,
    "delay_between_requests": 2,  # detik
}

# News Sources
NEWS_SOURCES = {
    "kontan": {
        "name": "Kontan",
        "base_url": "https://investasi.kontan.co.id",
        "search_url": "https://www.kontan.co.id/search/?search=",
    },
    "cnbc": {
        "name": "CNBC Indonesia", 
        "base_url": "https://www.cnbcindonesia.com",
        "search_url": "https://www.cnbcindonesia.com/search?query=",
    },
}

# NLP Configuration
NLP_CONFIG = {
    "min_word_length": 3,
    "max_features_tfidf": 5000,
    "ngram_range": (1, 2),
}

# Recommendation Configuration
RECOMMENDATION_CONFIG = {
    "top_n_recommendations": 10,
    "min_news_count": 3,  # Minimal berita untuk analisis
    "sentiment_weight": 0.4,
    "frequency_weight": 0.2,
    "recency_weight": 0.2,
    "similarity_weight": 0.2,
}

# Streamlit UI Configuration
UI_CONFIG = {
    "page_title": "Sistem Rekomendasi Saham",
    "page_icon": "📈",
    "layout": "wide",
}
