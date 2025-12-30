"""
Kontan News Scraper
Scraper untuk mengambil berita dari Kontan.co.id
"""

from typing import List, Dict, Optional
from datetime import datetime
import re
import logging

from app.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class KontanScraper(BaseScraper):
    """Scraper untuk Kontan.co.id"""
    
    @property
    def source_name(self) -> str:
        return "Kontan"
    
    @property
    def base_url(self) -> str:
        return "https://www.kontan.co.id"
    
    def search_news(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """
        Cari berita di Kontan berdasarkan keyword
        
        Args:
            keyword: Kode saham atau kata kunci (e.g., "BBCA", "Bank BCA")
            max_results: Maksimal hasil
            
        Returns:
            List of news articles
        """
        results = []
        search_url = f"{self.base_url}/search/?search={keyword}"
        
        logger.info(f"[Kontan] Searching for: {keyword}")
        
        soup = self.fetch_page(search_url)
        if not soup:
            return results
        
        # Find all news links with /news/ or /investasi/ in URL
        all_links = soup.find_all("a", href=True)
        seen_urls = set()
        
        for link in all_links:
            if len(results) >= max_results:
                break
                
            href = link.get("href", "")
            
            # Filter only news URLs
            if "/news/" not in href and "/investasi/" not in href:
                continue
            
            # Skip duplicate URLs
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            # Get title
            title = link.get_text(strip=True)
            if not title or len(title) < 20:  # Skip short/empty titles
                continue
            
            # Build full URL
            url = href
            if url.startswith("//"):
                url = "https:" + url
            elif not url.startswith("http"):
                url = self.base_url + url
            
            # Try to get date from parent/sibling elements
            published_date = None
            parent = link.find_parent()
            if parent:
                date_tag = parent.find("span", class_="date") or parent.find("time")
                if date_tag:
                    published_date = self.parse_date(date_tag.get_text(strip=True))
            
            results.append({
                "title": self.clean_text(title),
                "url": url,
                "summary": "",
                "published_date": published_date,
                "source": self.source_name
            })
        
        logger.info(f"[Kontan] Found {len(results)} articles for '{keyword}'")
        return results
    
    def get_article_content(self, url: str) -> Optional[Dict]:
        """
        Ambil konten lengkap artikel dari Kontan
        
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
            title_tag = soup.find("h1", class_="detail-title") or soup.find("h1")
            title = self.clean_text(title_tag.get_text()) if title_tag else ""
            
            # Get published date
            date_tag = soup.find("span", class_="detail-date") or soup.find("time")
            published_date = None
            if date_tag:
                date_text = date_tag.get_text(strip=True)
                # Extract date from text like "Senin, 30 Desember 2024 / 10:30 WIB"
                date_match = re.search(r"(\d{1,2}\s+\w+\s+\d{4})", date_text)
                if date_match:
                    published_date = self.parse_date(date_match.group(1))
            
            # Get content
            content_div = soup.find("div", class_="detail-text") or soup.find("article")
            content = ""
            
            if content_div:
                # Get all paragraphs
                paragraphs = content_div.find_all("p")
                content_parts = []
                
                for p in paragraphs:
                    text = self.clean_text(p.get_text())
                    # Filter out ads, related articles, etc.
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
        """Check if text is noise (ads, related articles, etc.)"""
        noise_patterns = [
            "baca juga",
            "baca selengkapnya",
            "artikel terkait",
            "lihat juga",
            "advertisement",
            "iklan",
            "sponsored",
            "share:",
            "bagikan:",
        ]
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in noise_patterns)
