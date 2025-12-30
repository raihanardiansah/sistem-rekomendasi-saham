"""
News Scraper Module
"""

from app.scraper.base_scraper import BaseScraper
from app.scraper.kontan_scraper import KontanScraper
from app.scraper.detik_scraper import DetikScraper
from app.scraper.newsapi_scraper import NewsAPIScraper, get_newsapi_scraper
from app.scraper.news_manager import NewsManager

__all__ = ["BaseScraper", "KontanScraper", "DetikScraper", "NewsAPIScraper", "get_newsapi_scraper", "NewsManager"]
