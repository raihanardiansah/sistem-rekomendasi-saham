"""
Base Scraper - Abstract class untuk semua news scraper
"""

import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import time
import logging
from datetime import datetime

from app.config import SCRAPER_CONFIG

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class untuk semua news scraper"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": SCRAPER_CONFIG["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        self.timeout = SCRAPER_CONFIG["timeout"]
        self.max_retries = SCRAPER_CONFIG["max_retries"]
        self.delay = SCRAPER_CONFIG["delay_between_requests"]
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Nama sumber berita"""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL sumber berita"""
        pass
    
    @abstractmethod
    def search_news(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """
        Cari berita berdasarkan keyword
        
        Args:
            keyword: Kata kunci pencarian (kode saham atau nama)
            max_results: Maksimal hasil yang diambil
            
        Returns:
            List of dict dengan keys: title, url, summary, published_date
        """
        pass
    
    @abstractmethod
    def get_article_content(self, url: str) -> Optional[Dict]:
        """
        Ambil konten lengkap artikel
        
        Args:
            url: URL artikel
            
        Returns:
            Dict dengan keys: title, content, published_date
        """
        pass
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch halaman web dan return BeautifulSoup object
        
        Args:
            url: URL halaman
            
        Returns:
            BeautifulSoup object atau None jika gagal
        """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.content, "lxml")
                
                # Delay untuk menghindari rate limiting
                time.sleep(self.delay)
                
                return soup
                
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.delay * 2)
                    
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None
    
    def clean_text(self, text: str) -> str:
        """Bersihkan text dari whitespace berlebih"""
        if not text:
            return ""
        # Remove extra whitespace
        text = " ".join(text.split())
        return text.strip()
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse string tanggal ke datetime object
        Override di subclass jika format berbeda
        """
        date_formats = [
            "%d %B %Y %H:%M",
            "%d %b %Y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%d %B %Y",
            "%d %b %Y",
        ]
        
        # Mapping bulan Indonesia ke English
        bulan_mapping = {
            "Januari": "January", "Februari": "February", "Maret": "March",
            "April": "April", "Mei": "May", "Juni": "June",
            "Juli": "July", "Agustus": "August", "September": "September",
            "Oktober": "October", "November": "November", "Desember": "December",
            "Jan": "Jan", "Feb": "Feb", "Mar": "Mar", "Apr": "Apr",
            "Jun": "Jun", "Jul": "Jul", "Agu": "Aug", "Sep": "Sep",
            "Okt": "Oct", "Nov": "Nov", "Des": "Dec"
        }
        
        # Replace bulan Indonesia
        for indo, eng in bulan_mapping.items():
            date_str = date_str.replace(indo, eng)
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
                
        return None
