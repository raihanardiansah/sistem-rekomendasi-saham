"""
Sentiment Analyzer - Analisis sentimen berita Bahasa Indonesia
"""

import re
from typing import Dict, List, Tuple, Optional
import logging

from app.nlp.preprocessor import get_preprocessor

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Sentiment Analyzer untuk berita saham Bahasa Indonesia
    Menggunakan pendekatan lexicon-based dengan kata-kata khusus domain finansial
    """
    
    def __init__(self):
        """Initialize sentiment analyzer dengan lexicon"""
        self.preprocessor = get_preprocessor(use_stemming=False, remove_stopwords=False)
        
        # Lexicon positif untuk domain finansial/saham
        self.positive_words = self._build_positive_lexicon()
        
        # Lexicon negatif untuk domain finansial/saham
        self.negative_words = self._build_negative_lexicon()
        
        # Intensifier words (penguat)
        self.intensifiers = {
            'sangat': 1.5, 'amat': 1.5, 'sekali': 1.3, 'begitu': 1.3,
            'paling': 1.5, 'ter': 1.3, 'sungguh': 1.4, 'benar': 1.3,
            'lumayan': 1.2, 'cukup': 1.1, 'agak': 0.8, 'sedikit': 0.7,
            'kurang': 0.6, 'hampir': 0.9, 'nyaris': 0.9
        }
        
        # Negation words (pembalik)
        self.negations = {
            'tidak', 'bukan', 'belum', 'tanpa', 'jangan', 'tak', 'tiada',
            'enggan', 'gagal', 'mustahil', 'tidak ada'
        }
    
    def _build_positive_lexicon(self) -> Dict[str, float]:
        """Bangun lexicon kata positif dengan skor"""
        return {
            # Strong positive (1.0)
            'untung': 1.0, 'laba': 1.0, 'profit': 1.0, 'surplus': 1.0,
            'melonjak': 1.0, 'meroket': 1.0, 'melejit': 1.0, 'melesat': 1.0,
            'rekor': 1.0, 'tertinggi': 1.0, 'terbaik': 1.0, 'optimal': 1.0,
            'sukses': 1.0, 'berhasil': 1.0, 'prestasi': 1.0, 'keberhasilan': 1.0,
            
            # Moderate positive (0.7)
            'naik': 0.7, 'meningkat': 0.7, 'tumbuh': 0.7, 'berkembang': 0.7,
            'menguat': 0.7, 'positif': 0.7, 'optimis': 0.7, 'prospek': 0.7,
            'potensi': 0.7, 'peluang': 0.7, 'ekspansi': 0.7, 'investasi': 0.6,
            'dividen': 0.7, 'bonus': 0.7, 'akuisisi': 0.6, 'merger': 0.5,
            
            # Mild positive (0.5)
            'stabil': 0.5, 'solid': 0.5, 'konsisten': 0.5, 'bagus': 0.5,
            'baik': 0.5, 'mendukung': 0.5, 'apresiasi': 0.5, 'pulih': 0.5,
            'recovery': 0.5, 'rebound': 0.6, 'breakout': 0.6, 'rally': 0.7,
            
            # Recommendation words
            'beli': 0.8, 'buy': 0.8, 'accumulate': 0.7, 'akumulasi': 0.7,
            'overweight': 0.6, 'outperform': 0.7, 'rekomen': 0.5,
            
            # Technical positive
            'support': 0.4, 'bullish': 0.8, 'uptrend': 0.7, 'golden cross': 0.8,
        }
    
    def _build_negative_lexicon(self) -> Dict[str, float]:
        """Bangun lexicon kata negatif dengan skor"""
        return {
            # Strong negative (-1.0)
            'rugi': -1.0, 'kerugian': -1.0, 'loss': -1.0, 'defisit': -1.0,
            'anjlok': -1.0, 'ambruk': -1.0, 'jatuh': -0.9, 'terjun': -0.9,
            'kolaps': -1.0, 'bangkrut': -1.0, 'pailit': -1.0, 'gagal': -0.9,
            'terburuk': -1.0, 'terendah': -0.9, 'krisis': -1.0, 'resesi': -1.0,
            
            # Moderate negative (-0.7)
            'turun': -0.7, 'menurun': -0.7, 'melemah': -0.7, 'merosot': -0.7,
            'susut': -0.7, 'negatif': -0.7, 'pesimis': -0.7, 'khawatir': -0.6,
            'risiko': -0.5, 'ancaman': -0.7, 'tekanan': -0.6, 'beban': -0.5,
            'hutang': -0.5, 'utang': -0.5, 'koreksi': -0.5, 'pelemahan': -0.6,
            
            # Mild negative (-0.5)
            'lambat': -0.4, 'stagnan': -0.5, 'flat': -0.3, 'tertahan': -0.4,
            'terbatas': -0.3, 'tantangan': -0.4, 'kendala': -0.5, 'hambatan': -0.5,
            'volatil': -0.4, 'fluktuatif': -0.3, 'tidak pasti': -0.5,
            
            # Recommendation words
            'jual': -0.8, 'sell': -0.8, 'reduce': -0.7, 'kurangi': -0.6,
            'underweight': -0.6, 'underperform': -0.7, 'hindari': -0.7,
            
            # Technical negative
            'resistance': -0.3, 'bearish': -0.8, 'downtrend': -0.7, 'death cross': -0.8,
            'breakdown': -0.6, 'overbought': -0.4, 'oversold': -0.3,
            
            # Event negative
            'fraud': -1.0, 'korupsi': -1.0, 'manipulasi': -0.9, 'skandal': -0.9,
            'investigasi': -0.6, 'gugatan': -0.7, 'sengketa': -0.6,
        }
    
    def analyze(self, text: str) -> Dict:
        """
        Analisis sentimen teks
        
        Args:
            text: Teks berita
            
        Returns:
            Dict dengan sentiment_score, sentiment_label, dan detail
        """
        if not text:
            return {
                'sentiment_score': 0.0,
                'sentiment_label': 'netral',
                'confidence': 0.0,
                'positive_words': [],
                'negative_words': [],
                'details': {}
            }
        
        # Preprocess text
        cleaned_text = self.preprocessor.clean_text(text)
        tokens = cleaned_text.split()
        
        positive_found = []
        negative_found = []
        total_score = 0.0
        word_count = 0
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            # Check for negation in previous words
            has_negation = False
            if i > 0 and tokens[i-1] in self.negations:
                has_negation = True
            
            # Check for intensifier in previous words
            intensifier = 1.0
            if i > 0 and tokens[i-1] in self.intensifiers:
                intensifier = self.intensifiers[tokens[i-1]]
            
            # Check positive words
            if token in self.positive_words:
                score = self.positive_words[token] * intensifier
                if has_negation:
                    score = -score * 0.5  # Negation flips and reduces
                    negative_found.append((token, score))
                else:
                    positive_found.append((token, score))
                total_score += score
                word_count += 1
            
            # Check negative words
            elif token in self.negative_words:
                score = self.negative_words[token] * intensifier
                if has_negation:
                    score = -score * 0.5  # Negation flips and reduces
                    positive_found.append((token, abs(score)))
                else:
                    negative_found.append((token, score))
                total_score += score
                word_count += 1
            
            # Check for bigrams (two-word phrases)
            if i < len(tokens) - 1:
                bigram = f"{token} {tokens[i+1]}"
                if bigram in self.positive_words:
                    score = self.positive_words[bigram]
                    positive_found.append((bigram, score))
                    total_score += score
                    word_count += 1
                elif bigram in self.negative_words:
                    score = self.negative_words[bigram]
                    negative_found.append((bigram, score))
                    total_score += score
                    word_count += 1
            
            i += 1
        
        # Calculate final score (normalized to -1 to 1)
        if word_count > 0:
            avg_score = total_score / word_count
            # Normalize dengan tanh untuk range -1 to 1
            import math
            sentiment_score = math.tanh(avg_score)
        else:
            sentiment_score = 0.0
        
        # Determine label
        if sentiment_score > 0.2:
            sentiment_label = 'positif'
        elif sentiment_score < -0.2:
            sentiment_label = 'negatif'
        else:
            sentiment_label = 'netral'
        
        # Calculate confidence based on word count and score magnitude
        confidence = min(1.0, (word_count / 10) * abs(sentiment_score) + 0.3) if word_count > 0 else 0.0
        
        return {
            'sentiment_score': round(sentiment_score, 4),
            'sentiment_label': sentiment_label,
            'confidence': round(confidence, 4),
            'positive_words': positive_found,
            'negative_words': negative_found,
            'details': {
                'total_sentiment_words': word_count,
                'raw_score': round(total_score, 4),
                'text_length': len(tokens)
            }
        }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        Analisis sentimen untuk multiple texts
        
        Args:
            texts: List of texts
            
        Returns:
            List of sentiment results
        """
        return [self.analyze(text) for text in texts]
    
    def get_sentiment_summary(self, results: List[Dict]) -> Dict:
        """
        Buat ringkasan dari multiple sentiment results
        
        Args:
            results: List of sentiment analysis results
            
        Returns:
            Summary statistics
        """
        if not results:
            return {
                'avg_score': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'total': 0
            }
        
        scores = [r['sentiment_score'] for r in results]
        labels = [r['sentiment_label'] for r in results]
        
        return {
            'avg_score': round(sum(scores) / len(scores), 4),
            'positive_count': labels.count('positif'),
            'negative_count': labels.count('negatif'),
            'neutral_count': labels.count('netral'),
            'total': len(results),
            'min_score': round(min(scores), 4),
            'max_score': round(max(scores), 4)
        }


# Singleton instance
_analyzer_instance: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get atau create SentimentAnalyzer instance"""
    global _analyzer_instance
    
    if _analyzer_instance is None:
        logger.info("Initializing SentimentAnalyzer...")
        _analyzer_instance = SentimentAnalyzer()
        logger.info("SentimentAnalyzer initialized!")
    
    return _analyzer_instance


if __name__ == "__main__":
    # Test sentiment analyzer
    analyzer = SentimentAnalyzer()
    
    test_texts = [
        "BBCA mencatatkan laba bersih yang melonjak signifikan, saham menguat ke level tertinggi",
        "Saham GOTO anjlok setelah laporan keuangan menunjukkan kerugian yang membengkak",
        "TLKM melaporkan pendapatan stabil di kuartal ini, analis merekomendasikan hold",
        "Tidak ada pertumbuhan yang signifikan untuk sektor perbankan bulan ini",
        "Meski ada tekanan, BMRI berhasil membukukan laba yang sangat positif"
    ]
    
    print("=" * 60)
    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\nText: {text[:60]}...")
        print(f"Score: {result['sentiment_score']:.4f}")
        print(f"Label: {result['sentiment_label']}")
        print(f"Confidence: {result['confidence']:.4f}")
        print(f"Positive: {result['positive_words']}")
        print(f"Negative: {result['negative_words']}")
        print("-" * 40)
