"""
Detik Finance News Scraper
Scraper untuk mengambil berita dari finance.detik.com
"""

from typing import List, Dict, Optional
from datetime import datetime
import re
import logging

from app.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class DetikScraper(BaseScraper):
    """Scraper untuk Detik Finance"""
    
    @property
    def source_name(self) -> str:
        return "Detik Finance"
    
    @property
    def base_url(self) -> str:
        return "https://finance.detik.com"
    
    def search_news(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """
        Cari berita di Detik Finance berdasarkan keyword
        
        Args:
            keyword: Kode saham atau kata kunci
            max_results: Maksimal hasil
            
        Returns:
            List of news articles
        """
        results = []
        search_url = f"https://www.detik.com/search/searchall?query={keyword}&siteid=3"
        
        logger.info(f"[Detik] Searching for: {keyword}")
        
        soup = self.fetch_page(search_url)
        if not soup:
            return results
        
        # Find article elements
        articles = soup.find_all("article")
        
        for article in articles[:max_results]:
            try:
                # Find title link within article
                title_div = article.find("h2", class_="title") or article.find("h3", class_="media__title")
                if not title_div:
                    title_div = article.find("a")
                
                if not title_div:
                    continue
                
                # Get link
                link_tag = title_div.find("a") if title_div.name != "a" else title_div
                if not link_tag:
                    link_tag = article.find("a")
                
                if not link_tag:
                    continue
                    
                url = link_tag.get("href", "")
                if not url:
                    continue
                
                # Get title
                title = link_tag.get_text(strip=True)
                if not title or len(title) < 15:
                    continue
                
                # Extract date
                date_tag = article.find("span", class_="date") or article.find("time") or article.find("span", class_="media__date")
                published_date = None
                if date_tag:
                    date_text = date_tag.get_text(strip=True)
                    published_date = self.parse_date(date_text)
                
                # Extract summary
                summary_tag = article.find("p") or article.find("span", class_="media__desc")
                summary = ""
                if summary_tag:
                    summary = self.clean_text(summary_tag.get_text())
                
                results.append({
                    "title": self.clean_text(title),
                    "url": url,
                    "summary": summary,
                    "published_date": published_date,
                    "source": self.source_name
                })
                
            except Exception as e:
                logger.warning(f"Error parsing article: {e}")
                continue
        
        logger.info(f"[Detik] Found {len(results)} articles for '{keyword}'")
        return results
    
    def get_article_content(self, url: str) -> Optional[Dict]:
        """
        Ambil konten lengkap artikel dari Detik
        
        Args:
            url: URL artikel
            
        Returns:
            Dict dengan title, content, published_date
        """
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        try:
            # Get title
            title_tag = soup.find("h1", class_="detail__title") or soup.find("h1")
            title = self.clean_text(title_tag.get_text()) if title_tag else ""
            
            # Get published date
            date_tag = soup.find("div", class_="detail__date") or soup.find("time")
            published_date = None
            if date_tag:
                date_text = date_tag.get_text(strip=True)
                # Format: "Senin, 30 Des 2024 10:30 WIB"
                date_match = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", date_text)
                if date_match:
                    published_date = self.parse_date(date_match.group(1))
            
            # Get content
            content_div = soup.find("div", class_="detail__body-text") or soup.find("article")
            content = ""
            
            if content_div:
                paragraphs = content_div.find_all("p")
                content_parts = []
                
                for p in paragraphs:
                    text = self.clean_text(p.get_text())
                    if text and not self._is_noise(text):
                        content_parts.append(text)
                
                content = "\n\n".join(content_parts)
            
            if not content:
                return None
            
            return {
                "title": title,
                "content": content,
                "published_date": published_date,
                "url": url,
                "source": self.source_name
            }
            
        except Exception as e:
            logger.error(f"Error getting article content from {url}: {e}")
            return None
    
    def _is_noise(self, text: str) -> bool:
        """Check if text is noise"""
        noise_patterns = [
            "baca juga",
            "baca selengkapnya",
            "artikel terkait",
            "lihat juga",
            "advertisement",
            "iklan",
            "simak video",
            "tonton video",
            "(erd/",
            "(kil/",
            "(das/",
        ]
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in noise_patterns)
