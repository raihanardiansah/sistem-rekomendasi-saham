"""
Text Preprocessor - Pembersihan dan normalisasi teks Bahasa Indonesia
"""

import re
import string
from typing import List, Optional
import logging

# PySastrawi untuk stemming Bahasa Indonesia
try:
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
    SASTRAWI_AVAILABLE = True
except ImportError:
    SASTRAWI_AVAILABLE = False

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """Preprocessor untuk teks Bahasa Indonesia"""
    
    def __init__(self, use_stemming: bool = True, remove_stopwords: bool = True):
        """
        Initialize preprocessor
        
        Args:
            use_stemming: Gunakan stemming Bahasa Indonesia
            remove_stopwords: Hapus stopwords Bahasa Indonesia
        """
        self.use_stemming = use_stemming and SASTRAWI_AVAILABLE
        self.remove_stopwords = remove_stopwords
        
        # Initialize Sastrawi stemmer
        if self.use_stemming and SASTRAWI_AVAILABLE:
            factory = StemmerFactory()
            self.stemmer = factory.createStemmer()
        else:
            self.stemmer = None
            if use_stemming and not SASTRAWI_AVAILABLE:
                logger.warning("Sastrawi not available. Stemming disabled.")
        
        # Initialize stopword remover
        if remove_stopwords and SASTRAWI_AVAILABLE:
            stopword_factory = StopWordRemoverFactory()
            self.stopwords = set(stopword_factory.getStopWords())
            # Add custom stopwords for news
            self.stopwords.update(self._get_custom_stopwords())
        else:
            self.stopwords = self._get_custom_stopwords()
    
    def _get_custom_stopwords(self) -> set:
        """Stopwords tambahan khusus untuk berita saham"""
        return {
            # Common news words
            "kompas", "kontan", "detik", "cnbc", "indonesia", "jakarta",
            "wartawan", "editor", "redaksi", "foto", "gambar", "video",
            "baca", "juga", "lihat", "klik", "share", "bagikan",
            
            # Time expressions
            "kemarin", "besok", "lusa", "senin", "selasa", "rabu", "kamis",
            "jumat", "sabtu", "minggu", "januari", "februari", "maret",
            "april", "mei", "juni", "juli", "agustus", "september",
            "oktober", "november", "desember", "wib", "wita", "wit",
            
            # Common filler words
            "hal", "oleh", "terhadap", "seperti", "bahwa", "karena",
            "sehingga", "namun", "tetapi", "akan", "dapat", "bisa",
            "harus", "perlu", "serta", "atau", "maupun", "hingga",
        }
    
    def clean_text(self, text: str) -> str:
        """
        Bersihkan teks dari karakter tidak perlu
        
        Args:
            text: Teks mentah
            
        Returns:
            Teks yang sudah dibersihkan
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove special characters but keep Indonesian characters
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove numbers (optional - bisa dipertahankan untuk analisis harga)
        # text = re.sub(r'\d+', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenisasi teks menjadi list kata
        
        Args:
            text: Teks yang sudah dibersihkan
            
        Returns:
            List of tokens
        """
        if not text:
            return []
        
        # Simple whitespace tokenization
        tokens = text.split()
        
        # Filter tokens yang terlalu pendek
        tokens = [t for t in tokens if len(t) >= 2]
        
        return tokens
    
    def remove_stopwords_from_tokens(self, tokens: List[str]) -> List[str]:
        """
        Hapus stopwords dari list token
        
        Args:
            tokens: List of tokens
            
        Returns:
            List of tokens tanpa stopwords
        """
        if not self.remove_stopwords:
            return tokens
        
        return [t for t in tokens if t not in self.stopwords]
    
    def stem_tokens(self, tokens: List[str]) -> List[str]:
        """
        Stem tokens menggunakan Sastrawi
        
        Args:
            tokens: List of tokens
            
        Returns:
            List of stemmed tokens
        """
        if not self.use_stemming or not self.stemmer:
            return tokens
        
        return [self.stemmer.stem(t) for t in tokens]
    
    def preprocess(self, text: str) -> str:
        """
        Full preprocessing pipeline
        
        Args:
            text: Teks mentah
            
        Returns:
            Teks yang sudah diproses
        """
        # Clean
        text = self.clean_text(text)
        
        # Tokenize
        tokens = self.tokenize(text)
        
        # Remove stopwords
        tokens = self.remove_stopwords_from_tokens(tokens)
        
        # Stem
        tokens = self.stem_tokens(tokens)
        
        # Join back
        return " ".join(tokens)
    
    def preprocess_for_sentiment(self, text: str) -> str:
        """
        Preprocessing khusus untuk sentiment analysis
        (tanpa stemming untuk menjaga konteks)
        
        Args:
            text: Teks mentah
            
        Returns:
            Teks yang sudah diproses
        """
        # Clean
        text = self.clean_text(text)
        
        # Tokenize
        tokens = self.tokenize(text)
        
        # Remove only basic stopwords (keep sentiment-related words)
        basic_stopwords = {'yang', 'dan', 'di', 'ke', 'dari', 'ini', 'itu', 'untuk', 'dengan'}
        tokens = [t for t in tokens if t not in basic_stopwords]
        
        return " ".join(tokens)
    
    def extract_stock_mentions(self, text: str) -> List[str]:
        """
        Ekstrak kode saham yang disebutkan dalam teks
        
        Args:
            text: Teks berita
            
        Returns:
            List of stock codes found
        """
        # Pattern for Indonesian stock codes (4 uppercase letters)
        pattern = r'\b[A-Z]{4}\b'
        
        matches = re.findall(pattern, text.upper())
        
        # Filter out common words that might match
        exclude = {'YANG', 'DARI', 'AKAN', 'PADA', 'JUGA', 'ATAS', 'ATAU', 'BISA', 'KATA'}
        
        return [m for m in matches if m not in exclude]


# Singleton instance untuk efisiensi
_preprocessor_instance: Optional[TextPreprocessor] = None


def get_preprocessor(use_stemming: bool = True, remove_stopwords: bool = True) -> TextPreprocessor:
    """Get atau create TextPreprocessor instance"""
    global _preprocessor_instance
    
    if _preprocessor_instance is None:
        logger.info("Initializing TextPreprocessor...")
        _preprocessor_instance = TextPreprocessor(use_stemming, remove_stopwords)
        logger.info("TextPreprocessor initialized!")
    
    return _preprocessor_instance


if __name__ == "__main__":
    # Test preprocessor
    preprocessor = TextPreprocessor()
    
    sample_text = """
    JAKARTA, KONTAN - PT Bank Central Asia Tbk (BBCA) mencatatkan pertumbuhan laba bersih 
    yang signifikan pada kuartal III 2024. Saham BBCA menguat 2,5% ke level Rp 9.500 per lembar.
    Analis merekomendasikan BUY untuk saham perbankan ini.
    """
    
    print("Original:")
    print(sample_text)
    print("\nCleaned:")
    print(preprocessor.clean_text(sample_text))
    print("\nPreprocessed:")
    print(preprocessor.preprocess(sample_text))
    print("\nStock mentions:")
    print(preprocessor.extract_stock_mentions(sample_text))
