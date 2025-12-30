"""
NewsAPI Scraper - Alternatif untuk scraping berita
Menggunakan NewsAPI.org (gratis 100 request/hari)

Untuk mendapatkan API key:
1. Daftar di https://newsapi.org/
2. Copy API key
3. Set di environment variable: NEWS_API_KEY
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import requests
import logging

from app.scraper.base_scraper import BaseScraper
from app.config import NEWS_API_KEY

logger = logging.getLogger(__name__)


class NewsAPIScraper(BaseScraper):
    """Scraper menggunakan NewsAPI.org"""
    
    def __init__(self):
        super().__init__()
        self.api_key = NEWS_API_KEY
        self.api_url = "https://newsapi.org/v2/everything"
    
    @property
    def source_name(self) -> str:
        return "NewsAPI"
    
    @property
    def base_url(self) -> str:
        return "https://newsapi.org"
    
    def is_available(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)
    
    def search_news(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """
        Cari berita menggunakan NewsAPI
        
        Args:
            keyword: Kata kunci pencarian
            max_results: Maksimal hasil
            
        Returns:
            List of news articles
        """
        if not self.is_available():
            logger.warning("NewsAPI key not configured")
            return []
        
        results = []
        
        # Search parameters
        params = {
            "q": f"{keyword} saham OR {keyword} stock",
            "language": "id",  # Indonesian
            "sortBy": "publishedAt",
            "pageSize": min(max_results, 100),
            "apiKey": self.api_key
        }
        
        # Add date range (last 30 days - free tier limit)
        from_date = (datetime.utcnow() - timedelta(days=29)).strftime("%Y-%m-%d")
        params["from"] = from_date
        
        logger.info(f"[NewsAPI] Searching for: {keyword}")
        
        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") != "ok":
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            
            articles = data.get("articles", [])
            
            for article in articles[:max_results]:
                # Parse date
                published_date = None
                if article.get("publishedAt"):
                    try:
                        published_date = datetime.fromisoformat(
                            article["publishedAt"].replace("Z", "+00:00")
                        )
                    except:
                        pass
                
                results.append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "summary": article.get("description", ""),
                    "published_date": published_date,
                    "source": f"NewsAPI - {article.get('source', {}).get('name', 'Unknown')}"
                })
            
            logger.info(f"[NewsAPI] Found {len(results)} articles for '{keyword}'")
            
        except requests.RequestException as e:
            logger.error(f"NewsAPI request error: {e}")
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
        
        return results
    
    def get_article_content(self, url: str) -> Optional[Dict]:
        """
        NewsAPI free tier tidak menyediakan full content
        Jadi kita fetch dari URL langsung
        """
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        try:
            # Get title
            title_tag = soup.find("h1")
            title = self.clean_text(title_tag.get_text()) if title_tag else ""
            
            # Get content from article or main tag
            content_tag = soup.find("article") or soup.find("main") or soup.find("div", class_="content")
            content = ""
            
            if content_tag:
                paragraphs = content_tag.find_all("p")
                content_parts = [self.clean_text(p.get_text()) for p in paragraphs]
                content = "\n\n".join([p for p in content_parts if p and len(p) > 50])
            
            if not content:
                return None
            
            return {
                "title": title,
                "content": content,
                "published_date": None,
                "url": url,
                "source": self.source_name
            }
            
        except Exception as e:
            logger.error(f"Error getting article content: {e}")
            return None


def get_newsapi_scraper() -> Optional[NewsAPIScraper]:
    """Get NewsAPI scraper if API key is available"""
    scraper = NewsAPIScraper()
    if scraper.is_available():
        return scraper
    return None
