"""
News Manager - Mengelola pengambilan dan penyimpanan berita
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from tqdm import tqdm

from app.database import get_session, Stock, News
from app.scraper.kontan_scraper import KontanScraper
from app.scraper.detik_scraper import DetikScraper
from app.scraper.newsapi_scraper import get_newsapi_scraper

logger = logging.getLogger(__name__)


class NewsManager:
    """Manager untuk mengambil dan menyimpan berita saham"""
    
    def __init__(self):
        self.scrapers = [
            KontanScraper(),
            DetikScraper(),
        ]
        
        # Tambahkan NewsAPI jika tersedia
        newsapi = get_newsapi_scraper()
        if newsapi:
            self.scrapers.append(newsapi)
            logger.info("NewsAPI scraper enabled")
        
        self.session = get_session()
    
    def update_news_for_stock(self, stock_code: str, max_per_source: int = 10) -> Dict:
        """
        Update berita untuk satu saham
        
        Args:
            stock_code: Kode saham (e.g., "BBCA")
            max_per_source: Maksimal berita per sumber
            
        Returns:
            Dict dengan statistik update
        """
        stats = {
            "stock_code": stock_code,
            "total_found": 0,
            "new_saved": 0,
            "duplicates": 0,
            "errors": 0,
            "sources": {}
        }
        
        # Get stock from database
        stock = self.session.query(Stock).filter(Stock.kode == stock_code.upper()).first()
        
        if not stock:
            logger.warning(f"Stock {stock_code} not found in database")
            return stats
        
        logger.info(f"Updating news for {stock_code} - {stock.nama}")
        
        # Search keywords: stock code and company name
        search_keywords = [stock_code.upper()]
        
        # Add company name variations
        if stock.nama:
            # Get first 2-3 words of company name
            name_parts = stock.nama.split()[:3]
            search_keywords.append(" ".join(name_parts))
        
        for scraper in self.scrapers:
            source_stats = {"found": 0, "saved": 0}
            
            for keyword in search_keywords:
                try:
                    # Search news
                    articles = scraper.search_news(keyword, max_results=max_per_source)
                    source_stats["found"] += len(articles)
                    stats["total_found"] += len(articles)
                    
                    for article in articles:
                        # Check if article already exists
                        existing = self.session.query(News).filter(
                            News.url == article["url"]
                        ).first()
                        
                        if existing:
                            stats["duplicates"] += 1
                            continue
                        
                        # Get full content
                        full_article = scraper.get_article_content(article["url"])
                        
                        if full_article:
                            # Save to database
                            news = News(
                                stock_id=stock.id,
                                title=full_article["title"],
                                content=full_article["content"],
                                summary=article.get("summary", ""),
                                url=article["url"],
                                source=scraper.source_name,
                                published_date=full_article.get("published_date") or article.get("published_date"),
                                scraped_at=datetime.utcnow()
                            )
                            
                            self.session.add(news)
                            source_stats["saved"] += 1
                            stats["new_saved"] += 1
                            
                except Exception as e:
                    logger.error(f"Error scraping {scraper.source_name} for {keyword}: {e}")
                    stats["errors"] += 1
            
            stats["sources"][scraper.source_name] = source_stats
        
        # Commit all changes
        try:
            self.session.commit()
        except Exception as e:
            logger.error(f"Error committing to database: {e}")
            self.session.rollback()
            stats["errors"] += 1
        
        return stats
    
    def update_news_for_multiple_stocks(
        self, 
        stock_codes: List[str], 
        max_per_source: int = 5,
        progress_callback=None
    ) -> List[Dict]:
        """
        Update berita untuk beberapa saham
        
        Args:
            stock_codes: List kode saham
            max_per_source: Maksimal berita per sumber per saham
            progress_callback: Callback function for progress updates
            
        Returns:
            List of stats per stock
        """
        all_stats = []
        
        for i, code in enumerate(tqdm(stock_codes, desc="Updating news")):
            stats = self.update_news_for_stock(code, max_per_source)
            all_stats.append(stats)
            
            if progress_callback:
                progress_callback(i + 1, len(stock_codes), code)
        
        return all_stats
    
    def get_news_for_stock(
        self, 
        stock_code: str, 
        limit: int = 50,
        days_back: int = 30
    ) -> List[News]:
        """
        Ambil berita tersimpan untuk suatu saham
        
        Args:
            stock_code: Kode saham
            limit: Maksimal berita yang diambil
            days_back: Ambil berita dalam N hari terakhir
            
        Returns:
            List of News objects
        """
        from datetime import timedelta
        
        stock = self.session.query(Stock).filter(Stock.kode == stock_code.upper()).first()
        
        if not stock:
            return []
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        news = self.session.query(News).filter(
            News.stock_id == stock.id,
            News.scraped_at >= cutoff_date
        ).order_by(News.published_date.desc()).limit(limit).all()
        
        return news
    
    def get_all_unanalyzed_news(self) -> List[News]:
        """Ambil semua berita yang belum dianalisis sentimennya"""
        return self.session.query(News).filter(
            News.sentiment_score.is_(None)
        ).all()
    
    def get_news_stats(self) -> Dict:
        """Dapatkan statistik berita di database"""
        total_news = self.session.query(News).count()
        analyzed_news = self.session.query(News).filter(
            News.sentiment_score.isnot(None)
        ).count()
        
        # Group by source
        from sqlalchemy import func
        source_stats = self.session.query(
            News.source, 
            func.count(News.id)
        ).group_by(News.source).all()
        
        # Group by stock
        stock_stats = self.session.query(
            Stock.kode,
            func.count(News.id)
        ).join(News).group_by(Stock.kode).order_by(func.count(News.id).desc()).limit(10).all()
        
        return {
            "total_news": total_news,
            "analyzed_news": analyzed_news,
            "unanalyzed_news": total_news - analyzed_news,
            "by_source": dict(source_stats),
            "top_stocks": dict(stock_stats)
        }
    
    def close(self):
        """Close database session"""
        self.session.close()


# Utility functions
def update_single_stock(stock_code: str) -> Dict:
    """Update berita untuk satu saham"""
    manager = NewsManager()
    try:
        return manager.update_news_for_stock(stock_code)
    finally:
        manager.close()


def update_multiple_stocks(stock_codes: List[str]) -> List[Dict]:
    """Update berita untuk beberapa saham"""
    manager = NewsManager()
    try:
        return manager.update_news_for_multiple_stocks(stock_codes)
    finally:
        manager.close()


if __name__ == "__main__":
    # Test scraper
    manager = NewsManager()
    
    # Update news for BBCA
    stats = manager.update_news_for_stock("BBCA", max_per_source=3)
    print(f"\nUpdate Stats: {stats}")
    
    # Get news stats
    print(f"\nNews Stats: {manager.get_news_stats()}")
    
    manager.close()
